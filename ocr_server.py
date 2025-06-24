#!/usr/bin/env python3
"""
PaddleOCR 3.0 Production Server - Multi-language (EN/ES)
Compatible con PDF (pdf2image) y batch.
"""

import time
import sys
import json
import os
from pathlib import Path
from paddleocr import PaddleOCR
from pdf2image import convert_from_path

# Configuración optimizada para PaddleOCR 3.0 (CPU)
OCR_CONFIG = {
    "use_gpu": False,
    "use_textline_orientation": True,
    "show_log": False,
    "text_det_limit_side_len": 960,
    "text_recognition_batch_size": 6,
    "cpu_threads": 4
}

class MultiLanguageOCRServer:
    """Servidor OCR multi-idioma optimizado para producción"""

    def __init__(self):
        print("🚀 Inicializando PaddleOCR 3.0 Multi-Language Server...")
        self.ocr_instances = {}
        self.supported_languages = ["en", "es"]

        # Directorios de trabajo
        self.base_dir = Path("/app")
        self.data_dir = self.base_dir / "data"
        self.input_dir = self.data_dir / "input"
        self.output_dir = self.data_dir / "output"

        # Crear directorios si no existen
        for dir_path in [self.input_dir, self.output_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Pre-cargar OCR para cada idioma
        for lang in self.supported_languages:
            print(f"📚 Cargando OCR para {lang.upper()}...")
            self.ocr_instances[lang] = PaddleOCR(lang=lang, **OCR_CONFIG)

        self.default_lang = "es"
        print(f"✅ PaddleOCR 3.0 listo con soporte para: {self.supported_languages}")
        print(f"📁 Input:  {self.input_dir}")
        print(f"📁 Output: {self.output_dir}")

    def get_ocr_instance(self, language=None):
        lang = language or self.default_lang
        if lang not in self.supported_languages:
            print(f"⚠️ Idioma {lang} no soportado. Usando {self.default_lang}")
            lang = self.default_lang
        return self.ocr_instances[lang]

    def process_image(self, image_path, language=None, detect_rotation=True, save_output=False):
        """Procesa una imagen (o PDF)"""
        start_time = time.time()
        lang = language or self.default_lang

        try:
            # Resolver ruta
            if not os.path.isabs(image_path):
                image_path = self.input_dir / image_path

            # Soporte para PDF → convertir a JPG (una página, por defecto la primera)
            if str(image_path).lower().endswith('.pdf'):
                print("🔄 Convirtiendo PDF a imagen...")
                pages = convert_from_path(str(image_path), dpi=300)
                # Solo procesamos la primera página, pero puedes hacer loop para todas
                temp_img = self.input_dir / (Path(image_path).stem + "_page1.jpg")
                pages[0].save(temp_img, "JPEG")
                image_path = temp_img

            ocr = self.get_ocr_instance(lang)
            result = ocr.ocr(str(image_path), cls=detect_rotation)
            elapsed = time.time() - start_time

            response = {
                "success": True,
                "result": result,
                "language": lang,
                "processing_time": round(elapsed, 3),
                "timestamp": time.time(),
                "version": "PaddleOCR 3.0.2 + PP-OCRv5",
                "angle_detection": detect_rotation,
                "image_path": str(image_path)
            }

            if save_output:
                output_file = self.output_dir / f"{Path(image_path).stem}_{lang}_result.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(response, f, indent=2, ensure_ascii=False)
                response["output_saved"] = str(output_file)

            return response

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "language": lang,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "image_path": str(image_path)
            }

    def process_batch(self, language=None):
        """Procesa todas las imágenes y PDFs en input/"""
        lang = language or self.default_lang
        results = []

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf'}
        image_files = [f for f in self.input_dir.iterdir() if f.suffix.lower() in image_extensions]

        if not image_files:
            return {
                "success": False,
                "error": "No se encontraron archivos en el directorio input",
                "input_dir": str(self.input_dir)
            }

        print(f"🔄 Procesando {len(image_files)} archivos...")

        for img_file in image_files:
            print(f"📷 Procesando: {img_file.name}")
            result = self.process_image(str(img_file), lang, save_output=True)
            results.append({
                "file": img_file.name,
                "result": result
            })

        # Guardar resumen batch
        batch_summary = {
            "total_files": len(image_files),
            "successful": sum(1 for r in results if r["result"]["success"]),
            "failed": sum(1 for r in results if not r["result"]["success"]),
            "language": lang,
            "timestamp": time.time(),
            "results": results
        }

        summary_file = self.output_dir / f"batch_summary_{lang}_{int(time.time())}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False)

        return batch_summary

    def health_check(self):
        """Verificación de estado"""
        try:
            import numpy as np
            test_img = np.ones((50, 100, 3), dtype=np.uint8) * 255

            health_status = {
                "status": "healthy",
                "version": "PaddleOCR 3.0.2",
                "supported_languages": self.supported_languages,
                "language_tests": {}
            }

            for lang in self.supported_languages:
                start = time.time()
                ocr = self.get_ocr_instance(lang)
                ocr.ocr(test_img, cls=False)
                elapsed = time.time() - start
                health_status["language_tests"][lang] = {
                    "status": "ok",
                    "response_time": round(elapsed, 3)
                }
            return health_status

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

ocr_server = MultiLanguageOCRServer()

def process_image(image_path, language=None):
    return ocr_server.process_image(image_path, language)

def process_batch(language=None):
    return ocr_server.process_batch(language)

def health_check():
    return ocr_server.health_check()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--health":
            result = health_check()
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == "--batch":
            lang = sys.argv[2] if len(sys.argv) > 2 else None
            result = process_batch(lang)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            img_path = sys.argv[1]
            lang = sys.argv[2] if len(sys.argv) > 2 else None
            result = process_image(img_path, lang, save_output=True)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("✅ PaddleOCR 3.0 Multi-Language Server Ready")
        print("🌍 Idiomas soportados: EN, ES")
        print("📁 Modelos en: /root/.paddleocr (volumen persistente)")
        print("📖 Uso:")
        print("  python ocr_server.py <imagen_o_pdf> [idioma]     # OCR de imagen/PDF")
        print("  python ocr_server.py --batch [idioma]            # Batch sobre input/")
        print("  python ocr_server.py --health                    # Estado del server")
        print("\n💡 Idiomas: en (inglés), es (español)")
        print("💡 Si no especificas ruta completa, busca en /data/input/")
