"""Собирает dist/pokedex.json: все 1025 видов National Pokédex для вкладки Pack.

Источник: PokeAPI (https://pokeapi.co), поля pokemon-species:
  - names (английское имя),
  - is_legendary / is_mythical (официальная классификация Legendary / Mythical Pokémon).

Формат файла:
  {"v": 1, "source": "PokeAPI", "count": 1025,
   "list": [[1, "Bulbasaur", ""], ..., [150, "Mewtwo", "L"], [151, "Mew", "M"], ...]}
  категория: "" обычный, "L" Legendary, "M" Mythical.

Запуск:  python3 scripts/build_pokedex.py --out dist/pokedex.json [--cache папка_с_json]
Если проверки не пройдены (не 1025 видов, дыры в номерах), файл не перезаписывается.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TOTAL = 1025
API = "https://pokeapi.co/api/v2/pokemon-species/{}/"


def fetch(i, cache):
    path = os.path.join(cache, f"{i}.json") if cache else None
    if path and os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(API.format(i), headers={"User-Agent": "prodex-build"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            return data
        except Exception as e:  # сеть / лимит запросов
            last = e
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"#{i}: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/pokedex.json")
    ap.add_argument("--cache", default="")
    a = ap.parse_args()
    if a.cache:
        os.makedirs(a.cache, exist_ok=True)

    with ThreadPoolExecutor(max_workers=12) as ex:
        species = list(ex.map(lambda i: fetch(i, a.cache), range(1, TOTAL + 1)))

    rows = []
    for i, d in enumerate(species, start=1):
        if d.get("id") != i:
            sys.exit(f"Ошибка: ожидался вид #{i}, получен #{d.get('id')}")
        name = next((n["name"] for n in d.get("names", []) if n["language"]["name"] == "en"), d["name"])
        cat = "M" if d.get("is_mythical") else ("L" if d.get("is_legendary") else "")
        rows.append([i, name, cat])

    if len(rows) != TOTAL or len({r[1] for r in rows}) != TOTAL:
        sys.exit("Ошибка: список неполный или есть повторы имён, файл не изменён")

    out = {"v": 1, "source": "PokeAPI", "count": TOTAL, "list": rows}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    n_l = sum(r[2] == "L" for r in rows)
    n_m = sum(r[2] == "M" for r in rows)
    print(f"OK: {len(rows)} видов, Legendary {n_l}, Mythical {n_m}, обычных {len(rows) - n_l - n_m} -> {a.out}")


if __name__ == "__main__":
    main()
