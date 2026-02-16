"""
Sistema de detección de bordes sin OpenCV
Implementa múltiples algoritmos combinables para mejor calidad
"""

from PIL import Image, ImageFilter, ImageOps
import numpy as np


class SimplePillowEdgeDetector:
    """
    Detector de bordes básico usando solo Pillow
    Rápido y ligero, sin dependencias adicionales
    """
    
    def __call__(self, image, threshold=128):
        """
        Detecta bordes usando filtros de Pillow
        
        Args:
            image: PIL Image
            threshold: Umbral para binarización (0-255)
            
        Returns:
            PIL Image con bordes detectados
        """
        # Convertir a escala de grises
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image
        
        # Aplicar filtro de detección de bordes
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # Mejorar contraste
        edges = ImageOps.autocontrast(edges)
        
        # Binarizar
        edges = edges.point(lambda x: 255 if x > threshold else 0)
        
        # Convertir a RGB para ControlNet
        return edges.convert('RGB')


class SobelEdgeDetector:
    """
    Detector de bordes usando operador Sobel
    Mejor calidad que Pillow, requiere scipy
    """
    
    def __call__(self, image, threshold=30):
        """
        Detecta bordes usando operador Sobel
        
        Args:
            image: PIL Image
            threshold: Umbral para binarización
            
        Returns:
            PIL Image con bordes detectados
        """
        try:
            from scipy import ndimage
        except ImportError:
            print("⚠️  scipy no disponible, usando SimplePillowEdgeDetector")
            return SimplePillowEdgeDetector()(image)
        
        # Convertir a escala de grises y array
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image
        
        gray_array = np.array(gray)
        
        # Operador Sobel en X e Y
        sobel_x = ndimage.sobel(gray_array, axis=1)
        sobel_y = ndimage.sobel(gray_array, axis=0)
        
        # Magnitud del gradiente
        magnitude = np.hypot(sobel_x, sobel_y)
        
        # Normalizar a 0-255
        magnitude = (magnitude / magnitude.max() * 255).astype(np.uint8)
        
        # Binarizar
        magnitude[magnitude < threshold] = 0
        magnitude[magnitude >= threshold] = 255
        
        # Convertir a PIL Image RGB
        return Image.fromarray(magnitude).convert('RGB')


class SkimageCannyDetector:
    """
    Detector Canny usando scikit-image
    Mejor calidad, algoritmo Canny completo
    """
    
    def __call__(self, image, sigma=1.0, low_threshold=0.1, high_threshold=0.3):
        """
        Detecta bordes usando algoritmo Canny
        
        Args:
            image: PIL Image
            sigma: Desviación estándar del filtro Gaussiano
            low_threshold: Umbral bajo (0-1)
            high_threshold: Umbral alto (0-1)
            
        Returns:
            PIL Image con bordes detectados
        """
        try:
            from skimage import feature
        except ImportError:
            print("⚠️  scikit-image no disponible, usando SobelEdgeDetector")
            return SobelEdgeDetector()(image)
        
        # Convertir a escala de grises y array
        if image.mode != 'L':
            gray = image.convert('L')
        else:
            gray = image
        
        gray_array = np.array(gray)
        
        # Aplicar algoritmo Canny
        edges = feature.canny(
            gray_array,
            sigma=sigma,
            low_threshold=low_threshold,
            high_threshold=high_threshold
        )
        
        # Convertir booleano a uint8
        edges_uint8 = (edges * 255).astype(np.uint8)
        
        # Convertir a PIL Image RGB
        return Image.fromarray(edges_uint8).convert('RGB')


class MultiScaleEdgeDetector:
    """
    Detector multi-escala usando pirámide Gaussiana
    Detecta bordes a diferentes escalas y los combina
    """
    
    def __call__(self, image, scales=[1.0, 0.5, 0.25]):
        """
        Detecta bordes a múltiples escalas
        
        Args:
            image: PIL Image
            scales: Lista de escalas a procesar
            
        Returns:
            PIL Image con bordes detectados
        """
        edges_list = []
        
        for scale in scales:
            # Redimensionar
            if scale != 1.0:
                size = (int(image.width * scale), int(image.height * scale))
                scaled = image.resize(size, Image.Resampling.LANCZOS)
            else:
                scaled = image
            
            # Detectar bordes en esta escala
            gray = scaled.convert('L')
            edges = gray.filter(ImageFilter.FIND_EDGES)
            
            # Volver al tamaño original si es necesario
            if scale != 1.0:
                edges = edges.resize(image.size, Image.Resampling.LANCZOS)
            
            edges_list.append(np.array(edges))
        
        # Combinar escalas (máximo)
        combined = np.max(edges_list, axis=0)
        
        # Normalizar
        if combined.max() > 0:
            combined = (combined / combined.max() * 255).astype(np.uint8)
        else:
            combined = combined.astype(np.uint8)
        
        # Mejorar contraste
        result = Image.fromarray(combined)
        result = ImageOps.autocontrast(result)
        
        return result.convert('RGB')


class HybridEdgeDetector:
    """
    Detector híbrido que combina múltiples métodos
    
    Usa Canny (scikit-image) como principal y Sobel como complemento
    para obtener los mejores resultados sin OpenCV
    
    Este es el detector recomendado para el MVP
    """
    
    def __init__(self, primary='canny', secondary='sobel', combine_weight=0.7):
        """
        Inicializa el detector híbrido
        
        Args:
            primary: Detector principal ('canny', 'sobel', 'pillow')
            secondary: Detector secundario ('canny', 'sobel', 'pillow', None)
            combine_weight: Peso del detector principal (0-1)
        """
        self.primary = primary
        self.secondary = secondary
        self.combine_weight = combine_weight
        
        # Inicializar detectores
        self.detectors = {
            'canny': SkimageCannyDetector(),
            'sobel': SobelEdgeDetector(),
            'pillow': SimplePillowEdgeDetector(),
            'multiscale': MultiScaleEdgeDetector()
        }
    
    def __call__(self, image):
        """
        Detecta bordes usando método híbrido
        
        Args:
            image: PIL Image
            
        Returns:
            PIL Image con bordes detectados
        """
        # Detector principal
        try:
            primary_detector = self.detectors.get(self.primary, self.detectors['canny'])
            primary_edges = primary_detector(image)
        except Exception as e:
            print(f"⚠️  Error en detector principal ({self.primary}): {e}")
            print("   Usando fallback...")
            primary_edges = SimplePillowEdgeDetector()(image)
        
        # Si no hay secundario, retornar solo el primario
        if self.secondary is None or self.secondary == self.primary:
            return primary_edges
        
        # Detector secundario
        try:
            secondary_detector = self.detectors.get(self.secondary, self.detectors['sobel'])
            secondary_edges = secondary_detector(image)
        except Exception as e:
            print(f"⚠️  Error en detector secundario ({self.secondary}): {e}")
            return primary_edges
        
        # Combinar ambos detectores
        primary_array = np.array(primary_edges.convert('L'))
        secondary_array = np.array(secondary_edges.convert('L'))
        
        # Promedio ponderado
        combined = (
            primary_array * self.combine_weight +
            secondary_array * (1 - self.combine_weight)
        ).astype(np.uint8)
        
        # Mejorar contraste
        result = Image.fromarray(combined)
        result = ImageOps.autocontrast(result)
        
        # Aplicar un poco de suavizado para reducir ruido
        result = result.filter(ImageFilter.SMOOTH_MORE)
        
        # Realzar bordes finales
        result = ImageOps.autocontrast(result)
        
        return result.convert('RGB')


# Configuraciones preestablecidas
def get_detector(quality='balanced'):
    """
    Obtiene un detector preconfigurado
    
    Args:
        quality: 'fast', 'balanced', 'high', 'ultra'
        
    Returns:
        Detector de bordes configurado
    """
    configs = {
        'fast': {
            'primary': 'pillow',
            'secondary': None,
            'combine_weight': 1.0
        },
        'balanced': {
            'primary': 'canny',
            'secondary': 'sobel',
            'combine_weight': 0.7
        },
        'high': {
            'primary': 'canny',
            'secondary': 'multiscale',
            'combine_weight': 0.6
        },
        'ultra': {
            'primary': 'multiscale',
            'secondary': 'canny',
            'combine_weight': 0.5
        }
    }
    
    config = configs.get(quality, configs['balanced'])
    return HybridEdgeDetector(**config)


# Para retrocompatibilidad con el código existente
class CannyDetector(HybridEdgeDetector):
    """
    Alias para retrocompatibilidad
    Usa el detector híbrido por defecto
    """
    def __init__(self):
        super().__init__(primary='canny', secondary='sobel', combine_weight=0.7)


if __name__ == "__main__":
    # Test de detectores
    print("🧪 Test de detectores de bordes\n")
    
    # Crear imagen de prueba
    from PIL import ImageDraw
    
    test_img = Image.new('RGB', (256, 256), color='white')
    draw = ImageDraw.Draw(test_img)
    draw.rectangle([50, 50, 200, 200], fill='black')
    draw.ellipse([80, 80, 170, 170], fill='gray')
    
    detectors_to_test = {
        'Pillow (Fast)': SimplePillowEdgeDetector(),
        'Sobel': SobelEdgeDetector(),
        'Canny (scikit-image)': SkimageCannyDetector(),
        'Multi-Scale': MultiScaleEdgeDetector(),
        'Hybrid (Balanced)': get_detector('balanced'),
        'Hybrid (High)': get_detector('high')
    }
    
    print("Detectores disponibles:")
    for name, detector in detectors_to_test.items():
        try:
            result = detector(test_img)
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ❌ {name}: {str(e)[:50]}")
    
    print("\n✅ Detector recomendado para MVP: HybridEdgeDetector")
