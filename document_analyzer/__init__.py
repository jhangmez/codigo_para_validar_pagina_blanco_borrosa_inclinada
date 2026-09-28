"""
Document Analyzer - Herramienta de alta eficiencia para control de calidad de documentos.

Detección de:
- Hoja en blanco
- Hoja borrosa (Laplacian variance)
- Inclinación y rotación (0°, 90°, 180°, 270°)
"""
from document_analyzer.analyzer import DocumentAnalyzer
from document_analyzer.blank_detector import detect_blank
from document_analyzer.blur_detector import detect_blur
from document_analyzer.image_loader import ImageLoadError, load_image
from document_analyzer.models import (
    BlankAnalysis,
    BlurAnalysis,
    DocumentQualityReport,
    OrientationAnalysis,
)
from document_analyzer.orientation_detector import (
    correct_image_orientation,
    detect_orientation_and_skew,
)

__all__ = [
    "DocumentAnalyzer",
    "BlankAnalysis",
    "BlurAnalysis",
    "OrientationAnalysis",
    "DocumentQualityReport",
    "detect_blank",
    "detect_blur",
    "detect_orientation_and_skew",
    "correct_image_orientation",
    "load_image",
    "ImageLoadError",
]
