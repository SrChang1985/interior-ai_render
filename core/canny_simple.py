# -*- coding: utf-8 -*-
"""
Detector de bordes Canny simple sin OpenCV
"""
from PIL import Image
import numpy as np
from skimage import feature

class CannyDetector:
    """Detector Canny usando scikit-image"""
    
    def __call__(self, image, low_threshold=100, high_threshold=200):
        """
        Detecta bordes usando algoritmo Canny
        
        Args:
            image: PIL Image
            low_threshold: Umbral bajo (0-255)
            high_threshold: Umbral alto (0-255)
            
        Returns:
            PIL Image con bordes detectados
        """
        # Convertir a escala de grises
        if image.mode != 'L':
            image = image.convert('L')
        
        gray = np.array(image)
        
        # Normalizar umbrales (0-1)
        low = low_threshold / 255.0
        high = high_threshold / 255.0
        
        # Aplicar Canny
        edges = feature.canny(
            gray,
            sigma=1.0,
            low_threshold=low,
            high_threshold=high
        )
        
        # Convertir a imagen RGB
        edges_uint8 = (edges * 255).astype(np.uint8)
        edges_rgb = Image.fromarray(edges_uint8).convert('RGB')
        
        return edges_rgb
