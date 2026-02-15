# utils/preset_manager.py

import yaml
import os
from database.repository import RenderRepository
from typing import List, Dict

class PresetManager:
    """Gestiona presets de materiales"""
    
    def __init__(self, config_path='config/material_presets.yaml'):
        self.config_path = config_path
        self.repo = RenderRepository()
        self.presets = self.load_presets()
    
    def load_presets(self) -> Dict:
        """Carga presets desde YAML"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}
    
    def sync_to_database(self):
        """Sincroniza presets de YAML a base de datos"""
        for category, presets in self.presets.items():
            for preset_data in presets:
                # Verificar si ya existe
                existing = self.repo.get_preset_by_name(preset_data['name'])
                if not existing:
                    self.repo.create_preset(
                        name=preset_data['name'],
                        description=preset_data.get('description', ''),
                        material_prompt=preset_data['material_prompt'],
                        style_preset=preset_data.get('style_preset', ''),
                        category=preset_data.get('category', category)
                    )
        print("✅ Presets sincronizados con base de datos")
    
    def get_presets_by_category(self, category: str) -> List[Dict]:
        """Obtiene presets de una categoría específica"""
        return self.presets.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """Obtiene lista de todas las categorías"""
        return list(self.presets.keys())
    
    def add_custom_preset(self, name: str, material_prompt: str, category: str, **kwargs):
        """Añade un preset personalizado del usuario"""
        self.repo.create_preset(
            name=name,
            material_prompt=material_prompt,
            category=category,
            **kwargs
        )
        print(f"✅ Preset personalizado '{name}' guardado")
    
    def get_popular_presets(self, limit: int = 5) -> List:
        """Obtiene presets más usados"""
        all_presets = self.repo.get_all_presets()
        return sorted(all_presets, key=lambda x: x.times_used, reverse=True)[:limit]
