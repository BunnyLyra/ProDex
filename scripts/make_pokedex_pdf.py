"""PDF для физического Pokédex: все 1025 покемонов по порядку National Pokédex.

Ячейка: картинка 2,1 x 2,5 см и под ней маленькое имя. Без рамок и лишнего текста.
Лист A4, 9 x 9 = 81 покемон на странице, ячейки стоят вплотную (один рез делит двух соседей).
Только на полях страницы стоят короткие метки реза, по которым удобно резать линейкой.

Картинки: официальные иллюстрации PokeAPI/sprites (other/official-artwork/<номер>.png).
Если картинки нет, в ячейке печатается номер (текстовая заглушка).

Запуск:
  python scripts/make_pokedex_pdf.py --pokedex dist/pokedex.json --art папка_с_png --out ProDex_Pokedex_1025.pdf
Нужны пакеты reportlab и pillow, шрифт Arial (C:/Windows/Fonts/arial.ttf) или любой TTF через --font.
"""
import argparse
import io
import json
import os

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

IMG_W, IMG_H = 2.1 * cm, 2.5 * cm   # размер картинки по ТЗ
CAP_H = 0.35 * cm                   # полоска под имя
COLS, ROWS = 9, 9
DPI = 300
FONT_SIZE, FONT_MIN = 6.5, 4.5


def prepared(path):
    """PNG с прозрачностью -> JPEG на белом, 300 dpi по ширине ячейки (вписать, пропорции сохраняются)."""
    im = Image.open(path)
    im.load()
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bg = Image.new("RGB", im.size, "white")
    bg.paste(im, mask=im.split()[3])
    px_w = round(IMG_W / cm / 2.54 * DPI)
    px_h = round(IMG_H / cm / 2.54 * DPI)
    k = min(px_w / bg.width, px_h / bg.height)
    bg = bg.resize((max(1, round(bg.width * k)), max(1, round(bg.height * k))), Image.LANCZOS)
    buf = io.BytesIO()
    bg.save(buf, "JPEG", quality=90, optimize=True)
    buf.seek(0)
    return ImageReader(buf), bg.width / px_w, bg.height / px_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pokedex", default="dist/pokedex.json")
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", default="ProDex_Pokedex_1025.pdf")
    ap.add_argument("--font", default="C:/Windows/Fonts/arial.ttf")
    a = ap.parse_args()

    rows = json.load(open(a.pokedex, encoding="utf-8"))["list"]
    assert len(rows) == 1025 and [r[0] for r in rows] == list(range(1, 1026)), "нужны все 1025 видов по порядку"
    pdfmetrics.registerFont(TTFont("Cap", a.font))

    pw, ph = A4
    cell_w, cell_h = IMG_W, IMG_H + CAP_H
    grid_w, grid_h = COLS * cell_w, ROWS * cell_h
    x0, y0 = (pw - grid_w) / 2, (ph + grid_h) / 2  # левый верхний угол сетки
    per_page = COLS * ROWS

    c = canvas.Canvas(a.out, pagesize=A4)
    c.setTitle("ProDex — физический Pokédex (1025)")
    c.setAuthor("ProDex")
    missing = []
    for start in range(0, len(rows), per_page):
        page = rows[start:start + per_page]
        n_rows = (len(page) + COLS - 1) // COLS
        # метки реза только на полях: по линиям между колонками и строками
        c.setStrokeGray(0.6)
        c.setLineWidth(0.25)
        mark, gap = 0.35 * cm, 0.1 * cm
        for k in range(COLS + 1):
            x = x0 + k * cell_w
            c.line(x, y0 + gap, x, y0 + gap + mark)
            yb = y0 - n_rows * cell_h
            c.line(x, yb - gap, x, yb - gap - mark)
        for k in range(n_rows + 1):
            y = y0 - k * cell_h
            c.line(x0 - gap, y, x0 - gap - mark, y)
            c.line(x0 + grid_w + gap, y, x0 + grid_w + gap + mark, y)

        for i, (pid, name, _cat) in enumerate(page):
            col, row = i % COLS, i // COLS
            cx = x0 + col * cell_w
            top = y0 - row * cell_h
            path = os.path.join(a.art, f"{pid}.png")
            ok = False
            if os.path.exists(path) and os.path.getsize(path) > 0:
                try:
                    img, fw, fh = prepared(path)
                    w, h = IMG_W * fw, IMG_H * fh
                    c.drawImage(img, cx + (IMG_W - w) / 2, top - IMG_H + (IMG_H - h) / 2, w, h)
                    ok = True
                except Exception:
                    pass
            if not ok:
                missing.append(pid)
                c.setFillGray(0.55)
                c.setFont("Cap", 11)
                c.drawCentredString(cx + IMG_W / 2, top - IMG_H / 2 - 4, f"#{pid}")
            # имя под картинкой, уменьшаем шрифт для длинных имён
            size = FONT_SIZE
            while size > FONT_MIN and pdfmetrics.stringWidth(name, "Cap", size) > IMG_W - 0.1 * cm:
                size -= 0.25
            c.setFillGray(0.1)
            c.setFont("Cap", size)
            c.drawCentredString(cx + IMG_W / 2, top - IMG_H - CAP_H + 0.1 * cm, name)
        c.showPage()
    c.save()
    pages = (len(rows) + per_page - 1) // per_page
    print(f"OK: {a.out}, страниц {pages}, без картинки: {missing or 'нет'}")


if __name__ == "__main__":
    main()
