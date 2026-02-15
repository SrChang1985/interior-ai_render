# core/lighting_controller.py

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

class ColorTemperature(Enum):
    """Temperaturas de color estándar en Kelvin"""
    CANDLE = 1850          # Luz de vela
    WARM_DIM = 2200        # Incandescente tenue
    WARM = 2700            # Incandescente estándar / Cálida
    SOFT_WHITE = 3000      # Halógena / Blanco suave
    NEUTRAL = 3500         # Neutral
    COOL_WHITE = 4000      # Fluorescente blanca fría
    DAYLIGHT = 5000        # Luz de día
    BRIGHT_DAYLIGHT = 5500 # Luz de día brillante
    CLOUDY_SKY = 6500      # Cielo nublado
    BLUE_SKY = 10000       # Cielo azul

@dataclass
class LightingProfile:
    """Perfil de iluminación completo"""
    name: str
    description: str
    primary_temp: ColorTemperature
    secondary_temp: Optional[ColorTemperature]
    intensity: str  # 'dim', 'medium', 'bright'
    direction: str  # 'natural', 'overhead', 'accent', 'mixed'
    time_of_day: str  # 'morning', 'midday', 'afternoon', 'evening', 'night'
    prompt_keywords: List[str]
    
class LightingController:
    """Controla configuraciones de iluminación para renders"""
    
    def __init__(self):
        self.profiles = self._init_profiles()
    
    def _init_profiles(self) -> Dict[str, LightingProfile]:
        """Inicializa perfiles de iluminación predefinidos"""
        return {
            # ===== ILUMINACIÓN NATURAL =====
            'natural_morning': LightingProfile(
                name='Mañana Natural',
                description='Luz de mañana suave, tonos cálidos',
                primary_temp=ColorTemperature.SOFT_WHITE,
                secondary_temp=None,
                intensity='medium',
                direction='natural',
                time_of_day='morning',
                prompt_keywords=['morning sunlight', 'soft natural light', '3000K warm glow', 
                               'gentle shadows', 'east-facing window light']
            ),
            
            'natural_midday': LightingProfile(
                name='Mediodía Natural',
                description='Luz de día brillante, tonos neutros',
                primary_temp=ColorTemperature.DAYLIGHT,
                secondary_temp=None,
                intensity='bright',
                direction='natural',
                time_of_day='midday',
                prompt_keywords=['bright daylight', 'natural sunlight', '5000K daylight', 
                               'crisp shadows', 'clear sky lighting']
            ),
            
            'natural_golden_hour': LightingProfile(
                name='Hora Dorada',
                description='Atardecer cálido, luz dorada',
                primary_temp=ColorTemperature.WARM,
                secondary_temp=None,
                intensity='medium',
                direction='natural',
                time_of_day='afternoon',
                prompt_keywords=['golden hour', 'warm sunset light', '2700K amber glow', 
                               'long soft shadows', 'late afternoon sunlight']
            ),
            
            # ===== ILUMINACIÓN ARTIFICIAL =====
            'artificial_warm_cozy': LightingProfile(
                name='Ambiente Cálido Acogedor',
                description='Iluminación cálida tipo living, acogedora',
                primary_temp=ColorTemperature.WARM,
                secondary_temp=ColorTemperature.WARM_DIM,
                intensity='dim',
                direction='mixed',
                time_of_day='evening',
                prompt_keywords=['warm ambient lighting', 'cozy 2700K incandescent', 
                               'table lamps', 'warm glow', 'intimate lighting']
            ),
            
            'artificial_neutral_work': LightingProfile(
                name='Trabajo Neutral',
                description='Iluminación neutra para oficinas y cocinas',
                primary_temp=ColorTemperature.NEUTRAL,
                secondary_temp=ColorTemperature.COOL_WHITE,
                intensity='bright',
                direction='overhead',
                time_of_day='midday',
                prompt_keywords=['neutral white lighting', '3500K-4000K LEDs', 
                               'overhead lighting', 'bright even illumination', 
                               'task lighting']
            ),
            
            'artificial_cool_modern': LightingProfile(
                name='Moderno Frío',
                description='Iluminación fría tipo galería o baño',
                primary_temp=ColorTemperature.COOL_WHITE,
                secondary_temp=None,
                intensity='bright',
                direction='overhead',
                time_of_day='midday',
                prompt_keywords=['cool white lighting', '4000K LED', 'modern lighting', 
                               'gallery lighting', 'bright white']
            ),
            
            # ===== ILUMINACIÓN MIXTA =====
            'mixed_scandinavian': LightingProfile(
                name='Escandinavo Mixto',
                description='Natural + cálida artificial (estilo nórdico)',
                primary_temp=ColorTemperature.DAYLIGHT,
                secondary_temp=ColorTemperature.WARM,
                intensity='medium',
                direction='mixed',
                time_of_day='afternoon',
                prompt_keywords=['scandinavian lighting', 'natural daylight with warm accents', 
                               '5000K daylight mixed with 2700K lamps', 
                               'hygge atmosphere', 'soft mixed lighting']
            ),
            
            'mixed_restaurant': LightingProfile(
                name='Restaurante/Bar',
                description='Iluminación de acento con ambiente',
                primary_temp=ColorTemperature.WARM_DIM,
                secondary_temp=ColorTemperature.WARM,
                intensity='dim',
                direction='accent',
                time_of_day='evening',
                prompt_keywords=['restaurant lighting', 'dim 2200K accent lights', 
                               'pendant lamps', 'dramatic shadows', 
                               'intimate dining atmosphere']
            ),
            
            'mixed_boutique': LightingProfile(
                name='Boutique/Retail',
                description='Iluminación comercial con acentos',
                primary_temp=ColorTemperature.NEUTRAL,
                secondary_temp=ColorTemperature.BRIGHT_DAYLIGHT,
                intensity='bright',
                direction='accent',
                time_of_day='midday',
                prompt_keywords=['retail lighting', '3500K track lighting', 
                               'accent spotlights', 'product highlighting', 
                               'commercial bright lighting']
            ),
            
            # ===== ILUMINACIÓN ESPECIAL =====
            'dramatic_studio': LightingProfile(
                name='Estudio Dramático',
                description='Iluminación tipo fotografía profesional',
                primary_temp=ColorTemperature.DAYLIGHT,
                secondary_temp=ColorTemperature.NEUTRAL,
                intensity='bright',
                direction='accent',
                time_of_day='midday',
                prompt_keywords=['studio lighting', 'professional photography lighting', 
                               '5000K key light', 'dramatic shadows', 
                               'architectural photography lighting']
            ),
            
            'sunset_interior': LightingProfile(
                name='Atardecer Interior',
                description='Luz de atardecer entrando por ventanas',
                primary_temp=ColorTemperature.WARM,
                secondary_temp=ColorTemperature.WARM_DIM,
                intensity='medium',
                direction='natural',
                time_of_day='evening',
                prompt_keywords=['sunset through windows', 'warm 2700K sunset glow', 
                               'orange hour', 'warm interior atmosphere', 
                               'dusk lighting']
            ),
            
            'night_ambient': LightingProfile(
                name='Noche Ambiental',
                description='Iluminación nocturna suave',
                primary_temp=ColorTemperature.WARM_DIM,
                secondary_temp=ColorTemperature.CANDLE,
                intensity='dim',
                direction='accent',
                time_of_day='night',
                prompt_keywords=['night ambient lighting', 'dim 2200K warm glow', 
                               'candlelight', 'moonlight through window', 
                               'nighttime cozy atmosphere']
            ),
        }
    
    def get_profile(self, profile_name: str) -> Optional[LightingProfile]:
        """Obtiene un perfil de iluminación por nombre"""
        return self.profiles.get(profile_name)
    
    def get_all_profiles(self) -> List[LightingProfile]:
        """Obtiene todos los perfiles disponibles"""
        return list(self.profiles.values())
    
    def get_profiles_by_category(self, category: str) -> List[LightingProfile]:
        """Obtiene perfiles filtrados por categoría"""
        categories = {
            'natural': ['natural_morning', 'natural_midday', 'natural_golden_hour'],
            'artificial': ['artificial_warm_cozy', 'artificial_neutral_work', 'artificial_cool_modern'],
            'mixed': ['mixed_scandinavian', 'mixed_restaurant', 'mixed_boutique'],
            'special': ['dramatic_studio', 'sunset_interior', 'night_ambient']
        }
        profile_names = categories.get(category, [])
        return [self.profiles[name] for name in profile_names if name in self.profiles]
    
    def build_lighting_prompt(self, profile_name: str, custom_additions: str = '') -> str:
        """Construye el prompt de iluminación completo"""
        profile = self.get_profile(profile_name)
        if not profile:
            return custom_additions
        
        # Construir prompt con keywords del perfil
        lighting_prompt = ', '.join(profile.prompt_keywords)
        
        # Añadir temperatura de color explícita
        temp_description = f"{profile.primary_temp.value}K color temperature"
        
        # Si hay temperatura secundaria
        if profile.secondary_temp:
            temp_description += f" with {profile.secondary_temp.value}K accent lighting"
        
        full_prompt = f"{lighting_prompt}, {temp_description}"
        
        # Añadir descripciones personalizadas
        if custom_additions:
            full_prompt += f", {custom_additions}"
        
        return full_prompt
    
    def get_recommendation(self, room_type: str, time_preference: str = 'any') -> LightingProfile:
        """Recomienda iluminación basada en tipo de habitación y hora"""
        
        recommendations = {
            'living_room': {
                'morning': 'natural_morning',
                'midday': 'mixed_scandinavian',
                'afternoon': 'natural_golden_hour',
                'evening': 'artificial_warm_cozy',
                'night': 'night_ambient',
                'any': 'mixed_scandinavian'
            },
            'bedroom': {
                'morning': 'natural_morning',
                'midday': 'natural_midday',
                'afternoon': 'natural_golden_hour',
                'evening': 'artificial_warm_cozy',
                'night': 'night_ambient',
                'any': 'natural_golden_hour'
            },
            'dining_room': {
                'morning': 'natural_morning',
                'midday': 'natural_midday',
                'afternoon': 'natural_golden_hour',
                'evening': 'mixed_restaurant',
                'night': 'mixed_restaurant',
                'any': 'mixed_restaurant'
            },
            'kitchen': {
                'morning': 'natural_morning',
                'midday': 'natural_midday',
                'afternoon': 'natural_midday',
                'evening': 'artificial_neutral_work',
                'night': 'artificial_neutral_work',
                'any': 'artificial_neutral_work'
            },
            'office': {
                'morning': 'natural_morning',
                'midday': 'artificial_neutral_work',
                'afternoon': 'natural_midday',
                'evening': 'artificial_neutral_work',
                'night': 'artificial_neutral_work',
                'any': 'artificial_neutral_work'
            },
            'bathroom': {
                'morning': 'natural_morning',
                'midday': 'artificial_cool_modern',
                'afternoon': 'artificial_cool_modern',
                'evening': 'artificial_cool_modern',
                'night': 'artificial_warm_cozy',
                'any': 'artificial_cool_modern'
            },
            'commercial': {
                'any': 'mixed_boutique'
            },
            'studio': {
                'any': 'dramatic_studio'
            }
        }
        
        room_recs = recommendations.get(room_type, recommendations['living_room'])
        profile_name = room_recs.get(time_preference, room_recs.get('any'))
        
        return self.profiles.get(profile_name)
    
    def get_lighting_metadata(self, profile_name: str) -> Dict:
        """Obtiene metadata completa del perfil de iluminación"""
        profile = self.get_profile(profile_name)
        if not profile:
            return {}
        
        return {
            'name': profile.name,
            'description': profile.description,
            'primary_temperature_k': profile.primary_temp.value,
            'primary_temperature_name': profile.primary_temp.name,
            'secondary_temperature_k': profile.secondary_temp.value if profile.secondary_temp else None,
            'secondary_temperature_name': profile.secondary_temp.name if profile.secondary_temp else None,
            'intensity': profile.intensity,
            'direction': profile.direction,
            'time_of_day': profile.time_of_day,
            'prompt_keywords': profile.prompt_keywords
        }
