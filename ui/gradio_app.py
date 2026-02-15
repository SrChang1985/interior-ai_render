"""
Interfaz Gradio para Interior AI Render
"""
import gradio as gr
from core.hardware_detector import HardwareDetector
from core.generator import RenderGenerator
from core.lighting_controller import LightingController
from utils.preset_manager import PresetManager
from database.repository import RenderRepository
from PIL import Image
import yaml
import os
from datetime import datetime

class InteriorAIApp:
    """Aplicación principal con interfaz Gradio"""
    
    def __init__(self):
        # Cargar configuración
        with open('config/app_settings.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Detectar hardware
        self.hardware_detector = HardwareDetector()
        
        # Inicializar componentes
        self.generator = RenderGenerator(self.hardware_detector.profile)
        self.lighting_controller = LightingController()
        self.preset_manager = PresetManager()
        self.repo = RenderRepository()
        
        self.models_loaded = False
    
    def load_models(self):
        """Carga los modelos de IA"""
        if self.models_loaded:
            return "✅ Modelos ya cargados"
        
        try:
            self.generator.load_models()
            self.models_loaded = True
            return "✅ Modelos cargados exitosamente"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def get_presets_by_category(self, category):
        """Obtiene presets filtrados por categoría"""
        presets = self.preset_manager.get_presets_by_category(category)
        return [p['name'] for p in presets]
    
    def get_preset_details(self, preset_name):
        """Obtiene detalles de un preset"""
        for category, presets in self.preset_manager.presets.items():
            for p in presets:
                if p['name'] == preset_name:
                    return p
        return None
    
    def get_lighting_profiles_by_category(self, category):
        """Obtiene perfiles de iluminación por categoría"""
        category_map = {
            'Natural': 'natural',
            'Artificial': 'artificial',
            'Mixta': 'mixed',
            'Especial': 'special'
        }
        profiles = self.lighting_controller.get_profiles_by_category(category_map[category])
        return [p.name for p in profiles]
    
    def generate_render(
        self,
        input_image,
        room_category,
        preset_name,
        lighting_category,
        lighting_profile_name,
        custom_lighting,
        resolution,
        steps,
        guidance,
        control_strength,
        seed
    ):
        """Genera el render fotorrealista"""
        
        if not self.models_loaded:
            return None, None, "❌ Primero debes cargar los modelos"
        
        if input_image is None:
            return None, None, "❌ Debes cargar una imagen"
        
        try:
            # Obtener detalles del preset
            preset_details = self.get_preset_details(preset_name)
            if not preset_details:
                return None, None, f"❌ Preset no encontrado: {preset_name}"
            
            # Encontrar perfil de iluminación
            lighting_profile = None
            for profile in self.lighting_controller.get_all_profiles():
                if profile.name == lighting_profile_name:
                    lighting_profile = profile
                    break
            
            if not lighting_profile:
                # Usar recomendación
                lighting_profile = self.lighting_controller.get_recommendation(
                    room_category.lower().replace(' ', '_')
                )
            
            # Generar
            result = self.generator.generate(
                input_image=Image.fromarray(input_image) if not isinstance(input_image, Image.Image) else input_image,
                material_prompt=preset_details['material_prompt'],
                style_preset=preset_details['style_preset'],
                lighting_profile=lighting_profile.name if hasattr(lighting_profile, 'name') else 'natural_midday',
                custom_lighting=custom_lighting,
                preset_name=preset_name,
                resolution=int(resolution),
                steps=int(steps),
                guidance_scale=float(guidance),
                control_strength=float(control_strength),
                seed=int(seed) if seed > 0 else None
            )
            
            # Guardar outputs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"outputs/render_{timestamp}.jpg"
            control_path = f"outputs/control_{timestamp}.jpg"
            
            result['image'].save(output_path, quality=95)
            result['control_image'].save(control_path, quality=90)
            
            # Guardar en base de datos
            render_record = self.repo.save_render(
                input_image_path="uploaded",
                output_image_path=output_path,
                control_image_path=control_path,
                material_prompt=preset_details['material_prompt'],
                style_preset=preset_details['style_preset'],
                resolution=int(resolution),
                steps=int(steps),
                guidance_scale=float(guidance),
                control_strength=float(control_strength),
                seed=int(seed) if seed > 0 else None,
                hardware_category=self.hardware_detector.profile['category'],
                device_used=self.hardware_detector.profile['recommended_settings']['device']
            )
            
            # Info
            info = f"""
✅ **Render generado exitosamente** (ID: {render_record.id})

**Configuración:**
- Preset: {preset_name}
- Iluminación: {lighting_profile.name if hasattr(lighting_profile, 'name') else 'N/A'}
- Temperatura: {result['metadata']['lighting_metadata'].get('primary_temperature_k', 'N/A')}K
- Resolución: {result['metadata']['resolution']}
- Pasos: {steps}

**Archivos guardados:**
- {output_path}
- {control_path}
            """
            
            return result['image'], result['control_image'], info
            
        except Exception as e:
            return None, None, f"❌ Error: {str(e)}"
    
    def create_interface(self):
        """Crea la interfaz Gradio"""
        
        with gr.Blocks(title="Interior AI Render", theme=gr.themes.Soft()) as app:
            
            gr.Markdown("""
            # 🏠 Interior AI Render - MVP
            ### Convierte renders 3D básicos en fotografías fotorrealistas
            """)
            
            # Información del sistema
            with gr.Accordion("🖥️ Información del Sistema", open=False):
                gr.Markdown(f"""
                **Hardware detectado:**
                - CPU: {self.hardware_detector.profile['cpu']['name']}
                - RAM: {self.hardware_detector.profile['ram_gb']:.1f} GB
                - GPU: {'✅ ' + self.hardware_detector.profile['gpu']['name'] if self.hardware_detector.profile['gpu']['available'] else '❌ No disponible'}
                - Categoría: {self.hardware_detector.profile['category']}
                
                **Configuración recomendada:**
                - Resolución: {self.hardware_detector.profile['recommended_settings']['resolution']}px
                - Pasos: {self.hardware_detector.profile['recommended_settings']['steps']}
                - Tiempo estimado: {self.hardware_detector.profile['recommended_settings']['estimated_time_per_render']}
                """)
            
            # Carga de modelos
            with gr.Row():
                load_btn = gr.Button("🔄 Cargar Modelos de IA", variant="primary", size="lg")
                load_status = gr.Textbox(label="Estado", value="⏳ Modelos no cargados", interactive=False)
            
            gr.Markdown("---")
            
            with gr.Row():
                # Panel izquierdo - Input
                with gr.Column(scale=1):
                    gr.Markdown("## 📤 Input")
                    
                    input_image = gr.Image(
                        label="Render 3D Base",
                        type="numpy",
                        source="upload"
                    )
                    
                    room_category = gr.Dropdown(
                        label="Categoría de Habitación",
                        choices=list(self.preset_manager.presets.keys()),
                        value=list(self.preset_manager.presets.keys())[0]
                    )
                    
                    preset_name = gr.Dropdown(
                        label="Preset de Materiales",
                        choices=[],
                        value=None
                    )
                    
                    with gr.Accordion("💡 Control de Iluminación", open=True):
                        lighting_category = gr.Radio(
                            label="Tipo de Iluminación",
                            choices=["Natural", "Artificial", "Mixta", "Especial"],
                            value="Natural"
                        )
                        
                        lighting_profile = gr.Dropdown(
                            label="Perfil de Iluminación",
                            choices=[],
                            value=None
                        )
                        
                        custom_lighting = gr.Textbox(
                            label="Modificadores Personalizados (Opcional)",
                            placeholder="soft shadows, rim lighting...",
                            lines=2
                        )
                    
                    with gr.Accordion("⚙️ Configuración Avanzada", open=False):
                        resolution = gr.Slider(
                            label="Resolución",
                            minimum=256,
                            maximum=1024,
                            step=128,
                            value=self.hardware_detector.profile['recommended_settings']['resolution']
                        )
                        
                        steps = gr.Slider(
                            label="Pasos",
                            minimum=8,
                            maximum=50,
                            step=1,
                            value=self.hardware_detector.profile['recommended_settings']['steps']
                        )
                        
                        guidance = gr.Slider(
                            label="Guidance Scale",
                            minimum=5.0,
                            maximum=15.0,
                            step=0.5,
                            value=7.0
                        )
                        
                        control_strength = gr.Slider(
                            label="Fidelidad Geométrica",
                            minimum=0.5,
                            maximum=1.0,
                            step=0.05,
                            value=0.85
                        )
                        
                        seed = gr.Number(
                            label="Semilla (0 = aleatorio)",
                            value=0,
                            precision=0
                        )
                    
                    generate_btn = gr.Button("🎨 Generar Render", variant="primary", size="lg")
                
                # Panel derecho - Output
                with gr.Column(scale=1):
                    gr.Markdown("## 📊 Resultados")
                    
                    output_image = gr.Image(
                        label="Render Fotorrealista",
                        type="pil"
                    )
                    
                    control_image = gr.Image(
                        label="Mapa de Control (Geometría)",
                        type="pil"
                    )
                    
                    output_info = gr.Markdown("ℹ️ Los resultados aparecerán aquí")
            
            # Event handlers
            def update_presets(category):
                presets = self.get_presets_by_category(category)
                return gr.update(choices=presets, value=presets[0] if presets else None)
            
            def update_lighting_profiles(category):
                profiles = self.get_lighting_profiles_by_category(category)
                return gr.update(choices=profiles, value=profiles[0] if profiles else None)
            
            room_category.change(
                fn=update_presets,
                inputs=[room_category],
                outputs=[preset_name]
            )
            
            lighting_category.change(
                fn=update_lighting_profiles,
                inputs=[lighting_category],
                outputs=[lighting_profile]
            )
            
            load_btn.click(
                fn=self.load_models,
                outputs=[load_status]
            )
            
            generate_btn.click(
                fn=self.generate_render,
                inputs=[
                    input_image,
                    room_category,
                    preset_name,
                    lighting_category,
                    lighting_profile,
                    custom_lighting,
                    resolution,
                    steps,
                    guidance,
                    control_strength,
                    seed
                ],
                outputs=[output_image, control_image, output_info]
            )
            
            # Inicializar presets
            app.load(
                fn=update_presets,
                inputs=[room_category],
                outputs=[preset_name]
            )
            
            app.load(
                fn=update_lighting_profiles,
                inputs=[lighting_category],
                outputs=[lighting_profile]
            )
        
        return app
    
    def launch(self):
        """Lanza la aplicación"""
        app = self.create_interface()
        app.queue()
        app.launch(
            server_name=self.config['app']['host'],
            server_port=self.config['app']['port'],
            share=self.config['app']['share'],
            inbrowser=True
        )
