import urllib.request
import os
import time

BASE_URL = "https://www.loteriadehoy.com"

LOTTERIES = {
    "lotto_activo": {"suffix": "2", "name": "Lotto Activo"},
    "la_granjita": {"suffix": "3", "name": "La Granjita"},
    "selvaplus": {"suffix": "16", "name": "Selva Plus"},
}

ANIMALS = [
    "Delfin", "Ballena", "Carnero", "Toro", "Ciempies", "Alacran",
    "Rana", "Raton", "Aguila", "Leon", "Perico", "Tigre",
    "Gato", "Caballo", "Mono", "Paloma", "Zorro", "Oso",
    "Pavo", "Burro", "Chivo", "Cochino", "Gallo", "Camello",
    "Cebra", "Iguana", "Gallina", "Vaca", "Perro", "Zamuro",
    "Elefante", "Caiman", "Lapa", "Ardilla", "Pescado", "Venado",
    "Jirafa", "Culebra",
]

def download(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        print(f"  SKIP {path} (exists)")
        return
    try:
        urllib.request.urlretrieve(url, path)
        print(f"  OK {path}")
    except Exception as e:
        print(f"  FAIL {path}: {e}")
    time.sleep(0.3)

print("=== Downloading lottery logos ===")
for key in LOTTERIES:
    url = f"{BASE_URL}/dist/files_img/{LOTTERIES[key]['name'].replace(' ', '_')}.webp"
    path = f"img/loterias/{key}.webp"
    download(url, path)

print("\n=== Downloading animal images ===")
for key, info in LOTTERIES.items():
    print(f"\n--- {info['name']} (suffix _{info['suffix']}) ---")
    for animal in ANIMALS:
        url = f"{BASE_URL}/dist/animals_img/{animal}_{info['suffix']}.webp"
        path = f"img/animales/{key}/{animal}.webp"
        download(url, path)

print("\nDone!")
