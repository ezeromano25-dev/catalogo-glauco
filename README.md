# Catálogo semanal de stock — Vivero Glauco

Programas que arman el catálogo en PDF con el stock de www.viveroglauco.com.
Las reglas del catálogo, la planilla de revisión y el paso a paso de los martes están en el
proyecto de Claude "Piezas gráficas GLAUCO" (`claude/catalogo-stock/README.md`).

## Uso
```bash
git clone --depth 1 https://github.com/ezeromano25-dev/catalogo-glauco glauco && cd glauco
bash setup.sh                                  # tipografías, logo y librerías
# copiar del proyecto: correcciones.json, textos.json, ultimo-stock.txt
python3 fetch_stock.py .                       # stock, precios, fotos y fichas de la tienda
python3 build.py                               # PDF: Glauco-disponibles-AAAA-MM-DD.pdf
python3 revision.py cambios stock.json claves.json ultimo-stock.txt   # cambios para la planilla de revisión
```

| Archivo | Qué hace |
| --- | --- |
| `fetch_stock.py` | Recorre las categorías de la tienda y guarda en `stock.json` lo que está disponible |
| `fichas.py` | Nombres científicos, exposición, sequía, frío y medidas a partir de la ficha |
| `build.py` | Diseño del PDF (marca Glauco). No se cambia sin pedido de Ezequiel |
| `revision.py` | Carga y aplica las correcciones de la planilla de revisión |
| `top_vendidas.py` | Ranking "Más vendidos" de la tienda con stock (plan B de la tarea de "más vendidas") |
| `setup.sh` | Prepara tipografías (versión fija), logo y librerías |

Los datos que cambian cada semana (`correcciones.json`, `textos.json`, `ultimo-stock.txt`) viven en el proyecto, no acá.
