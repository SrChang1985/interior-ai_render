# database/models.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class MaterialPreset(Base):
    """Presets de materiales guardados"""
    __tablename__ = 'material_presets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    material_prompt = Column(Text, nullable=False)
    style_preset = Column(String(100))
    custom_style = Column(Text)
    category = Column(String(50))  # 'living_room', 'bedroom', 'dining', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    times_used = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    
    renders = relationship("RenderHistory", back_populates="preset")

class RenderHistory(Base):
    """Historial de renders generados"""
    __tablename__ = 'render_history'
    
    id = Column(Integer, primary_key=True)
    
    # Información del render
    input_image_path = Column(String(500), nullable=False)
    output_image_path = Column(String(500), nullable=False)
    control_image_path = Column(String(500))
    
    # Configuración usada
    preset_id = Column(Integer, ForeignKey('material_presets.id'))
    material_prompt = Column(Text, nullable=False)
    style_preset = Column(String(100))
    custom_style = Column(Text)
    resolution = Column(Integer)
    steps = Column(Integer)
    guidance_scale = Column(Float)
    control_strength = Column(Float)
    seed = Column(Integer)
    
    # Hardware usado
    hardware_category = Column(String(50))
    device_used = Column(String(20))  # 'cpu', 'cuda', 'mps'
    
    # Métricas
    generation_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Feedback del usuario
    is_successful = Column(Boolean, default=None)  # None = no evaluado
    user_rating = Column(Integer)  # 1-5 estrellas
    user_notes = Column(Text)
    marked_for_training = Column(Boolean, default=False)
    
    preset = relationship("MaterialPreset", back_populates="renders")
    embeddings = relationship("StyleEmbedding", back_populates="render", uselist=False)

class StyleEmbedding(Base):
    """Embeddings de estilo para aprendizaje"""
    __tablename__ = 'style_embeddings'
    
    id = Column(Integer, primary_key=True)
    render_id = Column(Integer, ForeignKey('render_history.id'), unique=True)
    
    # Embedding vectorial del estilo (guardado como JSON)
    embedding_vector = Column(Text)  # JSON array
    
    # Características extraídas
    dominant_colors = Column(Text)  # JSON array de colores RGB
    brightness = Column(Float)
    contrast = Column(Float)
    saturation = Column(Float)
    
    # Clasificación de contenido
    detected_materials = Column(Text)  # JSON array
    detected_furniture = Column(Text)  # JSON array
    lighting_type = Column(String(50))  # 'natural', 'artificial', 'mixed'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    render = relationship("RenderHistory", back_populates="embeddings")

class LearningMetrics(Base):
    """Métricas de aprendizaje del sistema"""
    __tablename__ = 'learning_metrics'
    
    id = Column(Integer, primary_key=True)
    
    # Prompts más exitosos
    successful_prompts = Column(Text)  # JSON array
    
    # Materiales preferidos del usuario
    favorite_materials = Column(Text)  # JSON object
    favorite_styles = Column(Text)  # JSON object
    
    # Configuraciones óptimas
    optimal_settings_per_category = Column(Text)  # JSON object
    
    # Estadísticas
    total_renders = Column(Integer, default=0)
    successful_renders = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Crear engine y sesión
engine = create_engine('sqlite:///data/renders.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
