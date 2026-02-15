# database/repository.py

from database.models import SessionLocal, MaterialPreset, RenderHistory, StyleEmbedding, LearningMetrics
from datetime import datetime
import json
from typing import List, Optional, Dict

class RenderRepository:
    """Repositorio para acceso a datos"""
    
    def __init__(self):
        self.session = SessionLocal()
    
    # ===== PRESETS =====
    
    def create_preset(self, name: str, material_prompt: str, **kwargs) -> MaterialPreset:
        """Crea un nuevo preset de material"""
        preset = MaterialPreset(
            name=name,
            material_prompt=material_prompt,
            **kwargs
        )
        self.session.add(preset)
        self.session.commit()
        return preset
    
    def get_all_presets(self, category: Optional[str] = None) -> List[MaterialPreset]:
        """Obtiene todos los presets, opcionalmente filtrados por categoría"""
        query = self.session.query(MaterialPreset)
        if category:
            query = query.filter(MaterialPreset.category == category)
        return query.order_by(MaterialPreset.times_used.desc()).all()
    
    def get_preset_by_name(self, name: str) -> Optional[MaterialPreset]:
        """Obtiene un preset por nombre"""
        return self.session.query(MaterialPreset).filter(MaterialPreset.name == name).first()
    
    def update_preset_usage(self, preset_id: int):
        """Incrementa contador de uso de preset"""
        preset = self.session.query(MaterialPreset).get(preset_id)
        if preset:
            preset.times_used += 1
            self.session.commit()
    
    def update_preset_rating(self, preset_id: int, new_rating: int):
        """Actualiza rating promedio del preset"""
        preset = self.session.query(MaterialPreset).get(preset_id)
        if preset:
            # Calcular nuevo promedio
            total_renders = len(preset.renders)
            if total_renders > 0:
                current_total = preset.avg_rating * (total_renders - 1)
                preset.avg_rating = (current_total + new_rating) / total_renders
                self.session.commit()
    
    # ===== HISTORIAL DE RENDERS =====
    
    def save_render(self, **kwargs) -> RenderHistory:
        """Guarda un render en el historial"""
        render = RenderHistory(**kwargs)
        self.session.add(render)
        self.session.commit()
        return render
    
    def mark_render_successful(self, render_id: int, rating: int, notes: str = None, for_training: bool = True):
        """Marca un render como exitoso"""
        render = self.session.query(RenderHistory).get(render_id)
        if render:
            render.is_successful = True
            render.user_rating = rating
            render.user_notes = notes
            render.marked_for_training = for_training
            self.session.commit()
            
            # Actualizar rating del preset si existe
            if render.preset_id:
                self.update_preset_rating(render.preset_id, rating)
    
    def get_successful_renders(self, min_rating: int = 4) -> List[RenderHistory]:
        """Obtiene renders exitosos para entrenamiento"""
        return self.session.query(RenderHistory).filter(
            RenderHistory.is_successful == True,
            RenderHistory.user_rating >= min_rating,
            RenderHistory.marked_for_training == True
        ).all()
    
    def get_render_history(self, limit: int = 50) -> List[RenderHistory]:
        """Obtiene historial reciente de renders"""
        return self.session.query(RenderHistory).order_by(
            RenderHistory.created_at.desc()
        ).limit(limit).all()
    
    # ===== EMBEDDINGS DE ESTILO =====
    
    def save_style_embedding(self, render_id: int, embedding_data: Dict) -> StyleEmbedding:
        """Guarda embedding de estilo de un render"""
        embedding = StyleEmbedding(
            render_id=render_id,
            embedding_vector=json.dumps(embedding_data.get('vector', [])),
            dominant_colors=json.dumps(embedding_data.get('colors', [])),
            brightness=embedding_data.get('brightness', 0.0),
            contrast=embedding_data.get('contrast', 0.0),
            saturation=embedding_data.get('saturation', 0.0),
            detected_materials=json.dumps(embedding_data.get('materials', [])),
            detected_furniture=json.dumps(embedding_data.get('furniture', [])),
            lighting_type=embedding_data.get('lighting', 'unknown')
        )
        self.session.add(embedding)
        self.session.commit()
        return embedding
    
    # ===== MÉTRICAS DE APRENDIZAJE =====
    
    def update_learning_metrics(self):
        """Actualiza métricas de aprendizaje del sistema"""
        
        # Obtener o crear registro de métricas
        metrics = self.session.query(LearningMetrics).first()
        if not metrics:
            metrics = LearningMetrics()
            self.session.add(metrics)
        
        # Calcular métricas
        all_renders = self.session.query(RenderHistory).all()
        successful = [r for r in all_renders if r.is_successful == True]
        
        metrics.total_renders = len(all_renders)
        metrics.successful_renders = len(successful)
        metrics.success_rate = len(successful) / len(all_renders) if all_renders else 0.0
        
        # Prompts más exitosos
        successful_prompts = {}
        for render in successful:
            prompt = render.material_prompt
            if prompt not in successful_prompts:
                successful_prompts[prompt] = {'count': 0, 'avg_rating': 0, 'ratings': []}
            successful_prompts[prompt]['count'] += 1
            if render.user_rating:
                successful_prompts[prompt]['ratings'].append(render.user_rating)
        
        # Calcular promedios
        for prompt in successful_prompts:
            ratings = successful_prompts[prompt]['ratings']
            if ratings:
                successful_prompts[prompt]['avg_rating'] = sum(ratings) / len(ratings)
        
        # Ordenar por rating y guardar top 20
        top_prompts = sorted(
            successful_prompts.items(),
            key=lambda x: (x[1]['avg_rating'], x[1]['count']),
            reverse=True
        )[:20]
        
        metrics.successful_prompts = json.dumps([
            {'prompt': p, 'count': d['count'], 'avg_rating': d['avg_rating']}
            for p, d in top_prompts
        ])
        
        # Materiales favoritos
        materials_count = {}
        for render in successful:
            # Extraer palabras clave de materiales
            words = render.material_prompt.lower().split()
            material_keywords = ['wood', 'oak', 'walnut', 'marble', 'concrete', 
                               'fabric', 'linen', 'leather', 'metal', 'glass']
            for word in words:
                for keyword in material_keywords:
                    if keyword in word:
                        materials_count[keyword] = materials_count.get(keyword, 0) + 1
        
        metrics.favorite_materials = json.dumps(materials_count)
        
        # Estilos favoritos
        styles_count = {}
        for render in successful:
            style = render.style_preset
            if style:
                styles_count[style] = styles_count.get(style, 0) + 1
        
        metrics.favorite_styles = json.dumps(styles_count)
        
        metrics.updated_at = datetime.utcnow()
        self.session.commit()
        
        return metrics
    
    def get_learning_insights(self) -> Dict:
        """Obtiene insights de aprendizaje del sistema"""
        metrics = self.session.query(LearningMetrics).first()
        if not metrics:
            return {}
        
        return {
            'total_renders': metrics.total_renders,
            'successful_renders': metrics.successful_renders,
            'success_rate': metrics.success_rate,
            'top_prompts': json.loads(metrics.successful_prompts) if metrics.successful_prompts else [],
            'favorite_materials': json.loads(metrics.favorite_materials) if metrics.favorite_materials else {},
            'favorite_styles': json.loads(metrics.favorite_styles) if metrics.favorite_styles else {}
        }
    
    def close(self):
        """Cierra la sesión"""
        self.session.close()
