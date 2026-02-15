# core/generator.py (actualizado con iluminación)

import torch
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, DDIMScheduler
from core.canny_simple import CannyDetector
print("✓ Usando CannyDetector simple (sin OpenCV)")
from PIL import Image
import gc
from typing import Optional, Dict
from core.lighting_controller import LightingController
from database.repository import RenderRepository

class RenderGenerator:
    """Motor principal de generación de renders fotorrealistas"""
    
    def __init__(self, hardware_profile: Dict):
        self.hardware = hardware_profile
        self.lighting_controller = LightingController()
        self.repo = RenderRepository()
        self.pipe = None
        self.controlnet = None
        self.canny_detector = None
        
    def load_models(self):
        """Carga modelos según perfil de hardware"""
        settings = self.hardware['recommended_settings']
        device = settings['device']
        
        print(f"🔧 Cargando modelos para {device.upper()}...")
        
        # Determinar dtype según hardware
        if settings['precision'] == 'fp16' and device in ['cuda', 'mps']:
            dtype = torch.float16
        else:
            dtype = torch.float32
        
        # ControlNet
        self.controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/control_v11p_sd15_canny",
            torch_dtype=dtype
        )
        
        # Pipeline
        self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            controlnet=self.controlnet,
            torch_dtype=dtype,
            safety_checker=None
        )
        
        # Mover a dispositivo correcto
        if device == 'cuda':
            self.pipe = self.pipe.to('cuda')
        elif device == 'mps':
            self.pipe = self.pipe.to('mps')
        # Para CPU se queda por defecto
        
        # Scheduler optimizado
        self.pipe.scheduler = DDIMScheduler.from_config(
            self.pipe.scheduler.config
        )
        
        # Aplicar optimizaciones
        if settings['enable_attention_slicing']:
            self.pipe.enable_attention_slicing(1)
        
        if settings['enable_vae_slicing']:
            self.pipe.enable_vae_slicing()
        
        if settings['cpu_offload']:
            self.pipe.enable_sequential_cpu_offload()
        
        # Detector de bordes
        self.canny_detector = CannyDetector()
        
        print("✅ Modelos cargados")
    
    def generate(
        self,
        input_image: Image.Image,
        material_prompt: str,
        style_preset: str,
        lighting_profile: str,
        custom_lighting: str = '',
        preset_name: Optional[str] = None,
        **generation_params
    ) -> Dict:
        """
        Genera render fotorrealista con control de iluminación
        
        Returns:
            Dict con 'image', 'control_image', 'metadata'
        """
        
        # Construir prompt de iluminación
        lighting_prompt = self.lighting_controller.build_lighting_prompt(
            lighting_profile,
            custom_lighting
        )
        
        # Construir prompt completo
        full_prompt = f"{material_prompt}, {lighting_prompt}, {style_preset}, photorealistic, 4k, sharp focus, architectural photography"
        
        negative_prompt = (
            "cartoon, 3d render, painting, illustration, anime, sketch, "
            "blurry, ugly, distorted, low quality, watermark, text, "
            "oversaturated, underexposed, overexposed, bad lighting"
        )
        
        # Preparar imagen
        settings = self.hardware['recommended_settings']
        resolution = generation_params.get('resolution', settings['resolution'])
        
        # Redimensionar manteniendo aspecto
        width, height = input_image.size
        aspect_ratio = width / height
        
        if width > height:
            new_width = resolution
            new_height = int(resolution / aspect_ratio)
        else:
            new_height = resolution
            new_width = int(resolution * aspect_ratio)
        
        # Múltiplos de 8
        new_width = (new_width // 8) * 8
        new_height = (new_height // 8) * 8
        
        resized_image = input_image.resize((new_width, new_height), Image.LANCZOS)
        
        # Extraer control (geometría)
        control_image = self.canny_detector(
            resized_image,
            low_threshold=100,
            high_threshold=200
        )
        
        # Generar
        steps = generation_params.get('steps', settings['steps'])
        guidance = generation_params.get('guidance_scale', 7.0)
        control_strength = generation_params.get('control_strength', 0.85)
        seed = generation_params.get('seed', None)
        
        generator = torch.Generator(device=settings['device'])
        if seed:
            generator.manual_seed(seed)
        
        with torch.no_grad():
            result = self.pipe(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                image=control_image,
                num_inference_steps=steps,
                guidance_scale=guidance,
                controlnet_conditioning_scale=control_strength,
                generator=generator,
                width=new_width,
                height=new_height
            ).images[0]
        
        # Limpiar memoria
        gc.collect()
        if settings['device'] == 'cuda':
            torch.cuda.empty_cache()
        elif settings['device'] == 'mps':
            torch.mps.empty_cache()
        
        # Metadata completa
        lighting_metadata = self.lighting_controller.get_lighting_metadata(lighting_profile)
        
        metadata = {
            'material_prompt': material_prompt,
            'lighting_profile': lighting_profile,
            'lighting_metadata': lighting_metadata,
            'lighting_prompt': lighting_prompt,
            'style_preset': style_preset,
            'full_prompt': full_prompt,
            'resolution': f"{new_width}x{new_height}",
            'steps': steps,
            'guidance_scale': guidance,
            'control_strength': control_strength,
            'seed': seed,
            'hardware_category': self.hardware['category'],
            'device': settings['device']
        }
        
        return {
            'image': result,
            'control_image': control_image,
            'metadata': metadata
        }
