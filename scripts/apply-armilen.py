#!/usr/bin/env python3
"""
Накладывает правки Armilen на апстримную админку rustdesk-api-web.

Тот же принцип, что у apply-branding в форке клиента: не расходящаяся копия
исходников, а идемпотентный скрипт правок поверх апстрима. Синхронизация с
апстримом от этого не болит, а объём расхождения виден одним файлом.

Правки двух видов:
  * перевод: 61 ключ, которого в апстримном ru.json нет, и 3 намеренные
    переформулировки. Значения лежат в i18n/ru-armilen.json
  * брендинг: фавиконки и заголовок вкладки

Запуск идемпотентен: повторный прогон ничего не меняет и выходит с нулём.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RU = ROOT / "src/utils/i18n/ru.json"
OVERLAY = ROOT / "i18n/ru-armilen.json"
INDEX = ROOT / "index.html"

TITLE = "Armilen"
UPSTREAM_TITLE = "Rustdesk API Admin"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_translations() -> int:
    ru = load(RU)
    overlay = load(OVERLAY)

    changed = 0
    for key, text in overlay.items():
        # Апстрим хранит значение как объект плюрализации {"One": "..."},
        # поэтому подставляем в ту же форму, а не голой строкой
        want = {"One": text}
        if ru.get(key) != want:
            ru[key] = want
            changed += 1

    if changed:
        RU.write_text(json.dumps(ru, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(f"перевод: {changed} ключ(ей) обновлено из {len(overlay)}")
    return changed


def apply_title() -> int:
    html = INDEX.read_text(encoding="utf-8")
    if f"<title>{TITLE}</title>" in html:
        print("заголовок: уже наш")
        return 0
    if f"<title>{UPSTREAM_TITLE}</title>" not in html:
        print(f"ОШИБКА: в index.html нет <title>{UPSTREAM_TITLE}</title>, "
              f"апстрим изменил разметку, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)
    INDEX.write_text(html.replace(f"<title>{UPSTREAM_TITLE}</title>", f"<title>{TITLE}</title>"),
                     encoding="utf-8")
    print("заголовок: заменён")
    return 1


def apply_favicons() -> int:
    src = ROOT / "branding"
    dst = ROOT / "public"
    changed = 0
    for name in ("favicon.svg", "favicon-hidden.svg"):
        s, d = src / name, dst / name
        if not s.exists():
            print(f"ОШИБКА: нет {s}", file=sys.stderr)
            raise SystemExit(1)
        if not d.exists() or d.read_bytes() != s.read_bytes():
            d.write_bytes(s.read_bytes())
            changed += 1
    print(f"фавиконки: {changed} файл(ов) обновлено")
    return changed


if __name__ == "__main__":
    total = apply_translations() + apply_title() + apply_favicons()
    print("правки Armilen наложены" if total else "правки Armilen уже на месте")
