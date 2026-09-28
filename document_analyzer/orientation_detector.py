"""
Detector de inclinación (skew) y orientación cardinal (0°, 90°, 180°, 270°) para documentos.
"""
from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np

from document_analyzer.models import OrientationAnalysis


def detect_orientation_and_skew(
    image: np.ndarray,
    skew_tolerance_deg: float = 1.0,
    search_range_deg: float = 15.0,
    coarse_step_deg: float = 0.5,
    fine_step_deg: float = 0.1
) -> OrientationAnalysis:
    """
    Detecta la orientación de la hoja (0°, 90°, 180°, 270°) y su ángulo de inclinación fina (skew).

    Algoritmo:
    1. Redimensionamiento a resolución óptima (~600px) para ejecución ultrarrápida (<25ms).
    2. Binarización invertida (tinta = blanco, fondo = negro).
    3. Análisis de perfil de proyección ortogonal para discriminar flujo horizontal (0°/180°)
       frente a vertical (90°/270°).
    4. Búsqueda de ángulo de inclinación fina (deskew) maximizando la varianza del perfil.
    5. Análisis de asimetría de la línea base tipográfica (centroides de masa) para
       distinguir 0° de 180° (documento invertido de cabeza) y 90° de 270°.

    Args:
        image: Matriz de imagen OpenCV.
        skew_tolerance_deg: Ángulo mínimo en grados para considerar que la hoja está inclinada.
        search_range_deg: Rango de búsqueda para inclinación leve (ej. +/- 15 grados).
        coarse_step_deg: Paso de búsqueda grueso en grados.
        fine_step_deg: Paso de refinamiento fino en grados.

    Returns:
        OrientationAnalysis: Análisis completo con ángulos, estado y corrección recomendada.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape

    # Redimensionar para análisis rápido sin perder la estructura geométrica
    max_dim = 650.0
    scale = min(1.0, max_dim / max(h, w))
    target_w, target_h = int(w * scale), int(h * scale)
    small = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # Binarización invertida (texto = 255, fondo = 0)
    _, bin_img = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Paso 1: Discriminación entre eje horizontal (0°/180°) y eje vertical (90°/270°)
    row_proj = np.sum(bin_img, axis=1)
    col_proj = np.sum(bin_img, axis=0)

    row_var = float(np.var(row_proj))
    col_var = float(np.var(col_proj))

    # Si col_var supera sensiblemente a row_var, el texto fluye en columnas (girado 90° o 270°)
    is_sideways = col_var > (row_var * 1.35)

    if is_sideways:
        # Rotamos temporalmente 90° para calcular el skew sobre el eje principal
        base_img = cv2.rotate(bin_img, cv2.ROTATE_90_CLOCKWISE)
        cardinal_base = 90
    else:
        base_img = bin_img
        cardinal_base = 0

    # Paso 2: Estimación del ángulo de inclinación fina (Skew)
    skew_angle = _find_best_skew_angle(
        base_img,
        search_range=search_range_deg,
        coarse_step=coarse_step_deg,
        fine_step=fine_step_deg
    )

    # Paso 3: Determinación de la polaridad (0° vs 180°, o 90° vs 270°)
    # Rotamos preliminarmente con el skew corregido para alinear las líneas de texto
    sh, sw = base_img.shape
    center = (sw // 2, sh // 2)
    rot_mat = cv2.getRotationMatrix2D(center, -skew_angle, 1.0)
    aligned_bin = cv2.warpAffine(base_img, rot_mat, (sw, sh), flags=cv2.INTER_NEAREST)

    line_centroid, detected_lines = _analyze_line_centroids(aligned_bin)

    if cardinal_base == 0:
        # En texto latino normal horizontal, el centroide normalizado es > 0.50 (mayor masa en la base)
        # Si está invertido (180°), el centroide cae por debajo de 0.49
        if detected_lines >= 3 and line_centroid < 0.495:
            cardinal_orientation = 180
        else:
            cardinal_orientation = 0
    else:
        # En imagen girada 90° vs 270°
        if detected_lines >= 3 and line_centroid > 0.505:
            cardinal_orientation = 270
        else:
            cardinal_orientation = 90

    # Ángulo total de rotación sugerido para dejar el documento recto a 0°
    # Si está a 180°, hay que rotar 180°. Si además tiene skew de +2°, rotamos 180° - 2°.
    recommended_correction = float((360 - cardinal_orientation - skew_angle) % 360)
    if recommended_correction > 180:
        recommended_correction -= 360  # Normalizar a rango [-180, +180]

    is_skewed = abs(skew_angle) >= skew_tolerance_deg
    is_rotated = (cardinal_orientation != 0) or is_skewed

    # Construcción de la descripción detallada
    desc_parts = []
    if cardinal_orientation != 0:
        desc_parts.append(f"Orientación cardinal invertida o lateral ({cardinal_orientation}°)")
    if is_skewed:
        desc_parts.append(f"Inclinación angular detectada ({skew_angle:+.2f}°)")
    if not desc_parts:
        details = f"Documento en orientación correcta (0°) y nivelado (inclinación: {skew_angle:+.2f}°)."
    else:
        details = (
            f"Desviación detectada: {', '.join(desc_parts)}. "
            f"Corrección sugerida: {recommended_correction:+.2f}°."
        )

    return OrientationAnalysis(
        is_skewed=is_skewed,
        skew_angle_deg=round(skew_angle, 2),
        cardinal_orientation_deg=cardinal_orientation,
        is_rotated=is_rotated,
        recommended_correction_deg=round(recommended_correction, 2),
        details=details
    )


def _find_best_skew_angle(
    bin_img: np.ndarray,
    search_range: float,
    coarse_step: float,
    fine_step: float
) -> float:
    """Busca el ángulo de rotación que maximiza la varianza del perfil de proyección horizontal."""
    h, w = bin_img.shape
    center = (w // 2, h // 2)

    # 1. Búsqueda gruesa
    best_angle = 0.0
    max_variance = -1.0
    coarse_angles = np.arange(-search_range, search_range + coarse_step, coarse_step)

    for ang in coarse_angles:
        mat = cv2.getRotationMatrix2D(center, float(ang), 1.0)
        rotated = cv2.warpAffine(bin_img, mat, (w, h), flags=cv2.INTER_NEAREST)
        proj = np.sum(rotated, axis=1)
        var = float(np.var(proj))
        if var > max_variance:
            max_variance = var
            best_angle = float(ang)

    # 2. Refinamiento fino alrededor del mejor ángulo grueso
    fine_range = coarse_step
    fine_angles = np.arange(
        best_angle - fine_range,
        best_angle + fine_range + (fine_step / 2.0),
        fine_step
    )
    for ang in fine_angles:
        mat = cv2.getRotationMatrix2D(center, float(ang), 1.0)
        rotated = cv2.warpAffine(bin_img, mat, (w, h), flags=cv2.INTER_NEAREST)
        proj = np.sum(rotated, axis=1)
        var = float(np.var(proj))
        if var > max_variance:
            max_variance = var
            best_angle = float(ang)

    # best_angle es la rotación aplicada para enderezar; por ende, el skew original es -best_angle
    return -best_angle


def _analyze_line_centroids(bin_img: np.ndarray) -> Tuple[float, int]:
    """Segmenta líneas horizontales de texto y calcula el centroide de masa vertical promedio."""
    row_sum = np.sum(bin_img, axis=1)
    max_val = np.max(row_sum) if row_sum.size > 0 else 0
    if max_val == 0:
        return 0.5, 0

    threshold = max_val * 0.06
    lines = []
    in_line = False
    start = 0

    for y, val in enumerate(row_sum):
        if val > threshold and not in_line:
            in_line = True
            start = y
        elif val <= threshold and in_line:
            in_line = False
            if y - start >= 6:  # Altura mínima de línea
                lines.append((start, y))

    centroids = []
    for y1, y2 in lines:
        strip = bin_img[y1:y2, :]
        profile = np.sum(strip, axis=1)
        h_line = len(profile)
        total_ink = np.sum(profile)
        if h_line > 5 and total_ink > 0:
            indices = np.arange(h_line)
            centroid = np.sum(indices * profile) / total_ink
            norm_centroid = centroid / (h_line - 1)
            centroids.append(norm_centroid)

    if not centroids:
        return 0.5, 0

    return float(np.mean(centroids)), len(lines)


def correct_image_orientation(image: np.ndarray, correction_deg: float) -> np.ndarray:
    """
    Aplica la rotación y corrección angular sobre la imagen original.

    Args:
        image: Imagen original OpenCV (BGR o Gray).
        correction_deg: Ángulo en grados a rotar (en sentido antihorario/horario estándar).

    Returns:
        np.ndarray: Imagen enderezada con fondo blanco.
    """
    if abs(correction_deg) < 0.05:
        return image.copy()

    # Si es una rotación exacta de 90°, 180° o 270°, usamos cv2.rotate nativo sin pérdidas ni bordes
    deg_round = round(correction_deg) % 360
    if deg_round == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif deg_round == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif deg_round == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Para ángulos arbitrarios o combinados (rotación afín con expansión de lienzo)
    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)
    
    # Matriz de rotación
    rot_mat = cv2.getRotationMatrix2D(center, correction_deg, 1.0)
    
    # Calcular nuevas dimensiones del bounding box para no recortar esquinas
    cos_val = abs(rot_mat[0, 0])
    sin_val = abs(rot_mat[0, 1])
    new_w = int((h * sin_val) + (w * cos_val))
    new_h = int((h * cos_val) + (w * sin_val))
    
    # Ajustar centro en la matriz de traslación
    rot_mat[0, 2] += (new_w / 2.0) - center[0]
    rot_mat[1, 2] += (new_h / 2.0) - center[1]

    # Warp affine rellenando bordes con color blanco (255)
    border_val = (255, 255, 255) if len(image.shape) == 3 else 255
    corrected = cv2.warpAffine(
        image,
        rot_mat,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border_val
    )
    return corrected
