"""
Interfaz Streamlit para Interior AI Render
Alternativa moderna y simple a Gradio
"""

import streamlit as st
from PIL import Image
import sys
import os
from pathlib import Path
import io
import zipfile

# Añadir directorio raíz al path
if '/home/claude' not in sys.path:
    sys.path.insert(0, '/home/claude')

from core.generator import RenderGenerator
from core.hardware_detector import HardwareDetector
from utils.preset_manager import PresetManager


# Configuración de página
st.set_page_config(
    page_title="Interior AI Render",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        height: 3rem;
        font-size: 1.1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Inicialización de session state
def init_session_state():
    """Inicializa variables de sesión"""
    if 'detector' not in st.session_state:
        with st.spinner('🔍 Detectando hardware...'):
            st.session_state.detector = HardwareDetector()
    
    if 'generator' not in st.session_state:
        st.session_state.generator = None
        st.session_state.models_loaded = False
    
    if 'preset_manager' not in st.session_state:
        st.session_state.preset_manager = PresetManager()
    
    if 'generated_results' not in st.session_state:
        st.session_state.generated_results = []


def load_models():
    """Carga los modelos de IA"""
    if not st.session_state.models_loaded:
        with st.spinner('📥 Cargando modelos de IA (primera vez: 5-10 min)...'):
            if st.session_state.generator is None:
                st.session_state.generator = RenderGenerator(st.session_state.detector.profile)
            
            st.session_state.generator.load_models()
            st.session_state.models_loaded = True
        
        st.success('✅ Modelos cargados correctamente')
        st.rerun()


def sidebar_config():
    """Configuración en sidebar"""
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # Hardware info
        detector = st.session_state.detector
        
        with st.expander("🖥️ Hardware Detectado", expanded=True):
            st.markdown(f"""
            **Categoría:** {detector.profile['category']}  
            **Tier:** {detector.profile['tier']}  
            **GPU:** {detector.profile['gpu']['name'] if detector.profile['gpu']['available'] else 'CPU only'}  
            **RAM:** {detector.profile['ram_gb']:.1f} GB  
            **Tiempo estimado:** {detector.profile['recommended_settings']['estimated_time_per_render']}
            """)
        
        st.divider()
        
        # Parámetros de generación
        st.subheader("📊 Parámetros")
        
        # Resolución
        rec_res = detector.profile['recommended_settings']['resolution']
        max_res = detector.profile['recommended_settings'].get('max_recommended_resolution', 1024)
        
        resolution = st.select_slider(
            "Resolución",
            options=[256, 384, 512, 640, 768, 896, 1024],
            value=rec_res,
            help=f"Recomendado: {rec_res}px. Máximo recomendado: {max_res}px"
        )
        
        # Pasos
        rec_steps = detector.profile['recommended_settings']['steps']
        steps = st.slider(
            "Pasos de inferencia",
            min_value=10,
            max_value=50,
            value=rec_steps,
            help="Más pasos = mejor calidad pero más lento"
        )
        
        # Fidelidad geométrica
        control_strength = st.slider(
            "Fidelidad geométrica",
            min_value=0.5,
            max_value=1.0,
            value=0.85,
            step=0.05,
            help="Qué tan fiel es al render 3D original"
        )
        
        # Guidance scale
        guidance = st.slider(
            "Guidance Scale",
            min_value=5.0,
            max_value=15.0,
            value=7.0,
            step=0.5,
            help="Control de adherencia al prompt"
        )
        
        # Semilla
        use_seed = st.checkbox("Usar semilla fija", value=False)
        seed = None
        if use_seed:
            seed = st.number_input("Semilla", min_value=0, max_value=9999999, value=42)
        
        return {
            'resolution': resolution,
            'steps': steps,
            'control_strength': control_strength,
            'guidance_scale': guidance,
            'seed': seed
        }


def create_project_zip(project_path):
    """Crea un ZIP del proyecto completo"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        project_path = Path(project_path)
        
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(project_path.parent)
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return zip_buffer


def main():
    """Función principal"""
    init_session_state()
    
    # Header
    st.markdown('<div class="main-header">🏠 Interior AI Render</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Convierte renders 3D en fotografías fotorrealistas con IA</div>', unsafe_allow_html=True)
    
    # Sidebar
    params = sidebar_config()
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["🎨 Generar", "📚 Presets", "📊 Historial"])
    
    with tab1:
        # Cargar modelos
        if not st.session_state.models_loaded:
            st.info("👋 Bienvenido! Primero necesitas cargar los modelos de IA.")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 Cargar Modelos de IA", type="primary", use_container_width=True):
                    load_models()
        
        else:
            # Upload de imagen
            st.subheader("📤 Sube tu render 3D")
            
            uploaded_file = st.file_uploader(
                "Selecciona tu render",
                type=['png', 'jpg', 'jpeg'],
                help="Formatos: PNG, JPG, JPEG. Recomendado: 512x512 o mayor"
            )
            
            if uploaded_file:
                # Mostrar imagen original
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📷 Original")
                    input_image = Image.open(uploaded_file)
                    st.image(input_image, use_container_width=True)
                    st.caption(f"Tamaño: {input_image.size[0]}x{input_image.size[1]}px")
                
                st.divider()
                
                # Configuración del render
                st.subheader("🎨 Configuración del Render")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    # Categoría
                    categories = list(st.session_state.preset_manager.presets.keys())
                    category = st.selectbox(
                        "Categoría de espacio",
                        categories,
                        index=0,
                        help="Tipo de habitación o espacio"
                    )
                    
                    # Presets de la categoría
                    presets = st.session_state.preset_manager.get_presets_by_category(category)
                    preset_names = [p['name'] for p in presets]
                    
                    selected_preset_name = st.selectbox(
                        "Preset de materiales",
                        preset_names,
                        help="Configuración predefinida de materiales y estilo"
                    )
                    
                    # Obtener preset completo
                    selected_preset = next(p for p in presets if p['name'] == selected_preset_name)
                
                with col_b:
                    # Iluminación
                    lighting_categories = ['Natural', 'Artificial', 'Mixta', 'Especial']
                    lighting_cat = st.selectbox(
                        "Tipo de iluminación",
                        lighting_categories,
                        help="Categoría de iluminación"
                    )
                    
                    # Perfiles según categoría
                    lighting_map = {
                        'Natural': ['natural_morning', 'natural_midday', 'natural_golden_hour'],
                        'Artificial': ['artificial_warm_cozy', 'artificial_neutral_work', 'artificial_cool_modern'],
                        'Mixta': ['mixed_scandinavian', 'mixed_restaurant', 'mixed_boutique'],
                        'Especial': ['dramatic_studio', 'sunset_interior', 'night_ambient']
                    }
                    
                    lighting_profile = st.selectbox(
                        "Perfil de iluminación",
                        lighting_map[lighting_cat],
                        help="Configuración específica de luz"
                    )
                    
                    # Custom lighting (opcional)
                    custom_lighting = st.text_input(
                        "Modificadores adicionales (opcional)",
                        placeholder="soft shadows, rim lighting...",
                        help="Añade modificadores personalizados a la iluminación"
                    )
                
                st.divider()
                
                # Modo de generación
                st.subheader("🔧 Modo de Generación")
                
                gen_mode = st.radio(
                    "Selecciona el modo:",
                    ["🎯 Render único", "🎨 Múltiples variaciones"],
                    horizontal=True
                )
                
                if gen_mode == "🎯 Render único":
                    # Render único
                    col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
                    with col_gen2:
                        if st.button("🎨 Generar Render Fotorrealista", type="primary", use_container_width=True):
                            with st.spinner(f'⏳ Generando render (estimado: {params["steps"]*2} seg)...'):
                                try:
                                    # Generar con sistema de carpetas
                                    result = st.session_state.generator.generate_with_project_structure(
                                        input_image=input_image,
                                        project_name=None,  # Auto
                                        configurations=[{
                                            'name': selected_preset_name.replace(' ', '_'),
                                            'description': selected_preset.get('description', ''),
                                            'params': {
                                                'material_prompt': selected_preset['material_prompt'],
                                                'style_preset': selected_preset['style_preset'],
                                                'lighting_profile': lighting_profile,
                                                'custom_lighting': custom_lighting,
                                                **params
                                            }
                                        }]
                                    )
                                    
                                    # Guardar en session state
                                    st.session_state.generated_results.append(result)
                                    
                                    st.success(f"✅ Render completado! Proyecto: {result['project_path']}")
                                    
                                    # Mostrar resultado
                                    with col2:
                                        st.markdown("### ✨ Fotorrealista")
                                        st.image(result['results'][0]['image'], use_container_width=True)
                                    
                                    # Botón de descarga
                                    st.divider()
                                    st.subheader("📥 Descargar Proyecto")
                                    
                                    zip_data = create_project_zip(result['project_path'])
                                    
                                    st.download_button(
                                        label="📦 Descargar Proyecto Completo (ZIP)",
                                        data=zip_data,
                                        file_name=f"{Path(result['project_path']).name}.zip",
                                        mime="application/zip",
                                        use_container_width=True
                                    )
                                    
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                
                else:
                    # Múltiples variaciones
                    st.info("Generará 3 variaciones con diferentes iluminaciones")
                    
                    variations = [
                        {'name': 'Mañana', 'lighting': 'natural_morning', 'desc': 'Luz suave de mañana (3000K)'},
                        {'name': 'Mediodía', 'lighting': 'natural_midday', 'desc': 'Luz brillante de día (5000K)'},
                        {'name': 'Atardecer', 'lighting': 'natural_golden_hour', 'desc': 'Luz dorada cálida (2700K)'}
                    ]
                    
                    for var in variations:
                        st.markdown(f"**{var['name']}:** {var['desc']}")
                    
                    col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
                    with col_gen2:
                        if st.button("🎨 Generar Variaciones", type="primary", use_container_width=True):
                            progress_bar = st.progress(0)
                            status = st.empty()
                            
                            try:
                                configs = []
                                for i, var in enumerate(variations):
                                    configs.append({
                                        'name': f"{selected_preset_name.replace(' ', '_')}_{var['name']}",
                                        'description': var['desc'],
                                        'params': {
                                            'material_prompt': selected_preset['material_prompt'],
                                            'style_preset': selected_preset['style_preset'],
                                            'lighting_profile': var['lighting'],
                                            'custom_lighting': custom_lighting,
                                            **params
                                        }
                                    })
                                
                                # Generar todas
                                result = st.session_state.generator.generate_with_project_structure(
                                    input_image=input_image,
                                    project_name=None,
                                    configurations=configs
                                )
                                
                                st.session_state.generated_results.append(result)
                                
                                progress_bar.progress(1.0)
                                status.success(f"✅ {len(variations)} variaciones completadas!")
                                
                                # Mostrar resultados
                                st.divider()
                                st.subheader("✨ Resultados")
                                
                                cols = st.columns(len(variations))
                                for i, (col, res) in enumerate(zip(cols, result['results'])):
                                    with col:
                                        st.markdown(f"**{variations[i]['name']}**")
                                        st.image(res['image'], use_container_width=True)
                                
                                # Descarga
                                st.divider()
                                zip_data = create_project_zip(result['project_path'])
                                st.download_button(
                                    label="📦 Descargar Proyecto Completo (ZIP)",
                                    data=zip_data,
                                    file_name=f"{Path(result['project_path']).name}.zip",
                                    mime="application/zip",
                                    use_container_width=True
                                )
                                
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
    
    with tab2:
        st.subheader("📚 Presets Disponibles")
        
        # Mostrar presets por categoría
        for category, presets in st.session_state.preset_manager.presets.items():
            with st.expander(f"📁 {category.replace('_', ' ').title()}", expanded=False):
                for preset in presets:
                    st.markdown(f"**{preset['name']}**")
                    st.caption(preset.get('description', ''))
                    st.text(f"Materiales: {preset['material_prompt'][:80]}...")
                    st.text(f"Estilo: {preset['style_preset']}")
                    st.divider()
    
    with tab3:
        st.subheader("📊 Historial de Generaciones")
        
        if not st.session_state.generated_results:
            st.info("No hay renders generados aún en esta sesión")
        else:
            for i, result in enumerate(reversed(st.session_state.generated_results), 1):
                with st.expander(f"Proyecto #{len(st.session_state.generated_results) - i + 1}: {result['metadata']['project_name']}", expanded=False):
                    st.markdown(f"**Fecha:** {result['metadata']['created_at']}")
                    st.markdown(f"**Renders:** {len(result['results'])}")
                    st.markdown(f"**Hardware:** {result['metadata']['hardware']['gpu']}")
                    
                    if result['project_path']:
                        zip_data = create_project_zip(result['project_path'])
                        st.download_button(
                            label="📥 Descargar",
                            data=zip_data,
                            file_name=f"{Path(result['project_path']).name}.zip",
                            mime="application/zip",
                            key=f"download_{i}"
                        )


if __name__ == "__main__":
    main()
