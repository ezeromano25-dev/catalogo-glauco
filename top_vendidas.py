#!/usr/bin/env python3
"""Top de especies más vendidas con stock en www.viveroglauco.com (sin semillas).

Uso: python3 top_vendidas.py [cantidad]   (por defecto 10)
Recorre /productos/ con el orden "Más vendidos" de la tienda (sort_by=best-selling),
se queda con los productos que tienen alguna variante disponible y descarta:
- semillas (todo producto con "semilla" en el nombre o solo en categorías de semillas
  sin ser planta),
- lo que no es planta: packs/diseños, fertilizantes, kits, sustratos, gift cards.
Imprime JSON con puesto, nombre, precio, variante y enlace.
"""
import json, re, sys
import requests
from bs4 import BeautifulSoup

BASE = "https://www.viveroglauco.com"
EXCLUIR = re.compile(
    r"semilla|dise[ñn]o|pack|fertiliz|kit|sustrato|gift|tarjeta|curso|abono|maceta vac",
    re.I,
)
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (catalogo-glauco)"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    top, seen, excluidos = [], set(), []
    for p in range(1, 40):
        r = S.get(f"{BASE}/productos/page/{p}/?sort_by=best-selling&results_only=true", timeout=30)
        r.raise_for_status()
        items = BeautifulSoup(r.text, "lxml").select(".js-item-product")
        nuevos = 0
        for el in items:
            pid = el.get("data-product-id")
            if pid in seen:
                continue
            seen.add(pid)
            nuevos += 1
            vtag = el.select_one("[data-variants]")
            variants = json.loads(vtag["data-variants"]) if vtag else []
            disp = [v for v in variants if v.get("available")]
            if not disp:
                continue
            a = el.select_one('a[href*="/productos/"]')
            name_el = el.select_one(".js-item-name, .item-name")
            nombre = name_el.get_text(strip=True) if name_el else a.get("title", "")
            if EXCLUIR.search(nombre):
                excluidos.append(nombre)
                continue
            v0 = disp[0]
            top.append({
                "puesto": len(top) + 1,
                "nombre": nombre,
                "precio": v0.get("price_number"),
                "variante": v0.get("option0"),
                "url": a["href"].split("?")[0],
            })
            if len(top) >= n:
                break
        if len(top) >= n or not nuevos:
            break
    print(json.dumps({"top": top, "excluidos_en_el_camino": excluidos}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
