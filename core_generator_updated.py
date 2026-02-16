"""
Motor de generación de renders con sistema de carpetas organizadas
"""

import torch
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, DDIMScheduler
from PIL import Image
import numpy as np
from datetime import datetime
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI

# Importar detector de bordes
try:
    from core.edge_detectors import HybridEdgeDetector
    print("✓ Usando HybridEdgeDetector (scikit-image + Sobel)")
except ImportError:
    from core.canny_simple import CannyDetector as HybridEdgeDetector
    print("✓ Usando CannyDetector simple (fallback)")

from core.lighting_controller import LightingController


class RenderGenerator:
    """
    Generador de renders fotorrealistas con organización automática de proyectos
    """
    
    def __init__(self, hardware_profile):
        """
        Inicializa el generador
        
        Args:
            hardware_profile: Perfil de hardware del HardwareDetector
        """
        self.hardware_profile = hardware_profile
        self.device = hardware_profile['recommended_settings']['device']
        self.precision = hardware_profile['recommended_settings']['precision']
        
        self.pipe = None
        self.edge_detector = HybridEdgeDetector()
        self.lighting_controller = LightingController()
        
    def load_models(self):
        """Carga los modelos de IA"""
        print("📥 Cargando modelos de IA...")
        
        # Modelo ControlNet
        controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/control_v11p_sd15_canny",
            torch_dtype=torch.float16 if self.precision == 'fp16' else torch.float32
        )
        
        # Pipeline Stable Diffusion + ControlNet
        self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            controlnet=controlnet,
            torch_dtype=torch.float16 if self.precision == 'fp16' else torch.float32,
            safety_checker=None
        )
        
        # Mover al dispositivo correcto
        self.pipe = self.pipe.to(self.device)
        
        # Optimizaciones según hardware
        settings = self.hardware_profile['recommended_settings']
        
        if settings.get('enable_attention_slicing'):
            self.pipe.enable_attention_slicing(1)
        
        if settings.get('enable_vae_slicing'):
            self.pipe.enable_vae_slicing()
        
        if settings.get('cpu_offload') and self.device != 'cpu':
            self.pipe.enable_sequential_cpu_offload()
        
        # Scheduler
        self.pipe.scheduler = DDIMScheduler.from_config(self.pipe.scheduler.config)
        
        print("✅ Modelos cargados correctamente")
    
    def generate(
        self,
        input_image,
        material_prompt,
        style_preset="Fotografía de Interiores Profesional",
        lighting_profile="natural_morning",
        custom_lighting="",
        resolution=512,
        steps=20,
        guidance_scale=7.0,
        control_strength=0.85,
        seed=None,
        **kwargs
    ):
        """
        Genera un render fotorrealista
        
        Args:
            input_image: PIL Image o path
            material_prompt: Descripción de materiales
            style_preset: Estilo fotográfico
            lighting_profile: Perfil de iluminación
            custom_lighting: Modificadores adicionales
            resolution: Resolución de salida
            steps: Pasos de inferencia
            guidance_scale: Escala de guidance
            control_strength: Fidelidad geométrica
            seed: Semilla aleatoria (None = aleatorio)
            
        Returns:
            dict con 'image', 'control_image', 'metadata'
        """
        if self.pipe is None:
            raise RuntimeError("Debes cargar los modelos primero con load_models()")
        
        # Cargar imagen si es path
        if isinstance(input_image, str):
            input_image = Image.open(input_image)
        
        # Redimensionar manteniendo aspecto
        aspect = input_image.width / input_image.height
        if aspect > 1:
            new_size = (resolution, int(resolution / aspect))
        else:
            new_size = (int(resolution * aspect), resolution)
        
        # Ajustar a múltiplos de 8
        new_size = (
            (new_size[0] // 8) * 8,
            (new_size[1] // 8) * 8
        )
        
        input_image = input_image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Detectar bordes
        control_image = self.edge_detector(input_image)
        
        # Construir prompt
        lighting_prompt = self.lighting_controller.build_lighting_prompt(
            lighting_profile,
            custom_additions=custom_lighting
        )
        
        full_prompt = f"{material_prompt}, {lighting_prompt}, {style_preset}, photorealistic, 4k, sharp focus, architectural photography"
        
        negative_prompt = "cartoon, 3d render, painting, illustration, anime, sketch, blurry, ugly, distorted, low quality, watermark, text, oversaturated, underexposed, overexposed, bad lighting"
        
        # Seed
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None
        
        # Generar
        with torch.no_grad():
            output = self.pipe(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                image=control_image,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                controlnet_conditioning_scale=control_strength,
                generator=generator
            )
        
        result_image = output.images[0]
        
        # Metadata
        metadata = {
            'resolution': new_size,
            'steps': steps,
            'guidance_scale': guidance_scale,
            'control_strength': control_strength,
            'seed': seed,
            'material_prompt': material_prompt,
            'style_preset': style_preset,
            'lighting_profile': lighting_profile,
            'custom_lighting': custom_lighting,
            'lighting_metadata': self.lighting_controller.get_profile_metadata(lighting_profile),
            'hardware_used': self.hardware_profile['category'],
            'device': self.device
        }
        
        return {
            'image': result_image,
            'control_image': control_image,
            'metadata': metadata
        }
    
    def generate_with_project_structure(
        self,
        input_image,
        project_name=None,
        configurations=None,
        save_outputs=True,
        **single_config_kwargs
    ):
        """
        Genera renders con estructura de carpetas organizada (FEATURE MVP)
        
        Args:
            input_image: PIL Image o path
            project_name: Nombre del proyecto (auto si None)
            configurations: Lista de configuraciones [{name, params}] o None
            save_outputs: Si False, solo retorna resultados sin guardar
            **single_config_kwargs: Si no hay configs, usar estos params
            
        Returns:
            dict con:
                - project_path: Path del proyecto
                - results: Lista de resultados
                - metadata: Metadata completa del proyecto
        """
        from datetime import datetime
        from pathlib import Path
        import json
        
        # Nombre del proyecto
        if project_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if isinstance(input_image, str):
                base_name = Path(input_image).stem
            else:
                base_name = "render"
            project_name = f"{base_name}_{timestamp}"
        
        # Crear estructura de carpetas
        if save_outputs:
            base_path = Path(f"outputs/{project_name}")
            folders = {
                'original': base_path / 'original',
                'renders': base_path / 'renders',
                'comparatives': base_path / 'comparatives',
                'controls': base_path / 'controls'
            }
            
            for folder in folders.values():
                folder.mkdir(parents=True, exist_ok=True)
        
        # Cargar imagen original
        if isinstance(input_image, str):
            input_image = Image.open(input_image)
        
        # Guardar original
        if save_outputs:
            original_path = folders['original'] / 'original.jpg'
            input_image.save(original_path, quality=95)
        
        # Si no hay configs, crear una con los kwargs
        if configurations is None:
            configurations = [{
                'name': 'default',
                'description': 'Render único',
                'params': single_config_kwargs
            }]
        
        results = []
        metadata = {
            'project_name': project_name,
            'created_at': datetime.now().isoformat(),
            'original_size': input_image.size,
            'hardware': {
                'category': self.hardware_profile['category'],
                'tier': self.hardware_profile['tier'],
                'gpu': self.hardware_profile['gpu']['name'] if self.hardware_profile['gpu']['available'] else 'CPU'
            },
            'renders': []
        }
        
        # Generar cada configuración
        import time
        
        for i, config in enumerate(configurations):
            config_name = config.get('name', f'render_{i+1}')
            config_desc = config.get('description', config_name)
            params = config.get('params', {})
            
            print(f"\n🎨 Generando: {config_name}")
            print(f"   {config_desc}")
            
            start_time = time.time()
            
            # Generar
            result = self.generate(input_image=input_image, **params)
            
            generation_time = time.time() - start_time
            
            if save_outputs:
                # Guardar render
                render_path = folders['renders'] / f"{config_name}.jpg"
                result['image'].save(render_path, quality=95)
                
                # Guardar control
                control_path = folders['controls'] / f"{config_name}_control.jpg"
                result['control_image'].save(control_path, quality=90)
                
                # Crear comparativa
                comparative_path = folders['comparatives'] / f"{config_name}_comparative.jpg"
                self._create_comparative(
                    input_image,
                    result['image'],
                    result['control_image'],
                    comparative_path,
                    config_name,
                    config_desc
                )
            
            # Metadata del render
            render_meta = {
                'name': config_name,
                'description': config_desc,
                'generation_time_seconds': round(generation_time, 2),
                'config': params,
                'render_metadata': result['metadata']
            }
            
            if save_outputs:
                render_meta.update({
                    'render_path': str(render_path),
                    'control_path': str(control_path),
                    'comparative_path': str(comparative_path)
                })
            
            metadata['renders'].append(render_meta)
            results.append({
                'name': config_name,
                'image': result['image'],
                'control_image': result['control_image'],
                'metadata': render_meta
            })
            
            print(f"   ✅ Completado en {generation_time:.1f}s")
        
        if save_outputs:
            # Guardar metadata JSON
            metadata_path = base_path / 'project_metadata.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                # Convertir paths a strings para JSON
                json_metadata = json.loads(json.dumps(metadata, default=str))
                json.dump(json_metadata, f, indent=2, ensure_ascii=False)
            
            # Crear resumen TXT
            self._create_summary(base_path, metadata)
            
            # Crear galería si hay múltiples renders
            if len(configurations) > 1:
                self._create_gallery(base_path, folders['comparatives'], configurations)
            
            print(f"\n✅ Proyecto guardado: {base_path}")
        
        return {
            'project_path': str(base_path) if save_outputs else None,
            'results': results,
            'metadata': metadata
        }
    
    def _create_comparative(self, original, render, control, save_path, title, description=""):
        """Crea imagen comparativa antes/después"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        axes[0].imshow(original)
        axes[0].set_title('ORIGINAL\n(Render 3D)', fontsize=12, fontweight='bold')
        axes[0].axis('off')
        
        axes[1].imshow(control)
        axes[1].set_title('GEOMETRÍA\n(Edge Detection)', fontsize=12)
        axes[1].axis('off')
        
        axes[2].imshow(render)
        axes[2].set_title('FOTORREALISTA\n(IA Generated)', fontsize=12, fontweight='bold', color='green')
        axes[2].axis('off')
        
        if description:
            plt.suptitle(f'{title}\n{description}', fontsize=14, y=0.98)
        else:
            plt.suptitle(title, fontsize=14, y=0.98)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def _create_summary(self, base_path, metadata):
        """Crea archivo README con resumen del proyecto"""
        summary_path = base_path / 'README.txt'
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("PROYECTO: RENDERS FOTORREALISTAS - INTERIOR AI RENDER\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Nombre del proyecto: {metadata['project_name']}\n")
            f.write(f"Fecha de creación: {metadata['created_at']}\n")
            f.write(f"Resolución original: {metadata['original_size'][0]}x{metadata['original_size'][1]}px\n")
            f.write(f"Total de renders: {len(metadata['renders'])}\n\n")
            
            f.write(f"Hardware utilizado:\n")
            f.write(f"  • Categoría: {metadata['hardware']['category']}\n")
            f.write(f"  • Tier: {metadata['hardware']['tier']}\n")
            f.write(f"  • GPU: {metadata['hardware']['gpu']}\n\n")
            
            f.write("="*70 + "\n")
            f.write("ESTRUCTURA DEL PROYECTO\n")
            f.write("="*70 + "\n\n")
            
            f.write("📁 original/          → Tu render 3D original\n")
            f.write("📁 renders/           → Renders fotorrealistas generados\n")
            f.write("📁 controls/          → Mapas de geometría (edge detection)\n")
            f.write("📁 comparatives/      → Comparativas antes/después\n")
            f.write("📄 project_metadata.json → Metadata técnica completa (JSON)\n")
            f.write("📄 README.txt         → Este archivo\n")
            if len(metadata['renders']) > 1:
                f.write("📄 GALLERY.jpg        → Galería con todas las comparativas\n")
            f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("RENDERS GENERADOS\n")
            f.write("="*70 + "\n\n")
            
            total_time = 0
            for i, render in enumerate(metadata['renders'], 1):
                f.write(f"{i}. {render['name']}\n")
                f.write(f"   Descripción: {render.get('description', 'N/A')}\n")
                
                config = render['config']
                f.write(f"   Materiales: {config.get('material_prompt', 'N/A')[:70]}...\n")
                f.write(f"   Iluminación: {config.get('lighting_profile', 'N/A')}\n")
                f.write(f"   Estilo: {config.get('style_preset', 'N/A')}\n")
                
                render_meta = render['render_metadata']
                f.write(f"   Resolución: {render_meta['resolution'][0]}x{render_meta['resolution'][1]}px\n")
                f.write(f"   Pasos: {render_meta['steps']}\n")
                f.write(f"   Fidelidad geométrica: {render_meta['control_strength']}\n")
                f.write(f"   Tiempo de generación: {render['generation_time_seconds']:.1f} segundos\n")
                
                total_time += render['generation_time_seconds']
                f.write("\n")
            
            f.write("="*70 + "\n")
            f.write(f"Tiempo total de generación: {total_time:.1f} segundos ({total_time/60:.1f} minutos)\n")
            f.write("="*70 + "\n\n")
            
            f.write("Generado por Interior AI Render MVP\n")
            f.write("Sistema de IA para generación de renders fotorrealistas\n")
    
    def _create_gallery(self, base_path, comparatives_folder, configurations):
        """Crea galería con todas las comparativas"""
        gallery_path = base_path / 'GALLERY.jpg'
        
        n_renders = len(configurations)
        fig, axes = plt.subplots(n_renders, 1, figsize=(18, 6*n_renders))
        
        if n_renders == 1:
            axes = [axes]
        
        for i, config in enumerate(configurations):
            config_name = config.get('name', f'render_{i+1}')
            comp_path = comparatives_folder / f"{config_name}_comparative.jpg"
            
            if comp_path.exists():
                comp_img = Image.open(comp_path)
                axes[i].imshow(comp_img)
                axes[i].set_title(
                    f"{config_name} - {config.get('description', '')}",
                    fontsize=14,
                    fontweight='bold'
                )
                axes[i].axis('off')
        
        plt.tight_layout()
        plt.savefig(gallery_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   📸 Galería creada: GALLERY.jpg")
