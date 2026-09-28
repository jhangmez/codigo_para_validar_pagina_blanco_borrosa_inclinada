#!/usr/bin/env python3
"""
Punto de entrada CLI para análisis de calidad de documentos.
Permite evaluar imágenes mediante URL web o archivos locales.
"""
from __future__ import annotations

import argparse
import os
import sys
import cv2

from document_analyzer import DocumentAnalyzer
from tests.generate_samples import generate_all_samples


def format_colored_report(report) -> str:
    """Genera un reporte formateado para terminal con indicadores visuales claros."""
    lines = []
    w, h = report.image_size
    lines.append("=" * 65)
    lines.append(" 📋 REPORTE DE CONTROL DE CALIDAD DOCUMENTAL")
    lines.append("=" * 65)
    lines.append(f"• Origen:          {report.source}")
    lines.append(f"• Dimensiones:     {w} x {h} píxeles")
    lines.append(f"• Tiempo cómputo:  {report.processing_time_ms:.1f} ms")
    lines.append("-" * 65)

    # 1. Página en blanco
    if report.blank.is_blank:
        blank_icon = "⚠️  [EN BLANCO]"
    else:
        blank_icon = "✅ [CON CONTENIDO]"
    lines.append(f"1. CONTENIDO / HOJA EN BLANCO: {blank_icon}")
    lines.append(f"   - ¿Está en blanco?: {'SÍ' if report.blank.is_blank else 'NO'}")
    lines.append(f"   - Cobertura tinta:  {report.blank.ink_ratio_percent:.3f}%")
    lines.append(f"   - Desv. estándar:   {report.blank.std_deviation:.2f}")
    lines.append(f"   - Diagnóstico:      {report.blank.details}")
    lines.append("-" * 65)

    # 2. Borrosidad
    if report.blur.is_blurry:
        blur_icon = "❌ [BORROSO / DESENFOCADO]"
    else:
        blur_icon = "✅ [NÍTIDO]"
    lines.append(f"2. ENFOQUE / NITIDEZ:           {blur_icon}")
    lines.append(f"   - ¿Está borrosa?:   {'SÍ' if report.blur.is_blurry else 'NO'}")
    lines.append(f"   - Varianza Laplace: {report.blur.laplacian_variance:.1f} (Umbral min: {report.blur.threshold:.1f})")
    lines.append(f"   - Score de nitidez: {report.blur.sharpness_score}/100")
    lines.append(f"   - Diagnóstico:      {report.blur.details}")
    lines.append("-" * 65)

    # 3. Orientación e Inclinación
    if report.orientation.is_rotated:
        orient_icon = "⚠️  [DESALINEADO / ROTADO]"
    else:
        orient_icon = "✅ [CORRECTO]"
    lines.append(f"3. ORIENTACIÓN E INCLINACIÓN:  {orient_icon}")
    lines.append(f"   - Orientación:      {report.orientation.cardinal_orientation_deg}°")
    lines.append(f"   - Inclinación:      {report.orientation.skew_angle_deg:+.2f}°")
    lines.append(f"   - Corrección sug.:  {report.orientation.recommended_correction_deg:+.2f}°")
    lines.append(f"   - Diagnóstico:      {report.orientation.details}")
    lines.append("=" * 65)

    # Veredicto general
    if report.is_acceptable_quality:
        verdict = "✅ ACEPTADO PARA PROCESAMIENTO / OCR"
    else:
        reasons = []
        if report.blank.is_blank:
            reasons.append("Hoja en blanco")
        if report.blur.is_blurry:
            reasons.append("Imagen borrosa")
        if report.orientation.cardinal_orientation_deg != 0:
            reasons.append(f"Rotada {report.orientation.cardinal_orientation_deg}°")
        verdict = f"❌ RECHAZADO ({', '.join(reasons)})"

    lines.append(f" VEREDICTO GENERAL: {verdict}")
    lines.append("=" * 65)
    return "\n".join(lines)


def run_demo(analyzer: DocumentAnalyzer) -> None:
    """Genera imágenes de prueba y ejecuta la demostración completa interactiva."""
    print("\n🚀 Generando casos de prueba sintéticos en 'sample_images/'...")
    samples = generate_all_samples("sample_images")

    print("\n" + "#" * 65)
    print(" DEMOSTRACIÓN DE CASOS DE CONTROL DE CALIDAD")
    print("#" * 65)

    for case_name, file_path in samples.items():
        print(f"\n>>> Evaluando caso: [{case_name.upper()}] ({file_path})")
        report = analyzer.analyze(file_path)
        print(format_colored_report(report))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analizador de Calidad de Documentos (Hoja en blanco, borrosidad y orientación).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Analizar una URL de imagen:
  python main.py https://ejemplo.com/factura.jpg

  # Analizar un archivo local:
  python main.py sample_images/01_normal.png

  # Formato JSON (ideal para APIs o microservicios):
  python main.py sample_images/04_inclinada_5grados.png --json

  # Corregir y guardar la imagen enderezada:
  python main.py sample_images/04_inclinada_5grados.png --correct salida_recta.png

  # Ejecutar suite de demostración interactiva:
  python main.py --demo
        """
    )

    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help="URL web (http/https) o ruta de archivo local de la imagen."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta una demostración automática con todos los escenarios posibles."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Devuelve el resultado estrictamente en formato JSON."
    )
    parser.add_argument(
        "--correct",
        metavar="OUTPUT_PATH",
        type=str,
        default=None,
        help="Ruta de archivo para guardar la imagen rotada y enderezada."
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=100.0,
        help="Umbral mínimo de varianza Laplaciana (defecto: 100.0)."
    )
    parser.add_argument(
        "--blank-threshold",
        type=float,
        default=0.35,
        help="Porcentaje máximo de tinta para considerarse en blanco (defecto: 0.35%%)."
    )
    parser.add_argument(
        "--skew-threshold",
        type=float,
        default=1.0,
        help="Tolerancia de inclinación angular en grados (defecto: 1.0°)."
    )

    args = parser.parse_args()

    analyzer = DocumentAnalyzer(
        blur_threshold=args.blur_threshold,
        blank_ink_threshold_percent=args.blank_threshold,
        skew_tolerance_deg=args.skew_threshold
    )

    if args.demo:
        run_demo(analyzer)
        return

    if not args.source:
        parser.print_help()
        print("\n💡 Sugerencia: Ejecuta 'python main.py --demo' para ver una demostración inmediata.")
        sys.exit(1)

    try:
        report = analyzer.analyze(args.source)

        if args.json:
            print(report.to_json())
        else:
            print(format_colored_report(report))

        if args.correct:
            corrected = analyzer.correct_document(args.source, report)
            cv2.imwrite(args.correct, corrected)
            print(f"\n💾 Imagen corregida guardada exitosamente en: '{args.correct}'")

    except Exception as e:
        print(f"\n❌ Error al procesar el documento: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
