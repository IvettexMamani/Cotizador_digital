# Cotizador Digital en Hugging Face Spaces (tipo Docker).
#
# Este Space no guarda una copia del código: lo descarga del repo público de
# GitHub cada vez que se construye. Para publicar cambios hechos en GitHub:
# en el Space, Settings -> "Factory rebuild".

FROM python:3.11-slim

# Librerías del sistema: libgomp1 (PaddlePaddle), libgl1 y libglib2.0-0 (OpenCV), git (descarga del código)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face ejecuta el contenedor con el usuario 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR $HOME/app

ARG REPO=https://github.com/IvettexMamani/Cotizador_digital.git
ARG RAMA=main
RUN git clone --depth 1 --branch $RAMA $REPO .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Descarga los modelos de PaddleOCR y prueba el OCR con la foto del ejemplo sintético.
# Si el OCR no funciona en este servidor, la construcción falla aquí y no en plena demo.
RUN python -c "from PIL import Image; from ai.ocr import leer_imagen; r = leer_imagen(Image.open('data/solicitudes/ejemplo_sintetico_foto.png')); print('OCR listo. Confianza:', round(r.confianza_promedio, 3)); assert r.confianza_promedio > 0.9"

EXPOSE 7860

# enableXsrfProtection=false: sin esto, subir archivos falla (error 403) cuando
# la app se muestra dentro de la página de Hugging Face.
CMD ["streamlit", "run", "app/streamlit_app.py", \
     "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true", \
     "--browser.gatherUsageStats=false", "--server.enableXsrfProtection=false"]
