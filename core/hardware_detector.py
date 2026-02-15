# core/hardware_detector.py

import platform
import subprocess
import psutil
import torch
import yaml
import os
from typing import Dict, Optional

class HardwareDetector:
    """
    Detecta automáticamente el hardware y recomienda configuración óptima.
    Soporta: MacBook Pro (Intel/Apple Silicon), PCs con NVIDIA, Cloud GPUs
    """
    
    def __init__(self):
        self.profile = self.detect_hardware()
        self.recommendations = self._generate_recommendations()
        
    def detect_hardware(self) -> Dict:
        """Detecta especificaciones completas del sistema"""
        
        profile = {
            'os': platform.system(),
            'os_version': platform.version(),
            'platform': platform.platform(),
            'cpu': self._get_cpu_info(),
            'ram_gb': psutil.virtual_memory().total / (1024**3),
            'gpu': self._get_gpu_info(),
            'is_cloud': self._detect_cloud_environment()
        }
        
        # Categorizar hardware
        profile['category'] = self._categorize_hardware(profile)
        profile['tier'] = self._get_performance_tier(profile['category'])
        profile['recommended_settings'] = self._get_recommended_settings(profile['category'])
        profile['warnings'] = self._get_warnings(profile)
        
        return profile
    
    def _get_cpu_info(self) -> Dict:
        """Detecta información detallada del CPU"""
        cpu_info = {
            'name': 'Unknown',
            'type': 'unknown',
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True),
            'architecture': platform.machine(),
            'supports_required_instructions': False
        }
        
        try:
            if platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True,
                    text=True
                )
                cpu_name = result.stdout.strip()
                cpu_info['name'] = cpu_name
                
                # Detectar tipo de Mac
                if any(chip in cpu_name for chip in ['M1', 'M2', 'M3', 'M4']):
                    cpu_info['type'] = 'apple_silicon'
                    cpu_info['supports_required_instructions'] = True
                    
                    # Detectar variante (Pro, Max, Ultra)
                    if 'Max' in cpu_name:
                        cpu_info['variant'] = 'max'
                    elif 'Ultra' in cpu_name:
                        cpu_info['variant'] = 'ultra'
                    elif 'Pro' in cpu_name:
                        cpu_info['variant'] = 'pro'
                    else:
                        cpu_info['variant'] = 'base'
                        
                elif 'Intel' in cpu_name:
                    cpu_info['type'] = 'intel_mac'
                    
                    # Verificar instrucciones requeridas
                    features = subprocess.run(
                        ['sysctl', '-n', 'machdep.cpu.features'],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    
                    has_ssse3 = 'SSSE3' in features
                    has_sse42 = 'SSE4.2' in features
                    cpu_info['supports_required_instructions'] = has_ssse3 and has_sse42
                    
                    # Detectar generación de Intel Mac
                    if 'Core 2' in cpu_name:
                        cpu_info['generation'] = 'core2'  # 2006-2010
                    elif any(gen in cpu_name for gen in ['i3', 'i5', 'i7', 'i9']):
                        # Extraer generación (e.g., "i7-4770" -> generación 4)
                        try:
                            gen_num = int(cpu_name.split('-')[1][0])
                            cpu_info['generation'] = f'core_i_gen{gen_num}'
                        except:
                            cpu_info['generation'] = 'core_i_unknown'
                            
            elif platform.system() == "Linux":
                # Detectar en Linux/Cloud
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    if 'model name' in cpuinfo:
                        cpu_info['name'] = cpuinfo.split('model name')[1].split(':')[1].split('\n')[0].strip()
                
                cpu_info['type'] = 'linux_x86'
                cpu_info['supports_required_instructions'] = True  # Asumimos cloud moderno
                
            elif platform.system() == "Windows":
                # Windows
                cpu_info['name'] = platform.processor()
                cpu_info['type'] = 'windows_x86'
                cpu_info['supports_required_instructions'] = True  # Asumimos moderno
                
        except Exception as e:
            print(f"⚠️  Advertencia detectando CPU: {e}")
        
        return cpu_info
    
    def _get_gpu_info(self) -> Dict:
        """Detecta GPU disponible"""
        gpu_info = {
            'available': False,
            'name': None,
            'type': None,
            'memory_gb': 0,
            'count': 0,
            'compute_capability': None
        }
        
        # NVIDIA CUDA
        if torch.cuda.is_available():
            gpu_info['available'] = True
            gpu_info['type'] = 'nvidia_cuda'
            gpu_info['count'] = torch.cuda.device_count()
            gpu_info['name'] = torch.cuda.get_device_name(0)
            gpu_info['memory_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            
            # Compute capability (importante para compatibilidad)
            props = torch.cuda.get_device_properties(0)
            gpu_info['compute_capability'] = f"{props.major}.{props.minor}"
            
        # Apple MPS (Metal Performance Shaders)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_info['available'] = True
            gpu_info['type'] = 'apple_mps'
            gpu_info['name'] = 'Apple GPU (Metal)'
            gpu_info['memory_gb'] = psutil.virtual_memory().total / (1024**3)  # Unified memory
            gpu_info['count'] = 1
        
        return gpu_info
    
    def _detect_cloud_environment(self) -> Dict:
        """Detecta si está en entorno cloud"""
        cloud_info = {
            'is_cloud': False,
            'provider': None,
            'instance_type': None
        }
        
        # AWS
        if os.path.exists('/sys/hypervisor/uuid'):
            try:
                with open('/sys/hypervisor/uuid', 'r') as f:
                    if f.read().startswith('ec2'):
                        cloud_info['is_cloud'] = True
                        cloud_info['provider'] = 'aws'
            except:
                pass
        
        # Google Cloud
        try:
            result = subprocess.run(
                ['curl', '-s', '-H', 'Metadata-Flavor: Google', 
                 'http://metadata.google.internal/computeMetadata/v1/instance/machine-type'],
                capture_output=True,
                timeout=1
            )
            if result.returncode == 0:
                cloud_info['is_cloud'] = True
                cloud_info['provider'] = 'gcp'
                cloud_info['instance_type'] = result.stdout.decode().strip()
        except:
            pass
        
        # Azure
        if os.path.exists('/var/lib/waagent'):
            cloud_info['is_cloud'] = True
            cloud_info['provider'] = 'azure'
        
        return cloud_info
    
    def _categorize_hardware(self, profile: Dict) -> str:
        """Categoriza el hardware en niveles de rendimiento"""
        
        cpu = profile['cpu']
        gpu = profile['gpu']
        cloud = profile['is_cloud']
        
        # Cloud con GPU
        if cloud['is_cloud'] and gpu['available']:
            if gpu['type'] == 'nvidia_cuda':
                if gpu['memory_gb'] >= 16:
                    return 'cloud_gpu_high'  # A100, V100
                elif gpu['memory_gb'] >= 8:
                    return 'cloud_gpu_mid'   # T4, P100
                else:
                    return 'cloud_gpu_low'   # K80
        
        # NVIDIA GPU local (PC gaming/workstation)
        if gpu['available'] and gpu['type'] == 'nvidia_cuda':
            if gpu['memory_gb'] >= 16:
                return 'nvidia_gpu_high'  # RTX 4090, 3090, A5000
            elif gpu['memory_gb'] >= 8:
                return 'nvidia_gpu_mid'   # RTX 4070, 3070, 2080
            elif gpu['memory_gb'] >= 4:
                return 'nvidia_gpu_low'   # RTX 3060, 2060, 1660
            else:
                return 'nvidia_gpu_legacy'  # GTX 1050, 960
        
        # Apple Silicon
        if cpu['type'] == 'apple_silicon':
            variant = cpu.get('variant', 'base')
            ram = profile['ram_gb']
            
            if variant == 'ultra' or (variant == 'max' and ram >= 64):
                return 'apple_silicon_ultra'  # M1/M2/M3 Ultra, M Max 64GB+
            elif variant == 'max' or ram >= 32:
                return 'apple_silicon_max'    # M Max, M Pro 32GB+
            elif variant == 'pro' or ram >= 16:
                return 'apple_silicon_pro'    # M Pro, M base 16GB+
            else:
                return 'apple_silicon_base'   # M base 8GB
        
        # Intel Mac
        if cpu['type'] == 'intel_mac':
            if not cpu['supports_required_instructions']:
                return 'legacy_mac_incompatible'  # Core 2 Duo, etc.
            
            generation = cpu.get('generation', '')
            
            if 'gen' in generation:
                gen_num = int(generation.split('gen')[1])
                if gen_num >= 8:  # 8th gen+ (2017+)
                    return 'intel_mac_modern'
                elif gen_num >= 4:  # 4th-7th gen (2013-2017)
                    return 'intel_mac_capable'
                else:
                    return 'intel_mac_old'
            else:
                return 'intel_mac_capable'
        
        # Linux/Windows CPU-only
        if cpu['supports_required_instructions']:
            if profile['ram_gb'] >= 32:
                return 'cpu_only_high'
            elif profile['ram_gb'] >= 16:
                return 'cpu_only_mid'
            else:
                return 'cpu_only_low'
        
        # Fallback incompatible
        return 'incompatible'
    
    def _get_performance_tier(self, category: str) -> str:
        """Asigna tier de rendimiento (S, A, B, C, D, F)"""
        tiers = {
            # S Tier - Professional/Enterprise
            'cloud_gpu_high': 'S',
            'nvidia_gpu_high': 'S',
            'apple_silicon_ultra': 'S',
            
            # A Tier - High-end consumer
            'cloud_gpu_mid': 'A',
            'nvidia_gpu_mid': 'A',
            'apple_silicon_max': 'A',
            
            # B Tier - Mid-range
            'nvidia_gpu_low': 'B',
            'apple_silicon_pro': 'B',
            'intel_mac_modern': 'B',
            
            # C Tier - Entry level
            'nvidia_gpu_legacy': 'C',
            'apple_silicon_base': 'C',
            'intel_mac_capable': 'C',
            'cpu_only_high': 'C',
            
            # D Tier - Minimal
            'cloud_gpu_low': 'D',
            'intel_mac_old': 'D',
            'cpu_only_mid': 'D',
            
            # F Tier - Incompatible
            'cpu_only_low': 'F',
            'legacy_mac_incompatible': 'F',
            'incompatible': 'F'
        }
        return tiers.get(category, 'F')
    
    def _get_recommended_settings(self, category: str) -> Dict:
        """Configuración recomendada según categoría de hardware"""
        
        settings_map = {
            # S Tier - Professional
            'cloud_gpu_high': {
                'device': 'cuda',
                'resolution': 1024,
                'steps': 50,
                'batch_size': 8,
                'precision': 'fp16',
                'enable_xformers': True,
                'enable_attention_slicing': False,
                'enable_vae_slicing': False,
                'cpu_offload': False,
                'estimated_time_per_render': '30-60 seconds',
                'max_recommended_resolution': 2048
            },
            'nvidia_gpu_high': {
                'device': 'cuda',
                'resolution': 1024,
                'steps': 40,
                'batch_size': 4,
                'precision': 'fp16',
                'enable_xformers': True,
                'enable_attention_slicing': False,
                'enable_vae_slicing': False,
                'cpu_offload': False,
                'estimated_time_per_render': '1-2 min',
                'max_recommended_resolution': 1536
            },
            'apple_silicon_ultra': {
                'device': 'mps',
                'resolution': 1024,
                'steps': 35,
                'batch_size': 4,
                'precision': 'fp16',
                'enable_attention_slicing': False,
                'enable_vae_slicing': False,
                'cpu_offload': False,
                'estimated_time_per_render': '1-3 min',
                'max_recommended_resolution': 1536
            },
            
            # A Tier - High-end
            'cloud_gpu_mid': {
                'device': 'cuda',
                'resolution': 768,
                'steps': 30,
                'batch_size': 2,
                'precision': 'fp16',
                'enable_xformers': True,
                'enable_attention_slicing': True,
                'enable_vae_slicing': False,
                'cpu_offload': False,
                'estimated_time_per_render': '2-4 min',
                'max_recommended_resolution': 1024
            },
            'nvidia_gpu_mid': {
                'device': 'cuda',
                'resolution': 768,
                'steps': 30,
                'batch_size': 2,
                'precision': 'fp16',
                'enable_xformers': True,
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '2-5 min',
                'max_recommended_resolution': 1024
            },
            'apple_silicon_max': {
                'device': 'mps',
                'resolution': 768,
                'steps': 30,
                'batch_size': 2,
                'precision': 'fp16',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '3-6 min',
                'max_recommended_resolution': 1024
            },
            
            # B Tier - Mid-range
            'nvidia_gpu_low': {
                'device': 'cuda',
                'resolution': 512,
                'steps': 25,
                'batch_size': 1,
                'precision': 'fp16',
                'enable_xformers': True,
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '4-8 min',
                'max_recommended_resolution': 768
            },
            'apple_silicon_pro': {
                'device': 'mps',
                'resolution': 512,
                'steps': 25,
                'batch_size': 1,
                'precision': 'fp16',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '5-10 min',
                'max_recommended_resolution': 768
            },
            'intel_mac_modern': {
                'device': 'cpu',
                'resolution': 512,
                'steps': 20,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '8-15 min',
                'max_recommended_resolution': 512
            },
            
            # C Tier - Entry
            'nvidia_gpu_legacy': {
                'device': 'cuda',
                'resolution': 384,
                'steps': 20,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': True,
                'estimated_time_per_render': '8-12 min',
                'max_recommended_resolution': 512
            },
            'apple_silicon_base': {
                'device': 'mps',
                'resolution': 512,
                'steps': 20,
                'batch_size': 1,
                'precision': 'fp16',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': True,
                'estimated_time_per_render': '7-12 min',
                'max_recommended_resolution': 768
            },
            'intel_mac_capable': {
                'device': 'cpu',
                'resolution': 384,
                'steps': 15,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '10-18 min',
                'max_recommended_resolution': 512
            },
            'cpu_only_high': {
                'device': 'cpu',
                'resolution': 512,
                'steps': 20,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '10-20 min',
                'max_recommended_resolution': 768
            },
            
            # D Tier - Minimal
            'cloud_gpu_low': {
                'device': 'cuda',
                'resolution': 384,
                'steps': 15,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': True,
                'estimated_time_per_render': '6-10 min',
                'max_recommended_resolution': 512
            },
            'intel_mac_old': {
                'device': 'cpu',
                'resolution': 384,
                'steps': 12,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '12-20 min',
                'max_recommended_resolution': 384
            },
            'cpu_only_mid': {
                'device': 'cpu',
                'resolution': 384,
                'steps': 12,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '15-25 min',
                'max_recommended_resolution': 384
            },
            
            # F Tier - Incompatible (valores mínimos para documentación)
            'legacy_mac_incompatible': {
                'device': 'cpu',
                'resolution': 256,
                'steps': 10,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': 'N/A - Incompatible',
                'max_recommended_resolution': 0,
                'warning': 'Hardware incompatible - requiere CPU con SSSE3/SSE4.2'
            },
            'cpu_only_low': {
                'device': 'cpu',
                'resolution': 256,
                'steps': 10,
                'batch_size': 1,
                'precision': 'fp32',
                'enable_attention_slicing': True,
                'enable_vae_slicing': True,
                'cpu_offload': False,
                'estimated_time_per_render': '20-40 min',
                'max_recommended_resolution': 256
            },
            'incompatible': {
                'device': 'cpu',
                'resolution': 0,
                'steps': 0,
                'batch_size': 0,
                'precision': 'fp32',
                'estimated_time_per_render': 'N/A',
                'max_recommended_resolution': 0,
                'warning': 'Hardware no soportado'
            }
        }
        
        return settings_map.get(category, settings_map['incompatible'])
    
    def _get_warnings(self, profile: Dict) -> list:
        """Genera advertencias basadas en el hardware detectado"""
        warnings = []
        
        cpu = profile['cpu']
        gpu = profile['gpu']
        tier = self._get_performance_tier(profile['category'])
        
        # Advertencia crítica: Hardware incompatible
        if tier == 'F':
            if not cpu['supports_required_instructions']:
                warnings.append({
                    'level': 'critical',
                    'message': f"CPU incompatible: {cpu['name']} no soporta instrucciones SSSE3/SSE4.2 requeridas por PyTorch moderno.",
                    'suggestion': 'Considera usar arquitectura cliente-servidor o migrar a hardware más reciente (post-2010).'
                })
            else:
                warnings.append({
                    'level': 'critical',
                    'message': 'Hardware detectado como incompatible.',
                    'suggestion': 'Verifica requisitos mínimos del sistema.'
                })
        
        # Advertencia: RAM baja
        if profile['ram_gb'] < 8:
            warnings.append({
                'level': 'warning',
                'message': f"RAM insuficiente: {profile['ram_gb']:.1f} GB (recomendado: 16 GB+)",
                'suggestion': 'Cierra otras aplicaciones durante la generación. Considera actualizar RAM.'
            })
        elif profile['ram_gb'] < 16 and tier in ['A', 'B']:
            warnings.append({
                'level': 'info',
                'message': f"RAM limitada: {profile['ram_gb']:.1f} GB. Rendimiento óptimo con 16 GB+",
                'suggestion': 'Reduce batch_size o resolución si encuentras errores de memoria.'
            })
        
        # Advertencia: GPU sin xformers
        if gpu['available'] and gpu['type'] == 'nvidia_cuda':
            warnings.append({
                'level': 'info',
                'message': 'Instala xformers para acelerar generación hasta 30%',
                'suggestion': 'pip install xformers==0.0.22'
            })
        
        # Info: Tier bajo
        if tier in ['C', 'D']:
            warnings.append({
                'level': 'info',
                'message': f'Hardware detectado como tier {tier} - tiempos de generación más largos',
                'suggestion': 'Usa resoluciones bajas (384-512px) y pocos pasos (12-20) para mejor experiencia.'
            })
        
        return warnings
    
    def _generate_recommendations(self) -> Dict:
        """Genera recomendaciones de uso según hardware"""
        tier = self.profile['tier']
        settings = self.profile['recommended_settings']
        
        recommendations = {
            'workflow': None,
            'tips': [],
            'optimizations': []
        }
        
        if tier == 'S':
            recommendations['workflow'] = 'production_high_quality'
            recommendations['tips'] = [
                'Puedes usar resoluciones altas (1024px+) sin problemas',
                'Batch processing recomendado (4-8 imágenes simultáneas)',
                'Experimenta con pasos altos (40-50) para máxima calidad'
            ]
        elif tier == 'A':
            recommendations['workflow'] = 'production_balanced'
            recommendations['tips'] = [
                'Resolución 768px es óptima para tu hardware',
                'Batch de 2 imágenes para aprovechar GPU',
                '30 pasos ofrecen excelente balance calidad/velocidad'
            ]
        elif tier == 'B':
            recommendations['workflow'] = 'development_iteration'
            recommendations['tips'] = [
                'Usa 512px durante iteración, 768px para renders finales',
                'Procesa de noche o batch pequeños',
                '20-25 pasos son suficientes para buenos resultados'
            ]
        elif tier == 'C':
            recommendations['workflow'] = 'mvp_testing'
            recommendations['tips'] = [
                'Mantén resolución en 384-512px',
                'Procesa renders importantes de noche',
                '15-20 pasos balance aceptable'
            ]
        elif tier == 'D':
            recommendations['workflow'] = 'minimal_viable'
            recommendations['tips'] = [
                'Usa 384px máximo',
                'Deja procesando de noche o fin de semana',
                'Genera pocas variaciones, elige la mejor'
            ]
        else:  # F
            recommendations['workflow'] = 'incompatible'
            recommendations['tips'] = [
                'Hardware no compatible con este proyecto',
                'Considera arquitectura cliente-servidor',
                'O migrar a equipo más moderno'
            ]
        
        return recommendations
    
    def print_summary(self):
        """Imprime resumen detallado del hardware detectado"""
        p = self.profile
        
        print("\n" + "="*70)
        print("🖥️  DETECCIÓN DE HARDWARE - Interior AI Render")
        print("="*70)
        
        # Sistema operativo
        print(f"\n📱 Sistema Operativo:")
        print(f"   {p['os']} - {p['platform']}")
        
        # CPU
        print(f"\n💻 CPU:")
        print(f"   Modelo: {p['cpu']['name']}")
        print(f"   Tipo: {p['cpu']['type']}")
        print(f"   Cores: {p['cpu']['cores']} físicos / {p['cpu']['threads']} threads")
        print(f"   Arquitectura: {p['cpu']['architecture']}")
        
        if p['cpu']['supports_required_instructions']:
            print(f"   ✅ Soporta instrucciones requeridas (SSSE3/SSE4.2)")
        else:
            print(f"   ❌ NO soporta instrucciones requeridas (SSSE3/SSE4.2)")
        
        # RAM
        print(f"\n🧠 RAM:")
        print(f"   Total: {p['ram_gb']:.1f} GB")
        if p['ram_gb'] >= 32:
            print(f"   ✅ Excelente para procesamiento de IA")
        elif p['ram_gb'] >= 16:
            print(f"   ✅ Suficiente para la mayoría de tareas")
        elif p['ram_gb'] >= 8:
            print(f"   ⚠️  Suficiente para resoluciones bajas")
        else:
            print(f"   ❌ Insuficiente (recomendado 16 GB+)")
        
        # GPU
        print(f"\n🎮 GPU:")
        if p['gpu']['available']:
            print(f"   ✅ Disponible: {p['gpu']['name']}")
            print(f"   Tipo: {p['gpu']['type']}")
            print(f"   Memoria: {p['gpu']['memory_gb']:.1f} GB")
            if p['gpu']['type'] == 'nvidia_cuda':
                print(f"   Compute Capability: {p['gpu']['compute_capability']}")
            print(f"   Dispositivos: {p['gpu']['count']}")
        else:
            print(f"   ❌ No disponible - usando CPU")
        
        # Cloud
        if p['is_cloud']['is_cloud']:
            print(f"\n☁️  Entorno Cloud:")
            print(f"   Proveedor: {p['is_cloud']['provider'].upper()}")
            if p['is_cloud']['instance_type']:
                print(f"   Tipo: {p['is_cloud']['instance_type']}")
        
        # Categoría y Tier
        print(f"\n⚙️  Categoría de Hardware:")
        print(f"   Clasificación: {p['category']}")
        print(f"   Tier de Rendimiento: {p['tier']}")
        
        # Configuración recomendada
        print(f"\n📊 CONFIGURACIÓN RECOMENDADA:")
        s = p['recommended_settings']
        print(f"   Dispositivo: {s['device'].upper()}")
        print(f"   Resolución: {s['resolution']}px")
        print(f"   Pasos: {s['steps']}")
        print(f"   Batch size: {s['batch_size']}")
        print(f"   Precisión: {s['precision'].upper()}")
        print(f"   Tiempo estimado: {s['estimated_time_per_render']}")
        print(f"   Resolución máxima recomendada: {s['max_recommended_resolution']}px")
        
        # Advertencias
        if p['warnings']:
            print(f"\n⚠️  ADVERTENCIAS:")
            for w in p['warnings']:
                icon = {'critical': '🔴', 'warning': '⚠️ ', 'info': 'ℹ️ '}[w['level']]
                print(f"   {icon} {w['message']}")
                print(f"      → {w['suggestion']}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        for tip in self.recommendations['tips']:
            print(f"   • {tip}")
        
        print("\n" + "="*70 + "\n")
    
    def save_profile(self, path='config/hardware_profile.yaml'):
        """Guarda el perfil detectado"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Preparar datos para guardar (convertir a tipos serializables)
        profile_to_save = {
            'detection_date': datetime.now().isoformat(),
            'os': self.profile['os'],
            'platform': self.profile['platform'],
            'cpu': self.profile['cpu'],
            'ram_gb': float(self.profile['ram_gb']),
            'gpu': self.profile['gpu'],
            'is_cloud': self.profile['is_cloud'],
            'category': self.profile['category'],
            'tier': self.profile['tier'],
            'recommended_settings': self.profile['recommended_settings'],
            'warnings': self.profile['warnings'],
            'recommendations': self.recommendations
        }
        
        with open(path, 'w') as f:
            yaml.dump(profile_to_save, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Perfil de hardware guardado en: {path}")
    
    def is_compatible(self) -> bool:
        """Verifica si el hardware es compatible"""
        return self.profile['tier'] != 'F'
    
    def get_user_adjustable_ranges(self) -> Dict:
        """Retorna rangos ajustables para el usuario"""
        s = self.profile['recommended_settings']
        tier = self.profile['tier']
        
        if tier == 'F':
            return {
                'resolution': {'min': 0, 'max': 0, 'recommended': 0},
                'steps': {'min': 0, 'max': 0, 'recommended': 0},
                'message': 'Hardware incompatible'
            }
        
        # Rangos por tier
        ranges = {
            'S': {'res_min': 512, 'res_max': 2048, 'steps_min': 20, 'steps_max': 100},
            'A': {'res_min': 384, 'res_max': 1536, 'steps_min': 15, 'steps_max': 75},
            'B': {'res_min': 256, 'res_max': 1024, 'steps_min': 12, 'steps_max': 50},
            'C': {'res_min': 256, 'res_max': 768, 'steps_min': 10, 'steps_max': 40},
            'D': {'res_min': 128, 'res_max': 512, 'steps_min': 8, 'steps_max': 30}
        }
        
        r = ranges.get(tier, ranges['D'])
        
        return {
            'resolution': {
                'min': r['res_min'],
                'max': r['res_max'],
                'recommended': s['resolution'],
                'step': 128
            },
            'steps': {
                'min': r['steps_min'],
                'max': r['steps_max'],
                'recommended': s['steps'],
                'step': 1
            },
            'guidance_scale': {
                'min': 5.0,
                'max': 15.0,
                'recommended': 7.0,
                'step': 0.5
            },
            'control_strength': {
                'min': 0.5,
                'max': 1.0,
                'recommended': 0.85,
                'step': 0.05
            }
        }


if __name__ == "__main__":
    from datetime import datetime
    
    detector = HardwareDetector()
    detector.print_summary()
    detector.save_profile()
    
    print("\n🎯 Compatibilidad:", "✅ COMPATIBLE" if detector.is_compatible() else "❌ INCOMPATIBLE")
    
    if detector.is_compatible():
        print("\n📐 Rangos ajustables para usuario:")
        ranges = detector.get_user_adjustable_ranges()
        for param, config in ranges.items():
            if isinstance(config, dict) and 'min' in config:
                print(f"   {param}:")
                print(f"      Rango: {config['min']} - {config['max']}")
                print(f"      Recomendado: {config['recommended']}")