# 🏠 Interior AI Render - MVP

Sistema de generación de renders fotorrealistas para interiores y mobiliario.

## 🚀 Instalación Rápida
```bash
# 1. Dar permisos
chmod +x setup.sh

# 2. Ejecutar setup
./setup.sh

# 3. Activar entorno
source venv/bin/activate

# 4. Lanzar aplicación
python main.py
```

## 📋 Requisitos

- macOS (probado en MacBook Pro 2010+)
- Python 3.8-3.9
- 16GB RAM mínimo
- ~10GB espacio en disco

## 🎯 Características MVP

- ✅ Detección automática de hardware
- ✅ Presets de materiales por categoría
- ✅ Control preciso de iluminación (temperatura de color)
- ✅ Base de datos de historial
- ✅ Interfaz gráfica intuitiva

## 📁 Estructura
```
interior-ai-render/
├── config/          # Configuración
├── core/            # Motor de generación
├── database/        # Base de datos
├── ui/              # Interfaz Gradio
├── utils/           # Utilidades
├── outputs/         # Renders generados
└── main.py          # Punto de entrada
```

## ⏱️ Tiempos Esperados

| Hardware | Resolución | Tiempo |
|----------|-----------|---------|
| MacBook Pro 2010 | 384px | 10-15 min |
| MacBook M1/M2 | 768px | 3-5 min |

## 💡 Uso

1. Cargar modelos (primera vez, ~10 min)
2. Subir render 3D
3. Seleccionar preset de materiales
4. Elegir iluminación
5. Generar

## 🔧 Configuración

Edita `config/app_settings.yaml` para personalizar.

## 📝 Licencia

Uso confidencial local.
```

---

### **21. .gitignore**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Modelos y datos
models/
data/*.db
outputs/
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# macOS
.DS_Store

# Temporales
*.tmp
*.log
