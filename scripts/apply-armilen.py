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

UPSTREAM_ICON = '<link rel="icon" href="/favicon.ico" />'
# Одна icon-ссылка и живая фавиконка ровно как на сайте (см. Layout.astro):
# в неактивной вкладке курсор _ гаснет в цвет символа >. Путь берём из самой
# ссылки, потому что Vite переписывает его на относительный при сборке.
ARMILEN_ICON = """<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <script>
      (function () {
        var link = document.querySelector('link[rel="icon"]');
        var active = link.getAttribute("href");
        var idle = active.replace("favicon.svg", "favicon-hidden.svg");
        document.addEventListener("visibilitychange", function () {
          link.setAttribute("href", document.hidden ? idle : active);
        });
      })();
    </script>"""


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


def apply_favicon_link() -> int:
    """Переводит ссылку на иконку с апстримного .ico на наш .svg.

    Раньше это делал sed в deploy-rustdesk-brand.sh на сервере, и каждое
    обновление панели откатывало правку до следующего прогона брендинга.
    Место правки одно: артефакт релиза, из которого панель и ставится.
    Апстримный favicon.ico остаётся в сборке, но уже наш: браузеры без
    поддержки SVG-иконок запрашивают его по конвенции, без ссылки.
    """
    html = INDEX.read_text(encoding="utf-8")
    if 'href="/favicon.svg"' in html:
        print("ссылка на иконку: уже наша")
        return 0
    if UPSTREAM_ICON not in html:
        print(f"ОШИБКА: в index.html нет {UPSTREAM_ICON}, апстрим изменил "
              f"разметку, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)
    INDEX.write_text(html.replace(UPSTREAM_ICON, ARMILEN_ICON), encoding="utf-8")
    print("ссылка на иконку: заменена")
    return 1


def apply_favicons() -> int:
    src = ROOT / "branding"
    dst = ROOT / "public"
    changed = 0
    for name in ("favicon.svg", "favicon-hidden.svg", "favicon.ico"):
        s, d = src / name, dst / name
        if not s.exists():
            print(f"ОШИБКА: нет {s}", file=sys.stderr)
            raise SystemExit(1)
        if not d.exists() or d.read_bytes() != s.read_bytes():
            d.write_bytes(s.read_bytes())
            changed += 1
    print(f"фавиконки: {changed} файл(ов) обновлено")
    return changed


# Страницы серверных настроек: апстрим показывает в заголовке сырое имя опции
# (ALWAYS_USE_RELAY), а человеку нужно название и объяснение, что опция делает.
# Прежний форк правил ровно эти пять карточек, и без них панель теряет
# пояснения, которые у вас уже были.
SETTINGS_CARDS = {
    "always_use_relay": "ALWAYS_USE_RELAY",
    "blacklist": "BLACK_LIST",
    "blocklist": "BLOCK_LIST",
    "must_login": "MUST_LOGIN",
    "relay_servers": "RELAY_SERVERS",
}


def apply_settings_headers() -> int:
    changed = 0
    for filename, raw_name in SETTINGS_CARDS.items():
        path = ROOT / "src/views/rustdesk" / f"{filename}.vue"
        html = path.read_text(encoding="utf-8")
        key = "".join(part.capitalize() for part in filename.split("_"))

        if f"T('{key}Title')" in html:
            continue
        if f"<span>{raw_name}</span>" not in html:
            print(f"ОШИБКА: в {path.name} нет <span>{raw_name}</span>, апстрим изменил "
                  f"разметку, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)

        html = html.replace(
            f"<span>{raw_name}</span>",
            f"<span>{{{{ T('{key}Title') }}}}</span>",
        ).replace(
            "    <el-form :disabled=\"!canSend\">",
            f"    <p class=\"armilen-card-desc\">{{{{ T('{key}Desc') }}}}</p>\n"
            "    <el-form :disabled=\"!canSend\">",
            1,
        )
        path.write_text(html, encoding="utf-8")
        changed += 1

    print(f"заголовки настроек: {changed} карточ(ек) обновлено из {len(SETTINGS_CARDS)}")
    return changed


if __name__ == "__main__":
    total = (apply_translations() + apply_title() + apply_favicon_link()
             + apply_favicons() + apply_settings_headers())
    print("правки Armilen наложены" if total else "правки Armilen уже на месте")
