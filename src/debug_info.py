from core.downloader import VideoDownloader
import os

def test_info():
    downloader = VideoDownloader()
    url = "https://www.youtube.com/watch?v=Yh3vg-qnT0E"
    print(f"Probando URL: {url}")
    print(f"Ruta FFmpeg configurada: {downloader.ffmpeg_path}")
    
    info = downloader.get_info(url)
    if "error" in info:
        print(f"¡ERROR DETECTADO!: {info['error']}")
    else:
        print("ÉXITO: Datos obtenidos:")
        print(f"Título: {info.get('title')}")
        print(f"Thumbnail: {info.get('thumbnail')}")

if __name__ == "__main__":
    test_info()
