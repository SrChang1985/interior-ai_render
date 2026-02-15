"""
Gestor de modelos de IA
"""
import os
from typing import Optional

class ModelManager:
    """Gestiona descarga y caché de modelos"""
    
    def __init__(self, cache_dir: str = "models"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Configurar cache de HuggingFace
        os.environ['HF_HOME'] = cache_dir
        os.environ['TRANSFORMERS_CACHE'] = cache_dir
    
    def get_cache_path(self) -> str:
        """Retorna path del cache"""
        return self.cache_dir
    
    def clear_cache(self):
        """Limpia el cache de modelos"""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir)
            print(f"✅ Cache limpiado: {self.cache_dir}")
