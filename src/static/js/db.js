// Configuración de la Base de Datos Local con Dexie.js
const db = new Dexie("MusicLibrary");

// v1 — schema original (no modificar; Dexie necesita el historial completo)
db.version(1).stores({
    songs: "++id, title, artist, duration, thumbnail, dateAdded, platform"
});

// v2 — agrega campo 'genre' para categorías
//       El upgrade asigna "Sin categoría" a los registros existentes.
db.version(2).stores({
    songs: "++id, title, artist, duration, thumbnail, dateAdded, platform, genre"
}).upgrade(tx => {
    return tx.table("songs").toCollection().modify(song => {
        if (!song.genre) song.genre = "Sin categoría";
    });
});

/**
 * Guarda una canción y su archivo (Blob) en IndexedDB.
 * @param {object} metadata - { title, artist, duration, thumbnail, platform, genre? }
 * @param {Blob}   audioBlob
 */
async function saveSongToLocal(metadata, audioBlob) {
    try {
        const songId = await db.songs.add({
            title:     metadata.title,
            artist:    metadata.artist,
            duration:  metadata.duration,
            thumbnail: metadata.thumbnail,
            platform:  metadata.platform,
            genre:     metadata.genre || "Sin categoría",
            dateAdded: new Date(),
            audioBlob: audioBlob
        });
        console.log("Éxito: Canción guardada en IndexedDB con ID:", songId);
        return songId;
    } catch (error) {
        console.error("Error guardando en IndexedDB:", error);
        throw error;
    }
}

/**
 * Recupera todas las canciones guardadas (más recientes primero).
 */
async function getAllLocalSongs() {
    return await db.songs.orderBy("dateAdded").reverse().toArray();
}

/**
 * Recupera todas las canciones de una categoría específica.
 */
async function getSongsByGenre(genre) {
    if (!genre || genre === "Todas") return getAllLocalSongs();
    return await db.songs.where("genre").equals(genre).reverse().sortBy("dateAdded");
}

/**
 * Actualiza la categoría de una canción local.
 */
async function updateSongGenre(id, genre) {
    return await db.songs.update(id, { genre });
}

/**
 * Devuelve las categorías únicas presentes en la biblioteca local.
 */
async function getLocalGenres() {
    const songs = await db.songs.toArray();
    const genres = [...new Set(songs.map(s => s.genre || "Sin categoría"))].sort();
    return genres;
}

/**
 * Elimina una canción por ID.
 */
async function deleteLocalSong(id) {
    return await db.songs.delete(id);
}
