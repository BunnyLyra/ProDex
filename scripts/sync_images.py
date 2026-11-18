#!/usr/bin/env python3
"""Достаёт из release.zip (flibustier/pokemon-tcg-pocket-database) только картинки карт
и кладёт их в dist/images/cards-by-set/<СЕТ>/<номер>.webp.

Новые файлы добавляются, изменившиеся (другой размер) заменяются, остальные не трогаются,
ничего не удаляется. Структура внутри архива не важна: берутся все файлы .webp,
в пути которых есть папка cards-by-set.

  python3 scripts/sync_images.py release.zip dist/images/cards-by-set
"""
import os, sys, zipfile

MARK = "cards-by-set/"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    zpath, dest = sys.argv[1], sys.argv[2]
    added = replaced = same = 0
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".webp") and MARK in n.replace("\\", "/")]
        if not names:
            sys.exit("В архиве нет картинок cards-by-set: структура архива изменилась, ничего не скопировано.")
        for n in names:
            rel = n.replace("\\", "/").split(MARK, 1)[1]
            parts = rel.split("/")
            if not rel or rel.startswith("/") or ".." in parts:
                continue                                  # защита от странных путей в архиве
            if any(p.startswith(".") for p in parts) or "__MACOSX" in n.split("/"):
                continue                                  # мусор macOS внутри архива (._файл, __MACOSX)
            target = os.path.join(dest, rel)
            info = z.getinfo(n)
            if os.path.exists(target):
                if os.path.getsize(target) == info.file_size:
                    same += 1
                    continue
                replaced += 1
            else:
                added += 1
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(n) as src, open(target, "wb") as out:
                out.write(src.read())
    print(f"Картинки: добавлено {added}, заменено {replaced}, без изменений {same}")


if __name__ == "__main__":
    main()
