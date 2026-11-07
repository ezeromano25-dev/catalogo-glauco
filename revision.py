#!/usr/bin/env python3
"""Planilla de revisión de textos del catálogo.

  python3 revision.py filas stock.json [ultimo-stock.txt]
      Escribe revision_filas.json con las filas para las pestañas "Especies" y "Tapa"
      y ultimo-stock.txt con la lista de esta semana.

  python3 revision.py aplicar especies.json tapa.json
      Lee lo que devolvió get_values de cada pestaña (lista de filas, con encabezado),
      guarda las correcciones en correcciones.json y textos.json y muestra qué cambió.
"""
import json, os, re, sys
import fichas as F

HERE = os.path.dirname(os.path.abspath(__file__))
COLS_ESPECIES = ["Sección", "Nombre en la tienda", "Nombre científico (así sale)",
                 "Corrección nombre científico", "Nombre común (así sale)", "Corrección nombre común",
                 "Comentario para Claude", "¿Nueva esta semana?", "Enlace a la tienda", "Clave (no tocar)"]
COLS_TAPA = ["Dónde aparece", "Texto (así sale)", "Corrección", "Clave (no tocar)"]
DONDE = {
    "tapa_aviso": "Tapa · aviso de disponibilidad",
    "comprar_1_titulo": "Tapa · Cómo comprar 1 (título)", "comprar_1_texto": "Tapa · Cómo comprar 1 (texto)",
    "comprar_2_titulo": "Tapa · Cómo comprar 2 (título)", "comprar_2_texto": "Tapa · Cómo comprar 2 (texto)",
    "comprar_3_titulo": "Tapa · Cómo comprar 3 (título)", "comprar_3_texto": "Tapa · Cómo comprar 3 (texto)",
    "comprar_4_titulo": "Tapa · Cómo comprar 4 (título)", "comprar_4_texto": "Tapa · Cómo comprar 4 (texto)",
    "leer_luz": "Tapa · Cómo leer: luz", "leer_sequia": "Tapa · Cómo leer: sequía", "leer_frio": "Tapa · Cómo leer: frío", "leer_tamano": "Tapa · Cómo leer: tamaño",
    "seccion_perennes": "Encabezado · Herbáceas perennes", "seccion_anuales": "Encabezado · Anuales y vida corta",
    "seccion_arbustos": "Encabezado · Arbustos y salvias", "seccion_gramineas": "Encabezado · Gramíneas y cárex",
    "seccion_semillas": "Encabezado · Semillas",
}
NOMBRE_SECCION = {"perennes": "Perennes", "anuales": "Anuales y vida corta", "arbustos": "Arbustos y salvias",
                  "gramineas": "Gramíneas y cárex"}


def secciones_de(p):
    out = [NOMBRE_SECCION[c] for c in p["cats"] if c in NOMBRE_SECCION]
    sem = [c for c in p["cats"] if c.startswith("semillas")]
    if sem and re.search(r"semilla", p["nombre_tienda"], re.I):
        out.append("Semillas (perenne)" if "semillas_perennes" in sem else "Semillas (anual o vida corta)")
    return out


def filas(stock_path, ultimo_path=None):
    import build  # para TEXTOS
    stock = json.load(open(stock_path, encoding="utf-8"))
    anteriores = set()
    if ultimo_path and os.path.exists(ultimo_path):
        anteriores = {l.split("|", 1)[-1].strip() for l in open(ultimo_path, encoding="utf-8") if l.strip()}
    especies, lista = [], []
    for p in stock:
        if F.EXCLUIR.search(p["nombre_tienda"]):
            continue
        secs = secciones_de(p)
        if not secs:
            continue
        sci, comun = F.nombres(p)
        nueva = "Sí" if anteriores and p["nombre_tienda"] not in anteriores else ""
        especies.append([", ".join(secs), p["nombre_tienda"], F.cientifico_a_texto(sci), "",
                         comun or "", "", "", nueva, p["url"], F._slug(p["url"])])
        for s in secs:
            lista.append(f"{s} | {p['nombre_tienda']}")
    especies.sort(key=lambda r: (r[0], r[2].lower()))
    tapa = [[DONDE[k], v, "", k] for k, v in build.TEXTOS.items()]
    json.dump({"especies": [COLS_ESPECIES] + especies, "tapa": [COLS_TAPA] + tapa},
              open(os.path.join(HERE, "revision_filas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(HERE, "ultimo-stock.txt"), "w", encoding="utf-8").write("\n".join(lista) + "\n")
    print(f"{len(especies)} especies, {len(tapa)} textos de tapa")


def _filas_de(path):
    d = json.load(open(path, encoding="utf-8"))
    return d.get("values", d) if isinstance(d, dict) else d


def aplicar(especies_path, tapa_path):
    cambios = []
    corr_p = os.path.join(HERE, "correcciones.json")
    corr = json.load(open(corr_p, encoding="utf-8")) if os.path.exists(corr_p) else {}
    for r in _filas_de(especies_path)[1:]:
        r = list(r) + [""] * (10 - len(r))
        clave, c_sci, c_com = r[9].strip(), r[3].strip(), r[5].strip()
        if not clave or not (c_sci or c_com):
            continue
        e = corr.setdefault(clave, {})
        if c_sci:
            e["cientifico"] = c_sci
            cambios.append(f"{r[1]}: científico → {c_sci}")
        if c_com:
            e["comun"] = c_com
            cambios.append(f"{r[1]}: común → {c_com}")
    json.dump(corr, open(corr_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    tex_p = os.path.join(HERE, "textos.json")
    tex = json.load(open(tex_p, encoding="utf-8")) if os.path.exists(tex_p) else {}
    for r in _filas_de(tapa_path)[1:]:
        r = list(r) + [""] * (4 - len(r))
        clave, c = r[3].strip(), r[2].strip()
        if clave in DONDE and c:
            tex[clave] = c
            cambios.append(f"{DONDE[clave]} → {c}")
    json.dump(tex, open(tex_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n".join(cambios) if cambios else "Sin correcciones.")


if __name__ == "__main__":
    if sys.argv[1] == "filas":
        filas(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif sys.argv[1] == "aplicar":
        aplicar(sys.argv[2], sys.argv[3])
