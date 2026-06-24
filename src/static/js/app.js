/**
 * Lógica principal de la aplicación PWA
 */

async function downloadAndSaveLocally(event, taskId, title, artist, duration, thumbnail) {
    console.log("Iniciando descarga local:", title);
    const btn = event.currentTarget || event.target;
    
    if (!btn) return;

    // 1. Verificar si ya existe en IndexedDB para evitar repetidos
    try {
        const existing = await db.songs
            .where('title').equals(title)
            .and(s => s.artist === artist)
            .first();
            
        if (existing) {
            btn.innerHTML = `
                <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>
                Ya está en tu biblioteca
            `;
            btn.classList.replace('bg-green-600', 'bg-blue-600');
            btn.disabled = true;
            return;
        }
    } catch (e) {
        console.warn("Error al verificar duplicados:", e);
    }

    // Cambiar estado a "Descargando..."
    btn.disabled = true;
    btn.innerHTML = `
        <span class="flex items-center">
            <svg class="animate-spin h-5 w-5 mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Guardando...
        </span>
    `;

    try {
        const response = await fetch(`/api/file/${taskId}`);
        if (!response.ok) throw new Error('Error al obtener el archivo del servidor');
        
        const blob = await response.blob();

        const metadata = {
            title: title,
            artist: artist,
            duration: parseInt(duration) || 0,
            thumbnail: thumbnail,
            platform: 'YouTube'
        };

        await saveSongToLocal(metadata, blob);

        // 3. Éxito: Cambiar botón permanentemente
        btn.innerHTML = `
            <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            Descargado con éxito
        `;
        btn.classList.remove('bg-green-600', 'hover:bg-green-700');
        btn.classList.add('bg-blue-600');
        btn.disabled = true;

        // Actualizar vista de biblioteca en segundo plano
        if (window.refreshLibraryView) window.refreshLibraryView();

    } catch (error) {
        console.error('Error:', error);
        btn.disabled = false;
        btn.innerHTML = 'Error. Reintentar descarga';
        btn.classList.add('bg-red-600');
    }
}

/**
 * Carga y renderiza la biblioteca musical desde IndexedDB
 */
async function loadLocalLibrary() {
    const container = document.getElementById('local-songs-container');
    if (!container) return;
    
    try {
        const songs = await getAllLocalSongs();

        // Registrar cola global para navegación anterior/siguiente
        window._libraryQueue = songs.map(s => ({
            id: s.id,
            title: s.title || 'Sin título',
            artist: s.artist || 'Desconocido',
            thumbnail: s.thumbnail || '',
            audioUrl: null
        }));

        // Guardar referencia global para filtrado/shuffle
        window._allLibrarySongs = songs;

        // Actualizar stats en el header
        const statsEl = document.getElementById('library-stats');
        if (statsEl) {
            if (songs.length === 0) {
                statsEl.textContent = 'Sin canciones';
            } else {
                const totalMin = Math.floor(songs.reduce((acc, s) => acc + (s.duration || 0), 0) / 60);
                statsEl.textContent = `${songs.length} ${songs.length === 1 ? 'canción' : 'canciones'} · ${totalMin} min`;
            }
        }

        if (songs.length === 0) {
            container.innerHTML = `
                <div class="text-center py-24 animate-fade-in">
                    <div class="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6 border border-white/5">
                        <svg class="w-10 h-10 text-white/10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/>
                        </svg>
                    </div>
                    <p class="text-white/30 font-black uppercase tracking-[0.2em] text-xs">Tu biblioteca está vacía.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = songs.map(song => {
            const title = (song.title || "Sin título").toString().replace(/'/g, "\\'");
            const artist = (song.artist || "Desconocido").toString().replace(/'/g, "\\'");
            const thumb = song.thumbnail || "";
            const safeDuration = formatDuration(song.duration);

            return `
            <div class="song-card crystal-glass rounded-[24px] flex items-center gap-4 animate-fade-in group cursor-pointer active:scale-[0.98] transition-all duration-200 relative overflow-hidden"
                 data-song-id="${song.id}"
                 data-genre="${(song.genre || 'Sin categoría').replace(/"/g, '&quot;')}"
                 onclick="playLocalSong(${song.id}, '${title}', '${artist}', '${thumb}')">

                <!-- Fondo borroso con la portada -->
                <div class="art-blur" style="background-image: url('${thumb}')"></div>

                <!-- Barra indicadora izquierda -->
                <div class="song-active-bar"></div>

                <!-- Contenido principal (sobre el blur) -->
                <div class="relative z-10 flex items-center gap-4 w-full p-3.5">

                    <!-- Portada -->
                    <div class="relative w-14 h-14 flex-shrink-0">
                        <img src="${thumb}" alt="${title}"
                             class="w-full h-full object-cover rounded-[16px] shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
                        <div class="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/25 transition-colors duration-200 rounded-[16px]">
                            <div class="w-8 h-8 flex items-center justify-center bg-white/90 rounded-full shadow-lg opacity-0 group-hover:opacity-100 scale-75 group-hover:scale-100 transition-all duration-200">
                                <svg class="w-4 h-4 text-black fill-current ml-0.5" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                        </div>
                    </div>

                    <!-- Info -->
                    <div class="flex-grow min-w-0">
                        <h3 class="text-white text-[14px] font-black tracking-tight truncate leading-tight">${song.title || "Sin título"}</h3>
                        <p class="text-white/40 text-[11px] font-semibold uppercase tracking-[0.12em] truncate mt-0.5">${song.artist || "Desconocido"}</p>
                    </div>

                    <!-- Duración + waveform + tres puntos -->
                    <div class="flex items-center gap-2 flex-shrink-0">
                        <span class="song-duration text-white/25 text-[11px] font-black tabular-nums">${safeDuration}</span>
                        <div class="song-waveform hidden items-end gap-[3px] h-4">
                            <div class="wave-bar wave-bar-1"></div>
                            <div class="wave-bar wave-bar-2"></div>
                            <div class="wave-bar wave-bar-3"></div>
                        </div>
                        <button onclick="event.stopPropagation(); showCardOptions(${song.id}, '${title}', '${artist}', '${thumb}', '${(song.genre || 'Sin categoría').replace(/'/g, "\\'")}', 'local')"
                                class="w-8 h-8 flex items-center justify-center rounded-xl text-white/20 hover:text-white/60 hover:bg-white/8 active:bg-white/15 transition-all">
                            <svg class="w-[18px] h-[18px]" fill="currentColor" viewBox="0 0 24 24">
                                <circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/>
                            </svg>
                        </button>
                    </div>

                </div>
            </div>
        `}).join('');

        // Renderizar pills de categoría y re-aplicar filtro activo
        renderLibraryGenrePills(songs);
        if (window._activeGenreFilter && window._activeGenreFilter !== 'Todas') {
            filterLibraryByGenre(window._activeGenreFilter);
        } else {
            window._activeGenreFilter = 'Todas';
        }

        // Aplicar estado activo si ya hay una canción sonando
        const alpineEl = document.querySelector('[x-data]');
        const activeSongId = window.Alpine ? window.Alpine.$data(alpineEl)?.currentSong?.id : null;
        if (activeSongId && window.updateActiveCard) {
            requestAnimationFrame(() => window.updateActiveCard(activeSongId, null));
        }

    } catch (error) {
        console.error('Error cargando biblioteca:', error);
        container.innerHTML = '<p class="text-red-500 text-center">Error al cargar la biblioteca local.</p>';
    }
}

/**
 * Reproduce una canción desde IndexedDB
 */
let currentObjectURL = null;

async function playLocalSong(id, title, artist, thumbnail) {
    try {
        const song = await db.songs.get(id);
        if (!song) return;

        if (currentObjectURL) {
            // Limpiar la referencia de la cola ANTES de revocar, para que
            // _loadAndPlay sepa que debe recargar desde IndexedDB si la necesita.
            const stale = (window._libraryQueue || []).find(s => s.audioUrl === currentObjectURL);
            if (stale) stale.audioUrl = null;
            URL.revokeObjectURL(currentObjectURL);
        }

        currentObjectURL = URL.createObjectURL(song.audioBlob);

        const el = document.querySelector('[x-data]');
        if (window.Alpine) {
            const data = window.Alpine.$data(el);

            // Sincronizar audioUrl en la cola y establecer posición
            const queue = window._libraryQueue || [];
            const index = queue.findIndex(s => s.id === id);
            if (index !== -1) {
                queue[index].audioUrl = currentObjectURL;
                data.setQueue(queue, index);
            }

            data.playSong(id, title, artist, thumbnail, currentObjectURL);
        }
    } catch (error) {
        console.error('Error al reproducir localmente:', error);
    }
}

/**
 * Elimina una canción de la biblioteca local
 */
async function deleteSong(id) {
    if (confirm('¿Quieres eliminar esta canción de tu dispositivo?')) {
        await deleteLocalSong(id);
        loadLocalLibrary();
    }
}

// Hacer global para que HTMX pueda llamarlo
window.refreshLibraryView = loadLocalLibrary;

/**
 * Reproduce una canción directamente desde el servidor (tab Online).
 * Construye una cola con todas las canciones visibles en el tab y usa
 * la URL de streaming del servidor como audioUrl (nunca se revoca).
 */
function playServerSong(songId, title, artist, thumbnail) {
    const el = document.querySelector('[x-data]');
    if (!window.Alpine || !el) return;
    const data = window.Alpine.$data(el);

    // Construir cola con todas las tarjetas visibles
    const cards = document.querySelectorAll('[data-server-song-id]');
    const queue = Array.from(cards).map(card => ({
        id: parseInt(card.dataset.serverSongId),
        title: card.dataset.songTitle || '',
        artist: card.dataset.songArtist || '',
        thumbnail: card.querySelector('img')?.src || '',
        audioUrl: `/api/audio/server/${card.dataset.serverSongId}`,
    }));

    window._serverQueue = queue;
    const index = queue.findIndex(s => s.id === songId);
    if (index !== -1) {
        data.setQueue(queue, index);
        data.playSong(songId, title, artist, thumbnail, `/api/audio/server/${songId}`);
    }
}

/**
 * Descarga el audio de una canción del servidor y la guarda en IndexedDB.
 */
async function saveServerSongOffline(btn, songId, title, artist, duration, thumbnail) {
    btn.disabled = true;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `
        <svg class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Guardando...
    `;
    try {
        const response = await fetch(`/api/audio/server/${songId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        await saveSongToLocal({ title, artist, duration, thumbnail, platform: 'YouTube' }, blob);

        btn.innerHTML = '✓ Guardado';
        btn.classList.add('opacity-40', 'cursor-default');

        // Mostrar badge "En dispositivo" en la tarjeta
        const card = btn.closest('[data-server-song-id]');
        if (card) {
            const badge = card.querySelector('.server-saved-badge');
            if (badge) badge.classList.remove('hidden');
        }

        if (window.refreshLibraryView) window.refreshLibraryView();
    } catch (err) {
        console.error('Error al guardar desde servidor:', err);
        btn.disabled = false;
        btn.innerHTML = originalHTML;
        btn.title = 'Error — intenta de nuevo';
    }
}

/**
 * Llama al endpoint de limpieza de duplicados en SQLite y recarga el tab Online.
 */
async function cleanOnlineDuplicates(btn) {
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.innerHTML = `<svg class="animate-spin w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
    </svg>`;
    try {
        const res  = await fetch('/api/clean-duplicates', { method: 'DELETE' });
        const data = await res.json();
        if (data.deleted > 0) {
            // Recargar el tab Online vía HTMX
            htmx.ajax('GET', '/ui/online-library', '#main-content');
        } else {
            btn.disabled = false;
            btn.innerHTML = original;
            btn.title = 'Sin duplicados que limpiar';
        }
    } catch (err) {
        console.error('Error limpiando duplicados:', err);
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

/**
 * Revisa qué canciones del servidor ya están en IndexedDB y actualiza
 * los botones de las tarjetas en el tab Online.
 */
async function checkServerSongsLocal() {
    const cards = document.querySelectorAll('[data-server-song-id]');
    for (const card of cards) {
        const title = card.dataset.songTitle;
        const artist = card.dataset.songArtist;
        if (!title) continue;
        try {
            const existing = await db.songs
                .where('title').equals(title)
                .and(s => s.artist === artist)
                .first();
            if (existing) {
                const btn = card.querySelector('.server-save-btn');
                if (btn) {
                    btn.innerHTML = '✓ Guardado';
                    btn.disabled = true;
                    btn.classList.add('opacity-40', 'cursor-default');
                }
                const badge = card.querySelector('.server-saved-badge');
                if (badge) badge.classList.remove('hidden');
            }
        } catch (_) { /* IndexedDB no disponible o error puntual */ }
    }
}

/**
 * Formatea segundos a MM:SS
 */
function formatDuration(seconds) {
    if (!seconds) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Filtra las tarjetas de la biblioteca según texto y/o género activo.
 */
function filterLibrary(query) {
    const q = (query || '').toLowerCase().trim();
    const activeGenre = window._activeGenreFilter || 'Todas';
    const cards = document.querySelectorAll('#local-songs-container [data-song-id]');
    let visible = 0;
    cards.forEach(card => {
        const cardGenre = card.dataset.genre || 'Sin categoría';
        const matchesGenre = activeGenre === 'Todas' || cardGenre === activeGenre;
        const h3 = card.querySelector('h3');
        const p  = card.querySelector('p');
        const title  = (h3?.textContent || '').toLowerCase();
        const artist = (p?.textContent  || '').toLowerCase();
        const matchesSearch = !q || title.includes(q) || artist.includes(q);
        const match = matchesGenre && matchesSearch;
        card.style.display = match ? '' : 'none';
        if (match) visible++;
    });
    const statsEl = document.getElementById('library-stats');
    if (!statsEl) return;
    if (q && activeGenre !== 'Todas') {
        statsEl.textContent = `${visible} resultado${visible !== 1 ? 's' : ''} en "${activeGenre}"`;
    } else if (q) {
        statsEl.textContent = `${visible} resultado${visible !== 1 ? 's' : ''}`;
    } else if (activeGenre !== 'Todas') {
        statsEl.textContent = `${visible} en "${activeGenre}"`;
    } else {
        const all = window._allLibrarySongs || [];
        const totalMin = Math.floor(all.reduce((acc, s) => acc + (s.duration || 0), 0) / 60);
        statsEl.textContent = `${all.length} ${all.length === 1 ? 'canción' : 'canciones'} · ${totalMin} min`;
    }
}

/**
 * Renderiza pills de categoría para la biblioteca local.
 */
function renderLibraryGenrePills(songs) {
    const container = document.getElementById('genre-pills-container');
    if (!container) return;

    const genreSet = new Set(songs.map(s => s.genre || 'Sin categoría'));
    if (genreSet.size <= 1) {
        container.classList.add('hidden');
        container.classList.remove('flex');
        return;
    }

    const activeGenre = window._activeGenreFilter || 'Todas';
    const genres = ['Todas', ...[...genreSet].sort()];

    container.innerHTML = genres.map(g => {
        const safeG = g.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const isActive = g === activeGenre;
        const activeCls = 'bg-red-500/20 text-red-300 border-red-500/30';
        const idleCls   = 'bg-white/5 text-white/40 border-white/10 hover:bg-white/10 hover:text-white/60';
        return `<button onclick="filterLibraryByGenre('${safeG}')"
                        data-genre="${safeG}"
                        class="flex-shrink-0 px-4 py-[9px] rounded-full text-[11px] font-black uppercase tracking-[0.08em] border transition-all active:scale-95 whitespace-nowrap ${isActive ? activeCls : idleCls}"
                >${g}</button>`;
    }).join('');

    container.classList.remove('hidden');
    container.classList.add('flex');
}

/**
 * Activa un filtro de categoría en la biblioteca local.
 */
function filterLibraryByGenre(genre) {
    window._activeGenreFilter = genre;

    // Actualizar estilos de pills
    document.querySelectorAll('#genre-pills-container button').forEach(pill => {
        const isActive = pill.dataset.genre === genre;
        const activeCls = ['bg-red-500/20', 'text-red-300', 'border-red-500/30'];
        const idleCls   = ['bg-white/5', 'text-white/40', 'border-white/10', 'hover:bg-white/10', 'hover:text-white/60'];
        activeCls.forEach(c => pill.classList.toggle(c, isActive));
        idleCls.forEach(c => pill.classList.toggle(c, !isActive));
    });

    // Re-aplicar filtro combinado (género + búsqueda activa)
    const searchVal = document.getElementById('library-search-input')?.value || '';
    filterLibrary(searchVal);
}

/**
 * Abre/cierra el campo de búsqueda de la biblioteca.
 */
function toggleLibrarySearch() {
    const wrapper = document.getElementById('library-search-wrapper');
    const input   = document.getElementById('library-search-input');
    const btn     = document.getElementById('library-search-btn');
    if (!wrapper) return;
    const isOpen = wrapper.classList.toggle('open');
    if (btn) btn.classList.toggle('text-white/70', isOpen);
    if (isOpen && input) {
        setTimeout(() => input.focus(), 50);
    } else {
        if (input) { input.value = ''; filterLibrary(''); }
    }
}

/**
 * Limpia el campo de búsqueda y muestra todas las canciones.
 */
function clearLibrarySearch() {
    const input = document.getElementById('library-search-input');
    if (input) { input.value = ''; input.focus(); }
    filterLibrary('');
}

/**
 * Mezcla la cola de la biblioteca y empieza a reproducir.
 */
function shuffleLibrary() {
    const songs = window._allLibrarySongs;
    if (!songs || songs.length === 0) return;
    const shuffled = [...songs].sort(() => Math.random() - 0.5);
    const el = document.querySelector('[x-data]');
    if (!window.Alpine || !el) return;
    const data = window.Alpine.$data(el);
    const queue = shuffled.map(s => ({
        id: s.id,
        title: s.title || 'Sin título',
        artist: s.artist || 'Desconocido',
        thumbnail: s.thumbnail || '',
        audioUrl: null,
    }));
    window._libraryQueue = queue;
    data.setQueue(queue, 0);
    playLocalSong(queue[0].id, queue[0].title, queue[0].artist, queue[0].thumbnail);
}

