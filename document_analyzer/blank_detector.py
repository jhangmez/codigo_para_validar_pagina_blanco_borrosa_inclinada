"""
Detector de páginas en blanco para documentos digitalizados.
"""
from __future__ import annotations

import cv2
import numpy as np

from document_analyzer.models import BlankAnalysis


def detect_blank(
    image: np.ndarray,
    ink_threshold_percent: float = 0.35,
    std_threshold: float = 10.0,
    margin_crop_percent: float = 0.03
) -> BlankAnalysis:
    """
    Determina si un documento está en blanco o carece de contenido sustancial.

    Algoritmo:
    1. Conversión a escala de grises.
    2. Recorte perimetral (default 3%) para descartar sombras de escáner o bordes negros.
    3. Cálculo de la desviación estándar de intensidades de grises.
    4. Binarización mediante umbralización Otsu + umbral adaptativo para calcular
       el porcentaje de píxeles oscuros (tinta/texto).
    5. Evaluación conjunta de métricas.

    Args:
        image: Matriz OpenCV (BGR o escala de grises).
        ink_threshold_percent: Porcentaje máximo de píxeles de tinta para considerarse en blanco (ej. 0.35%).
        std_threshold: Desviación estándar mínima para considerar que existe contenido variado.
        margin_crop_percent: Porcentaje de margen a recortar en cada borde (0.0 a 0.1).

    Returns:
        BlankAnalysis: Resultado con bandera booleana, métricas cuantitativas y descripción.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape

    # 1. Recortar márgenes exteriores si la imagen es suficientemente grande
    if h > 50 and w > 50 and margin_crop_percent > 0:
        my = int(h * margin_crop_percent)
        mx = int(w * margin_crop_percent)
        cropped = gray[my:h - my, mx:w - mx]
    else:
        cropped = gray

    total_pixels = cropped.size
    if total_pixels == 0:
        return BlankAnalysis(
            is_blank=True,
            ink_ratio_percent=0.0,
            std_deviation=0.0,
            confidence=1.0,
            details="La imagen recortada tiene tamaño 0."
        )

    # 2. Desviación estándar de los niveles de gris
    std_dev = float(np.std(cropped))

    # 3. Detección de píxeles de tinta/contenido
    # Aplicamos filtro de mediana ligero para eliminar motas microscópicas de polvo
    denoised = cv2.medianBlur(cropped, 3)

    # Binarización: consideramos píxel de contenido si es significativamente más oscuro que el fondo
    # En un documento estándar blanco (~230-255), tinta suele ser < 195
    _, otsu_thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    dark_mask = (denoised < 195)
    
    # Combinamos para evitar que variaciones suaves de iluminación engañen a Otsu
    ink_mask = cv2.bitwise_and(otsu_thresh, otsu_thresh, mask=dark_mask.astype(np.uint8) * 255)
    ink_pixels = cv2.countNonZero(ink_mask)
    ink_ratio = (ink_pixels / total_pixels) * 100.0

    # 4. Decisión
    is_blank = False
    confidence = 0.95

    if ink_ratio < (ink_threshold_percent * 0.5) and std_dev < std_threshold:
        # Prácticamente nulo contenido
        is_blank = True
        confidence = 0.99
        details = (
            f"Página en blanco confirmada. Cobertura de tinta: {ink_ratio:.3f}% "
            f"(umbral: {ink_threshold_percent}%), Desv. Estándar: {std_dev:.2f}."
        )
    elif ink_ratio < ink_threshold_percent:
        is_blank = True
        confidence = 0.90
        details = (
            f"Página considerada en blanco (rastros mínimos de ruido o marcas tenues). "
            f"Cobertura de tinta: {ink_ratio:.3f}%, Desv. Estándar: {std_dev:.2f}."
        )
    elif std_dev < (std_threshold * 0.7):
        # Superficie extremadamente homogénea
        is_blank = True
        confidence = 0.88
        details = (
            f"Superficie homogénea sin contraste detectable. "
            f"Desv. Estándar: {std_dev:.2f} (umbral: {std_threshold})."
        )
    else:
        is_blank = False
        confidence = min(0.99, round(0.70 + (ink_ratio / 5.0) * 0.29, 2))
        details = (
            f"Documento con contenido detectado. Cobertura de tinta: {ink_ratio:.3f}%, "
            f"Desv. Estándar: {std_dev:.2f}."
        )

    return BlankAnalysis(
        is_blank=is_blank,
        ink_ratio_percent=round(ink_ratio, 4),
        std_deviation=round(std_dev, 2),
        confidence=round(confidence, 2),
        details=details
    )
