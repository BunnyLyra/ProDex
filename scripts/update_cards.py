#!/usr/bin/env python3
"""Собирает dist/cards.json для сайта из двух источников.

  --base   cards.json из flibustier/pokemon-tcg-pocket-database (список карт, картинки, паки, редкость)
  --decks  data/v5/cards.json из PocketDecks/pokemon-tcg-pocket-cards (тип, стихия, HP, атаки ...)
  --prev   текущий dist/cards.json (нужен для защитных проверок и чтобы сохранить goodWith)
  --out    куда записать результат

Если проверки не прошли, скрипт завершается с кодом 1 и НИЧЕГО не записывает.
Источник данных PocketDecks v5: лицензия AGPL-3.0-or-later (указывать на сайте).
"""
import argparse, collections, json, os, sys

MIN_TYPED_SHARE = 0.97   # столько карт должно получить тип, иначе считаем, что источник сломан


def load_list(path):
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict):
        d = next((v for v in d.values() if isinstance(v, list)), [])
    if not isinstance(d, list):
        raise SystemExit(f"{path}: ожидался список карт")
    return d


def decks_code(set_name):
    """A1 -> a1, PROMO-A -> pa, PROMO-B -> pb ... (так названы сеты в PocketDecks)"""
    s = str(set_name).lower()
    if s.startswith("promo-") and len(s) == 7:
        return "p" + s[-1]
    return s


def norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def convert(src):
    """Поля PocketDecks -> формат сайта."""
    t = src.get("type")
    out = {"type": "pokemon" if t == "Pokémon" else (src.get("subtype") or "trainer").lower()}
    if t == "Pokémon":
        out["element"] = (src.get("subtype") or "").lower() or None
        if src.get("subtype_2"):
            out["element2"] = src["subtype_2"].lower()
        out["stage"] = {"Basic": "basic", "Stage 1": 1, "Stage 2": 2}.get(src.get("stage"), src.get("stage"))
        out["health"] = src.get("health")
        out["retreatCost"] = src.get("retreat")
        out["weakness"] = src.get("weakness")
        if src.get("evolves_from"):
            out["evolvesFrom"] = src["evolves_from"]
        ab = src.get("ability") or {}
        if ab.get("exists"):
            out["ability"] = {"name": ab.get("name"), "effect": ab.get("effect")}
        atk = [{"cost": a.get("cost"), "name": a.get("name"), "damage": a.get("damage"), "effect": a.get("effect")}
               for a in (src.get("attacks") or {}).values() if a.get("name")]
        if atk:
            out["attacks"] = atk
    if src.get("card_text"):
        out["text"] = src["card_text"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--decks", required=True)
    ap.add_argument("--prev")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    base, decks = load_list(a.base), load_list(a.decks)
    prev = load_list(a.prev) if a.prev and os.path.exists(a.prev) else []
    prev_map = {(x["set"], x["number"]): x for x in prev}
    by_id = {d["id"]: d for d in decks}
    by_name = collections.defaultdict(list)
    for d in decks:
        by_name[norm(d["name"])].append(d)
    decks_sets = {d["set_code"] for d in decks}

    how = collections.Counter()
    no_type, new_cards, result = [], [], []
    for c in base:
        sid = f'{decks_code(c["set"])}-{int(c["number"]):03d}'
        src, kind = by_id.get(sid), "id"
        if src is None and decks_code(c["set"]) not in decks_sets:
            # по имени ищем ТОЛЬКО для наборов, которых в PocketDecks нет совсем (например SP1).
            # Для остальных карт отсутствие записи значит «данные ещё не вышли», а не «угадай по имени».
            cand = by_name.get(norm(c["name"]), [])
            if cand and len({(x["type"], x["subtype"]) for x in cand}) == 1:
                src, kind = cand[0], "name"          # например SP1 (в PocketDecks такого набора нет)
        n = dict(c)
        if src is not None:
            n.update(convert(src))
            how[kind] += 1
        else:
            how["none"] += 1
            no_type.append(f'{c["set"]} {c["number"]} {c["name"]}')
        old = prev_map.get((c["set"], c["number"]))
        if old and old.get("goodWith"):
            n["goodWith"] = old["goodWith"]
        if prev and (c["set"], c["number"]) not in prev_map:
            new_cards.append(f'{c["set"]} {c["number"]} {c["name"]}')
        result.append(n)

    # --- защитные проверки: при любой проблеме ничего не пишем
    problems = []
    if not base:
        problems.append("основной cards.json пуст")
    if prev and len(result) < len(prev):
        problems.append(f"карт стало меньше: было {len(prev)}, стало {len(result)}")
    # доля карт с типом считается только по наборам, которые в PocketDecks есть:
    # целиком новый набор, которого там ещё нет, не должен блокировать обновление
    known = [c for c in base if decks_code(c["set"]) in decks_sets]
    typed_known = sum(1 for c in known if f'{decks_code(c["set"])}-{int(c["number"]):03d}' in by_id)
    if known and typed_known / len(known) < MIN_TYPED_SHARE:
        problems.append(f"в известных наборах тип нашёлся только у {typed_known} из {len(known)} карт (меньше {MIN_TYPED_SHARE:.0%})")
    if any(("set" not in x or "number" not in x or "name" not in x) for x in base):
        problems.append("в основном файле у карт нет set/number/name")

    # изменения относительно прошлой версии
    changed = []
    for n in result:
        old = prev_map.get((n["set"], n["number"]))
        if old and old.get("element") and n.get("element") and old["element"] != n["element"]:
            changed.append(f'{n["set"]} {n["number"]} {n["name"]}: {old["element"]} -> {n["element"]}')

    lines = [
        f"Карт в основе (flibustier): {len(base)}, в PocketDecks: {len(decks)}",
        f"Тип найден по номеру: {how['id']}, по имени: {how['name']}, не найден: {how['none']}",
        f"Новых карт по сравнению с прошлой версией: {len(new_cards)}" + (" -> " + "; ".join(new_cards[:15]) if new_cards else ""),
        f"Без типа ({len(no_type)}): " + ("; ".join(no_type[:20]) + (" ..." if len(no_type) > 20 else "") if no_type else "нет"),
        f"Изменилась стихия у {len(changed)} карт" + (": " + "; ".join(changed[:15]) if changed else ""),
    ]
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Сборка cards.json\n" + "\n".join("- " + l for l in lines) + "\n")

    if problems:
        print("\nОШИБКА, файл не записан:\n- " + "\n- ".join(problems), file=sys.stderr)
        sys.exit(1)

    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if os.path.exists(a.out) and open(a.out, encoding="utf-8").read() == text:
        print("\nФайл не изменился.")
        return
    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, a.out)
    print(f"\nЗаписано: {a.out} ({len(result)} карт)")


if __name__ == "__main__":
    main()
