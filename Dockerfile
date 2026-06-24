FROM python:3.12-slim

WORKDIR /app

# FFmpeg es necesario para que yt-dlp convierta a MP3
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/

# Carpeta de descargas
RUN mkdir -p /app/downloads

EXPOSE 8000

# PORT es inyectado por Render; en local usa 8000
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
