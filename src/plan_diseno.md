# Plan de Mejora — Diseño (Liquid Glass · iOS 26+)
> Proyecto: Crystal Premium Downloader  
> Lenguaje visual base: **Liquid Glass** — el material de diseño de Apple introducido en iOS 26  
> Stack: Tailwind CDN + CSS custom + Alpine.js

---

## Qué es Liquid Glass

iOS 26 introduce un nuevo material unificado llamado **Liquid Glass**. No es simplemente "vidrio esmerilado" (frosted glass) de versiones anteriores. Sus características clave son:

1. **Refracción dinámica** — el vidrio distorsiona y magnifica ligeramente lo que hay detrás, como una lupa de vidrio real
2. **Borde especular** — el contorno del elemento tiene un highlight de luz que simula el grosor físico del vidrio
3. **Tintado ambiental** — el glass absorbe y refleja el color dominante del contenido detrás de él
4. **Sombra interior** — sombra suave hacia adentro en el borde superior, como un cristal con grosor
5. **Brillos de superficie** — gradiente especular sutil en la esquina superior del elemento
6. **Opacidad variable** — distintas capas del mismo elemento tienen distintas opacidades, creando profundidad
7. **Animaciones fluidas morfológicas** — los elementos se transforman suavemente como si fueran líquido, no objetos rígidos

---

## Material base: `liquid-glass`

### CSS del material principal

```css
/* Variables del sistema Liquid Glass */
:root {
    /* Colores de acento */
    --accent: #ef4444;
    --accent-glow: rgba(239, 68, 68, 0.35);
    --accent-soft: rgba(239, 68, 68, 0.12);

    /* Superficies */
    --surface-base: rgba(10, 15, 30, 0.55);
    --surface-elevated: rgba(20, 28, 48, 0.70);
    --surface-overlay: rgba(30, 42, 68, 0.80);

    /* Bordes Liquid Glass */
    --border-glass: rgba(255, 255, 255, 0.14);
    --border-specular: rgba(255, 255, 255, 0.28);  /* borde superior más brillante */
    --border-bottom: rgba(0, 0, 0, 0.25);           /* borde inferior más oscuro */

    /* Texto */
    --text-primary: rgba(255, 255, 255, 0.95);
    --text-secondary: rgba(255, 255, 255, 0.45);
    --text-tertiary: rgba(255, 255, 255, 0.20);

    /* Blur levels */
    --blur-sm: blur(12px) saturate(160%);
    --blur-md: blur(28px) saturate(180%);
    --blur-lg: blur(48px) saturate(200%) brightness(1.05);
}

/* Material Liquid Glass estándar */
.liquid-glass {
    background: var(--surface-base);
    backdrop-filter: var(--blur-md);
    -webkit-backdrop-filter: var(--blur-md);

    /* Borde con gradiente: arriba brillante, abajo oscuro */
    border: 1px solid transparent;
    background-clip: padding-box;
    box-shadow:
        /* Sombra exterior de profundidad */
        0 8px 40px rgba(0, 0, 0, 0.45),
        0 2px 8px rgba(0, 0, 0, 0.30),
        /* Borde especular superior (simula grosor del vidrio) */
        inset 0 1px 0 var(--border-specular),
        /* Sombra interior superior (refracción) */
        inset 0 -1px 0 var(--border-bottom),
        /* Borde lateral izquierdo */
        inset 1px 0 0 var(--border-glass),
        /* Borde lateral derecho */
        inset -1px 0 0 var(--border-glass);
}

/* Material elevado (menús, sheets, modales) */
.liquid-glass-elevated {
    background: var(--surface-elevated);
    backdrop-filter: var(--blur-lg);
    -webkit-backdrop-filter: var(--blur-lg);
    box-shadow:
        0 24px 80px rgba(0, 0, 0, 0.65),
        0 8px 24px rgba(0, 0, 0, 0.40),
        inset 0 1px 0 rgba(255, 255, 255, 0.22),
        inset 0 -1px 0 rgba(0, 0, 0, 0.30),
        inset 1px 0 0 rgba(255, 255, 255, 0.10),
        inset -1px 0 0 rgba(255, 255, 255, 0.10);
}

/* Highlight especular en esquina superior izquierda (reflejo de luz) */
.liquid-glass::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background: radial-gradient(
        ellipse 60% 40% at 30% 0%,
        rgba(255, 255, 255, 0.08) 0%,
        transparent 70%
    );
    pointer-events: none;
}

/* Tintado ambiental — se aplica via JS con color extraído del artwork */
.liquid-glass-tinted {
    background: color-mix(in srgb, var(--ambient-color, rgba(239,68,68,0.15)) 40%, var(--surface-base) 60%);
}
```

---

## Fase 1 — Sistema de materiales y tokens de diseño
**Archivos:** `src/templates/index.html` (sección `<style>`)  
**Objetivo:** Reemplazar las clases actuales `crystal-glass` por el sistema Liquid Glass unificado

### 1.1 Reemplazar `crystal-glass` por `liquid-glass`
La clase actual `crystal-glass` usa un blur básico. Reemplazarla con el sistema completo descrito arriba.

### 1.2 Sistema de elevación (z-layers)
Definir 4 niveles de material con profundidad visual creciente:

| Nivel | Clase | Uso | Blur | Opacidad fondo |
|---|---|---|---|---|
| 0 | Fondo global | Body background | — | — |
| 1 | `lg-surface` | Cards de biblioteca | 20px | 50% |
| 2 | `lg-elevated` | Tab bar, mini player | 32px | 65% |
| 3 | `lg-overlay` | Menús, sheets | 48px | 75% |
| 4 | `lg-modal` | Player expandido | 60px | 85% |

### 1.3 Paleta de colores semántica
```css
/* Colores del tema (únicos, sin variaciones Tailwind ad-hoc) */
:root {
    --color-bg:        #05080f;   /* fondo global */
    --color-accent:    #ef4444;   /* rojo de acción */
    --color-success:   #22c55e;
    --color-warning:   #f59e0b;
    --color-danger:    #ef4444;
}
```

---

## Fase 2 — Fondo global animado y ambient light
**Archivos:** `src/templates/index.html`  
**Objetivo:** El fondo responde visualmente a la canción que suena

### 2.1 Capas de fondo
```html
<!-- Capa 1: color base oscuro -->
<div class="fixed inset-0 z-[-3]" style="background: var(--color-bg)"></div>

<!-- Capa 2: nebulosas de color fijas (decoración estática) -->
<div class="fixed inset-0 z-[-2] overflow-hidden pointer-events-none">
    <div class="nebula nebula-1"></div>  <!-- esquina superior izquierda -->
    <div class="nebula nebula-2"></div>  <!-- esquina inferior derecha -->
    <div class="nebula nebula-3"></div>  <!-- centro -->
</div>

<!-- Capa 3: ambient light de la canción actual (controlado por Alpine) -->
<div class="fixed inset-0 z-[-1] transition-all duration-[2000ms] pointer-events-none"
     :style="'background: radial-gradient(ellipse 70% 50% at 50% 100%, ' + accentColor + ' 0%, transparent 70%)'">
</div>
```

```css
.nebula {
    position: absolute;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.18;
    animation: nebula-drift 20s ease-in-out infinite alternate;
}
.nebula-1 {
    width: 50vw; height: 50vw;
    top: -15%; left: -15%;
    background: radial-gradient(circle, #7c3aed, #3b0764);
    animation-delay: 0s;
}
.nebula-2 {
    width: 40vw; height: 40vw;
    bottom: -10%; right: -10%;
    background: radial-gradient(circle, #1d4ed8, #0c1445);
    animation-delay: -8s;
}
.nebula-3 {
    width: 30vw; height: 30vw;
    top: 40%; left: 35%;
    background: radial-gradient(circle, #991b1b, #450a0a);
    animation-delay: -14s;
}

@keyframes nebula-drift {
    0%   { transform: translate(0, 0) scale(1); }
    33%  { transform: translate(5%, -5%) scale(1.05); }
    66%  { transform: translate(-3%, 8%) scale(0.97); }
    100% { transform: translate(4%, 3%) scale(1.02); }
}
```

### 2.2 Extracción de color del artwork (Alpine)
```js
// Reemplazar el Math.random() actual por extracción real

async extractDominantColor(imgUrl) {
    return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = 1;
            canvas.getContext('2d').drawImage(img, 0, 0, 1, 1);
            const [r, g, b] = canvas.getContext('2d').getImageData(0, 0, 1, 1).data;
            // Saturar el color para hacerlo más vívido
            const factor = 1.4;
            resolve(`rgba(${Math.min(255,r*factor)}, ${Math.min(255,g*factor*0.6)}, ${Math.min(255,b*factor*0.6)}, 0.5)`);
        };
        img.onerror = () => resolve('rgba(239, 68, 68, 0.4)');
        img.src = imgUrl;
    });
},

// En playSong(), reemplazar la línea de Math.random():
this.accentColor = await this.extractDominantColor(thumbnail);
```

---

## Fase 3 — Rediseño de la página de descarga
**Archivos:** `src/templates/download_view.html`  
**Objetivo:** Hero más impactante, input con vidrio líquido, estados visuales más claros

### 3.1 Hero section
```
┌─────────────────────────────────────────────────┐
│                                                 │
│   DESCARGA                        ← texto grande│
│   SIN LÍMITES.                    ← tracking    │
│                                                 │
│   Pega cualquier link de YouTube               │
│   y descarga en MP4 o MP3.                     │
│                                                 │
│  ┌────────────────────────────────────────────┐ │
│  │ 🔗  youtube.com/watch?v=...            [→] │ │  ← liquid-glass
│  └────────────────────────────────────────────┘ │
│                                                 │
│  ⚡ Rápido  ·  🔒 Sin registro  ·  📱 Offline  │
└─────────────────────────────────────────────────┘
```

```css
/* Input estilo Liquid Glass */
.lg-input {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(20px) saturate(150%);
    border: 1px solid transparent;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.12),
        inset 0 -1px 0 rgba(0,0,0,0.20),
        0 4px 20px rgba(0,0,0,0.30);
    transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
}
.lg-input:focus-within {
    background: rgba(255, 255, 255, 0.07);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.18),
        inset 0 -1px 0 rgba(0,0,0,0.20),
        0 0 0 2px var(--accent-glow),
        0 8px 32px rgba(0,0,0,0.40);
}
```

### 3.2 Card de preview de video
```
┌─────────────────────────────────────────────────┐  ← liquid-glass-elevated
│ ┌──────────┐  Título del Video Muy Largo...     │
│ │ thumbnail│  Canal · 5:32                      │
│ │  16:9    │                                    │
│ │          │  [───── Resolución ▾ ──────]        │
│ └──────────┘                                    │
│                                                 │
│  [      ▼ VIDEO      ]  [  ♪ AUDIO MP3  ]      │
└─────────────────────────────────────────────────┘
```

Los botones de descarga con estilo Liquid Glass:
```css
.btn-lg-primary {
    background: rgba(255,255,255,0.92);
    color: #000;
    box-shadow:
        0 1px 0 rgba(255,255,255,1) inset,  /* highlight superior */
        0 4px 16px rgba(0,0,0,0.3),
        0 1px 4px rgba(0,0,0,0.2);
    transition: all 0.2s cubic-bezier(0.23,1,0.32,1);
}
.btn-lg-primary:active {
    transform: scale(0.97);
    box-shadow: 0 1px 6px rgba(0,0,0,0.2);
}

.btn-lg-secondary {
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.18),
        inset 0 -1px 0 rgba(0,0,0,0.15),
        0 4px 12px rgba(0,0,0,0.25);
}
```

### 3.3 Barra de progreso de descarga
```css
.progress-bar-liquid {
    height: 4px;
    background: rgba(255,255,255,0.06);
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.3);
}
.progress-bar-liquid-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), #f97316);
    border-radius: 999px;
    box-shadow: 0 0 12px rgba(239,68,68,0.6);
    transition: width 0.3s ease-out;
}
```

---

## Fase 4 — Rediseño de la biblioteca
**Archivos:** `src/static/js/app.js`, `src/templates/index.html`  
**Objetivo:** Cards con más personalidad, jerarquía visual clara, estado activo

### 4.1 Card de canción — Anatomía rediseñada
```
┌─────────────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│ ← blur de artwork como fondo
│ ┌──────┐  Título de la canción            3:45 │
│ │      │  ARTISTA                    [▶] [···] │
│ └──────┘                                       │
│ ──────────────────────────────────────────────  │ ← divisor
└─────────────────────────────────────────────────┘
```

Para la card activa, añadir:
- Borde izquierdo rojo (`border-l-2 border-red-500`)
- Fondo tintado con el color de acento de la canción
- Waveform animado en lugar del botón play

```css
.song-card {
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
}
/* Reflejo de artwork como fondo difuso */
.song-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: inherit;   /* se setea via JS con el thumbnail */
    filter: blur(40px) saturate(200%);
    opacity: 0;
    transition: opacity 0.5s ease;
    z-index: 0;
}
.song-card.active::before {
    opacity: 0.15;
}
```

### 4.2 Encabezado de biblioteca con stats
```
┌─────────────────────────────────────────────────┐
│  Mi Biblioteca          [🔀] [Buscar 🔍]        │
│  12 canciones · 47 min                          │
└─────────────────────────────────────────────────┘
```

### 4.3 Campo de búsqueda estilo Liquid Glass
```html
<div class="lg-input flex items-center gap-3 rounded-2xl px-4 py-3 mb-4" x-show="showSearch">
    <svg class="w-4 h-4 text-white/30 flex-shrink-0"><!-- search icon --></svg>
    <input type="text" 
           x-model="searchQuery"
           placeholder="Buscar en biblioteca..."
           class="bg-transparent text-sm outline-none text-white placeholder-white/30 w-full">
    <button @click="searchQuery = ''; showSearch = false" x-show="searchQuery">
        <svg><!-- x icon --></svg>
    </button>
</div>
```

---

## Fase 5 — Rediseño del player expandido
**Archivos:** `src/templates/index.html`  
**Objetivo:** Full Liquid Glass experience, fondo ambiental dinámico, controles con material glass

### 5.1 Estructura del player expandido
```
┌─────────────────────────────────────────────────┐
│  [∨ Cerrar]      NOW PLAYING         [···]      │  ← header
│                                                 │
│          ╔═══════════════════╗                  │
│          ║                   ║                  │
│          ║   Album Art       ║                  │  ← artwork elevado
│          ║   (cuadrado)      ║                  │    con sombra líquida
│          ╚═══════════════════╝                  │
│                                                 │
│           Título de la Canción                  │  ← texto
│           ARTISTA                    [♡]        │
│                                                 │
│  0:00  ████████████████░░░░░░░░  3:45          │  ← seekbar interactiva
│                                                 │
│         [⏮]    [    ▶▶    ]    [⏭]            │  ← controles
│                                                 │
│              [🔀]         [🔁]                 │  ← shuffle / repeat
│                                                 │
│  ─────────── VOLUME ──────────────────────────  │
│  [🔇]  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  [🔊]              │
└─────────────────────────────────────────────────┘
```

### 5.2 Artwork con efecto Liquid Glass
```css
.player-artwork {
    border-radius: 32px;
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.15),        /* borde especular */
        0 24px 80px -12px rgba(0,0,0,0.8),       /* sombra principal */
        0 4px 16px rgba(0,0,0,0.5),              /* sombra cercana */
        inset 0 1px 0 rgba(255,255,255,0.2);     /* highlight superior */
    transition: transform 0.5s cubic-bezier(0.23, 1, 0.32, 1),
                box-shadow 0.5s ease;
}
/* Cuando está reproduciendo, la cover "flota" levemente */
.player-artwork.playing {
    transform: scale(1.03) translateY(-4px);
    box-shadow:
        0 0 0 1px rgba(255,255,255,0.18),
        0 40px 100px -12px rgba(0,0,0,0.9),
        0 8px 24px rgba(0,0,0,0.6),
        inset 0 1px 0 rgba(255,255,255,0.25);
}
```

### 5.3 Controles con material Liquid Glass
```css
/* Botón principal play/pause */
.btn-play-liquid {
    width: 80px; height: 80px;
    border-radius: 50%;
    background: rgba(255,255,255,0.90);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,1),
        inset 0 -2px 0 rgba(0,0,0,0.10),
        0 8px 32px rgba(0,0,0,0.40),
        0 2px 8px rgba(0,0,0,0.25);
    transition: all 0.2s cubic-bezier(0.23,1,0.32,1);
}
.btn-play-liquid:active {
    transform: scale(0.92);
    box-shadow: 0 4px 16px rgba(0,0,0,0.30);
}

/* Botones secundarios (anterior/siguiente) */
.btn-control-liquid {
    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(10px);
    border-radius: 50%;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.15),
        0 4px 12px rgba(0,0,0,0.25);
    transition: all 0.2s ease;
}
.btn-control-liquid:active {
    transform: scale(0.90);
    background: rgba(255,255,255,0.12);
}
```

### 5.4 Seekbar interactiva estilo Liquid Glass
```css
.seekbar-track {
    height: 4px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.4);
    cursor: pointer;
    position: relative;
    /* Ampliar área de toque sin cambiar la visual */
    padding: 12px 0;
    margin: -12px 0;
}
.seekbar-fill {
    height: 4px;
    border-radius: 999px;
    background: white;
    box-shadow: 0 0 12px rgba(255,255,255,0.5);
    position: relative;
}
/* Thumb invisible hasta hover/touch */
.seekbar-thumb {
    width: 14px; height: 14px;
    border-radius: 50%;
    background: white;
    position: absolute;
    right: -7px; top: -5px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    opacity: 0;
    transition: opacity 0.2s;
}
.seekbar-track:hover .seekbar-thumb,
.seekbar-track:active .seekbar-thumb {
    opacity: 1;
}
```

---

## Fase 6 — Tab bar y mini player
**Archivos:** `src/templates/index.html`  
**Objetivo:** Tab bar como island flotante con Liquid Glass, mini player refinado

### 6.1 Tab bar — Pill activo animado
```html
<div class="tab-bar-island rounded-[32px] flex p-1.5 relative">
    <!-- Pill de fondo que se mueve con transición -->
    <div class="absolute h-[calc(100%-12px)] transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] rounded-[24px] bg-white/10 backdrop-blur-sm"
         :style="activeTab === 'download' ? 'left: 6px; width: calc(50% - 9px)' : 'left: calc(50% + 3px); width: calc(50% - 9px)'">
    </div>
    
    <button class="flex-1 flex flex-col items-center py-3.5 rounded-[24px] relative z-10 transition-all" ...>
        <!-- icon + label -->
    </button>
    <button class="flex-1 flex flex-col items-center py-3.5 rounded-[24px] relative z-10 transition-all" ...>
        <!-- icon + label -->
    </button>
</div>
```

### 6.2 Mini player — Barra de progreso integrada
```html
<div class="tab-bar-island rounded-2xl overflow-hidden relative">
    <!-- Contenido del mini player -->
    <div class="p-3 flex items-center gap-4">
        <img ...>
        <div class="flex-grow min-w-0">...</div>
        <button @click.stop="playPrev()" ...>⏮</button>
        <button @click.stop="togglePlay()" ...>▶/⏸</button>
        <button @click.stop="playNext()" ...>⏭</button>
    </div>
    
    <!-- Barra de progreso ultra-fina en la base -->
    <div class="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5">
        <div class="h-full bg-white/60 transition-all duration-300"
             :style="'width: ' + progress + '%'">
        </div>
    </div>
</div>
```

### 6.3 Animación de entrada del mini player
```css
/* Reemplazar la animación de entrada actual por una más fluida */
@keyframes mini-player-enter {
    0%   { transform: translateY(100%) scale(0.95); opacity: 0; }
    60%  { transform: translateY(-4px) scale(1.01); opacity: 1; }
    100% { transform: translateY(0) scale(1); opacity: 1; }
}
.mini-player-enter { animation: mini-player-enter 0.5s cubic-bezier(0.23, 1, 0.32, 1) forwards; }
```

---

## Fase 7 — Tipografía y detalles finales
**Archivos:** `src/templates/index.html`  

### 7.1 Jerarquía tipográfica
```css
/* Títulos de pantalla */
.text-screen-title {
    font-size: clamp(2rem, 6vw, 3rem);
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 1.0;
}
/* Títulos de sección */
.text-section-title {
    font-size: 1.25rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}
/* Labels de metadatos */
.text-meta {
    font-size: 0.6875rem;  /* 11px */
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-secondary);
}
```

### 7.2 Micro-interacciones
```css
/* Feedback táctil en todos los botones interactivos */
[role="button"], button {
    -webkit-tap-highlight-color: transparent;
    user-select: none;
}
.tap-scale:active { transform: scale(0.94); }
.tap-scale-sm:active { transform: scale(0.96); }

/* Transiciones de página entre tabs */
.tab-enter { animation: tab-slide-in 0.35s cubic-bezier(0.23, 1, 0.32, 1) forwards; }
@keyframes tab-slide-in {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
```

### 7.3 Estados vacíos con personalidad
Para biblioteca vacía:
```
        ╔═══════╗
        ║  ♪ ♫ ║   ← ícono grande con liquid-glass
        ╚═══════╝
        
    Tu biblioteca está vacía
    Descarga tu primera canción
    para empezar a escuchar.
    
    [  Ir a Descargar  ]   ← botón que lleva al tab de descarga
```

---

## Resumen de fases

| Fase | Contenido | Complejidad | Impacto visual |
|---|---|---|---|
| **1** | Sistema de materiales y tokens CSS | Baja | Base de todo |
| **2** | Fondo ambiental animado + extracción de color | Media | Muy alto |
| **3** | Rediseño página de descarga | Baja | Alto |
| **4** | Rediseño de biblioteca + cards | Media | Alto |
| **5** | Rediseño player expandido full Liquid Glass | Alta | Muy alto |
| **6** | Tab bar pill animado + mini player refinado | Baja | Alto |
| **7** | Tipografía, micro-interacciones, estados vacíos | Baja | Medio |

**Orden recomendado:** 1 → 6 → 2 → 7 → 3 → 4 → 5  
Razón: empezar por la infraestructura CSS (1) y los elementos globales (6, 7) antes de refinar pantallas individuales (3, 4, 5).
