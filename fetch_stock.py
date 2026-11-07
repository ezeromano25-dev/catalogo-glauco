#!/usr/bin/env python3
"""Lee la tienda viveroglauco.com y guarda en stock.json los productos disponibles.

Uso: python3 fetch_stock.py [carpeta_salida]
Para cada producto con stock: categorías, precio, variante, enlace, primera foto,
y las líneas de exposición, riego y temperatura mínima de la ficha.
"""
import json, re, sys, os, concurrent.futures as cf
import requests
from bs4 import BeautifulSoup

BASE = "https://www.viveroglauco.com"
CATS = {
    "perennes": "/herbaceas-perennes/",
    "anuales": "/herbaceas-anuales/",
    "arbustos": "/arbustos-y-arboles-para-canteros/",
    "gramineas": "/gramineas/",
    "semillas_perennes": "/semillas-de-perennes/",
    "semillas_anuales": "/semillas-de-anuales/",
}
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (catalogo-glauco)"


def get(url):
    r = S.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def listar():
    prods = {}
    for cat, path in CATS.items():
        seen = set()
        for p in range(1, 30):
            soup = BeautifulSoup(get(f"{BASE}{path}page/{p}/?results_only=true"), "lxml")
            items = soup.select(".js-item-product")
            nuevos = 0
            for el in items:
                pid = el.get("data-product-id")
                if pid in seen:
                    continue
                seen.add(pid)
                nuevos += 1
                vtag = el.select_one("[data-variants]")
                variants = json.loads(vtag["data-variants"]) if vtag else []
                if not any(v.get("available") for v in variants):
                    continue
                a = el.select_one('a[href*="/productos/"]')
                name_el = el.select_one(".js-item-name, .item-name")
                v0 = next(v for v in variants if v.get("available"))
                prod = prods.setdefault(pid, {
                    "id": pid,
                    "nombre_tienda": (name_el.get_text(strip=True) if name_el else a.get("title", "")),
                    "url": a["href"].split("?")[0],
                    "precio": v0.get("price_number"),
                    "variante": v0.get("option0"),
                    "cats": [],
                })
                if cat not in prod["cats"]:
                    prod["cats"].append(cat)
            if not nuevos:
                break
    return list(prods.values())


def ficha(prod):
    soup = BeautifulSoup(get(prod["url"]), "lxml")
    desc = soup.select_one(".product-description, [data-store='product-description']")
    t = desc.get_text("\n") if desc else ""

    def linea(rx):
        m = re.search(rx, t, re.I)
        return m.group(1).strip() if m else None

    prod["expo_txt"] = linea(r"Exposici[oó]n solar\s*:\s*([^\n]+)")
    prod["riego_txt"] = linea(r"Necesidad de riego\s*:\s*([^\n]+)")
    prod["frio_txt"] = linea(r"Temperatura m[ií]nima[^:\n]*:\s*([^\n]+)")
    # Medidas: el texto puede venir cortado en varias etiquetas, así que se toma hasta el ítem siguiente.
    t_plano = " ".join(desc.get_text(" ").split()) if desc else ""
    m = re.search(r"Dimensiones que[^:]*:\s*(.+?)(?:🐜|Plagas y enfermedades|$)", t_plano, re.I)
    prod["dim_txt"] = m.group(1).strip() if m else None
    # Primera imagen de la galería del artículo
    img = None
    for im in soup.select(".js-product-slide img, .product-slider img"):
        src = im.get("data-srcset") or im.get("srcset") or im.get("data-src") or im.get("src") or ""
        src = src.split(" ")[0]
        if src and "empty-placeholder" not in src and "no-photo" not in src:
            img = src
            break
    if not img:
        og = soup.select_one("meta[property='og:image']")
        img = og["content"] if og else None
    if img and "no-photo" in img:  # imagen genérica de Tiendanube: el producto no tiene foto
        img = None
    if img:
        img = re.sub(r"-\d+-\d+\.(webp|jpg|png)", r"-640-0.\1", img)
        if img.startswith("//"):
            img = "https:" + img
        img = img.replace("http://", "https://")
    prod["foto"] = img
    return prod


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    prods = listar()
    with cf.ThreadPoolExecutor(8) as ex:
        prods = list(ex.map(ficha, prods))
    with open(os.path.join(out, "stock.json"), "w") as f:
        json.dump(prods, f, ensure_ascii=False, indent=1)
    print(f"{len(prods)} productos disponibles")


if __name__ == "__main__":
    main()
