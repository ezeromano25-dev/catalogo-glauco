#!/usr/bin/env bash
# Prepara la carpeta para generar el catálogo: tipografías (versión fija), logo y librerías.
# Uso: bash setup.sh
set -e
cd "$(dirname "$0")"
mkdir -p fonts logos

if [ ! -f fonts/Montserrat.woff2 ]; then
  tmp=$(mktemp -d)
  (cd "$tmp" && npm pack @fontsource-variable/montserrat@5.3.0 @fontsource-variable/plus-jakarta-sans@5.3.0 --silent >/dev/null)
  for f in "$tmp"/*.tgz; do tar xzf "$f" -C "$tmp" && mv "$tmp/package" "$tmp/$(basename "$f" .tgz)"; done
  cp "$tmp"/fontsource-variable-montserrat-*/files/montserrat-latin-wght-normal.woff2 fonts/Montserrat.woff2
  cp "$tmp"/fontsource-variable-plus-jakarta-sans-*/files/plus-jakarta-sans-latin-wght-normal.woff2 fonts/Jakarta.woff2
  cp "$tmp"/fontsource-variable-plus-jakarta-sans-*/files/plus-jakarta-sans-latin-wght-italic.woff2 fonts/Jakarta-Italic.woff2
  rm -rf "$tmp"
fi

python3 -c "import playwright, pypdf, bs4, lxml, PIL, requests" 2>/dev/null || \
  pip install --break-system-packages -q playwright pypdf beautifulsoup4 lxml pillow requests

if [ ! -f logos/logo_tienda.png ]; then
  curl -sSf -o logos/logo_tienda.webp "https://acdn-us.mitiendanube.com/stores/003/871/462/themes/common/logo-613994067-1740429562-aa74a25c2894d0456b8e6cfc121d9ea51740429562-1024-1024.webp"
  python3 -c "from PIL import Image; Image.open('logos/logo_tienda.webp').save('logos/logo_tienda.png')"
fi
echo "Listo: fonts/, logos/ y librerías preparados."
