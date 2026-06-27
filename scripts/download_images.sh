#!/bin/bash
# Download lottery images from loteriadehoy.com
BASE="https://www.loteriadehoy.com"

download() {
  mkdir -p "$(dirname "$2")"
  if [ -f "$2" ]; then
    echo "SKIP $2"
    return
  fi
  curl -s -o "$2" "$1" && echo "OK $2" || echo "FAIL $2"
}

export -f download

echo "=== Lottery logos ==="
download "$BASE/dist/files_img/Lotto_Activo.webp" "img/loterias/lotto_activo.webp"
download "$BASE/dist/files_img/La_Granjita.webp" "img/loterias/la_granjita.webp"
download "$BASE/dist/files_img/Selva_Plus.webp" "img/loterias/selvaplus.webp"

echo "=== Animal images ==="
ANIMALS=(Delfin Ballena Carnero Toro Ciempies Alacran Rana Raton Aguila Leon Perico Tigre Gato Caballo Mono Paloma Zorro Oso Pavo Burro Chivo Cochino Gallo Camello Cebra Iguana Gallina Vaca Perro Zamuro Elefante Caiman Lapa Ardilla Pescado Venado Jirafa Culebra)

echo "--- Lotto Activo (suffix _2) ---"
for a in "${ANIMALS[@]}"; do
  download "$BASE/dist/animals_img/${a}_2.webp" "img/animales/lotto_activo/${a}.webp"
done

echo "--- La Granjita (suffix _3) ---"
for a in "${ANIMALS[@]}"; do
  download "$BASE/dist/animals_img/${a}_3.webp" "img/animales/la_granjita/${a}.webp"
done

echo "--- Selva Plus (suffix _16) ---"
for a in "${ANIMALS[@]}"; do
  download "$BASE/dist/animals_img/${a}_16.webp" "img/animales/selvaplus/${a}.webp"
done

echo "Done!"
