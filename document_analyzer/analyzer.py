"""
Fachada principal DocumentAnalyzer que orquesta todas las validaciones de calidad.
"""
from __future__ import annotations

import time
from typing import Optional, Union

import cv2
import numpy as np

from document_analyzer.blank_detector import detect_blank
from document_analyzer.blur_detector import detect_blur
from document_analyzer.image_loader import load_image
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


class DocumentAnalyzer:
    """
    Analizador integral de calidad para documentos escaneados o fotografiados.

    Valida:
    1. Si la hoja está en blanco (blank page).
    2. Si la hoja está borrosa o desenfocada (blur / Laplacian variance).
    3. Si la hoja está rotada (0°, 90°, 180°, 270°) o inclinada (skew angle).
    """

    def __init__(
        self,
        blur_threshold: float = 100.0,
        blank_ink_threshold_percent: float = 0.35,
        blank_std_threshold: float = 10.0,
        skew_tolerance_deg: float = 1.0,
        download_timeout_seconds: float = 12.0
    ) -> None:
        """
        Inicializa el analizador con umbrales configurables.

        Args:
            blur_threshold: Varianza mínima del Laplaciano (por debajo es borroso).
            blank_ink_threshold_percent: Porcentaje máximo de tinta para considerarse en blanco.
            blank_std_threshold: Desviación estándar mínima para considerarse en blanco.
            skew_tolerance_deg: Tolerancia en grados antes de marcar inclinación.
            download_timeout_seconds: Tiempo límite de red para URLs.
        """
        self.blur_threshold = blur_threshold
        self.blank_ink_threshold_percent = blank_ink_threshold_percent
        self.blank_std_threshold = blank_std_threshold
        self.skew_tolerance_deg = skew_tolerance_deg
        self.download_timeout_seconds = download_timeout_seconds

    def analyze(
        self,
        source: Union[str, bytes, np.ndarray]
    ) -> DocumentQualityReport:
        """
        Ejecuta el pipeline completo de análisis sobre el documento provisto.

        Args:
            source: URL web (http/https), ruta de archivo local, bytes binarios o ndarray.

        Returns:
            DocumentQualityReport: Reporte estructurado con todas las métricas y diagnóstico.
        """
        start_time = time.perf_counter()

        # Determinar etiqueta de origen para el reporte
        if isinstance(source, str):
            source_label = source
        elif isinstance(source, bytes):
            source_label = f"<bytes en memoria ({len(source)} bytes)>"
        else:
            source_label = f"<ndarray {source.shape}>"

        # 1. Cargar imagen (desde URL, disco o memoria)
        image = load_image(source, timeout_seconds=self.download_timeout_seconds)
        h, w = image.shape[:2]

        # 2. Análisis de página en blanco
        blank_result = detect_blank(
            image,
            ink_threshold_percent=self.blank_ink_threshold_percent,
            std_threshold=self.blank_std_threshold
        )

        if blank_result.is_blank:
            # Si la hoja está totalmente vacía, no tiene sentido evaluar nitidez de texto ni rotación
            blur_result = BlurAnalysis(
                is_blurry=False,
                laplacian_variance=0.0,
                sharpness_score=0.0,
                threshold=self.blur_threshold,
                details="No evaluado: la hoja está en blanco (no hay texto ni trazos para medir nitidez)."
            )
            orientation_result = OrientationAnalysis(
                is_skewed=False,
                skew_angle_deg=0.0,
                cardinal_orientation_deg=0,
                is_rotated=False,
                recommended_correction_deg=0.0,
                details="No evaluado: la hoja está en blanco (no contiene patrones orientables)."
            )
            is_acceptable = False
        else:
            # 3. Análisis de borrosidad / desenfoque
            blur_result = detect_blur(
                image,
                blur_threshold=self.blur_threshold
            )

            # 4. Análisis de inclinación y orientación cardinal
            orientation_result = detect_orientation_and_skew(
                image,
                skew_tolerance_deg=self.skew_tolerance_deg
            )

            # Criterio de calidad aceptable para procesamiento automático / OCR:
            # No debe estar en blanco, no debe estar borrosa, y no debe estar invertida
            is_acceptable = (not blur_result.is_blurry) and (orientation_result.cardinal_orientation_deg == 0)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return DocumentQualityReport(
            source=source_label,
            image_size=(w, h),
            blank=blank_result,
            blur=blur_result,
            orientation=orientation_result,
            is_acceptable_quality=is_acceptable,
            processing_time_ms=round(elapsed_ms, 2)
        )

    def correct_document(
        self,
        source: Union[str, bytes, np.ndarray],
        report: Optional[DocumentQualityReport] = None
    ) -> np.ndarray:
        """
        Devuelve la imagen corregida (enderezada y reorientada a 0°).

        Args:
            source: Imagen o origen a corregir.
            report: Reporte previamente generado con analyze(), o None para generarlo al vuelo.

        Returns:
            np.ndarray: Imagen rotada y nivelada con fondo limpio.
        """
        image = load_image(source, timeout_seconds=self.download_timeout_seconds)

        if report is None:
            report = self.analyze(image)

        if report.blank.is_blank:
            return image

        correction_deg = report.orientation.recommended_correction_deg
        return correct_image_orientation(image, correction_deg)
