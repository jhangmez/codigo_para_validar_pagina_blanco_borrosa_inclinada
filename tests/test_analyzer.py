"""
Pruebas automatizadas para DocumentAnalyzer.
Verifica:
1. Detección de documento normal
2. Detección de hoja en blanco
3. Detección de hoja borrosa
4. Detección de inclinación angular (skew)
5. Detección de hoja rotada 90°
6. Detección de hoja invertida 180°
7. Detección de hoja rotada 270°
8. Corrección geométrica y enderezado
"""
import unittest
import os
import cv2

from document_analyzer import DocumentAnalyzer
from tests.generate_samples import generate_all_samples


class TestDocumentAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples_dir = "sample_images"
        cls.samples = generate_all_samples(cls.samples_dir)
        cls.analyzer = DocumentAnalyzer(
            blur_threshold=100.0,
            blank_ink_threshold_percent=0.35,
            skew_tolerance_deg=1.0
        )

    def test_01_normal_document(self):
        report = self.analyzer.analyze(self.samples["normal"])
        self.assertFalse(report.blank.is_blank, "El documento normal NO debe marcarse como en blanco")
        self.assertFalse(report.blur.is_blurry, "El documento normal NO debe marcarse como borroso")
        self.assertFalse(report.orientation.is_skewed, "El documento normal NO debe tener inclinación")
        self.assertEqual(report.orientation.cardinal_orientation_deg, 0, "Orientación debe ser 0°")
        self.assertTrue(report.is_acceptable_quality, "La calidad general debe ser aceptable")
        self.assertGreater(report.blur.laplacian_variance, 300.0, "La varianza debe ser alta")

    def test_02_blank_document(self):
        report = self.analyzer.analyze(self.samples["blank"])
        self.assertTrue(report.blank.is_blank, "La hoja vacía DEBE marcarse como en blanco")
        self.assertFalse(report.is_acceptable_quality, "Una hoja en blanco NO debe tener calidad aceptable")
        self.assertLess(report.blank.ink_ratio_percent, 0.35, "Porcentaje de tinta debe ser muy bajo")

    def test_03_blurry_document(self):
        report = self.analyzer.analyze(self.samples["blurry"])
        self.assertFalse(report.blank.is_blank, "El documento borroso tiene texto, no está en blanco")
        self.assertTrue(report.blur.is_blurry, "El documento borroso DEBE marcarse como borroso")
        self.assertLess(report.blur.laplacian_variance, 100.0, "La varianza debe ser menor a 100")
        self.assertFalse(report.is_acceptable_quality, "Un documento borroso NO debe ser aceptable")

    def test_04_skewed_document(self):
        report = self.analyzer.analyze(self.samples["skewed"])
        self.assertFalse(report.blank.is_blank)
        self.assertTrue(report.orientation.is_skewed, "Debe detectar que está inclinado")
        # El ángulo aplicado fue 5.5 grados
        self.assertAlmostEqual(report.orientation.skew_angle_deg, 5.5, delta=1.5)

    def test_05_rotated_90(self):
        report = self.analyzer.analyze(self.samples["rot90"])
        self.assertFalse(report.blank.is_blank)
        self.assertEqual(report.orientation.cardinal_orientation_deg, 90, "Debe detectar rotación a 90°")
        self.assertTrue(report.orientation.is_rotated)

    def test_06_rotated_180(self):
        report = self.analyzer.analyze(self.samples["rot180"])
        self.assertFalse(report.blank.is_blank)
        self.assertEqual(report.orientation.cardinal_orientation_deg, 180, "Debe detectar rotación a 180°")
        self.assertTrue(report.orientation.is_rotated)

    def test_07_rotated_270(self):
        report = self.analyzer.analyze(self.samples["rot270"])
        self.assertFalse(report.blank.is_blank)
        self.assertEqual(report.orientation.cardinal_orientation_deg, 270, "Debe detectar rotación a 270°")
        self.assertTrue(report.orientation.is_rotated)

    def test_08_correction(self):
        # Tomamos el documento inclinado y lo enderezamos
        original = cv2.imread(self.samples["skewed"])
        corrected = self.analyzer.correct_document(original)
        self.assertIsNotNone(corrected)
        
        # Analizamos la imagen corregida
        new_report = self.analyzer.analyze(corrected)
        self.assertLess(abs(new_report.orientation.skew_angle_deg), 1.0, "El documento corregido debe quedar nivelado")

    def test_09_analyze_from_url(self):
        import http.server
        import threading
        import time

        port = 8991
        handler = http.server.SimpleHTTPRequestHandler
        httpd = http.server.HTTPServer(("127.0.0.1", port), handler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        try:
            url = f"http://127.0.0.1:{port}/{self.samples['normal']}"
            report = self.analyzer.analyze(url)
            self.assertEqual(report.source, url)
            self.assertFalse(report.blank.is_blank)
            self.assertFalse(report.blur.is_blurry)
            self.assertEqual(report.orientation.cardinal_orientation_deg, 0)
        finally:
            httpd.shutdown()
            httpd.server_close()



if __name__ == "__main__":
    unittest.main()
