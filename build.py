#!/usr/bin/env python3
"""Arma el catálogo de stock de Vivero Glauco en PDF a partir de stock.json.

Uso: python3 build.py [stock.json] [salida.pdf]
"""
import json, os, re, sys, hashlib, html, datetime
import concurrent.futures as cf
import requests
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter, PdfReader
import fichas as F

HERE = os.path.dirname(os.path.abspath(__file__))
FOTOS = os.path.join(HERE, "fotos")
os.makedirs(FOTOS, exist_ok=True)

# Textos editables (Ezequiel los corrige en la pestaña "Tapa" de la planilla de revisión).
# Los valores de abajo son los originales; textos.json, si existe, los reemplaza.
TEXTOS = {
    "tapa_aviso": "Este catálogo se arma todos los miércoles con las plantas y semillas disponibles ese día. Como las ventas siguen durante la semana, alguna especie puede agotarse antes de tu pedido. Confirmá la disponibilidad en la tienda o por WhatsApp.",
    "comprar_1_titulo": "Envíos a toda la Argentina en cajas de 24 plantas",
    "comprar_1_texto": "Todas en maceta M12. Pueden ser de una misma especie o surtidas, como quieras.",
    "comprar_2_titulo": "¿Querés más plantas?",
    "comprar_2_texto": "Elegí otras 24 para armar una segunda caja, y así sucesivamente.",
    "comprar_3_titulo": "Las semillas no suman a la caja",
    "comprar_3_texto": "Comprá todas las que quieras: viajan aparte.",
    "comprar_4_titulo": "Gran Mendoza: sin límite de compra",
    "comprar_4_texto": "Comprás lo que quieras y después coordinamos la entrega o el retiro.",
    "leer_luz": "Luz: pleno sol, media sombra y sombra. Los íconos marcados son los lugares donde crece bien.",
    "leer_sequia": "Cuánto aguanta sin riego una vez establecida: alta, media o baja.",
    "leer_frio": "La temperatura mínima que resiste. \"Ciclo de verano\": anual que no pasa el invierno.",
    "leer_tamano": "Alto y ancho aproximados de la planta adulta, con flor. Varían según el cultivo.",
    "seccion_perennes": "Viven varios años en el jardín. Se envían en maceta M12.",
    "seccion_anuales": "Completan su ciclo en una temporada o en pocos años. Se envían en maceta M12.",
    "seccion_arbustos": "Estructura y floración larga para los canteros. Se envían en maceta M12.",
    "seccion_gramineas": "Movimiento, textura e interés en invierno. Se envían en maceta M12.",
    "seccion_semillas": "Sobres con semillas para sembrar en almácigo o directo en el cantero. Viajan aparte, en la cantidad que quieras.",
}
_tj = os.path.join(HERE, "textos.json")
if os.path.exists(_tj):
    TEXTOS.update({k: v for k, v in json.load(open(_tj, encoding="utf-8")).items() if v and k in TEXTOS})

SECCIONES = [
    ("perennes", "Herbáceas perennes", TEXTOS["seccion_perennes"]),
    ("anuales", "Herbáceas anuales y de vida corta", TEXTOS["seccion_anuales"]),
    ("arbustos", "Arbustos y salvias", TEXTOS["seccion_arbustos"]),
    ("gramineas", "Gramíneas y cárex", TEXTOS["seccion_gramineas"]),
    ("semillas", "Semillas", TEXTOS["seccion_semillas"]),
]

WHATSAPP = "5492616675555"
WA_URL = "https://wa.me/" + WHATSAPP + "?text=" + "Hola%2C%20quiero%20hacer%20un%20pedido"
MM = 72 / 25.4
BTN_W, BTN_H = 64, 10          # mm
BTN_RIGHT, BTN_BOTTOM = 12, 12  # mm desde el borde derecho e inferior

BTN_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:M;src:url(file://%(f)s/Montserrat.woff2);font-weight:100 900}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(w)smm;height:%(h)smm;-webkit-print-color-adjust:exact}
.b{width:100%%;height:100%%;background:#CDA34F;color:#373F27;font-family:M;font-weight:600;font-size:9.5pt;
display:flex;align-items:center;justify-content:center;gap:2.2mm;letter-spacing:.01em}
svg{width:4.6mm;height:4.6mm}
</style></head><body><div class="b"><svg viewBox="0 0 24 24"><path d="M4 4h16v12H9l-5 4z" fill="none" stroke="#373F27" stroke-width="2.2" stroke-linejoin="miter"/></svg>Iniciar pedido por WhatsApp</div></body></html>"""

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def esc(s):
    return html.escape(s or "", quote=True)


def markup_cientifico(s):
    out = esc(s)
    return re.sub(r"\*([^*]+)\*", r"<i>\1</i>", out)


def bajar_foto(url):
    if not url:
        return None
    h = hashlib.md5(url.encode()).hexdigest()[:16]
    path = os.path.join(FOTOS, h + os.path.splitext(url.split("?")[0])[1])
    jpg = os.path.join(FOTOS, h + "-169.jpg")
    if not os.path.exists(jpg):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        from PIL import Image, ImageOps
        import io
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(r.content))).convert("RGB")
        im = ImageOps.fit(im, (640, 360), Image.LANCZOS)  # recorte rectangular 16:9
        im.save(jpg, "JPEG", quality=80, optimize=True)
    return jpg


# ---------- iconos (SVG en línea, color oscuro) ----------
def ico_sol(on=True):
    o = "1" if on else ".22"
    rays = "".join(
        f'<line x1="{12+7.5*c:.1f}" y1="{12+7.5*s:.1f}" x2="{12+10*c:.1f}" y2="{12+10*s:.1f}"/>'
        for c, s in [(1, 0), (-1, 0), (0, 1), (0, -1), (.707, .707), (-.707, .707), (.707, -.707), (-.707, -.707)])
    return (f'<svg viewBox="0 0 24 24" class="ic" style="opacity:{o}"><g stroke="#373F27" stroke-width="2" '
            f'stroke-linecap="square" fill="none"><circle cx="12" cy="12" r="4.5" fill="#373F27"/>{rays}</g></svg>')


def ico_media(on=True):
    o = "1" if on else ".22"
    return (f'<svg viewBox="0 0 24 24" class="ic" style="opacity:{o}"><circle cx="12" cy="12" r="8" fill="none" '
            f'stroke="#373F27" stroke-width="2"/><path d="M12 4a8 8 0 0 1 0 16z" fill="#373F27"/></svg>')


def ico_sombra(on=True):
    o = "1" if on else ".22"
    return (f'<svg viewBox="0 0 24 24" class="ic" style="opacity:{o}"><circle cx="12" cy="12" r="8" '
            f'fill="#373F27"/></svg>')


def ico_gota():
    return ('<svg viewBox="0 0 24 24" class="ic"><path d="M12 3c3.5 5 6 8.2 6 11.2A6 6 0 0 1 6 14.2C6 11.2 8.5 8 12 3z" '
            'fill="none" stroke="#373F27" stroke-width="2"/></svg>')


def ico_copo():
    lines = "".join(
        f'<line x1="{12-9*c:.1f}" y1="{12-9*s:.1f}" x2="{12+9*c:.1f}" y2="{12+9*s:.1f}"/>'
        for c, s in [(1, 0), (.5, .866), (-.5, .866)])
    return f'<svg viewBox="0 0 24 24" class="ic"><g stroke="#373F27" stroke-width="2" fill="none">{lines}</g></svg>'


def ico_regla():
    return ('<svg viewBox="0 0 24 24" class="ic"><g fill="none" stroke="#373F27" stroke-width="2">'
            '<path d="M2 8h20v8H2z"/><path d="M6 8v4M10 8v3M14 8v4M18 8v3"/></g></svg>')


def medidor(n, total=3):
    return '<span class="med">' + "".join(
        f'<span class="{"on" if i < n else ""}"></span>' for i in range(total)) + "</span>"


NIVEL_SEQ = {3: "alta", 2: "media", 1: "baja"}


def tarjeta(e):
    expo = e["expo"]
    seq = e["seq"]
    fn, ft = e["frio"]
    tag = f'<span class="tag">{esc(e["tag"])}</span>' if e.get("tag") else ""
    foto = f'<img src="file://{e["foto_local"]}">' if e.get("foto_local") else '<div class="sinfoto">Foto próximamente</div>'
    comun = f'<div class="comun">{esc(e["comun"])}</div>' if e["comun"] else '<div class="comun">&nbsp;</div>'
    medidas = ""
    if e.get("dims"):
        alto, ancho = e["dims"]
        txt = f"Alto {alto}" + (f" · Ancho {ancho}" if ancho else "")
        medidas = f'<div class="attr">{ico_regla()}<span>{esc(txt)}</span></div>'
    return f"""
<a class="card" href="{esc(e['url'])}">
  <div class="foto">{foto}{tag}</div>
  <div class="cient">{markup_cientifico(e['cientifico'])}</div>
  {comun}
  <div class="attrs">
    <div class="attr expo">{ico_sol('sol' in expo)}{ico_media('media' in expo)}{ico_sombra('sombra' in expo)}</div>
    <div class="attr">{ico_gota()}<span>Sequía: {NIVEL_SEQ[seq]}</span></div>
    <div class="attr">{ico_copo()}<span>{esc(ft)}</span></div>
    {medidas}
  </div>
  <div class="piecard"><div class="precio"><b>{fmt_precio(e['precio'])}</b><span>{esc(e['formato'])}</span></div><div class="ver">Ver en la tienda&nbsp;›</div></div>
</a>"""


def fmt_precio(p):
    return "$" + f"{int(round(p)):,}".replace(",", ".")


def formato(p, es_semilla):
    v = (p.get("variante") or "").strip()
    if es_semilla and re.search(r"semilla", p["nombre_tienda"], re.I):
        m = re.search(r"(\d+)\s*semillas", v + " " + p["nombre_tienda"], re.I)
        return f"Sobre x {m.group(1)} semillas" if m else "Sobre de semillas"
    if re.search(r"m12", v, re.I):
        return "Maceta M12"
    return v


def preparar(stock):
    entradas = {k: [] for k, _, _ in SECCIONES}
    for p in stock:
        if F.EXCLUIR.search(p["nombre_tienda"]):
            continue
        cient, comun = F.nombres(p)
        expo = F.exposicion(p.get("expo_txt"))
        base = dict(id=p["id"], url=p["url"], cientifico=cient, comun=comun, expo=expo,
                    gexpo=F.grupo_expo(expo), seq=F.sequia(p.get("riego_txt")),
                    frio=F.frio(p.get("frio_txt")), precio=p["precio"], foto=p.get("foto"),
                    dims=F.dimensiones(p.get("dim_txt")))
        orden = re.sub(r"[*'\"]", "", cient).lower()
        base["orden"] = orden
        semillas = [c for c in p["cats"] if c.startswith("semillas")]
        for c in p["cats"]:
            if c in entradas:
                entradas[c].append(dict(base, formato=formato(p, False)))
        if semillas and re.search(r"semilla", p["nombre_tienda"], re.I):
            tag = "Perenne" if "semillas_perennes" in semillas else "Anual o vida corta"
            entradas["semillas"].append(dict(base, formato=formato(p, True), tag=tag))
    for k in entradas:
        entradas[k].sort(key=lambda e: (e["gexpo"][0], e["orden"]))
    return entradas


CSS = """
@font-face{font-family:M;src:url(file://%(f)s/Montserrat.woff2);font-weight:100 900}
@font-face{font-family:J;src:url(file://%(f)s/Jakarta.woff2);font-weight:200 800}
@font-face{font-family:J;src:url(file://%(f)s/Jakarta-Italic.woff2);font-weight:200 800;font-style:italic}
*{box-sizing:border-box;margin:0;padding:0}
html{background:#E9E7DA;color:#373F27;font-family:J,sans-serif;font-size:9pt;-webkit-print-color-adjust:exact}
i{font-style:italic}
a{color:inherit;text-decoration:none}
/* Las secciones siguen en la misma página si entra el encabezado más una fila: así no quedan huecos al final */
.sec+.sec{margin-top:6mm}
.sechead{break-after:avoid;break-inside:avoid;background:#373F27;color:#E9E7DA;padding:3.2mm 6mm 3.4mm;margin-bottom:3.5mm}
.sechead .fila{display:flex;justify-content:space-between;align-items:baseline;gap:4mm}
.sechead .kicker{font-family:M;font-weight:400;font-size:7.5pt;letter-spacing:.13em;text-transform:uppercase;opacity:.85;white-space:nowrap}
.sechead h2{font-family:M;font-weight:500;font-size:15pt;line-height:1.2}
.sechead p{font-size:8.6pt;margin-top:.8mm;line-height:1.3}
.grupo{font-family:M;font-weight:500;font-size:8pt;letter-spacing:.13em;text-transform:uppercase;
  display:flex;align-items:center;gap:2.5mm;margin:5mm 0 3mm;break-after:avoid}
.grupo:before{content:"";flex:0 0 6mm;height:0;border-top:1.2pt solid #373F27}
.grupo .ics{display:flex;gap:1mm}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:3.5mm 5mm}
.card{display:block;break-inside:avoid}
.foto{position:relative;aspect-ratio:16/9;background:#636B46;overflow:hidden}
.foto img{width:100%%;height:100%%;object-fit:cover;display:block}
.sinfoto{color:#E9E7DA;display:flex;align-items:center;justify-content:center;height:100%%}
.tag{position:absolute;left:0;top:0;background:#373F27;color:#E9E7DA;font-size:7pt;font-weight:600;padding:1.2mm 2.2mm;letter-spacing:.02em}
.cient{font-size:9.5pt;font-weight:600;margin-top:1.8mm;line-height:1.2}
.comun{font-size:8.5pt;margin-top:.4mm}
.attrs{margin-top:1.6mm;border-top:.6pt solid #636B46;padding-top:1.4mm;display:flex;flex-direction:column;gap:.8mm}
.attr{display:flex;align-items:center;gap:1.4mm;font-size:7.6pt}
.attr.expo{gap:.8mm}
.ic{width:3.6mm;height:3.6mm;flex:0 0 3.6mm}
.piecard{display:flex;margin-top:1.8mm}
.precio{flex:1;background:#373F27;color:#E9E7DA;display:flex;flex-direction:column;justify-content:center;padding:1.2mm 2.2mm;min-width:0}
.precio b{font-size:9.5pt;font-weight:700;line-height:1.15}
.precio span{font-size:6.8pt;line-height:1.2}
.ver{background:#CDA34F;color:#373F27;font-weight:700;font-size:7.6pt;display:flex;align-items:center;padding:0 2.4mm;white-space:nowrap}
"""

COVER_CSS = """
@font-face{font-family:M;src:url(file://%(f)s/Montserrat.woff2);font-weight:100 900}
@font-face{font-family:J;src:url(file://%(f)s/Jakarta.woff2);font-weight:200 800}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:210mm;height:297mm;background:#373F27;color:#E9E7DA;font-family:J,sans-serif;-webkit-print-color-adjust:exact}
.wrap{padding:12mm 18mm 34mm;height:297mm;display:flex;flex-direction:column}
.logo{text-align:center}
.logo img{width:76mm}
.kick{font-family:M;font-weight:400;font-size:8.5pt;letter-spacing:.13em;text-transform:uppercase;text-align:center;margin-top:7mm}
.palabra{font-family:M;font-weight:500;font-size:38pt;letter-spacing:.04em;text-transform:uppercase;color:#E9E7DA;text-align:center;margin-top:2mm;line-height:1}
.fecha{font-size:12pt;text-align:center;margin-top:4mm}
.aviso{font-size:10.5pt;line-height:1.45;text-align:center;margin:3.5mm auto 0;max-width:160mm}
.envios{background:#E9E7DA;color:#373F27;padding:8mm 9mm 9mm;margin-top:8mm}
.envios h2{font-family:M;font-weight:500;font-size:10pt;letter-spacing:.13em;text-transform:uppercase;margin-bottom:5mm;display:flex;align-items:center;gap:2.5mm}
.envios h2:before{content:"";flex:0 0 7mm;border-top:1.4pt solid #373F27}
.env{display:grid;grid-template-columns:1fr 1fr;gap:8mm 9mm}
.it{display:flex;gap:3.5mm;align-items:flex-start}
.it svg{flex:0 0 13mm;width:13mm;height:13mm}
.it b{display:block;font-family:M;font-weight:600;font-size:14pt;line-height:1.2;margin-bottom:1.2mm}
.it p{font-size:11pt;line-height:1.4}
.placa{background:#636B46;padding:6.5mm 9mm 7mm;margin-top:7mm}
.placa h3{font-family:M;font-weight:500;font-size:13pt;margin-bottom:4mm}
.ley{display:grid;grid-template-columns:1.15fr 1fr 1fr 1fr;gap:6mm;font-size:9.6pt;line-height:1.4}
.ley .t{font-weight:700;font-size:11pt;display:flex;align-items:center;gap:2mm;margin-bottom:1.8mm}
.ley svg{width:5.4mm;height:5.4mm}
.ley svg *{stroke:#E9E7DA}
.ley svg circle[fill="#373F27"],.ley svg path[fill="#373F27"]{fill:#E9E7DA}
"""


def _svg(body):
    return ('<svg viewBox="0 0 32 32"><g fill="none" stroke="#373F27" stroke-width="2" stroke-linejoin="miter">'
            + body + '</g></svg>')


ICO_CAJA = _svg('<path d="M4 10l12-5 12 5v14l-12 5-12-5z"/><path d="M4 10l12 5 12-5M16 15v14"/>')
ICO_CAJAS = _svg('<path d="M2 14l8-3.5 8 3.5v10l-8 3.5-8-3.5z"/><path d="M2 14l8 3.5 8-3.5M10 17.5V27"/>'
                 '<path d="M14 8l8-3.5 8 3.5v10l-8 3.5"/><path d="M14 8l8 3.5 8-3.5M22 11.5V21"/>')
ICO_BROTE = _svg('<path d="M16 28V14"/><path d="M16 16c0-6-4-9-11-9 0 6 4 9 11 9z"/><path d="M16 13c0-5 3-8 10-8 0 5-3 8-10 8z"/><path d="M8 28h16"/>')
ICO_PIN = _svg('<path d="M16 29s-9-9.5-9-16a9 9 0 0 1 18 0c0 6.5-9 16-9 16z"/><circle cx="16" cy="13" r="3.5"/>')


def cover_html(entradas, fecha, logo):
    f = os.path.join(HERE, "fonts")
    T = TEXTOS
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{COVER_CSS % {'f': f}}</style></head>
<body><div class="wrap">
<div class="logo"><img src="file://{logo}"></div>
<div class="kick">Plantas y semillas disponibles</div>
<div class="palabra">Esta semana</div>
<div class="fecha">Stock disponible al {fecha}</div>
<div class="aviso">{esc(T["tapa_aviso"])}</div>
<div class="envios"><h2>Cómo comprar</h2><div class="env">
 <div class="it">{ICO_CAJA}<div><b>{esc(T["comprar_1_titulo"])}</b><p>{esc(T["comprar_1_texto"])}</p></div></div>
 <div class="it">{ICO_CAJAS}<div><b>{esc(T["comprar_2_titulo"])}</b><p>{esc(T["comprar_2_texto"])}</p></div></div>
 <div class="it">{ICO_BROTE}<div><b>{esc(T["comprar_3_titulo"])}</b><p>{esc(T["comprar_3_texto"])}</p></div></div>
 <div class="it">{ICO_PIN}<div><b>{esc(T["comprar_4_titulo"])}</b><p>{esc(T["comprar_4_texto"])}</p></div></div>
</div></div>
<div class="placa"><h3>Cómo leer cada especie</h3>
<div class="ley">
 <div><div class="t">{ico_sol()}{ico_media()}{ico_sombra()}</div>{esc(T["leer_luz"])}</div>
 <div><div class="t">{ico_gota()} Sequía</div>{esc(T["leer_sequia"])}</div>
 <div><div class="t">{ico_copo()} Frío</div>{esc(T["leer_frio"])}</div>
 <div><div class="t">{ico_regla()} Tamaño</div>{esc(T["leer_tamano"])}</div>
</div></div>
</div></body></html>"""


def body_html(entradas):
    f = os.path.join(HERE, "fonts")
    secs = []
    for k, titulo, sub in SECCIONES:
        es = entradas[k]
        if not es:
            continue
        partes = [f'<section class="sec"><div class="sechead"><div class="fila"><h2>{titulo}</h2>'
                  f'<div class="kicker">{len(es)} disponibles</div></div><p>{esc(sub)}</p></div>']
        # Una sola grilla corrida por sección: las filas se completan siempre y solo la última
        # puede quedar incompleta. El orden sigue siendo de más sol a más sombra y alfabético;
        # la luz de cada especie se ve en sus íconos.
        partes.append('<div class="grid">')
        for e in es:
            partes.append(tarjeta(e))
        partes.append("</div></section>")
        secs.append("".join(partes))
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS % {'f': f}}</style></head>
<body>{''.join(secs)}</body></html>"""


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fecha_larga(d):
    return f"{d.day} de {MESES[d.month-1]} de {d.year}"


def fecha_con_dia(d):
    return f"{DIAS[d.weekday()]} {fecha_larga(d)}"


def fecha_corta(d):
    return f"{DIAS[d.weekday()]} {d.day}/{d.month}"


def main():
    stock_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "stock.json")
    hoy = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date()
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, f"Glauco-disponibles-{hoy.isoformat()}.pdf")
    stock = json.load(open(stock_path))
    entradas = preparar(stock)
    todas = [e for es in entradas.values() for e in es]
    urls = sorted({e["foto"] for e in todas if e["foto"]})
    with cf.ThreadPoolExecutor(8) as ex:
        locales = dict(zip(urls, ex.map(lambda u: _try(bajar_foto, u), urls)))
    for e in todas:
        e["foto_local"] = locales.get(e["foto"])
    sin_foto = sorted({re.sub(r"[*]", "", e["cientifico"]) for e in todas if not e["foto_local"]})

    logo = os.path.join(HERE, "logos", "logo_tienda.png")
    tmp_c, tmp_b = out + ".cover.pdf", out + ".body.pdf"
    open(os.path.join(HERE, "_cover.html"), "w").write(cover_html(entradas, fecha_con_dia(hoy), logo))
    open(os.path.join(HERE, "_body.html"), "w").write(body_html(entradas))
    footer = ('<div style="width:100%;font-family:sans-serif;font-size:7pt;color:#373F27;padding:16mm 12mm 0;'
              'display:flex;justify-content:space-between"><span>Vivero Glauco · www.viveroglauco.com · '
              f'Stock al {fecha_corta(hoy)}, sujeto a disponibilidad</span>'
              '<span><span class="pageNumber"></span></span></div>')
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files"])
        pg = b.new_page()
        pg.goto("file://" + os.path.join(HERE, "_cover.html"))
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=tmp_c, width="210mm", height="297mm", print_background=True,
               margin=dict(top="0", bottom="0", left="0", right="0"))
        pg.goto("file://" + os.path.join(HERE, "_body.html"))
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=tmp_b, format="A4", print_background=True, display_header_footer=True,
               header_template="<span></span>", footer_template=footer,
               margin=dict(top="10mm", bottom="24mm", left="12mm", right="12mm"))
        tmp_btn = out + ".btn.pdf"
        open(os.path.join(HERE, "_btn.html"), "w").write(
            BTN_HTML % {"f": os.path.join(HERE, "fonts"), "w": BTN_W, "h": BTN_H})
        pg.goto("file://" + os.path.join(HERE, "_btn.html"))
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=tmp_btn, width=f"{BTN_W}mm", height=f"{BTN_H}mm", print_background=True,
               margin=dict(top="0", bottom="0", left="0", right="0"))
        b.close()
    w = PdfWriter()
    w.append(PdfReader(tmp_c))
    # fondo crema de página completa debajo de cada página interior (incluye márgenes)
    from pypdf import PageObject, Transformation
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject, ArrayObject, FloatObject
    for pg_ in PdfReader(tmp_b).pages:
        wpt, hpt = float(pg_.mediabox.width), float(pg_.mediabox.height)
        bg = PageObject.create_blank_page(width=wpt, height=hpt)
        st = DecodedStreamObject()
        st.set_data(f"0.914 0.906 0.855 rg 0 0 {wpt} {hpt} re f".encode())
        bg[NameObject("/Contents")] = w._add_object(st)
        bg.merge_page(pg_)
        w.add_page(bg)
    # botón de WhatsApp en todas las páginas, abajo a la derecha, con su enlace
    from pypdf.generic import DictionaryObject, ArrayObject, FloatObject, NumberObject, TextStringObject
    btn = PdfReader(tmp_btn).pages[0]
    for i, page in enumerate(w.pages):
        wpt = float(page.mediabox.width)
        x0 = wpt - (BTN_RIGHT + BTN_W) * MM
        y0 = BTN_BOTTOM * MM
        page.merge_transformed_page(btn, Transformation().translate(x0, y0))
        link = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject([FloatObject(x0), FloatObject(y0),
                                              FloatObject(x0 + BTN_W * MM), FloatObject(y0 + BTN_H * MM)]),
            NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
            NameObject("/A"): DictionaryObject({NameObject("/S"): NameObject("/URI"),
                                                NameObject("/URI"): TextStringObject(WA_URL)}),
        })
        w.add_annotation(page_number=i, annotation=link)
    os.remove(tmp_btn)
    w.add_metadata({"/Title": f"Vivero Glauco · Disponibles al {fecha_larga(hoy)}"})
    w.write(out)
    os.remove(tmp_c); os.remove(tmp_b)
    resumen = {k: len(v) for k, v in entradas.items()}
    print(json.dumps({"pdf": out, "por_seccion": resumen, "sin_foto": sin_foto}, ensure_ascii=False))


def _try(f, *a):
    try:
        return f(*a)
    except Exception:
        return None


if __name__ == "__main__":
    main()
