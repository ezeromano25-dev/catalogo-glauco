"""Reglas fijas del catálogo: nombres, etiquetas y clasificación de exposición, sequía y frío.

Para corregir una especie a mano, agregá su enlace de la tienda en CORRECCIONES.
"""
import re

# Correcciones manuales (clave: final del enlace de la tienda, sin barras).
# cientifico usa *cursiva* para género y especie; el resto va en redonda.
CORRECCIONES = {
    "nasella-tenuissima-stipa-comun-coiron": {"cientifico": "*Nassella tenuissima*", "comun": "stipa común, coirón"},
    "nasella-tenuissima-stipa-comun-coiron-semillas": {"cientifico": "*Nassella tenuissima*", "comun": "stipa común, coirón"},
    "eryngium-planum-white-gliter-1rkx7": {"cientifico": "*Eryngium planum* 'White Glitter'", "comun": "cardito"},
    "eragrostis-ellioti-lovey-igr1n": {"cientifico": "*Eragrostis elliottii* 'Lovey'", "comun": None},
    "aster-novi-belgii-aster-de-nueva-york": {"cientifico": "*Symphyotrichum novi-belgii*", "comun": "áster de Nueva York"},
    "agastache-foeniculum-flor-de-anis": {"cientifico": "*Agastache foeniculum*", "comun": "flor de anís"},
    "agastache-liquorice-blue-si6gm": {"cientifico": "*Agastache* 'Liquorice Blue'", "comun": None},
    "scabiosa-qis-mix-seleccion-especial-de-escabiosas-gxfns": {"cientifico": "*Scabiosa atropurpurea* 'QIS Mix'", "comun": "escabiosa"},
    "cosmos-bipinnatus-cosmos-anual-flor-rosa-y-blanca-mix-6rzlv": {"cientifico": "*Cosmos bipinnatus* (mix rosa y blanco)", "comun": "cosmos"},
    "salvia-farinacea-victoria-blue-salvia-azul-salvia-farinacea": {"cientifico": "*Salvia farinacea* 'Victoria Blue'", "comun": "salvia azul"},
    "verbena-bonariensis-verbena-bonariensis": {"cientifico": "*Verbena bonariensis*", "comun": "verbena"},
    "paspalum-exaltatum-paspalum-exaltatum-gb1ak": {"cientifico": "*Paspalum exaltatum*", "comun": None},
    "penstemon-tenuis-penstemon-tenuis": {"cientifico": "*Penstemon tenuis*", "comun": None},
    "dietes-bicolor-dietes-bicolor": {"cientifico": "*Dietes bicolor*", "comun": None},
    "calamagrostis-x-acutiflora-karl-foerster": {"cientifico": "*Calamagrostis* × *acutiflora* 'Karl Foerster'", "comun": None},
    "limonium-mini-1pljg": {"cientifico": "*Limonium* (mini)", "comun": "limonium"},
    "alcea-rosea-flor-bordo-20-semillas": {"cientifico": "*Alcea rosea* (flor bordó)", "comun": "malva real"},
    "papaver-rhoeas-mix-de-colores-amapola1": {"cientifico": "*Papaver rhoeas* (mix de colores)", "comun": "amapola"},
    "papaver-rhoeas-40-semillas": {"cientifico": "*Papaver rhoeas*", "comun": "amapola"},
    "verbascum-chaixxi-wedding-candle-40-semillas": {"cientifico": "*Verbascum chaixii* 'Wedding Candles'", "comun": None},
    "scabiosa-chat-noir-black-cat-20-semillas": {"cientifico": "*Scabiosa atropurpurea* 'Chat Noir'", "comun": "escabiosa negra"},
    "rudbeckia-hirta-40-semillas": {"cientifico": "*Rudbeckia hirta*", "comun": "susana de ojos negros"},
    "nierembergia-yvoty-blanca-inta-nierembergia": {"cientifico": "*Nierembergia* 'Yvoty Blanca INTA'", "comun": "nierembergia"},
    "cupressus-sempervirens-stricta-totem-cipres-columnar-compacto":{"cientifico": "*Cupressus sempervirens* 'Stricta'", "comun": "ciprés columnar compacto"},
}

# Productos que no son plantas ni semillas: quedan fuera del catálogo.
EXCLUIR = re.compile(r"fertilizante|kit de siembra|sustrato", re.I)

LATIN_STOP = {"flor", "forma", "mix", "colores", "rosados", "x", "híbrida", "hibrida"}


def _slug(url):
    return url.rstrip("/").split("/")[-1]


def markup_desde_texto(txt):
    """Convierte un nombre escrito normal ("Eryngium planum 'White Glitter'") al formato con cursivas.

    Van en cursiva las palabras latinas del principio (género y epítetos en minúscula),
    hasta la primera comilla o paréntesis. El signo × queda en redonda.
    """
    txt = " ".join(txt.replace("´", "'").replace("’", "'").replace('"', "'").split())
    txt = re.sub(r"\s+x\s+", " × ", txt)
    m = re.search(r"['(]", txt)
    cabeza, resto = (txt[:m.start()].strip(), txt[m.start():]) if m else (txt, "")
    partes = []
    for i, w in enumerate(cabeza.split()):
        if w == "×":
            partes.append(w)
        elif i == 0 or (w[:1].islower() and w not in ("sp.", "spp.", "var.", "subsp.") and w not in LATIN_STOP):
            partes.append(f"*{w}*")
        else:
            partes.append(w)
    out = " ".join(partes).replace("* *", " ")
    return (out + (" " + resto if resto else "")).strip()


def cientifico_a_texto(markup):
    return markup.replace("*", "")


# Correcciones hechas por Ezequiel en la planilla de revisión (se guardan en correcciones.json).
# Formato: {"<slug>": {"cientifico": "texto normal o vacío", "comun": "texto, '-' para ninguno, o vacío"}}
def _cargar_correcciones_json():
    import json, os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "correcciones.json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p, encoding="utf-8"))


CORRECCIONES_EZE = _cargar_correcciones_json()


def nombres(prod):
    """Devuelve (cientifico_markup, comun) a partir del nombre de la tienda."""
    sci, comun = _nombres_base(prod)
    fix = CORRECCIONES_EZE.get(_slug(prod["url"]), {})
    if fix.get("cientifico"):
        sci = markup_desde_texto(fix["cientifico"])
    if fix.get("comun"):
        comun = None if fix["comun"].strip() in ("-", "—") else fix["comun"].strip()
    return sci, comun


def _nombres_base(prod):
    fix = CORRECCIONES.get(_slug(prod["url"]))
    if fix:
        return fix["cientifico"], fix["comun"]
    n = prod["nombre_tienda"]
    n = re.sub(r"\s*-?\s*(\d+\s*)?SEMILLAS\s*$", "", n, flags=re.I).strip(" -")
    n = n.replace("´", "'").replace("’", "'")
    comun = None
    # nombre común entre paréntesis
    m = re.search(r"\(([^)]*)\)", n)
    if m:
        comun = m.group(1).strip()
        n = (n[:m.start()] + n[m.end():]).strip(" -")
    # nombre común entre comillas tras guion: - "Amapola de California"
    m = re.search(r'-\s*"([^"]+)"\s*$', n)
    if m:
        comun = comun or m.group(1)
        n = n[:m.start()].strip(" -")
    # descriptor tras guion: "- flor rosada", "- forma compacta"
    extra = None
    m = re.search(r"\s+-\s*(.+)$", n)
    if m:
        extra = m.group(1).strip(" -")
        n = n[:m.start()].strip()
    n = re.sub(r"-\s*$", "", n).strip()
    # cultivar
    cultivar = None
    m = re.search(r"[\"']([^\"']+)[\"']", n)
    if m:
        cultivar = m.group(1).strip()
        n = (n[:m.start()] + n[m.end():]).strip()
    n = re.sub(r"\s+x\s+", " × ", n)
    # "Scabiosa Chat Noir / Black Cat" -> cultivar sin comillas en la tienda
    words = n.split()
    latin = []
    rest = []
    for i, w in enumerate(words):
        if rest:
            rest.append(w)
            continue
        if i == 0 or w == "×" or (w.islower() and w not in LATIN_STOP and re.fullmatch(r"[a-zë-]+", w)):
            latin.append(w)
        else:
            rest.append(w)
    if rest and not cultivar:
        cultivar = " ".join(rest).replace(" / ", " / ")
    elif rest:
        extra = (" ".join(rest) + (" " + extra if extra else "")).strip()
    parts = []
    for w in latin:
        parts.append(w if w == "×" else f"*{w}*")
    sci = " ".join(parts).replace("* *", " ")
    if cultivar:
        sci += f" '{cultivar}'"
    if extra:
        sci += f" ({extra.lower()})"
    if comun and comun.lower().replace(" ", "") == " ".join(latin).lower().replace(" ", "").replace("×", "x"):
        comun = None
    if comun:
        comun = comun[0].lower() + comun[1:] if not comun[:2].isupper() else comun
    return sci, comun


def exposicion(txt):
    """Devuelve el conjunto de exposiciones toleradas: 'sol', 'media', 'sombra'."""
    t = (txt or "").lower().replace("mediasombra", "media sombra")
    s = set()
    if t.startswith("pleno sol") or t.startswith("sol"):
        s.add("sol")
    if re.search(r"media sombra|sombra ligera|sombra clara", t):
        s.add("media")
    if re.search(r"(?<!media )sombra(?! ligera| clara)", t.replace("media sombra", "")):
        # "sombra" sola (no media sombra), incluida "sombra luminosa"
        s.add("sombra")
    if not s:
        s.add("sol")
    return s


GRUPOS_EXPO = [
    ("Pleno sol", lambda s: s == {"sol"}),
    ("Sol o media sombra", lambda s: s == {"sol", "media"}),
    ("Sol, media sombra o sombra", lambda s: s == {"sol", "media", "sombra"}),
    ("Media sombra o sombra", lambda s: "sol" not in s),
]


def grupo_expo(s):
    for i, (nombre, f) in enumerate(GRUPOS_EXPO):
        if f(s):
            return i, nombre
    return 1, "Sol o media sombra"


def sequia(txt):
    """Resistencia a la sequía: 3 alta, 2 media, 1 baja."""
    t = (txt or "").lower()
    muy = re.search(r"muy resistente|altamente|extremadamente|muy tolerante|tolera muy bien|muy buena tolerancia|herbácea de sequía|prolongados|rmuy", t)
    if re.match(r"(muy baja|extremadamente)", t):
        return 3
    if re.match(r"baja(?! a media)", t):
        return 3
    if re.match(r"(baja a media|media a baja|moderada a baja|normal a baja)", t):
        return 3 if (muy or re.search(r"resistente a (la )?sequía|resistente a los suelos", t)) else 2
    if re.search(r"baja tolerancia|sequías prolongadas pueden afectar", t):
        return 1
    if re.match(r"(media|moderada)", t):
        return 2
    if re.match(r"(regular|requiere riego|riego regular)", t):
        return 1
    return 2


def frio(txt):
    """Devuelve (nivel, texto corto). nivel 3 heladas fuertes, 2 moderadas, 1 suaves, 0 ciclo de verano."""
    t = (txt or "").lower().replace("\xa0", " ")
    if re.search(r"no tolera heladas|no vive en invierno|no vegeta en invierno|primavera-verano", t):
        return 0, "Ciclo de verano"
    m = re.search(r"(\d+)\s*°?\s*c?\s*bajo cero", t)
    temp = -int(m.group(1)) if m else None
    if temp is None:
        m = re.search(r"-\s?(\d+)", t)
        temp = -int(m.group(1)) if m else None
    if temp is not None:
        nivel = 3 if temp <= -10 else 2 if temp <= -6 else 1
        return nivel, f"Hasta {temp} °C".replace("-", "−")
    if re.search(r"resisten|toleran|tolera|problemas con el frío|rústica", t):
        return 3, "Resiste heladas"
    return 2, "Heladas moderadas"


def _num(s):
    s = s.replace(",", ".")
    if re.fullmatch(r"0\d+", s):  # "060" -> 0.60
        s = "0." + s[1:]
    return float(s)


_RANGO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:m(?:etros?)?)?(?:\s*(?:–|-|a)\s*(\d+(?:[.,]\d+)?))?")


def _rango(txt):
    m = _RANGO.search(txt or "")
    if not m:
        return None
    a = _num(m.group(1))
    b = _num(m.group(2)) if m.group(2) else None
    return (a, b)


def _rangos(txt):
    return [(_num(m.group(1)), _num(m.group(2)) if m.group(2) else None) for m in _RANGO.finditer(txt or "")]


def _fmt_rango(r):
    a, b = r
    mx = b if b is not None else a
    if mx < 1:
        f = lambda v: f"{round(v * 100):d}"
        return (f"{f(a)}–{f(b)}" if b is not None and b != a else f(a)) + " cm"
    f = lambda v: (f"{v:.2f}".rstrip("0").rstrip(".")).replace(".", ",")
    return (f"{f(a)}–{f(b)}" if b is not None and b != a else f(a)) + " m"


def dimensiones(txt):
    """Devuelve (alto, ancho) como textos cortos, o None si la ficha no trae medidas.

    Alto: si la ficha da alto de follaje y alto en floración, se usa el de floración.
    Ancho: rango, o "expansiva" si la ficha dice indefinido o expansiva.
    """
    if not txt:
        return None
    t = " ".join(txt.split())
    t = re.sub(r"(\d)\s+\.(\d)", r"\1.\2", t)  # "0 .3" -> "0.3"
    t = re.split(r"\.\s+[A-ZÁÉÍÓÚ]", t)[0]  # corta notas como "Las dimensiones pueden variar..."
    low = t.lower()
    i_ancho = low.find("ancho")
    if i_ancho < 0:
        return None
    seps = [m.start() for m in re.finditer(r"\s(?:x|y|,\s*con)\s", low[:i_ancho])]
    corte = seps[-1] if seps else i_ancho
    parte_alto, parte_ancho = t[:corte], t[corte:]
    r_alto = _rangos(parte_alto)
    if not r_alto:
        return None
    alto = _fmt_rango(r_alto[-1])
    if re.search(r"alto y ancho\s*\.?$", low):
        return alto, alto
    if re.search(r"indefinido|expansiva", parte_ancho.lower()):
        ancho = "expansiva"
    else:
        r = _rango(parte_ancho)
        if not r:
            return alto, None
        ancho = _fmt_rango(r)
        if re.search(r"hasta", parte_ancho.lower()) and r[1] is None:
            ancho = "hasta " + ancho
        if "o más" in parte_ancho.lower():
            ancho += " o más"
    return alto, ancho
