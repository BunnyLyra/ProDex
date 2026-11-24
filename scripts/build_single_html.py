"""Собирает однофайловую версию ProDex: index.html + missions.js + данные из dist/ в одном HTML.

Такой файл можно открыть прямо с диска (двойной клик), сервер не нужен.
Свежие данные и картинки он всё равно пробует взять из репозитория на GitHub,
а встроенные данные используются, если их там нет или нет интернета.

Запуск (из корня репозитория):  python scripts/build_single_html.py --out ProDex.html
"""
import argparse
import json

EMBED = ["dist/cards.json", "dist/sets.json", "dist/pullRates.json", "dist/pokedex.json"]
MISSIONS_TAG = '<script src="missions.js?v=27"></script>'


def js_safe(text):
    # нельзя, чтобы внутри встречалось "</script"; U+2028/2029 экранируем на всякий случай
    return text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="index.html")
    ap.add_argument("--missions", default="missions.js")
    ap.add_argument("--out", default="ProDex.html")
    a = ap.parse_args()

    html = open(a.src, encoding="utf-8").read()
    missions = open(a.missions, encoding="utf-8").read()
    if html.count(MISSIONS_TAG) != 1:
        raise SystemExit("Не найден тег подключения missions.js")

    emb = {}
    for path in EMBED:
        with open(path, encoding="utf-8") as f:
            emb[path] = json.load(f)
    emb_js = "window.EMB = " + json.dumps(emb, ensure_ascii=False, separators=(",", ":")) + ";"

    block = "<script>\n" + js_safe(missions) + "\n</script>\n<script>" + js_safe(emb_js) + "</script>"
    out = html.replace(MISSIONS_TAG, block)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)
    print(f"OK: {a.out}, {len(out.encode('utf-8')) / 1024 / 1024:.2f} МБ, встроено: {', '.join(EMBED)} и missions.js")


if __name__ == "__main__":
    main()
