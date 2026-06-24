import yt_dlp
import os
import re

class VideoDownloader:
    def __init__(self, download_path="downloads"):
        self.download_path = download_path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Intentar usar la carpeta local bin, pero permitir que el sistema use su propio ffmpeg
        local_bin = os.path.join(os.path.dirname(current_dir), "bin")
        if os.path.exists(local_bin):
            self.ffmpeg_path = local_bin
        else:
            self.ffmpeg_path = None # Usará el ffmpeg del PATH del sistema
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def validate_url(self, url):
        """Valida si la URL pertenece a una plataforma soportada."""
        patterns = [
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$',
            r'^(https?://)?(www\.)?(tiktok\.com)/.+$',
            r'^(https?://)?(www\.)?(instagram\.com)/(reels?|p|tv)/.+$',
            r'^(https?://)?(www\.)?(facebook\.com|fb\.watch)/.+$',
            r'^(https?://)?(www\.)?(twitter\.com|x\.com)/.+$'
        ]
        return any(re.match(p, url) for p in patterns)

    def clean_title(self, title):
        """Limpia el título de ruidos comunes como (Official Video), HD, etc."""
        if not title: return "video_sin_titulo"
        # Eliminar contenido entre paréntesis o corchetes comunes
        title = re.sub(r'[\(\[][^)\]]*(official|video|lyric|audio|hd|4k|full|1080p)[^)\]]*[\)\]]', '', title, flags=re.IGNORECASE)
        # Eliminar palabras sueltas comunes
        title = re.sub(r'\b(official video|video oficial|lyric video|video lyric|full hd|4k|hd|1080p)\b', '', title, flags=re.IGNORECASE)
        # Limpiar espacios extra y guiones al final
        title = re.sub(r'\s+', ' ', title).strip().strip('-').strip()
        return title

    def get_info(self, url):
        """Obtiene información del video sin descargarlo."""
        if not self.validate_url(url):
            return {"error": "URL no soportada o inválida."}

        ydl_opts = {
            'ffmpeg_location': self.ffmpeg_path,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_embedded', 'ios'],
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return {
                    "id": info.get("id"),
                    "title": self.clean_title(info.get("title")),
                    "original_title": info.get("title"),
                    "thumbnail": info.get("thumbnail"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "formats": [
                        {
                            "format_id": f.get("format_id"),
                            "ext": f.get("ext"),
                            "resolution": f.get("resolution"),
                            "filesize": f.get("filesize"),
                            "vcodec": f.get("vcodec"),
                        }
                        for f in info.get("formats", [])
                        if f.get("vcodec") != "none"
                    ]
                }
            except Exception as e:
                error_msg = str(e)
                if "Incomplete YouTube ID" in error_msg: return {"error": "ID de YouTube incompleto o mal formado."}
                if "Private video" in error_msg: return {"error": "El video es privado."}
                if "Video unavailable" in error_msg: return {"error": "El video no está disponible."}
                return {"error": f"Error al obtener información: {error_msg}"}

    def download(self, url, format_id="best", prefix=None, progress_hook=None, postprocessor_hook=None):
        """Descarga el video o audio con el formato especificado, metadatos y carátula."""
        # Primero obtenemos info para tener el título limpio
        info_brief = self.get_info(url)
        if "error" in info_brief:
            return {"success": False, "error": info_brief["error"]}
        
        clean_name = info_brief["title"]
        filename_format = f"{clean_name}.%(ext)s"
        if prefix:
            filename_format = f"{prefix}_{clean_name}.%(ext)s"
            
        output_template = os.path.join(self.download_path, filename_format)
        
        ydl_opts = {
            'outtmpl': output_template,
            'ffmpeg_location': self.ffmpeg_path,
            'noplaylist': True,
            'playlist_items': '1',
            'writethumbnail': True,
            'restrictfilenames': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_embedded', 'ios'],
                }
            },
        }
        
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        if postprocessor_hook:
            ydl_opts['postprocessor_hooks'] = [postprocessor_hook]

        # Post-procesadores para metadatos y carátula
        postprocessors = [
            {'key': 'FFmpegMetadata', 'add_metadata': True},
            {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}
        ]

        if format_id == "mp3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    *postprocessors
                ],
            })
        else:
            ydl_opts.update({
                'format': f"{format_id.split('+')[0]}+bestaudio/best" if '+' in format_id else format_id,
                'merge_output_format': 'mp4',
                'postprocessors': postprocessors
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Ajuste de extensiones post-procesamiento
                if format_id == "mp3":
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                elif not os.path.exists(filename):
                    base, _ = os.path.splitext(filename)
                    if os.path.exists(base + ".mp4"):
                        filename = base + ".mp4"
                
                if not os.path.exists(filename):
                    files = os.listdir(self.download_path)
                    for f in files:
                        if prefix and f.startswith(prefix) and f.endswith((".mp3", ".mp4")):
                            filename = os.path.join(self.download_path, f)
                            break

                return {"success": True, "filepath": filename}
            except Exception as e:
                return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Prueba rápida
    downloader = VideoDownloader()
    test_url = "https://www.youtube.com/shorts/Yh3vg-qnT0E"
    print(f"Obteniendo info de: {test_url}")
    info = downloader.get_info(test_url)
    if "error" not in info:
        print(f"Título: {info['title']}")
        print("Descargando...")
        result = downloader.download(test_url)
        print(f"Resultado: {result}")
    else:
        print(f"Error: {info['error']}")
