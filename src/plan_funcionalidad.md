# Plan de Mejora — Funcionalidad
> Proyecto: Crystal Premium Downloader  
> Estado base: descarga MP4/MP3 funcional, biblioteca con 2 canciones desde IndexedDB, play/pause funcional, resto de controles del player sin implementar.

---

## Diagnóstico del estado actual

| Componente | Estado | Causa raíz |
|---|---|---|
| Biblioteca muestra solo 2 canciones | Bug | Lee IndexedDB del navegador, no SQLite del servidor |
| Botones anterior / siguiente | Roto | No tienen `@click` handler ni existe concepto de cola/queue |
| Menú tres puntos | Roto | Botón sin handler, sin panel de opciones |
| Barra de progreso | Solo lectura | No hay handler de click/drag para hacer seeking |
| Canción activa en biblioteca | Inexistente | No hay comparación `currentSong.id === song.id` |
| Auto-advance al terminar canción | Inexistente | `@ended` solo pone `playing = false` |

---

## Fase 1 — Controles del player (sin tocar backend)
**Archivos:** `src/templates/index.html`, `src/static/js/app.js`  
**Duración estimada:** 1 sesión

### 1.1 Sistema de cola (queue)
Agregar al objeto `playerData()` en `index.html`:

```js
queue: [],        // [{id, title, artist, thumbnail, audioUrl}]
queueIndex: -1,   // índice actual en la cola

setQueue(songs, startIndex) {
    this.queue = songs;
    this.queueIndex = startIndex;
},

playNext() {
    if (this.queueIndex < this.queue.length - 1) {
        const next = this.queue[++this.queueIndex];
        this.playSong(next.id, next.title, next.artist, next.thumbnail, next.audioUrl);
    }
},

playPrev() {
    const audio = document.getElementById('main-audio');
    // Si llevamos más de 3s reproducidos, volver al inicio de la canción actual
    if (audio.currentTime > 3) {
        audio.currentTime = 0;
        return;
    }
    if (this.queueIndex > 0) {
        const prev = this.queue[--this.queueIndex];
        this.playSong(prev.id, prev.title, prev.artist, prev.thumbnail, prev.audioUrl);
    }
},

canGoNext() { return this.queueIndex < this.queue.length - 1; },
canGoPrev() { return this.queueIndex > 0 || document.getElementById('main-audio').currentTime > 3; },
```

En `app.js`, al renderizar la biblioteca, registrar el queue antes de reproducir:
```js
// En loadLocalLibrary(), tras cargar songs:
window._libraryQueue = songs.map(s => ({
    id: s.id, title: s.title, artist: s.artist,
    thumbnail: s.thumbnail, audioUrl: null // se crea en playLocalSong()
}));

// Al hacer click en una canción:
async function playLocalSong(id, title, artist, thumbnail) {
    const index = window._libraryQueue.findIndex(s => s.id === id);
    // ... crear objectURL ...
    window._libraryQueue[index].audioUrl = currentObjectURL;
    const data = window.Alpine.$data(document.querySelector('[x-data]'));
    data.setQueue(window._libraryQueue, index);
    data.playSong(id, title, artist, thumbnail, currentObjectURL);
}
```

### 1.2 Conectar botones anterior / siguiente
En `index.html`, botones del player expandido (líneas 243 y 248):
```html
<!-- Anterior -->
<button @click="playPrev()" 
        :class="canGoPrev() ? 'text-white' : 'text-white/20 cursor-not-allowed'"
        class="transition-colors active:scale-90">
    <svg .../>
</button>

<!-- Siguiente -->
<button @click="playNext()"
        :class="canGoNext() ? 'text-white' : 'text-white/20 cursor-not-allowed'"
        class="transition-colors active:scale-90">
    <svg .../>
</button>
```

### 1.3 Auto-advance al terminar canción
En el `<audio>` tag:
```html
<audio id="main-audio" 
       @timeupdate="updateProgress()" 
       @ended="onSongEnd()">
</audio>
```
```js
onSongEnd() {
    if (this.shuffle) {
        const randomIndex = Math.floor(Math.random() * this.queue.length);
        this.queueIndex = randomIndex;
        const s = this.queue[randomIndex];
        this.playSong(s.id, s.title, s.artist, s.thumbnail, s.audioUrl);
    } else if (this.repeat === 'one') {
        document.getElementById('main-audio').play();
    } else if (this.canGoNext()) {
        this.playNext();
    } else {
        this.playing = false;
    }
},
```

### 1.4 Seeking en barra de progreso
```html
<!-- Barra clickeable en player expandido -->
<div class="h-1.5 bg-white/5 rounded-full w-full relative mb-4 overflow-visible cursor-pointer"
     @click="seekTo($event)"
     @mousedown="dragging = true"
     @mousemove="dragging && seekTo($event)"
     @mouseup="dragging = false"
     @touchstart="touchSeek($event)"
     @touchmove="touchSeek($event)">
    ...
</div>
```
```js
dragging: false,
seekTo(event) {
    const bar = event.currentTarget;
    const rect = bar.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const audio = document.getElementById('main-audio');
    if (audio.duration) audio.currentTime = ratio * audio.duration;
},
touchSeek(event) {
    event.preventDefault();
    const touch = event.touches[0];
    this.seekTo({ currentTarget: event.currentTarget, clientX: touch.clientX });
},
```

### 1.5 MediaSession — botones de pantalla de bloqueo
Agregar en `playSong()` los handlers de sistema operativo:
```js
navigator.mediaSession.setActionHandler('previoustrack', () => this.playPrev());
navigator.mediaSession.setActionHandler('nexttrack', () => this.playNext());
navigator.mediaSession.setActionHandler('seekto', (d) => {
    document.getElementById('main-audio').currentTime = d.seekTime;
});
```

---

## Fase 2 — Menú de tres puntos y opciones de canción
**Archivos:** `src/templates/index.html`, `src/static/js/app.js`  
**Duración estimada:** 1 sesión

### 2.1 Panel de opciones en el player expandido
```js
// En playerData()
showOptions: false,
```

```html
<!-- Botón tres puntos — conectar -->
<button @click="showOptions = !showOptions" class="...">
    <svg .../>
</button>

<!-- Panel de opciones (sheet desde abajo) -->
<div x-show="showOptions"
     x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="opacity-0 translate-y-4"
     x-transition:enter-end="opacity-100 translate-y-0"
     @click.outside="showOptions = false"
     class="absolute bottom-0 left-0 right-0 liquid-glass rounded-t-[40px] p-6 z-10">
    
    <div class="w-12 h-1 bg-white/20 rounded-full mx-auto mb-6"></div>
    
    <button @click="deleteCurrentSong()" class="w-full flex items-center gap-4 py-4 text-red-400">
        <svg><!-- trash icon --></svg>
        Eliminar de la biblioteca
    </button>
    <button @click="shareCurrentSong()" class="w-full flex items-center gap-4 py-4 text-white/80">
        <svg><!-- share icon --></svg>
        Compartir
    </button>
    <button @click="showOptions = false" class="w-full text-center py-4 text-white/40 text-sm">
        Cancelar
    </button>
</div>
```

```js
async deleteCurrentSong() {
    if (confirm(`¿Eliminar "${this.currentSong.title}" de tu biblioteca?`)) {
        await deleteLocalSong(this.currentSong.id);
        this.currentSong = { id: null };
        this.playing = false;
        document.getElementById('main-audio').src = '';
        this.expandPlayer = false;
        this.showOptions = false;
        if (window.refreshLibraryView) window.refreshLibraryView();
    }
},
shareCurrentSong() {
    if (navigator.share) {
        navigator.share({ title: this.currentSong.title, text: `Escucha: ${this.currentSong.title}` });
    }
    this.showOptions = false;
},
```

### 2.2 Menú contextual en cards de biblioteca
Agregar botón `···` en cada card que abre un sheet con:
- Reproducir
- Eliminar de biblioteca
- Ver info (título, artista, duración, fecha descarga)

---

## Fase 3 — Indicadores visuales de canción activa
**Archivos:** `src/static/js/app.js`, `src/templates/index.html`  
**Duración estimada:** media sesión

### 3.1 Waveform animado en card activa
En `app.js`, al renderizar cada card comparar con `currentSong`:
```js
// Obtener canción activa desde Alpine
const alpineData = window.Alpine?.$data(document.querySelector('[x-data]'));
const activeSongId = alpineData?.currentSong?.id;

// En el template de cada card:
const isActive = song.id === activeSongId;
const waveHTML = isActive ? `
    <div class="flex items-end gap-[3px] h-5">
        <div class="w-[3px] bg-red-500 rounded-full wave-bar-1"></div>
        <div class="w-[3px] bg-red-500 rounded-full wave-bar-2"></div>
        <div class="w-[3px] bg-red-500 rounded-full wave-bar-3"></div>
    </div>
` : `<span class="text-white/20 text-[11px]">${formatDuration(song.duration)}</span>`;
```

CSS para las barras (en `index.html` `<style>`):
```css
@keyframes wave1 { 0%,100%{height:4px} 50%{height:16px} }
@keyframes wave2 { 0%,100%{height:12px} 50%{height:4px} }
@keyframes wave3 { 0%,100%{height:6px} 50%{height:14px} }

.wave-bar-1 { animation: wave1 0.8s ease-in-out infinite; }
.wave-bar-2 { animation: wave2 0.8s ease-in-out infinite 0.15s; }
.wave-bar-3 { animation: wave3 0.8s ease-in-out infinite 0.3s; }
```

### 3.2 Borde activo en card
```js
const activeClass = isActive 
    ? 'ring-1 ring-red-500/40 bg-red-500/5' 
    : '';
```

### 3.3 Barra de progreso en mini player
```html
<!-- Al fondo del mini player island -->
<div class="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5 rounded-full overflow-hidden">
    <div class="h-full bg-red-500 transition-all duration-300"
         :style="'width: ' + progress + '%'"></div>
</div>
```

---

## Fase 4 — Biblioteca unificada (IndexedDB + SQLite)
**Archivos:** `src/main.py`, `src/templates/library.html`, `src/static/js/app.js`  
**Duración estimada:** 2 sesiones — requiere cambios en backend

### 4.1 Nuevo endpoint de sincronización
```python
# En main.py
@app.get("/api/library/server-songs")
async def get_server_songs():
    """Devuelve canciones del SQLite que pueden ser re-descargadas a IndexedDB."""
    with get_session() as session:
        songs = session.exec(select(Song).order_by(Song.date_added.desc())).all()
        result = []
        for song in songs:
            result.append({
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "duration": song.duration,
                "thumbnail_url": song.thumbnail_url,
                "available": os.path.exists(song.file_path),
                "date_added": song.date_added.isoformat()
            })
    return result
```

### 4.2 Modo "biblioteca híbrida" en frontend
Al entrar a Library tab:
1. Cargar canciones de IndexedDB (disponibles offline, reproducción inmediata)
2. Fetch a `/api/library/server-songs`
3. Para songs del servidor que NO estén en IndexedDB, mostrarlas con badge "En servidor" y botón "Guardar offline"
4. Para songs que estén en ambos, mostrar solo la local (con prioridad IndexedDB)

### 4.3 Botón "Guardar offline" en songs del servidor
```js
async saveServerSongOffline(serverId) {
    // Fetch el archivo desde /api/audio/{serverId}
    const response = await fetch(`/api/audio/${serverId}`);
    const blob = await response.blob();
    // Guardar en IndexedDB
    await saveSongToLocal(metadata, blob);
    loadLocalLibrary();
}
```

---

## Fase 5 — Funciones adicionales de calidad
**Duración estimada:** 1-2 sesiones

### 5.1 Shuffle y Repeat
```js
// En playerData()
shuffle: false,
repeat: 'none',  // 'none' | 'all' | 'one'

toggleShuffle() { this.shuffle = !this.shuffle; },
toggleRepeat() {
    const modes = ['none', 'all', 'one'];
    const i = modes.indexOf(this.repeat);
    this.repeat = modes[(i + 1) % 3];
},
```

### 5.2 Volumen y mute
```js
volume: 1,
muted: false,
setVolume(val) {
    this.volume = val;
    document.getElementById('main-audio').volume = val;
},
toggleMute() {
    this.muted = !this.muted;
    document.getElementById('main-audio').muted = this.muted;
},
```

### 5.3 Búsqueda en biblioteca
```js
searchQuery: '',
get filteredQueue() {
    if (!this.searchQuery) return this.queue;
    const q = this.searchQuery.toLowerCase();
    return this.queue.filter(s => 
        s.title.toLowerCase().includes(q) || 
        s.artist.toLowerCase().includes(q)
    );
}
```

### 5.4 Persistencia del estado del player
Guardar en `localStorage` la canción actual y posición:
```js
// Al cambiar canción
localStorage.setItem('lastSong', JSON.stringify(this.currentSong));
localStorage.setItem('lastPosition', audio.currentTime);

// Al iniciar app
const last = localStorage.getItem('lastSong');
if (last) this.currentSong = JSON.parse(last);
```

---

## Resumen de prioridades

| Fase | Tareas | Backend? | Impacto usuario |
|---|---|---|---|
| **1** | Queue, anterior/siguiente, seeking, auto-advance | No | Muy alto |
| **2** | Menú tres puntos, opciones de canción | No | Alto |
| **3** | Indicadores visuales, waveform, barra mini player | No | Alto |
| **4** | Biblioteca unificada SQLite + IndexedDB | Sí | Medio |
| **5** | Shuffle, repeat, volumen, búsqueda, persistencia | No | Medio |

**Recomendación:** Implementar Fases 1, 2 y 3 en una sola sesión ya que son puramente frontend. Fase 4 requiere coordinar backend y es la más compleja.
