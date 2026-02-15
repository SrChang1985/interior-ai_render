"""
Punto de entrada principal
"""
import os
import sys

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.gradio_app import InteriorAIApp
from utils.logger import setup_logger

def main():
    """Función principal"""
    
    # Setup logger
    logger = setup_logger()
    logger.info(" Iniciando Interior AI Render MVP")
    
    # Crear directorios necesarios
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("renders_input", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Lanzar aplicación
    try:
        app = InteriorAIApp()
        logger.info(" Aplicación inicializada")
        app.launch()
    except Exception as e:
        logger.error(f" Error al iniciar aplicación: {str(e)}")
        raise

if __name__ == "__main__":
    main()
