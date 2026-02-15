# check_setup.py
"""
Script para verificar que todos los archivos necesarios existen
"""
import os
import sys

REQUIRED_FILES = [
    'requirements.txt',
    'setup.sh',
    'main.py',
    'README.md',
    '.gitignore',
    'config/hardware_profiles.yaml',
    'config/material_presets.yaml',
    'config/app_settings.yaml',
    'core/__init__.py',
    'core/hardware_detector.py',
    'core/lighting_controller.py',
    'core/model_manager.py',
    'core/generator.py',
    'database/__init__.py',
    'database/models.py',
    'database/repository.py',
    'ui/__init__.py',
    'ui/gradio_app.py',
    'utils/__init__.py',
    'utils/preset_manager.py',
    'utils/logger.py',
]

REQUIRED_DIRS = [
    'config',
    'core',
    'database',
    'ui',
    'utils',
    'data',
    'outputs',
    'renders_input',
]

def check_setup():
    """Verifica que todos los archivos existen"""
    
    print("Verificando estructura del proyecto...\n")
    
    missing_files = []
    missing_dirs = []
    
    # Verificar directorios
    print("Verificando directorios:")
    for dir_name in REQUIRED_DIRS:
        if os.path.isdir(dir_name):
            print("   OK {}/".format(dir_name))
        else:
            print("   FALTA {}/".format(dir_name))
            missing_dirs.append(dir_name)
    
    print()
    
    # Verificar archivos
    print("Verificando archivos:")
    for file_path in REQUIRED_FILES:
        if os.path.isfile(file_path):
            print("   OK {}".format(file_path))
        else:
            print("   FALTA {}".format(file_path))
            missing_files.append(file_path)
    
    print()
    
    # Resumen
    if not missing_files and not missing_dirs:
        print("Todos los archivos necesarios estan presentes!")
        print("\nProximo paso:")
        print("   chmod +x setup.sh")
        print("   ./setup.sh")
        return True
    else:
        print("Faltan algunos archivos/directorios:")
        if missing_dirs:
            print("\nDirectorios faltantes:")
            for d in missing_dirs:
                print("   - {}".format(d))
        if missing_files:
            print("\nArchivos faltantes:")
            for f in missing_files:
                print("   - {}".format(f))
        return False

if __name__ == "__main__":
    success = check_setup()
    sys.exit(0 if success else 1)