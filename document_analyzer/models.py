"""
Modelos de datos tipados para el análisis de calidad de documentos.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Tuple


@dataclass
class BlankAnalysis:
    """Resultado del análisis de página en blanco."""
    is_blank: bool
    ink_ratio_percent: float
    std_deviation: float
    confidence: float
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BlurAnalysis:
    """Resultado del análisis de borrosidad / nitidez."""
    is_blurry: bool
    laplacian_variance: float
    sharpness_score: float  # Escala 0-100
    threshold: float
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrientationAnalysis:
    """Resultado del análisis de orientación e inclinación geométrica."""
    is_skewed: bool
    skew_angle_deg: float
    cardinal_orientation_deg: int  # 0, 90, 180, 270
    is_rotated: bool
    recommended_correction_deg: float
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentQualityReport:
    """Reporte integral del estado y calidad del documento analizado."""
    source: str
    image_size: Tuple[int, int]  # (width, height)
    blank: BlankAnalysis
    blur: BlurAnalysis
    orientation: OrientationAnalysis
    is_acceptable_quality: bool
    processing_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
