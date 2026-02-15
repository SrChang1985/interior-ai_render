#!/bin/bash

echo "🏠 =========================================="
echo "   Interior AI Render - Setup MVP"
echo "=========================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo primero."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
python3 -m venv venv

# Activar entorno
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "⬆️  Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo "📥 Instalando dependencias (10-15 minutos)..."
pip install -r requirements.txt

# Crear estructura de carpetas
echo ""
echo "📁 Creando estructura de carpetas..."
mkdir -p config
mkdir -p core
mkdir -p database
mkdir -p ui
mkdir -p utils
mkdir -p data
mkdir -p outputs
mkdir -p renders_input

# Crear archivos __init__.py
touch core/__init__.py
touch database/__init__.py
touch ui/__init__.py
touch utils/__init__.py

# Inicializar base de datos
echo "🗄️  Inicializando base de datos..."
python -c "from database.models import Base, engine; Base.metadata.create_all(engine); print('✅ Base de datos creada')"

# Detectar hardware
echo "🖥️  Detectando hardware..."
python -c "from core.hardware_detector import HardwareDetector; d = HardwareDetector(); d.print_summary(); d.save_profile()"

# Sincronizar presets
echo "📋 Sincronizando presets..."
python -c "from utils.preset_manager import PresetManager; pm = PresetManager(); pm.sync_to_database()"

echo ""
echo "✅ =========================================="
echo "   ¡Setup completado!"
echo "=========================================="
echo ""
echo "📋 Para ejecutar la aplicación:"
echo ""
echo "1. Activa el entorno:"
echo "   source venv/bin/activate"
echo ""
echo "2. Ejecuta:"
echo "   python main.py"
echo ""
echo "3. Abre tu navegador en:"
echo "   http://127.0.0.1:7860"
echo ""
