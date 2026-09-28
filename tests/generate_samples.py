"""
Generador de documentos de prueba sintéticos con diferentes patologías de imagen:
- Documento normal (nítido, recto, con contenido)
- Documento en blanco (con y sin leve ruido de escáner)
- Documento borroso (desenfoque gaussiano severo)
- Documento inclinado (skew de 5.5 grados)
- Documento rotado 90°
- Documento invertido 180° (de cabeza)
- Documento rotado 270°
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def create_base_document(width: int = 800, height: int = 1100) -> np.ndarray:
    """Crea una página de documento de alta resolución con texto en español."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Cargar fuentes del sistema o por defecto
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        font_header = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Encabezado
    draw.text((60, 60), "REPORTE TÉCNICO DE AUDITORÍA Y CONTROL", fill=(20, 20, 20), font=font_title)
    draw.text((60, 95), "Departamento de Procesamiento y Calidad Documental", fill=(90, 90, 90), font=font_header)
    draw.line([(60, 120), (740, 120)], fill=(40, 40, 40), width=2)

    # Párrafos de texto
    paragraphs = [
        "1. ANTECEDENTES Y PROPÓSITO DEL SISTEMA:",
        "El presente componente evalúa de manera automática la calidad visual de hojas digitalizadas,",
        "determinando la presencia de contenido textual, nivel de nitidez o borrosidad óptica,",
        "e identificando el grado de inclinación angular y orientación cardinal del documento.",
        "",
        "2. METODOLOGÍA COMPUTACIONAL:",
        "Para la detección de hojas en blanco se combina un filtrado morfológico con el cálculo de",
        "la densidad de píxeles oscuros y la desviación estándar de la escala de grises.",
        "El análisis de borrosidad se fundamenta en la varianza del operador diferencial Laplaciano,",
        "el cual cuantifica las transiciones de alta frecuencia asociadas a bordes nítidos de texto.",
        "La corrección de orientación analiza la varianza de los perfiles de proyección ortogonal",
        "y la asimetría de la línea base tipográfica característica del alfabeto latino.",
        "",
        "3. CONCLUSIÓN Y RECOMENDACIONES:",
        "Los documentos que cumplan con los umbrales de nitidez y nivelación geométrica son derivados",
        "directamente a los motores de reconocimiento óptico de caracteres (OCR) para extracción de entidades."
    ]

    y = 145
    for line in paragraphs:
        if line == "":
            y += 15
            continue
        is_heading = line.startswith(("1.", "2.", "3."))
        f = font_header if is_heading else font_body
        color = (15, 15, 15) if is_heading else (45, 45, 45)
        draw.text((60, y), line, fill=color, font=f)
        y += 24

    # Pie de página
    draw.line([(60, 1020), (740, 1020)], fill=(180, 180, 180), width=1)
    draw.text((60, 1035), "Documento de Validación Interna - Confidencial", fill=(130, 130, 130), font=font_body)
    draw.text((680, 1035), "Pág. 1 de 1", fill=(130, 130, 130), font=font_body)

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def generate_all_samples(output_dir: str = "sample_images") -> dict[str, str]:
    """Genera y guarda en disco los 7 tipos de imágenes de prueba."""
    os.makedirs(output_dir, exist_ok=True)
    base = create_base_document()
    samples = {}

    # 1. Normal
    path_normal = os.path.join(output_dir, "01_normal.png")
    cv2.imwrite(path_normal, base)
    samples["normal"] = path_normal

    # 2. Hoja en blanco
    blank = np.ones_like(base) * 255
    # Añadir un mínimo ruido de sensor de escáner imperceptible
    noise = np.random.normal(0, 1.5, blank.shape).astype(np.int16)
    blank = np.clip(blank.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    path_blank = os.path.join(output_dir, "02_en_blanco.png")
    cv2.imwrite(path_blank, blank)
    samples["blank"] = path_blank

    # 3. Borrosa (desenfoque gaussiano)
    blurry = cv2.GaussianBlur(base, (29, 29), 0)
    path_blurry = os.path.join(output_dir, "03_borrosa.png")
    cv2.imwrite(path_blurry, blurry)
    samples["blurry"] = path_blurry

    # 4. Inclinada 5.5 grados (Skew)
    h, w = base.shape[:2]
    center = (w // 2, h // 2)
    mat_skew = cv2.getRotationMatrix2D(center, 5.5, 1.0)
    skewed = cv2.warpAffine(base, mat_skew, (w, h), borderValue=(255, 255, 255))
    path_skewed = os.path.join(output_dir, "04_inclinada_5grados.png")
    cv2.imwrite(path_skewed, skewed)
    samples["skewed"] = path_skewed

    # 5. Rotada 90° horario
    rot90 = cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE)
    path_90 = os.path.join(output_dir, "05_rotada_90.png")
    cv2.imwrite(path_90, rot90)
    samples["rot90"] = path_90

    # 6. Invertida 180° (de cabeza)
    rot180 = cv2.rotate(base, cv2.ROTATE_180)
    path_180 = os.path.join(output_dir, "06_invertida_180.png")
    cv2.imwrite(path_180, rot180)
    samples["rot180"] = path_180

    # 7. Rotada 270° horario (o 90° antihorario)
    rot270 = cv2.rotate(base, cv2.ROTATE_90_COUNTERCLOCKWISE)
    path_270 = os.path.join(output_dir, "07_rotada_270.png")
    cv2.imwrite(path_270, rot270)
    samples["rot270"] = path_270

    return samples


if __name__ == "__main__":
    generated = generate_all_samples()
    print("Imágenes de muestra generadas exitosamente en 'sample_images/':")
    for key, path in generated.items():
        print(f"  - [{key}]: {path}")
