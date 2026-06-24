import os
import uuid
import sys
from typing import Optional

# Asegurar que el directorio src esté en el path para las importaciones de core
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel
from contextlib import asynccontextmanager
from core.downloader import VideoDownloader
from core.database import create_db_and_tables, Song, get_session, select

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    import base64
    yt_cookies_b64 = os.environ.get('YOUTUBE_COOKIES_B64', '').strip()
    if yt_cookies_b64:
        try:
            # Eliminar saltos de línea que algunos editores añaden al copiar
            clean_b64 = yt_cookies_b64.replace('\n', '').replace('\r', '').replace(' ', '')
            cookies_bytes = base64.b64decode(clean_b64 + '==')  # padding extra es inofensivo
            with open('/tmp/yt_cookies.txt', 'wb') as f:
                f.write(cookies_bytes)
            print(f"[cookies] Archivo creado: {len(cookies_bytes)} bytes")
        except Exception as e:
            print(f"[cookies] ERROR al decodificar YOUTUBE_COOKIES_B64: {e}")
    else:
        print("[cookies] Variable YOUTUBE_COOKIES_B64 no configurada — se usarán clientes alternativos")
    yield

app = FastAPI(title="Downloader Premium", lifespan=lifespan)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar el dominio de la PWA
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Evitar ruidos en logs de Chrome DevTools
@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools():
    return Response(status_code=204)

# Modelos de datos para API
class VideoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str = "best"

# Estado de las descargas en memoria
DOWNLOAD_TASKS = {}

# Instancia global del downloader
print(f"Iniciando VideoDownloader con BASE_DIR: {BASE_DIR}")
downloader = VideoDownloader()

# Configuración de rutas absolutas para estáticos y plantillas
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Evitar error 404 del favicon
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/health", include_in_schema=False)
async def health():
    """Endpoint para servicios de monitoreo. También muestra estado de cookies."""
    cookies_ok = os.path.exists('/tmp/yt_cookies.txt')
    cookies_size = os.path.getsize('/tmp/yt_cookies.txt') if cookies_ok else 0
    return {
        "status": "ok",
        "yt_cookies": "active" if cookies_ok else "not configured",
        "yt_cookies_bytes": cookies_size,
    }

def format_duration(seconds):
    if not seconds: return "N/A"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h > 0 else f"{m:d}:{s:02d}"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    print("Acceso a la página principal")
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/ui/download-view", response_class=HTMLResponse)
async def ui_get_download_view(request: Request):
    return templates.TemplateResponse(request=request, name="download_view.html")

@app.get("/ui/library", response_class=HTMLResponse)
async def ui_get_library(request: Request, genre: Optional[str] = None):
    with get_session() as session:
        statement = select(Song).order_by(Song.date_added.desc())
        if genre and genre != "Todos":
            statement = statement.where(Song.genre == genre)
        songs = session.exec(statement).all()
        
        # Obtener géneros únicos para el filtro
        all_genres = session.exec(select(Song.genre)).all()
        unique_genres = sorted(list(set(all_genres)))
        if "Desconocido" in unique_genres:
            unique_genres.remove("Desconocido")
            unique_genres.append("Desconocido")
            
    return templates.TemplateResponse(
        request=request, 
        name="library.html", 
        context={"songs": songs, "genres": unique_genres, "current_genre": genre or "Todos"}
    )

def _resolve_song_file(song) -> str | None:
    """Resuelve el path absoluto del archivo de una canción. Retorna None si no existe."""
    if not song:
        return None
    file_path = song.file_path if os.path.isabs(song.file_path) else os.path.abspath(song.file_path)
    return file_path if os.path.exists(file_path) else None

@app.get("/api/audio/{song_id}")
async def get_audio_stream(song_id: int):
    with get_session() as session:
        song = session.get(Song, song_id)
        file_path = _resolve_song_file(song)
        if not file_path:
            raise HTTPException(status_code=404, detail="Canción o archivo no encontrado")
        return FileResponse(
            path=file_path,
            media_type="audio/mpeg" if file_path.endswith(".mp3") else "video/mp4"
        )

@app.get("/api/audio/server/{song_id}")
async def get_server_audio(song_id: int):
    """Alias explícito para reproducción de canciones del servidor (tab Online)."""
    return await get_audio_stream(song_id)

@app.get("/ui/online-library", response_class=HTMLResponse)
async def ui_online_library(request: Request, genre: Optional[str] = None):
    with get_session() as session:
        songs_db = session.exec(select(Song).order_by(Song.date_added.desc())).all()

    # Deduplicar por title+artist (la query ya viene ordenada desc por fecha,
    # así el primero que encontramos es el más reciente).
    seen: set[tuple] = set()
    unique: list = []
    for s in songs_db:
        key = (s.title.lower().strip(), s.artist.lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(s)

    # Géneros únicos para pills (sobre la lista deduplicada, antes de filtrar)
    all_genres = sorted(set(s.genre or "Sin categoría" for s in unique))

    # Filtrar por género si se especificó
    if genre and genre != "Todas":
        unique = [s for s in unique if (s.genre or "Sin categoría") == genre]

    songs = [
        {
            "id": s.id,
            "title": s.title,
            "artist": s.artist,
            "genre": s.genre or "Sin categoría",
            "duration": s.duration or 0,
            "thumbnail_url": s.thumbnail_url or "",
            "available": _resolve_song_file(s) is not None,
            "date_added": s.date_added.strftime("%d/%m/%Y"),
        }
        for s in unique
    ]
    return templates.TemplateResponse(
        request=request,
        name="online_library.html",
        context={"songs": songs, "genres": all_genres, "current_genre": genre or "Todas"}
    )

@app.get("/api/genres")
async def get_genres():
    """Devuelve todas las categorías únicas presentes en SQLite (para el picker de categorías)."""
    with get_session() as session:
        songs = session.exec(select(Song)).all()
    genres = sorted(set(s.genre for s in songs if s.genre))
    return genres

@app.patch("/api/songs/{song_id}/genre")
async def update_song_genre(song_id: int, genre: str = Form(...)):
    """Actualiza la categoría (genre) de una canción del servidor."""
    genre_val = genre.strip() or "Sin categoría"
    with get_session() as session:
        song = session.get(Song, song_id)
        if not song:
            raise HTTPException(status_code=404, detail="Canción no encontrada")
        song.genre = genre_val
        session.add(song)
        session.commit()
    return {"id": song_id, "genre": genre_val}

@app.delete("/api/songs/{song_id}")
async def delete_song(song_id: int):
    """Elimina una canción del servidor (SQLite + archivo de disco)."""
    with get_session() as session:
        song = session.get(Song, song_id)
        if not song:
            raise HTTPException(status_code=404, detail="Canción no encontrada")
        file_path = _resolve_song_file(song)
        session.delete(song)
        session.commit()
    if file_path:
        try:
            os.remove(file_path)
        except OSError:
            pass
    return {"deleted": song_id}

@app.delete("/api/clean-duplicates")
async def clean_duplicates():
    """Elimina de la DB las filas duplicadas (mismo title+artist), conservando la más reciente."""
    with get_session() as session:
        songs = session.exec(select(Song).order_by(Song.date_added.desc())).all()
        seen: set[tuple] = set()
        to_delete: list[Song] = []
        for s in songs:
            key = (s.title.lower().strip(), s.artist.lower().strip())
            if key in seen:
                to_delete.append(s)
            else:
                seen.add(key)
        for s in to_delete:
            session.delete(s)
        session.commit()
    return {"deleted": len(to_delete)}

# --- Endpoints para la Interfaz (UI) ---

@app.post("/ui/info", response_class=HTMLResponse)
def ui_get_info(request: Request, url: str = Form(...)):
    print(f"Analizando URL: {url}")
    try:
        info = downloader.get_info(url)
        if "error" in info:
            print(f"Error en get_info: {info['error']}")
            return f"""
            <div class="bg-red-500/10 border border-red-500/50 text-red-200 p-6 rounded-2xl text-center animate-shake">
                <div class="bg-red-500 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                    </svg>
                </div>
                <h4 class="text-lg font-bold mb-1">Algo salió mal</h4>
                <p class="text-red-300/80 text-sm">{info["error"]}</p>
            </div>
            """
        
        duration = format_duration(info.get("duration"))
        print(f"Información obtenida: {info.get('title')}")
        
        # --- Generar selector de resoluciones ---
        formats_html = ""
        # Filtrar formatos que tengan resolución (ej. 1080x1920 o 1080p), ordenarlos y evitar duplicados básicos
        seen_resolutions = set()
        valid_formats = []
        for f in info.get("formats", []):
            res = f.get('resolution')
            if res and res != 'audio only' and 'x' in res:
                try:
                    height = int(res.split('x')[1])
                    # Limitar a ≤1080p (excluir 4K/2160p y similares que son webm sin compatibilidad amplia)
                    if height > 1080:
                        continue
                    if height not in seen_resolutions:
                        seen_resolutions.add(height)
                        valid_formats.append((height, f))
                except:
                    pass
        
        # Ordenar de mayor a menor calidad
        valid_formats.sort(key=lambda x: x[0], reverse=True)
        
        if valid_formats:
            formats_html += '<select name="format_id" id="format-select" class="w-full bg-white/5 border border-white/10 text-white text-xs sm:text-sm rounded-2xl px-4 py-2.5 outline-none focus:border-red-500/50 transition-all mb-3 cursor-pointer" style="color-scheme: dark;">'
            for height, f in valid_formats:
                fid = f.get('format_id')
                combo_id = f"{fid}+bestaudio/best"
                ext_display = f.get('ext', 'mp4')
                formats_html += f'<option value="{combo_id}" style="background:#1e293b;color:#fff;">{height}p ({ext_display})</option>'
            formats_html += '</select>'
        else:
            formats_html = '<input type="hidden" name="format_id" id="format-select" value="best">'
        # ----------------------------------------
        
        return f"""
        <div class="crystal-glass rounded-[32px] flex flex-col gap-0 animate-fade-in relative overflow-hidden">
            <!-- Banner thumbnail -->
            <div class="relative w-full h-44 flex-shrink-0 overflow-hidden rounded-t-[32px]">
                <img src="{info.get('thumbnail')}" class="w-full h-full object-cover">
                <div class="absolute inset-0 bg-gradient-to-b from-black/10 via-black/20 to-black/70"></div>
                <div class="absolute bottom-0 left-0 right-0 px-6 pb-4">
                    <h3 class="text-white text-lg font-black tracking-tight leading-tight line-clamp-2 drop-shadow-lg">{info.get('title')}</h3>
                    <p class="text-white/50 text-[11px] font-bold uppercase tracking-widest mt-1">{info.get('uploader')} · {duration}</p>
                </div>
            </div>

            <!-- Controls -->
            <div class="p-5 flex flex-col gap-3">
                {formats_html}
                <div id="download-status" class="flex gap-3">
                    <button
                        hx-post="/ui/download"
                        hx-vals='js:{{"url": "{url}", "format_id": document.getElementById("format-select")?.value || "best"}}'
                        hx-target="#download-status"
                        class="btn-lg-primary flex-1 font-black py-4 px-4 rounded-2xl flex items-center justify-center gap-2 active:scale-95 text-sm"
                    >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10l-3 3m0 0l-3-3m3 3V3M21 16v4a1 1 0 01-1 1H4a1 1 0 01-1-1v-4"/></svg>
                        VIDEO
                    </button>
                    <button
                        hx-post="/ui/download"
                        hx-vals='{{"url": "{url}", "format_id": "mp3"}}'
                        hx-target="#download-status"
                        class="btn-lg-secondary flex-1 font-black py-4 px-4 rounded-2xl flex items-center justify-center gap-2 active:scale-95 text-sm"
                    >
                        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2zm12-3c0 1.1-1.34 2-3 2s-3-.9-3-2 1.34-2 3-2 3 .9 3 2z"/></svg>
                        AUDIO MP3
                    </button>
                </div>
            </div>
        </div>
        """
    except Exception as e:
        print(f"Excepción en ui_get_info: {str(e)}")
        return f'<div class="bg-red-500/20 border border-red-500 text-red-200 p-4 rounded-xl text-center">Excepción: {str(e)}</div>'


@app.post("/ui/download", response_class=HTMLResponse)
async def ui_start_download(background_tasks: BackgroundTasks, url: str = Form(...), format_id: str = Form(...)):
    task_id = str(uuid.uuid4())
    # Inicializar con todos los campos necesarios para evitar errores visuales
    DOWNLOAD_TASKS[task_id] = {
        "status": "processing", 
        "file_path": None, 
        "error": None, 
        "progress": "0%",
        "eta": ""
    }
    background_tasks.add_task(run_download_task, task_id, url, format_id)
    
    return f"""
    <div hx-get="/ui/status/{task_id}" hx-trigger="load delay:1s" hx-swap="outerHTML" class="crystal-glass p-5 rounded-[24px] flex flex-col gap-3 animate-fade-in">
        <div class="flex justify-between items-center text-sm font-bold text-white/60">
            <span class="flex items-center gap-2">
                <svg class="animate-spin h-4 w-4 text-red-400" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Iniciando descarga...
            </span>
            <span class="font-black text-white/40">0%</span>
        </div>
        <div class="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500"
                 style="width: 0%; background: linear-gradient(90deg, #ef4444, #f97316)"></div>
        </div>
    </div>
    """

@app.get("/ui/status/{task_id}", response_class=HTMLResponse)
async def ui_get_status(task_id: str):
    if task_id not in DOWNLOAD_TASKS:
        # Si la tarea ya se borró pero el navegador sigue consultando, devolvemos un estado neutro
        return '<div class="text-slate-500 text-sm">Finalizando sesión...</div>'
    
    task = DOWNLOAD_TASKS[task_id]
    
    if task["status"] in ["processing", "converting"]:
        progress_str = task.get("progress", "0%")
        p_val = progress_str.replace('%', '').strip() if '%' in progress_str else '0'
        
        if task["status"] == "converting":
            msg = "Convirtiendo a MP3 (ffmpeg)..."
            p_val = "99"
        else:
            import re as _re
            raw_eta = str(task.get('eta', ''))
            raw_eta = _re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw_eta).strip()
            bad_values = {'', 'N/A', 'None', '0', '--:--', 'unknown', '00:00'}
            if raw_eta and raw_eta not in bad_values:
                msg = f"Descargando... · {raw_eta}"
            else:
                msg = "Descargando..."

        pulse_overlay = '<div class="absolute inset-0 bg-white/20 animate-pulse rounded-full"></div>' if task["status"] == "converting" else ''
        return f"""
        <div hx-get="/ui/status/{task_id}" hx-trigger="load delay:1s" hx-swap="outerHTML" class="crystal-glass p-5 rounded-[24px] flex flex-col gap-3">
            <div class="flex justify-between items-center text-sm font-bold text-white/60">
                <span class="flex items-center gap-2">
                    <svg class="animate-spin h-4 w-4 text-red-400" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                    {msg}
                </span>
                <span class="font-black text-white/80">{progress_str}</span>
            </div>
            <div class="w-full bg-white/5 rounded-full h-1.5 overflow-hidden relative">
                <div class="h-full rounded-full transition-all duration-500 relative"
                     style="width: {p_val}%; background: linear-gradient(90deg, #ef4444, #f97316)">
                    {pulse_overlay}
                </div>
            </div>
        </div>
        """
    elif task["status"] == "completed":
        m = task["metadata"]
        return f"""
        <div class="crystal-glass rounded-[24px] overflow-hidden flex flex-col gap-0 animate-fade-in">
            <!-- Success banner -->
            <div class="flex items-center gap-3 px-5 py-4 border-b border-white/5">
                <div class="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                    <svg class="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                    </svg>
                </div>
                <div>
                    <p class="text-white font-black text-sm leading-tight line-clamp-1">{m['title']}</p>
                    <p class="text-white/40 text-[11px] font-bold uppercase tracking-widest">Listo en el servidor</p>
                </div>
            </div>
            <!-- Action -->
            <div class="p-4">
                <button
                    onclick="downloadAndSaveLocally(event, '{task_id}', '{m['title']}', '{m['artist']}', {m['duration'] or 0}, '{m['thumbnail']}')"
                    class="btn-lg-primary w-full font-black py-4 px-6 rounded-[18px] flex items-center justify-center gap-2 active:scale-95 text-sm"
                >
                    <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                    Guardar en mi dispositivo
                </button>
            </div>
        </div>
        """
    else:
        return f'<div class="bg-red-500/20 text-red-300 p-4 rounded-xl">Error: {task["error"]}</div>'

# --- Endpoints de la API Original (JSON) ---

@app.post("/api/info")
def get_video_info(request: VideoRequest):
    info = downloader.get_info(request.url)
    if "error" in info:
        raise HTTPException(status_code=400, detail=info["error"])
    return info

def run_download_task(task_id: str, url: str, format_id: str):
    """Tarea que se ejecuta en segundo plano con inyección de progreso y persistencia en DB."""
    def progress_hook(d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').strip()
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            p_clean = ansi_escape.sub('', p)
            DOWNLOAD_TASKS[task_id]['progress'] = p_clean
            raw_eta = d.get('_eta_str', '')
            DOWNLOAD_TASKS[task_id]['eta'] = ansi_escape.sub('', raw_eta).strip()
        elif d['status'] == 'finished':
            DOWNLOAD_TASKS[task_id]['progress'] = '100%'
            DOWNLOAD_TASKS[task_id]['status'] = 'converting'

    # Obtener info antes para la DB
    info = downloader.get_info(url)

    result = downloader.download(
        url, 
        format_id=format_id, 
        prefix=task_id, 
        progress_hook=progress_hook
    )
    
    if result["success"]:
        # Normalizar a path absoluto para que SQLite sea independiente del cwd
        file_path_abs = os.path.abspath(result["filepath"])
        if os.path.exists(file_path_abs):
            title_val  = info.get("title", "Unknown")
            artist_val = info.get("uploader", "Unknown")
            with get_session() as session:
                # Upsert: si ya existe la misma canción (title+artist) actualizar el archivo,
                # no crear una fila duplicada.
                existing = session.exec(
                    select(Song).where(Song.title == title_val, Song.artist == artist_val)
                ).first()
                if existing:
                    existing.file_path    = file_path_abs
                    existing.thumbnail_url = info.get("thumbnail") or existing.thumbnail_url
                    existing.duration     = info.get("duration")   or existing.duration
                    session.add(existing)
                else:
                    session.add(Song(
                        title=title_val,
                        artist=artist_val,
                        duration=info.get("duration"),
                        file_path=file_path_abs,
                        thumbnail_url=info.get("thumbnail"),
                        platform="YouTube" if "youtube" in url else "Other"
                    ))
                session.commit()

            DOWNLOAD_TASKS[task_id].update({
                "status": "completed", 
                "file_path": result["filepath"], 
                "progress": "100%",
                "metadata": {
                    "title": info.get("title", "Unknown").replace("'", "\\'").replace('"', '&quot;'),
                    "artist": info.get("uploader", "Unknown").replace("'", "\\'").replace('"', '&quot;'),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail")
                }
            })
        else:
            DOWNLOAD_TASKS[task_id].update({
                "status": "failed", 
                "error": "El archivo se procesó pero no se encuentra en el disco."
            })
    else:
        DOWNLOAD_TASKS[task_id].update({"status": "failed", "error": result["error"]})

@app.post("/api/download")
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    DOWNLOAD_TASKS[task_id] = {"status": "processing", "file_path": None, "error": None, "progress": "0%"}
    background_tasks.add_task(run_download_task, task_id, request.url, request.format_id)
    return {"task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in DOWNLOAD_TASKS:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return DOWNLOAD_TASKS[task_id]

from fastapi.responses import FileResponse

@app.get("/api/file/{task_id}")
async def get_file(task_id: str, background_tasks: BackgroundTasks):
    if task_id not in DOWNLOAD_TASKS:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    task = DOWNLOAD_TASKS[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="La descarga aún no ha terminado")
    
    file_path = task["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="El archivo ya no existe en el servidor")

    # Función para limpiar el archivo después de enviarlo (opcional para modo puente)
    def remove_file(path: str, tid: str):
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Archivo eliminado tras descarga: {path}")
            except Exception as e:
                print(f"Error al eliminar archivo: {e}")
        if tid in DOWNLOAD_TASKS:
            del DOWNLOAD_TASKS[tid]

    # En el modo PWA/Nube, queremos que el servidor sea ligero. 
    # Descomenta la línea de abajo si quieres que el servidor borre el archivo inmediatamente tras bajarlo.
    # background_tasks.add_task(remove_file, file_path, task_id)
    
    filename = os.path.basename(file_path).split("_", 1)[-1]
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
