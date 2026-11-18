"""Menu DVD-style per serie TV.

Il menu e' disegnato con pygame. Quando scegli una puntata, il menu
cede il posto a VLC in una finestra a schermo intero; quando il video
finisce (o chiudi VLC), si torna al menu. I video restano nel loro
formato originale (H.265 incluso): nessuna conversione.

Impostazione della schermata (4 puntate per pagina):
    1) sfondo e scritta LAZARUS, liberi nella fascia alta
    2) fila di 4 celle al centro-alto: miniatura se selezionata,
       titolo se a riposo
    3) frecce di pagina ai lati della fila
    4) nome della puntata e descrizione, direttamente sullo sfondo,
       nella fascia bassa (senza riquadro)
    5) pallini di pagina e legenda in fondo

La selezione segue il puntatore del mouse: passando su una cella
cambiano miniatura e descrizione.

Struttura della cartella:
    SerieTV/
    |-- main.py
    |-- menu_config.json
    |-- sfondo.jpg
    |-- font_lazarus.ttf    (Cinzel: facoltativo)
    |-- musica.mp3          (musica di sottofondo: facoltativa)
    |-- descrizioni.json    (testi degli episodi)
    |-- citta/              (una miniatura per puntata)
    +-- puntate/
        |-- Puntata #01 - Seattle.mp4
        +-- ...

Comandi nel menu:
    frecce            : muovi la selezione
    Invio / Spazio    : riproduci la voce selezionata
    click del mouse   : seleziona e riproduci
    Esc               : esci
"""

import json
import os
import subprocess
import sys

import pygame


# ---------------------------------------------------------------- percorsi
def base_path():
    """Cartella delle risorse, valida sia da script sia dagli exe (Win/Mac)."""
    if getattr(sys, "frozen", False):
        eseguibile = os.path.dirname(os.path.abspath(sys.executable))
        for candidato in (
            os.path.join(eseguibile, "_internal"),
            os.path.abspath(os.path.join(eseguibile, "..", "Resources")),
            os.path.abspath(os.path.join(eseguibile, "..", "Frameworks")),
        ):
            if os.path.isdir(candidato) and os.path.exists(os.path.join(candidato, "menu_config.json")):
                return candidato
        return getattr(sys, "_MEIPASS", eseguibile)
    return os.path.dirname(os.path.abspath(__file__))


def trova_video_dir(base):
    """Cerca 'puntate' dentro base (_internal) oppure accanto all'eseguibile/app."""
    interno = os.path.join(base, "puntate")
    if os.path.isdir(interno):
        return interno
    if getattr(sys, "frozen", False):
        eseguibile = os.path.dirname(os.path.abspath(sys.executable))
        if sys.platform == "darwin" and ".app/Contents/MacOS" in eseguibile.replace("\\", "/"):
            esterno = os.path.abspath(os.path.join(eseguibile, "..", "..", "..", "puntate"))
        else:
            esterno = os.path.join(eseguibile, "puntate")
        if os.path.isdir(esterno):
            return esterno
    return interno


BASE = base_path()
VIDEO_DIR = trova_video_dir(BASE)
CITTA_DIR = os.path.join(BASE, "citta")
LUOGHI_DIR = os.path.join(BASE, "luoghi")
# mappe di dettaglio delle tappe: mappe/seattle.png, mappe/los_angeles.png...
MAPPE_DIR = os.path.join(BASE, "mappe")
CONFIG_PATH = os.path.join(BASE, "menu_config.json")
DESCR_PATH = os.path.join(BASE, "descrizioni.json")

DEFAULT_CONFIG = {
    "titolo": "LAZARUS",
    "sottotitolo": "Stagione 1",
    "sfondo": "sfondo.jpg",
    "colonne": 3,
    "musica": "musica.mp3",
    "volume": 0.30,
}

ESTENSIONI = (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".ts", ".mpg")
EST_IMG = (".jpg", ".jpeg", ".png", ".bmp")

# quante puntate per pagina
PER_PAGINA = 4


# ---------------------------------------------------------------- le sei pagine
# Ogni pagina e' una lista di puntate, con il nome del file senza
# estensione. Dove la pagina ha meno di quattro puntate, la cella che
# avanza resta vuota.
PAGINE = [
    ["promo", "Puntata #01 - Seattle", "Puntata #02 - Seattle",
     "Puntata #03 - Portland"],
    ["Puntata #04 - San Francisco", "Puntata #05 - San Francisco",
     "Puntata #06 - San Francisco", "Puntata #07 - On The Road"],
    ["Puntata #08 - Los Angeles", "Puntata #09 - Los Angeles",
     "Puntata #10 - Los Angeles", "Puntata #11 - Los Angeles"],
    ["Puntata #12 - Death Valley", "Puntata #13 - Las Vegas",
     "Puntata #14 - Las Vegas"],
    ["Puntata #15 - Memphis", "Puntata #16 - Memphis",
     "Puntata #17 - Memphis-Nashville"],
    ["Puntata #18 - New York", "Puntata #19 - New York",
     "Puntata #20 - New York"],
]
N_PAGINE = len(PAGINE)


# ------------------------------------------------------------- le tappe sulla mappa
# Ogni tappa: nome da mostrare, posizione sull'immagine in percentuale
# (x da sinistra, y dall'alto) e le puntate ambientate li'.
# Le posizioni vanno ritoccate guardando dove cade il punto sulla mappa.
# "etichetta": False per le tappe che non mostrano il nome fisso
# sulla mappa: resta il punto, e il nome compare nel pannello al
# passaggio del puntatore.
TAPPE = [
    {"nome": "SEATTLE", "x": 0.162, "y": 0.086,
     "puntate": ["Puntata #01 - Seattle", "Puntata #02 - Seattle"]},
    {"nome": "PORTLAND", "x": 0.144, "y": 0.163,
     "puntate": ["Puntata #03 - Portland"]},
    {"nome": "SAN FRANCISCO", "x": 0.119, "y": 0.424,
     "puntate": ["Puntata #04 - San Francisco",
                 "Puntata #05 - San Francisco",
                 "Puntata #06 - San Francisco"]},
    {"nome": "ON THE ROAD", "x": 0.130, "y": 0.500, "etichetta": False,
     "puntate": ["Puntata #07 - On The Road"]},
    {"nome": "LOS ANGELES", "x": 0.165, "y": 0.586,
     "puntate": ["Puntata #08 - Los Angeles", "Puntata #09 - Los Angeles",
                 "Puntata #10 - Los Angeles", "Puntata #11 - Los Angeles"]},
    {"nome": "DEATH VALLEY", "x": 0.185, "y": 0.545, "etichetta": False,
     "puntate": ["Puntata #12 - Death Valley"]},
    {"nome": "LAS VEGAS", "x": 0.215, "y": 0.524,
     "puntate": ["Puntata #13 - Las Vegas", "Puntata #14 - Las Vegas"]},
    {"nome": "MEMPHIS", "x": 0.617, "y": 0.608,
     "puntate": ["Puntata #15 - Memphis", "Puntata #16 - Memphis",
                 "Puntata #17 - Memphis-Nashville"]},
    {"nome": "NEW YORK", "x": 0.840, "y": 0.340,
     "puntate": ["Puntata #18 - New York", "Puntata #19 - New York",
                 "Puntata #20 - New York"]},
]
N_TAPPE = len(TAPPE)


# --------------------------------------------------------- griglia di riferimento
# Metti True per vedere la griglia sulla mappa: serve a leggere le
# coordinate dei segnaposto. A lavoro finito, rimetti False.
MOSTRA_GRIGLIA = False

# Titoli mostrati nelle celle, quando devono essere diversi dal nome
# del file. La chiave e' il nome del file senza estensione.
TITOLI_CELLE = {
    "promo": ["Trailer"],
}

# Titoli da mostrare diversi dal nome del file. Serve per i caratteri
# non ammessi nei nomi su Windows (lo slash).
TITOLI_SPECIALI = {
    "Memphis-Nashville": "Memphis/Nashville",
}


def carica_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def carica_descrizioni():
    """Legge descrizioni.json: nome senza estensione -> [titolo, testo]."""
    dati = {}
    try:
        with open(DESCR_PATH, "r", encoding="utf-8") as f:
            grezzo = json.load(f)
    except Exception as e:
        print("[descrizioni] non lette:", e)
        return dati

    for chiave, valore in grezzo.items():
        if isinstance(valore, dict):
            dati[chiave] = [valore.get("titolo", ""), valore.get("testo", "")]
        else:
            dati[chiave] = ["", str(valore)]

    print("[descrizioni] caricate:", len(dati), "voci")
    return dati


def elenca_puntate():
    if not os.path.isdir(VIDEO_DIR):
        return []
    return sorted(f for f in os.listdir(VIDEO_DIR)
                  if f.lower().endswith(ESTENSIONI))


def dividi_titolo(label):
    """Divide il titolo su due righe, senza trattino."""
    for finto, vero in TITOLI_SPECIALI.items():
        label = label.replace(finto, vero)

    if " - " in label:
        prima, _, dopo = label.partition(" - ")
        return [prima.strip(), dopo.strip()]

    return [label.strip()]


def trova_immagine_citta(nome_senza_estensione):
    """Cerca citta/<nome>.<ext>: per le miniature delle celle.

    Vale per le puntate e per la cella "IL VIAGGIO": l'immagine si
    cerca nella stessa cartella citta/, con il nome che le si passa.
    """
    if not nome_senza_estensione or not os.path.isdir(CITTA_DIR):
        return None
    for ext in EST_IMG:
        percorso = os.path.join(CITTA_DIR,
                                nome_senza_estensione + ext)
        if os.path.isfile(percorso):
            return percorso
    return None


def trova_immagine(nome_video):
    """Cerca citta/<titolo del video>.<ext>, con il nome identico."""
    if not nome_video or not os.path.isdir(CITTA_DIR):
        return None
    base = os.path.splitext(nome_video)[0]
    for ext in EST_IMG:
        percorso = os.path.join(CITTA_DIR, base + ext)
        if os.path.isfile(percorso):
            return percorso
    return None


# ---------------------------------------------------------- eseguibile VLC
_VLC_CACHE = {"percorso": None, "cercato": False}


def trova_vlc():
    """Trova l'eseguibile di VLC, anche portatile accanto al menu."""
    if _VLC_CACHE["cercato"]:
        return _VLC_CACHE["percorso"]

    candidati = []
    if sys.platform == "darwin":
        for sottocartella in ("", "vlc", "VLC"):
            b = os.path.join(BASE, sottocartella) if sottocartella else BASE
            candidati.append(os.path.join(b, "VLC.app", "Contents", "MacOS", "VLC"))
        candidati.append("/Applications/VLC.app/Contents/MacOS/VLC")
        candidati.append(os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC"))
    for sottocartella in ("vlc", "VLC", "vlc-portable", "VLC-portable"):
        candidati.append(os.path.join(BASE, sottocartella, "vlc.exe"))

    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        base = os.environ.get(var)
        if base:
            candidati.append(os.path.join(base, "VideoLAN", "VLC", "vlc.exe"))
    candidati.append(r"C:\Program Files\VideoLAN\VLC\vlc.exe")
    candidati.append(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe")

    trovato = None
    for c in candidati:
        if os.path.isfile(c):
            trovato = c
            break

    if trovato is None and sys.platform == "win32":
        try:
            import winreg
            for radice in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(radice, r"SOFTWARE\VideoLAN\VLC") as k:
                        percorso = winreg.QueryValueEx(k, "")[0]
                        c = os.path.join(percorso, "vlc.exe")
                        if os.path.isfile(c):
                            trovato = c
                            break
                except Exception:
                    pass
        except Exception:
            pass

    if trovato is None:
        trovato = "vlc"

    _VLC_CACHE["percorso"] = trovato
    _VLC_CACHE["cercato"] = True
    return trovato


def riproduci_attesa(percorso):
    """Apre VLC a schermo intero sul video e aspetta.

    Comando ridotto all'essenziale: niente opzioni di log, che su
    alcuni sistemi fanno uscire VLC subito. Stampa nel terminale cosa
    succede, cosi' un problema non resta in silenzio.
    """
    vlc = trova_vlc()
    comando = [vlc, "--fullscreen", "--no-video-title-show",
               "--play-and-exit", percorso]
    try:
        processo = subprocess.Popen(comando)
    except Exception as e:
        print("[vlc] non avviato:", e)
        return False

    print("[vlc] avviato su", os.path.basename(percorso))
    codice = processo.wait()
    print("[vlc] chiuso con codice", codice)
    return True


# ---------------------------------------------------------------- pygame
pygame.init()
info = pygame.display.Info()
W, H = info.current_w, info.current_h

screen = pygame.display.set_mode((W, H), pygame.NOFRAME)
pygame.display.set_caption("Menu Serie")
pygame.mouse.set_visible(True)
pygame.event.pump()
pygame.event.clear()
clock = pygame.time.Clock()

cfg = carica_config()
puntate = elenca_puntate()
descrizioni = carica_descrizioni()

# ---------------------------------------------------------------- colori
PIETRA = (237, 232, 222)
ORO = (201, 162, 39)
GELO = (168, 200, 220)
AZZURRO = (185, 198, 210)
NERO = (8, 10, 14)
SCURO = (16, 24, 34)

# ---------------------------------------------------------------- font
FONT_FILE = os.path.join(BASE, "font_lazarus.ttf")

if os.path.isfile(FONT_FILE):
    def _crea_font(dimensione):
        return pygame.font.Font(FONT_FILE, dimensione)
    print("[font] uso font_lazarus.ttf")
else:
    def _crea_font(dimensione):
        return pygame.font.SysFont("georgia", dimensione, bold=True)
    print("[font] font_lazarus.ttf non trovato: uso georgia")

F_LEG = pygame.font.SysFont("arial", int(H * 0.022))
F_DESCR = pygame.font.SysFont("arial", int(H * 0.028))
F_DESCR_T = pygame.font.SysFont("arial", int(H * 0.028), italic=True)
F_FRECCIA = pygame.font.SysFont("arial", int(H * 0.050), bold=True)

_cache_font = {}


def font_voce(dimensione):
    dimensione = max(10, int(dimensione))
    if dimensione not in _cache_font:
        _cache_font[dimensione] = _crea_font(dimensione)
    return _cache_font[dimensione]


def prepara_sfondo():
    percorso = os.path.join(BASE, cfg["sfondo"])
    if os.path.exists(percorso):
        try:
            img = pygame.image.load(percorso).convert()
            return pygame.transform.smoothscale(img, (W, H))
        except Exception:
            pass
    surf = pygame.Surface((W, H))
    for y in range(H):
        t = y / float(H)
        surf.fill((int(12 + 25 * t), int(14 + 30 * t), int(30 + 45 * t)),
                  (0, y, W, 1))
    return surf


def prepara_mappa():
    """La mappa del viaggio, a tutta pagina.

    Cerca mappa.jpg (o .jpeg, .png, .bmp) nella cartella del progetto.
    Se non la trova, disegna uno sfondo scuro neutro: la schermata
    funziona lo stesso e non si rompe nulla.
    """
    for ext in EST_IMG:
        percorso = os.path.join(BASE, "mappa" + ext)
        if os.path.isfile(percorso):
            try:
                img = pygame.image.load(percorso).convert()
                print("[mappa] uso", os.path.basename(percorso))
                return pygame.transform.smoothscale(img, (W, H))
            except Exception:
                pass
    print("[mappa] immagine non trovata: uso un fondo scuro")
    surf = pygame.Surface((W, H))
    for y in range(H):
        t = y / float(H)
        surf.fill((int(10 + 14 * t), int(13 + 18 * t), int(20 + 26 * t)),
                  (0, y, W, 1))
    return surf


sfondo = prepara_sfondo()
mappa = prepara_mappa()

# su quale schermata siamo: "episodi" oppure "mappa"
schermata = "episodi"
# tappa di cui e' aperta la mappa di dettaglio (None = nessuna)
dettaglio = None
# quante immagini sono state sfogliate per ogni tappa
indice_immagine = {}
_cache_dettaglio = {}

# ---------------------------------------------------------------- musica
MUSICA_PRONTA = False


def avvia_musica():
    if not MUSICA_PRONTA:
        return
    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
    except Exception:
        pass


def ferma_musica():
    if not MUSICA_PRONTA:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def prepara_musica():
    global MUSICA_PRONTA
    percorso = os.path.join(BASE, cfg.get("musica", "musica.mp3"))
    if not os.path.isfile(percorso):
        print("[musica] file non trovato:", percorso)
        return
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(percorso)
        pygame.mixer.music.set_volume(float(cfg.get("volume", 0.30)))
        MUSICA_PRONTA = True
        print("[musica] caricata:", os.path.basename(percorso))
    except Exception as e:
        print("[musica] errore nel caricamento:", e)
        MUSICA_PRONTA = False


prepara_musica()
avvia_musica()

# ---------------------------------------------------------------- layout
# fascia 2: fila di 4 celle, alzata ancora: il bordo basso delle
# celle deve restare sopra le lettere di LAZARUS
MARGINE_FILA = int(W * 0.11)
GAP_X = int(W * 0.020)
CELL_W = (W - 2 * MARGINE_FILA - (PER_PAGINA - 1) * GAP_X) // PER_PAGINA
CELL_H = int(H * 0.17)
CELL_Y = int(H * 0.32)

# la cella MAPPA DEL VIAGGIO: sopra la fila delle puntate, con un po'
# di respiro fra le due
VIAGGIO_W = int(W * 0.30)
VIAGGIO_H = int(H * 0.11)
VIAGGIO_RECT = pygame.Rect((W - VIAGGIO_W) // 2,
                           CELL_Y - VIAGGIO_H - int(H * 0.075),
                           VIAGGIO_W, VIAGGIO_H)

# fascia 3: frecce ai lati della fila
FREC_W = int(W * 0.045)
FREC_H = CELL_H
FREC_SX = pygame.Rect(int(W * 0.035), CELL_Y, FREC_W, FREC_H)
FREC_DX = pygame.Rect(W - int(W * 0.035) - FREC_W, CELL_Y, FREC_W, FREC_H)

# fascia 4: testo della descrizione, dove stava
DESC_X = int(W * 0.08)
DESC_Y = int(H * 0.62)
DESC_W = int(W * 0.84)

# fascia 5: pallini e legenda
PAG_Y = int(H * 0.965)
PAG_R = int(H * 0.008)
PAG_GAP = int(W * 0.022)


def allineamento_pagina():
    """Dove appoggiare la fila delle celle in questa pagina.

    - "destra":  c'e' solo la freccia avanti (prima pagina)
    - "sinistra": c'e' solo la freccia indietro (ultima pagina)
    - "centro":  ci sono entrambe le frecce
    """
    ha_indietro = pagina > 0
    ha_avanti = pagina < n_pagine - 1
    if ha_avanti and not ha_indietro:
        return "destra"
    if ha_indietro and not ha_avanti:
        return "sinistra"
    return "centro"


def x_iniziale_fila():
    """La x da cui parte la fila, secondo l'allineamento della pagina."""
    quante = len(PAGINE[pagina][:PER_PAGINA])
    if quante >= PER_PAGINA:
        return MARGINE_FILA

    larghezza_fila = quante * CELL_W + (quante - 1) * GAP_X
    sinistra = MARGINE_FILA
    destra = W - MARGINE_FILA - larghezza_fila

    allineamento = allineamento_pagina()
    if allineamento == "destra":
        return destra
    if allineamento == "sinistra":
        return sinistra
    return (W - larghezza_fila) // 2


def posizione_cella(indice):
    """Il rettangolo della cella numero `indice` nella fila."""
    return pygame.Rect(x_iniziale_fila() + indice * (CELL_W + GAP_X),
                       CELL_Y, CELL_W, CELL_H)


def font_per_cella(righe):
    """Il font piu' grande con cui tutte le righe entrano nella cella."""
    larghezza_max = int(CELL_W * 0.86)
    altezza_max = int(CELL_H * 0.72)
    dimensione = int(H * 0.030)
    while dimensione > 10:
        f = font_voce(dimensione)
        larga = max(f.size(r)[0] for r in righe)
        alta = f.get_height() * len(righe)
        if larga <= larghezza_max and alta <= altezza_max:
            return f
        dimensione -= 1
    return font_voce(10)


def costruisci_pulsanti():
    """Costruisce celle e frecce della pagina corrente.

    Le puntate di ogni pagina sono fissate nella tabella PAGINE: se la
    pagina ne ha meno di quattro, le celle che avanzano non esistono e
    resta spazio vuoto.
    """
    pulsanti = []

    # la cella d'accesso alla mappa, sopra la fila delle puntate
    pulsanti.append({
        "tipo": "viaggio",
        "rect": VIAGGIO_RECT,
        "label": "IL VIAGGIO",
        "righe": ["IL VIAGGIO"],
        "font": font_voce(int(H * 0.036)),
        "ep": None,
        "descr_titolo": "",
        "descr_testo": "",
        "file_citta": None,
    })

    for i, nome in enumerate(PAGINE[pagina][:PER_PAGINA]):
        label = os.path.splitext(nome)[0]
        righe = dividi_titolo(label)
        # il promo si mostra come "Trailer" invece che col nome del file
        if label in TITOLI_CELLE:
            righe = list(TITOLI_CELLE[label])
        # la chiave di descrizioni.json e' il nome SENZA estensione
        descr = descrizioni.get(label, ["", ""])
        pulsanti.append({
            "tipo": "ep",
            "rect": posizione_cella(i),
            "label": label,
            "righe": righe,
            "font": font_per_cella(righe),
            "ep": nome,
            "descr_titolo": descr[0],
            "descr_testo": descr[1],
            "file_citta": trova_immagine(nome),
        })

    if pagina > 0:
        pulsanti.append({"tipo": "pagina", "rect": FREC_SX, "verso": -1})
    if pagina < n_pagine - 1:
        pulsanti.append({"tipo": "pagina", "rect": FREC_DX, "verso": 1})

    return pulsanti


# ---------------------------------------------------------------- stato
pagina = 0
selezionato = 0
n_pagine = N_PAGINE

pulsanti = costruisci_pulsanti()

_mini_cache = {}


def miniatura(percorso, larghezza, altezza):
    if percorso is None:
        return None
    chiave = (percorso, larghezza, altezza)
    if chiave in _mini_cache:
        return _mini_cache[chiave]
    try:
        img = pygame.image.load(percorso).convert()
    except Exception:
        _mini_cache[chiave] = None
        return None
    lw, lh = img.get_size()
    scala = max(larghezza / float(lw), altezza / float(lh))
    nuova = pygame.transform.smoothscale(
        img, (max(1, int(lw * scala)), max(1, int(lh * scala))))
    ritaglio = pygame.Surface((larghezza, altezza))
    ritaglio.blit(nuova, ((larghezza - nuova.get_width()) // 2,
                          (altezza - nuova.get_height()) // 2))
    _mini_cache[chiave] = ritaglio
    return ritaglio


def spezza_testo(testo, font, larghezza_max):
    """Manda a capo il testo sulle parole che entrano in larghezza."""
    parole = testo.split()
    righe = []
    corrente = ""
    for parola in parole:
        prova = (corrente + " " + parola).strip()
        if font.size(prova)[0] <= larghezza_max or not corrente:
            corrente = prova
        else:
            righe.append(corrente)
            corrente = parola
    if corrente:
        righe.append(corrente)
    return righe


def disegna_testo_centrato(righe, font, colore, centro_x, centro_y):
    passo = font.get_height() + int(font.get_height() * 0.12)
    y0 = centro_y - (passo * len(righe)) // 2
    for k, riga in enumerate(righe):
        ombra = font.render(riga, True, NERO)
        testo = font.render(riga, True, colore)
        tx = centro_x - testo.get_width() // 2
        ty = y0 + k * passo
        screen.blit(ombra, (tx + 2, ty + 3))
        screen.blit(testo, (tx, ty))


# ---------------------------------------- la cella MAPPA DEL VIAGGIO
# Non ha descrizione: cliccandola si apre la mappa a tutta pagina.
DESCR_VIAGGIO = (
    "Alessandro Cattelan e Francesco Mandelli partono per un viaggio negli "
    "USA seguendo un insolito itinerario: quello attraverso i luoghi in cui "
    "grandi artisti sono venuti a mancare per diventare immortali."
    "\n\n"
    "Curiosita', indagini, riflessioni racchiuse in un programma on the road "
    "che offre molti spunti di lettura, che lascia spazio a momenti di "
    "sincera introspezione e al racconto piu' preciso e documentaristico dei "
    "fatti, senza perdere la liberta' di muoversi tra i tanti argomenti "
    "diversi generati dai luoghi e dalle situazioni."
)


def disegna_descrizione(p):
    """Descrizione della voce selezionata, direttamente sullo sfondo.

    Vale per le puntate. La cella MAPPA DEL VIAGGIO non ha
    descrizione: viene saltata.
    """
    if p is None:
        return

    if p["tipo"] == "viaggio":
        return                            # la cella mappa non ha descrizione

    elif p["tipo"] == "ep":
        intest = p["label"].replace(" - ", ": ")
        testo = p["descr_testo"]
    else:
        return

    righe = []
    for parte in testo.split("\n\n"):
        parte = parte.strip()
        if not parte:
            continue
        if righe:
            righe.append("")
        righe.extend(spezza_testo(parte, F_DESCR, DESC_W))
    if not righe:
        righe = ["(nessuna descrizione)"]

    passo = F_DESCR.get_height() + int(H * 0.007)
    altezza_blocco = int(H * 0.045) + passo * len(righe)

    velo = pygame.Surface((W, altezza_blocco + int(H * 0.03)),
                          pygame.SRCALPHA)
    hv = velo.get_height()
    for y in range(hv):
        t = y / float(hv)
        alpha = int(170 * (1 - abs(t - 0.5) * 2) ** 0.6)
        velo.fill((0, 0, 0, alpha), (0, y, W, 1))
    screen.blit(velo, (0, DESC_Y - int(H * 0.02)))

    y = DESC_Y
    if intest:
        f_int = font_voce(int(H * 0.030))
        t = f_int.render(intest, True, ORO)
        ombra = f_int.render(intest, True, NERO)
        screen.blit(ombra, (DESC_X + 2, DESC_Y + 2))
        screen.blit(t, (DESC_X, DESC_Y))
        y = DESC_Y + t.get_height() + int(H * 0.012)

    ha_testo = (p["tipo"] == "viaggio") or bool(p["descr_testo"])
    colore = PIETRA if ha_testo else (140, 155, 170)
    for riga in righe:
        if not riga:
            y += int(H * 0.012)
            continue
        ombra = F_DESCR.render(riga, True, NERO)
        testo_render = F_DESCR.render(riga, True, colore)
        screen.blit(ombra, (DESC_X + 2, y + 2))
        screen.blit(testo_render, (DESC_X, y))
        y += passo


def indice_sotto_mouse():
    """L'indice della voce sotto il puntatore, o None."""
    mouse = pygame.mouse.get_pos()
    for i, p in enumerate(pulsanti):
        if p["rect"].collidepoint(mouse):
            return i
    return None


def posizione_tappa(i):
    """Il rettangolo sensibile intorno al punto della tappa i."""
    t = TAPPE[i]
    cx, cy = int(W * t["x"]), int(H * t["y"])
    raggio = int(H * 0.026)
    return pygame.Rect(cx - raggio, cy - raggio, raggio * 2, raggio * 2)


def tappa_sotto_mouse():
    """L'indice della tappa sotto il puntatore, o None."""
    mouse = pygame.mouse.get_pos()
    for i in range(N_TAPPE):
        if posizione_tappa(i).collidepoint(mouse):
            return i
    return None


def disegna_pannello_tappa(i):
    """Nome della tappa e puntate ambientate li', in un pannello."""
    t = TAPPE[i]
    righe = [t["nome"]] + [p.replace(" - ", ": ") for p in t["puntate"]]

    f_nome = font_voce(int(H * 0.034))
    f_voce = F_LEG

    # larghezza del pannello: quella della riga piu' lunga
    larga = max(f_nome.size(t["nome"])[0],
                *(f_voce.size(r)[0] for r in righe[1:]))
    larga += int(W * 0.06)
    passo = f_voce.get_height() + int(H * 0.010)
    alta = int(H * 0.03) + f_nome.get_height() + int(H * 0.012) \
        + passo * len(righe[1:])

    # il pannello compare vicino al punto, spostato per non uscire
    # dallo schermo e per non coprire il punto stesso
    cx = int(W * t["x"])
    cy = int(H * t["y"])
    distanza = int(H * 0.045)

    # di preferenza a destra; se non c'e' spazio, a sinistra
    x = cx + distanza
    y = cy - alta // 2
    if x + larga > W - int(W * 0.02):
        x = cx - distanza - larga
    if y < int(H * 0.02):
        y = int(H * 0.02)
    if y + alta > H - int(H * 0.06):
        y = H - int(H * 0.06) - alta

    # una linea sottile collega il pannello al suo punto
    ancora_x = x if x > cx else x + larga
    pygame.draw.line(screen, (120, 150, 175),
                     (ancora_x, y + alta // 2), (cx, cy), 1)

    r = pygame.Rect(x, y, larga, alta)

    box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    box.fill((10, 14, 20, 200))
    screen.blit(box, (r.x, r.y))
    pygame.draw.rect(screen, (120, 140, 165), r, 2, border_radius=8)

    # il nome della tappa, in oro
    tx = r.x + int(W * 0.02)
    ty = r.y + int(H * 0.015)
    t_nome = f_nome.render(t["nome"], True, ORO)
    screen.blit(t_nome, (tx, ty))
    ty += t_nome.get_height() + int(H * 0.012)

    # le puntate ambientate li'
    for riga in righe[1:]:
        ombra = f_voce.render(riga, True, NERO)
        testo = f_voce.render(riga, True, PIETRA)
        screen.blit(ombra, (tx + 2, ty + 2))
        screen.blit(testo, (tx, ty))
        ty += passo


def coordinata_sotto_puntatore():
    """La posizione del puntatore in percentuale, sulla mappa."""
    mx, my = pygame.mouse.get_pos()
    return (round(mx / float(W), 3), round(my / float(H), 3))


def disegna_mirino():
    """Mirino sotto il puntatore con la coordinata in tempo reale."""
    mx, my = pygame.mouse.get_pos()
    cx, cy = coordinata_sotto_puntatore()

    col = (255, 210, 120)
    pygame.draw.line(screen, col, (mx - 14, my), (mx - 4, my), 2)
    pygame.draw.line(screen, col, (mx + 4, my), (mx + 14, my), 2)
    pygame.draw.line(screen, col, (mx, my - 14), (mx, my - 4), 2)
    pygame.draw.line(screen, col, (mx, my + 4), (mx, my + 14), 2)
    pygame.draw.circle(screen, col, (mx, my), 7, 1)

    f = pygame.font.SysFont("arial", int(H * 0.026), bold=True)
    testo = "x %.3f    y %.3f" % (cx, cy)
    t = f.render(testo, True, (255, 235, 180))
    o = f.render(testo, True, (0, 0, 0))

    larg = t.get_width() + int(W * 0.03)
    alt = t.get_height() + int(H * 0.018)
    rx = mx + 22
    ry = my - alt - 10
    if rx + larg > W:
        rx = mx - larg - 22
    if ry < 0:
        ry = my + 22

    box = pygame.Surface((larg, alt), pygame.SRCALPHA)
    box.fill((12, 16, 22, 215))
    screen.blit(box, (rx, ry))
    pygame.draw.rect(screen, (150, 175, 200), (rx, ry, larg, alt), 2,
                     border_radius=6)
    screen.blit(o, (rx + int(W * 0.015) + 2, ry + int(H * 0.009) + 2))
    screen.blit(t, (rx + int(W * 0.015), ry + int(H * 0.009)))


def disegna_griglia():
    """Griglia di riferimento: linee ogni 10%, numeri e crocette."""
    f_num = pygame.font.SysFont("arial", int(H * 0.016), bold=True)

    for k in range(1, 10):
        x = int(W * k / 10.0)
        y = int(H * k / 10.0)
        pygame.draw.line(screen, (95, 115, 140), (x, 0), (x, H), 1)
        pygame.draw.line(screen, (95, 115, 140), (0, y), (W, y), 1)

        etichetta = "%.1f" % (k / 10.0)
        t = f_num.render(etichetta, True, (160, 200, 230))
        o = f_num.render(etichetta, True, (0, 0, 0))
        screen.blit(o, (x + 4, 5 + 1)); screen.blit(t, (x + 4, 5))
        screen.blit(o, (x + 4, H - t.get_height() - 5 + 1))
        screen.blit(t, (x + 4, H - t.get_height() - 5))
        screen.blit(o, (5 + 1, y + 4)); screen.blit(t, (5, y + 4))
        screen.blit(o, (W - t.get_width() - 5 + 1, y + 4))
        screen.blit(t, (W - t.get_width() - 5, y + 4))

    f_pun = pygame.font.SysFont("arial", int(H * 0.018), bold=True)
    for j in range(N_TAPPE):
        t = TAPPE[j]
        cx, cy = int(W * t["x"]), int(H * t["y"])
        bx, by = int(W * 0.013), int(H * 0.024)
        pygame.draw.line(screen, (240, 110, 110), (cx - bx, cy), (cx + bx, cy), 2)
        pygame.draw.line(screen, (240, 110, 110), (cx, cy - by), (cx, cy + by), 2)

        testo = "%s  %.3f, %.3f" % (t["nome"], t["x"], t["y"])
        tt = f_pun.render(testo, True, (255, 205, 120))
        oo = f_pun.render(testo, True, (0, 0, 0))
        tx = cx + bx + int(W * 0.006)
        ty = cy - tt.get_height() // 2
        screen.blit(oo, (tx + 2, ty + 2))
        screen.blit(tt, (tx, ty))

    f_i = pygame.font.SysFont("arial", int(H * 0.019), bold=True)
    avviso = "GRIGLIA ATTIVA: leggi le coordinate e comunicamele"
    at = f_i.render(avviso, True, (255, 230, 150))
    ao = f_i.render(avviso, True, (0, 0, 0))
    ax = (W - at.get_width()) // 2
    screen.blit(ao, (ax + 2, int(H * 0.008) + 2))
    screen.blit(at, (ax, int(H * 0.008)))


def disegna_nomi_tappe():
    """I nomi delle tappe, sempre visibili accanto al loro punto.

    Solo per le citta': le tappe "On The Road" e "Death Valley" non
    hanno un nome fisso, resta il punto e il pannello al passaggio.
    """
    f = pygame.font.SysFont("arial", int(H * 0.019), bold=True)
    mouse = pygame.mouse.get_pos()

    for i in range(N_TAPPE):
        t = TAPPE[i]
        if not t.get("etichetta", True):
            continue

        cx, cy = int(W * t["x"]), int(H * t["y"])
        attiva = posizione_tappa(i).collidepoint(mouse)

        colore = (235, 245, 252) if attiva else (150, 168, 185)
        testo = f.render(t["nome"], True, colore)
        ombra = f.render(t["nome"], True, (0, 0, 0))

        # il nome sta a destra del punto; se sborda, a sinistra
        offset = int(H * 0.022)
        x = cx + offset
        if x + testo.get_width() > W - int(W * 0.02):
            x = cx - offset - testo.get_width()
        y = cy - testo.get_height() // 2

        screen.blit(ombra, (x + 2, y + 2))
        screen.blit(testo, (x, y))


def disegna_punto(cx, cy, attiva, alone=True):
    """Un segnaposto sulla mappa, nello stesso stile per tutte le tappe.

    Sempre visibile: cerchio chiaro con bordo azzurro-ghiaccio.
    Quando e' attivo si allarga e prende un alone luminoso.
    """
    r_base = int(H * 0.011)          # raggio del punto a riposo
    r_att = int(H * 0.015)           # raggio quando e' attivo

    if attiva and alone:
        raggio_alone = int(H * 0.040)
        halo = pygame.Surface((raggio_alone * 2, raggio_alone * 2),
                              pygame.SRCALPHA)
        # alone morbido: piu' chiaro al centro, sfuma verso il bordo
        for k in range(raggio_alone, 0, -1):
            t = k / float(raggio_alone)
            alpha = int(90 * (1 - t) ** 1.5)
            pygame.draw.circle(halo, (150, 190, 220, alpha),
                               (raggio_alone, raggio_alone), k)
        screen.blit(halo, (cx - raggio_alone, cy - raggio_alone))

    r = r_att if attiva else r_base

    # ombra sotto, per staccare il punto dall'immagine
    pygame.draw.circle(screen, (0, 0, 0), (cx + 1, cy + 2), r + 1)

    if attiva:
        pygame.draw.circle(screen, PIETRA, (cx, cy), r)
        pygame.draw.circle(screen, GELO, (cx, cy), r, 3)
    else:
        pygame.draw.circle(screen, (215, 228, 238), (cx, cy), r)
        pygame.draw.circle(screen, (120, 150, 175), (cx, cy), r, 2)


def trova_immagine_luogo(nome_luogo):
    """Cerca luoghi/<nome>.<ext> per la miniatura della tappa."""
    if not nome_luogo or not os.path.isdir(LUOGHI_DIR):
        return None
    for ext in EST_IMG:
        percorso = os.path.join(LUOGHI_DIR, nome_luogo + ext)
        if os.path.isfile(percorso):
            return percorso
    return None


def disegna_riquadro_luogo(i):
    """Il riquadro con la miniatura della tappa, in alto al centro.

    Compare solo quando una tappa e' sotto il puntatore: senza
    selezione lo spazio resta completamente vuoto.
    """
    if i is None:
        return

    t = TAPPE[i]
    percorso = trova_immagine_luogo(t.get("luogo"))
    if percorso is None:
        return

    larghezza = int(W * 0.216)
    altezza = int(H * 0.264)
    r = pygame.Rect((W - larghezza) // 2, int(H * 0.045),
                    larghezza, altezza)

    # fondo e cornice, come le celle delle puntate
    box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    box.fill((16, 24, 34, 175))
    screen.blit(box, (r.x, r.y))

    # l'immagine riempie il riquadro, ritagliando l'eccesso
    try:
        img = pygame.image.load(percorso).convert()
    except Exception as e:
        print("[luogo] immagine non caricata:", percorso, e)
        pygame.draw.rect(screen, GELO, r, 3, border_radius=6)
        return

    lw, lh = img.get_size()
    scala = max(r.w / float(lw), r.h / float(lh))
    nuova = pygame.transform.smoothscale(
        img, (max(1, int(round(lw * scala))),
              max(1, int(round(lh * scala)))))

    # ritaglio della parte centrale, della misura esatta del riquadro
    sx = max(0, (nuova.get_width() - r.w) // 2)
    sy = max(0, (nuova.get_height() - r.h) // 2)
    try:
        ritaglio = nuova.subsurface((sx, sy, r.w, r.h)).copy()
    except Exception:
        ritaglio = pygame.Surface((r.w, r.h))
        ritaglio.blit(nuova, ((r.w - nuova.get_width()) // 2,
                              (r.h - nuova.get_height()) // 2))
    screen.blit(ritaglio, (r.x, r.y))

    # la cornice si disegna sopra l'immagine, cosi' resta visibile
    pygame.draw.rect(screen, GELO, r, 3, border_radius=6)


def nome_file_tappa(t):
    """SEATTLE -> seattle, SAN FRANCISCO -> san_francisco."""
    return t.get("file", t["nome"].lower().replace(" ", "_"))


def elenco_immagini(i):
    """Tutte le immagini della tappa i, in ordine alfabetico.

    Si raccolgono tutte le estensioni: seattle.png, seattle_1.jpg,
    seattle_2.png... Cosi' una tappa puo' mostrare piu' mappe.
    """
    elenco = []
    if not os.path.isdir(MAPPE_DIR):
        return elenco
    testa = nome_file_tappa(TAPPE[i])
    for nome in sorted(os.listdir(MAPPE_DIR)):
        radice, ext = os.path.splitext(nome)
        if ext.lower() not in EST_IMG:
            continue
        if radice == testa or radice.startswith(testa + "_"):
            elenco.append(os.path.join(MAPPE_DIR, nome))
    return elenco


def quante_immagini(i):
    """Quante immagini ha la tappa i."""
    return len(elenco_immagini(i))


def indice_corrente(i):
    """Quale immagine sta mostrando la tappa i (0 se non c'e' scelta)."""
    n = quante_immagini(i)
    if n == 0:
        return 0
    return indice_immagine.get(i, 0) % n


def cambia_immagine(i, delta):
    """Passa all'immagine successiva o precedente della tappa i."""
    n = quante_immagini(i)
    if n <= 1:
        return
    indice_immagine[i] = (indice_corrente(i) + delta) % n


def immagine_dettaglio(i, larghezza, altezza):
    """Carica l'immagine corrente della tappa i, adattata al pannello."""
    indice = indice_corrente(i)
    chiave = (i, indice, larghezza, altezza)
    if chiave in _cache_dettaglio:
        return _cache_dettaglio[chiave]

    elenco = elenco_immagini(i)
    img = None
    if elenco:
        try:
            orig = pygame.image.load(elenco[indice]).convert()
            lw, lh = orig.get_size()
            scala = min(larghezza / float(lw), altezza / float(lh))
            img = pygame.transform.smoothscale(
                orig, (int(lw * scala), int(lh * scala)))
        except Exception as e:
            print("[dettaglio] immagine non caricata:", elenco[indice], e)
    _cache_dettaglio[chiave] = img
    return img


def frecce_dettaglio(r):
    """Le due zone cliccabili per sfogliare le immagini."""
    larga = int(W * 0.09)
    alta = int(r.h * 0.34)
    y = r.y + (r.h - alta) // 2
    sinistra = pygame.Rect(r.x + int(W * 0.008), y, larga, alta)
    destra = pygame.Rect(r.right - larga - int(W * 0.008), y, larga, alta)
    return sinistra, destra


def disegna_freccia(rect, verso, accesa):
    """Un triangolo chiaro, con la punta a sinistra o a destra."""
    col = (237, 232, 222) if accesa else (110, 122, 136)
    cx, cy = rect.centerx, rect.centery
    m = int(rect.w * 0.26)
    h = int(rect.h * 0.34)
    if verso < 0:
        punti = [(cx + m // 2, cy - h), (cx + m // 2, cy + h), (cx - m, cy)]
    else:
        punti = [(cx - m // 2, cy - h), (cx - m // 2, cy + h), (cx + m, cy)]
    pygame.draw.polygon(screen, col, punti)


def rect_dettaglio():
    """Il pannello occupa gran parte dello schermo, non tutto."""
    larga, alta = int(W * 0.84), int(H * 0.84)
    return pygame.Rect((W - larga) // 2, int(H * 0.05), larga, alta)


def disegna_dettaglio(i):
    """Mappa di dettaglio della tappa i, sopra la mappa principale."""
    velo = pygame.Surface((W, H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))

    r = rect_dettaglio()
    box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    box.fill((8, 12, 18, 235))
    screen.blit(box, r.topleft)

    t = TAPPE[i]
    f_nome = font_voce(int(H * 0.040))
    margine = int(H * 0.02)
    testa = f_nome.get_height() + margine * 2
    piede = F_LEG.get_height() + margine * 2

    screen.blit(f_nome.render(t["nome"], True, ORO),
                (r.x + margine * 2, r.y + margine))

    area = pygame.Rect(r.x + margine, r.y + testa,
                       r.w - margine * 2, r.h - testa - piede)
    img = immagine_dettaglio(i, area.w, area.h)
    if img is not None:
        screen.blit(img, (area.centerx - img.get_width() // 2,
                          area.centery - img.get_height() // 2))
    else:
        msg = ("Nessuna immagine in mappe/ per %s" % nome_file_tappa(t))
        tm = F_LEG.render(msg, True, (150, 160, 170))
        screen.blit(tm, (area.centerx - tm.get_width() // 2,
                         area.centery - tm.get_height() // 2))

    # frecce e contatore, solo se la tappa ha piu' di un'immagine
    n = quante_immagini(i)
    if n > 1:
        sinistra, destra = frecce_dettaglio(r)
        mouse = pygame.mouse.get_pos()
        disegna_freccia(sinistra, -1, sinistra.collidepoint(mouse))
        disegna_freccia(destra, 1, destra.collidepoint(mouse))
        conta = F_LEG.render("%d / %d" % (indice_corrente(i) + 1, n),
                             True, GELO)
        screen.blit(conta, (r.centerx - conta.get_width() // 2,
                            area.bottom + margine // 2))

    riga = "   .   ".join(p.replace(" - ", ": ") for p in t["puntate"])
    tp = F_LEG.render(riga, True, PIETRA)
    screen.blit(tp, (r.centerx - tp.get_width() // 2,
                     r.bottom - piede + margine))

    pygame.draw.rect(screen, (120, 140, 165), r, 2, border_radius=10)


def disegna_mappa():
    """La mappa a tutta pagina, con i punti di tutte le tappe."""
    screen.blit(mappa, (0, 0))

    # i nove punti, sempre visibili: quello sotto il puntatore si accende
    mouse = pygame.mouse.get_pos()
    for i in range(N_TAPPE):
        t = TAPPE[i]
        cx, cy = int(W * t["x"]), int(H * t["y"])
        attiva = posizione_tappa(i).collidepoint(mouse)
        disegna_punto(cx, cy, attiva)

    # i nomi delle citta', sempre visibili
    disegna_nomi_tappe()

    if MOSTRA_GRIGLIA:
        disegna_griglia()
        disegna_mirino()

    # velo tenue in basso: la legenda resta leggibile
    velo = pygame.Surface((W, int(H * 0.10)), pygame.SRCALPHA)
    hv = velo.get_height()
    for y in range(hv):
        t = y / float(hv)
        alpha = int(180 * (t ** 1.2))
        velo.fill((0, 0, 0, alpha), (0, y, W, 1))
    screen.blit(velo, (0, H - int(H * 0.10)))

    # il pannello con nome e puntate, quando il puntatore e' su un punto
    if dettaglio is not None:
        disegna_dettaglio(dettaglio)
        if quante_immagini(dettaglio) > 1:
            testo_leg = ("Frecce o click sui lati: cambia mappa   .   "
                         "Esc: torna alla mappa")
        else:
            testo_leg = "Esc o click fuori dal pannello: torna alla mappa"
        leg = F_LEG.render(testo_leg, True, (190, 200, 210))
        screen.blit(leg, ((W - leg.get_width()) // 2, H - int(H * 0.018)))
        pygame.display.flip()
        return

    i = tappa_sotto_mouse()
    if i is not None:
        disegna_riquadro_luogo(i)
        disegna_pannello_tappa(i)

    leg = F_LEG.render("Passa sui punti   .   Click: mappa della zona   .   Esc: torna alle puntate",
                       True, (190, 200, 210))
    screen.blit(leg, ((W - leg.get_width()) // 2, H - int(H * 0.018)))
    pygame.display.flip()


def disegna():
    global selezionato

    if schermata == "mappa":
        disegna_mappa()
        return

    sopra = indice_sotto_mouse()
    if sopra is not None:
        selezionato = sopra

    screen.blit(sfondo, (0, 0))

    # velo scuro: comincia ancora piu' in basso, cosi' la scritta
    # LAZARUS resta ben visibile
    h_fascia = int(H * 0.67)
    fascia = pygame.Surface((W, h_fascia), pygame.SRCALPHA)
    for y in range(h_fascia):
        t = y / float(h_fascia)
        alpha = int(200 * (t ** 1.4))
        fascia.fill((0, 0, 0, alpha), (0, y, W, 1))
    screen.blit(fascia, (0, H - h_fascia))

    corrente = pulsanti[selezionato] if pulsanti else None

    for i, p in enumerate(pulsanti):
        r = p["rect"]
        attiva = (i == selezionato)

        if p["tipo"] == "viaggio":
            # la cella mostra la miniatura "viaggio" se c'e', con il
            # testo sempre sopra; altrimenti solo fondo e testo
            mostrata = miniatura(trova_immagine_citta("viaggio"),
                                 r.w, r.h)

            if mostrata is not None:
                screen.blit(mostrata, (r.x, r.y))
                # velo scuro: il testo resta leggibile sopra l'immagine
                velo = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                velo.fill((0, 0, 0, 110 if attiva else 150))
                screen.blit(velo, (r.x, r.y))
            else:
                if attiva:
                    riempimento = (120, 160, 185, 90)
                else:
                    riempimento = (16, 24, 34, 175)
                box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                box.fill(riempimento)
                screen.blit(box, (r.x, r.y))

            # il bordo resta sempre dello stesso colore: cambia solo
            # lo spessore, quindi si illumina senza cambiare tinta
            pygame.draw.rect(screen, GELO if attiva else (110, 122, 135),
                             r, 3 if attiva else 2, border_radius=6)

            # il testo si vede sempre, anche con la miniatura
            f = p["font"]
            colore_testo = PIETRA if (attiva or mostrata is not None) else AZZURRO
            disegna_testo_centrato(["IL VIAGGIO"], f, colore_testo,
                                   r.x + r.w // 2, r.y + r.h // 2)
            continue

        if p["tipo"] == "pagina":
            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            box.fill((120, 160, 185, 90) if attiva else (16, 24, 34, 150))
            screen.blit(box, (r.x, r.y))
            pygame.draw.rect(screen, GELO if attiva else (110, 122, 135),
                             r, 2, border_radius=6)
            simbolo = "\u2190" if p["verso"] < 0 else "\u2192"
            t = F_FRECCIA.render(simbolo, True, PIETRA if attiva else AZZURRO)
            screen.blit(t, (r.x + (r.w - t.get_width()) // 2,
                            r.y + (r.h - t.get_height()) // 2))
            continue

        mostrata = None
        if attiva:
            mostrata = miniatura(p["file_citta"], r.w, r.h)

        if mostrata is not None:
            screen.blit(mostrata, (r.x, r.y))
            velo = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            velo.fill((0, 0, 0, 30))
            screen.blit(velo, (r.x, r.y))
        else:
            riempimento = (120, 160, 185, 90) if attiva else (16, 24, 34, 175)
            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            box.fill(riempimento)
            screen.blit(box, (r.x, r.y))

        pygame.draw.rect(screen, GELO if attiva else (110, 122, 135), r,
                         3 if attiva else 2, border_radius=6)

        if mostrata is None:
            f = p.get("font") or font_voce(int(H * 0.030))
            disegna_testo_centrato(p["righe"], f, PIETRA if attiva else AZZURRO,
                                   r.x + r.w // 2, r.y + r.h // 2)

    disegna_descrizione(corrente)

    if n_pagine > 1:
        larghezza_tot = n_pagine * PAG_R * 2 + (n_pagine - 1) * PAG_GAP
        x0 = (W - larghezza_tot) // 2
        for k in range(n_pagine):
            cx = x0 + k * (PAG_R * 2 + PAG_GAP) + PAG_R
            colore = GELO if k == pagina else (90, 100, 112)
            pygame.draw.circle(screen, colore, (cx, PAG_Y), PAG_R,
                               0 if k == pagina else 2)

    leg = F_LEG.render(
        "Invio: riproduci   .   Frecce: naviga   .   Esc: esci",
        True, (150, 162, 175))
    screen.blit(leg, ((W - leg.get_width()) // 2, H - int(H * 0.018)))
    pygame.display.flip()


def cambia_pagina(delta):
    global pagina, selezionato, pulsanti
    if n_pagine <= 1:
        return
    pagina = (pagina + delta) % n_pagine
    selezionato = 0
    pulsanti = costruisci_pulsanti()


def attiva_voce(p):
    if p is None:
        print("[voce] nessun pulsante da attivare")
        return
    print("[voce] attivo:", p.get("tipo"), p.get("label"))
    if p["tipo"] == "viaggio":
        vai_alla_mappa()
    elif p["tipo"] == "pagina":
        cambia_pagina(p["verso"])
    else:
        avvia_riproduzione([p["ep"]])


def vai_alla_mappa():
    """Apre la mappa a tutta pagina."""
    global schermata
    schermata = "mappa"


def vai_agli_episodi():
    """Torna alla griglia delle puntate."""
    global schermata, dettaglio
    schermata = "episodi"
    dettaglio = None


def avvia_riproduzione(lista):
    """Riproduce la coda di puntate."""
    print("[riproduzione] inizio, coda:", lista)
    ferma_musica()
    for nome in lista:
        # i nomi nella tabella PAGINE sono senza estensione: qui si
        # aggiunge quella del file, cercandola nella cartella puntate
        percorso = os.path.join(VIDEO_DIR, nome)
        if not os.path.isfile(percorso):
            trovato = None
            for ext in ESTENSIONI:
                prova = os.path.join(VIDEO_DIR, nome + ext)
                if os.path.isfile(prova):
                    trovato = prova
                    break
            percorso = trovato
        print("[riproduzione] file:", percorso)
        if percorso is None or not os.path.isfile(percorso):
            print("[riproduzione] SALTATO: file non trovato")
            continue
        finito_da_solo = riproduci_attesa(percorso)
        pygame.event.pump()
        pygame.event.clear()
        if not finito_da_solo:
            break
    avvia_musica()
    print("[riproduzione] fine")


# ---------------------------------------------------------------- loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            key = event.key

            if key == pygame.K_ESCAPE:
                if schermata == "mappa" and dettaglio is not None:
                    dettaglio = None
                elif schermata == "mappa":
                    vai_agli_episodi()
                else:
                    running = False

            elif schermata == "mappa":
                if dettaglio is None:
                    pass
                elif key == pygame.K_RIGHT:
                    cambia_immagine(dettaglio, 1)
                elif key == pygame.K_LEFT:
                    cambia_immagine(dettaglio, -1)

            elif key in (pygame.K_PAGEDOWN, pygame.K_DOWN):
                cambia_pagina(1)

            elif key in (pygame.K_PAGEUP, pygame.K_UP):
                cambia_pagina(-1)

            elif key in (pygame.K_RIGHT,):
                selezionato = (selezionato + 1) % len(pulsanti)

            elif key in (pygame.K_LEFT,):
                selezionato = (selezionato - 1) % len(pulsanti)

            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                attiva_voce(pulsanti[selezionato] if pulsanti else None)

        elif event.type == pygame.MOUSEWHEEL:
            if schermata == "mappa" and dettaglio is not None:
                cambia_immagine(dettaglio, -1 if event.y > 0 else 1)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            print("[click] su", event.pos, "schermata:", schermata)
            if schermata == "mappa":
                if dettaglio is not None:
                    r = rect_dettaglio()
                    sinistra, destra = frecce_dettaglio(r)
                    if sinistra.collidepoint(event.pos):
                        cambia_immagine(dettaglio, -1)
                    elif destra.collidepoint(event.pos):
                        cambia_immagine(dettaglio, 1)
                    elif not r.collidepoint(event.pos):
                        dettaglio = None
                else:
                    dettaglio = tappa_sotto_mouse()
                continue
            i = indice_sotto_mouse()
            print("[click] indice trovato:", i)
            if i is not None:
                selezionato = i
                attiva_voce(pulsanti[i])
            else:
                print("[click] nessuna voce sotto il puntatore")

    disegna()
    clock.tick(60)

pygame.quit()
sys.exit()
