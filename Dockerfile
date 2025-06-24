# 1. Imagen base: Python slim, más ligera y control total
FROM python:3.10-slim

# 2. Instala librerías necesarias del sistema para PDF y OCR
RUN apt-get update && \
    apt-get install -y libgl1 poppler-utils tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Carpeta de trabajo
WORKDIR /app

# 4. Copia tu script
COPY ocr_server.py /app/ocr_server.py

# 5. Instala PaddleOCR, pdf2image y Flask por si quieres API (no ocupa casi nada)
RUN pip install --no-cache-dir paddleocr==3.0.2 paddlepaddle==2.4.2 pdf2image pillow flask

# 6. Volumen para modelos de PaddleOCR (persistentes)
VOLUME ["/root/.paddleocr"]

# 7. Volumen para tus datos (input/output)
VOLUME ["/app/data"]

# 8. Puerto para API (opcional, puedes quitar si solo CLI)
EXPOSE 8501

# 9. Comando por defecto: modo CLI
ENTRYPOINT ["python", "/app/ocr_server.py"]
