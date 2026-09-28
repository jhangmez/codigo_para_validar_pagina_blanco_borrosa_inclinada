"""
Detector de borrosidad y cálculo de nitidez basado en la Varianza del Laplaciano.
"""
from __future__ import annotations

import cv2
import numpy as np

from document_analyzer.models import BlurAnalysis


def detect_blur(
    image: np.ndarray,
    blur_threshold: float = 100.0,
    k_normalization: float = 200.0
) -> BlurAnalysis:
    """
    Evalúa la nitidez del documento y detecta si está desenfocado o borroso.

    Fundamento Matemático:
    Aplica el operador Laplaciano (segunda derivada espacial en 2D) sobre la imagen
    en escala de grises. Las letras y trazos nítidos generan altas frecuencias espaciales
    con grandes gradientes de intensidad, lo que produce una alta varianza estadística.
    Las imágenes borrosas sufren atenuación de frecuencias altas y presentan transiciones
    suaves, resultando en una varianza del Laplaciano baja.

    Args:
        image: Matriz de imagen OpenCV (BGR o escala de grises).
        blur_threshold: Varianza mínima recomendada. Por debajo de este valor se considera borrosa.
                        Valores típicos: 80.0 a 150.0 según la resolución.
        k_normalization: Constante para normalizar el índice de nitidez en la curva sigmoidal 0-100.

    Returns:
        BlurAnalysis: Objeto con estado booleano, varianza exacta, score 0-100 y explicación.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Cálculo del operador Laplaciano con profundidad de punto flotante de 64 bits (CV_64F)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())

    # Índice de nitidez normalizado de 0 a 100 (función no lineal)
    sharpness_score = round(min(100.0, (variance / (variance + k_normalization)) * 100.0), 1)

    is_blurry = variance < blur_threshold

    if is_blurry:
        details = (
            f"Documento borroso o desenfocado. Varianza Laplaciana: {variance:.2f} "
            f"(umbral requerido: {blur_threshold:.1f}, nitidez: {sharpness_score}/100)."
        )
    else:
        details = (
            f"Documento nítido y legible. Varianza Laplaciana: {variance:.2f} "
            f"(superior al umbral {blur_threshold:.1f}, nitidez: {sharpness_score}/100)."
        )

    return BlurAnalysis(
        is_blurry=is_blurry,
        laplacian_variance=round(variance, 2),
        sharpness_score=sharpness_score,
        threshold=blur_threshold,
        details=details
    )
