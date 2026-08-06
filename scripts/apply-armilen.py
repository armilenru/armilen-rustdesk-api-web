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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RU = ROOT / "src/utils/i18n/ru.json"
OVERLAY = ROOT / "i18n/ru-armilen.json"
INDEX = ROOT / "index.html"
LOGIN = ROOT / "src/views/login/login.vue"
AUTH = ROOT / "src/utils/auth.js"
HEADER = ROOT / "src/layout/components/header.vue"
VIEWS = ROOT / "src/views"

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


UPSTREAM_PUSH = "router.push({ path: redirect || '/', replace: true })"
UPSTREAM_REDIRECT_ANCHOR = "  const redirect = route.query?.redirect\n"
ARMILEN_REDIRECT = """  const redirect = route.query?.redirect
  // Armilen: наш сайт присылает в redirect абсолютный адрес возврата
  // (https://www.armilen.ru/...), а router.push принимает его за внутренний
  // путь, не находит и роняет на /404. Внешний адрес отдаём браузеру, но
  // только на наши домены: чужой хост в query иначе превращает страницу
  // входа в открытый редирект.
  const goAfterLogin = () => {
    if (typeof redirect === 'string' && /^https?:\\/\\//i.test(redirect)) {
      try {
        const url = new URL(redirect)
        if (url.protocol === 'https:' && /(^|\\.)armilen\\.ru$/i.test(url.hostname)) {
          window.location.replace(url.href)
          return
        }
      } catch (e) {
        // адрес не разобрался, уходим на главную панели
      }
    }
    router.push({ path: redirect || '/', replace: true })
  }
"""


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


UPSTREAM_SET_TOKEN = """export function setToken (token) {
  localStorage.setItem(`wc-option:local:access_token`, token)
  return localStorage.setItem(TokenKey, token)
}

export function removeToken () {
  return localStorage.removeItem(TokenKey)
}"""
ARMILEN_SET_TOKEN = """// Armilen: SSO поверх входа в панель. Токен кладётся ещё и в куку на домен
// второго уровня, потому что им закрыты страницы за пределами desk.armilen.ru:
// /services/cms/manage-reviews и /x-project/logs на www.armilen.ru проверяют
// её сами, а /webclient и /desk-guide через forward_auth Caddy на
// server/sso-verify.ts. localStorage сюда не годится, он раздельный на каждый
// домен, и без куки страницы отбрасывают обратно на этот вход по кругу.
const ArmilenCookie = 'armilen_token'
const ArmilenCookieDomain = 'armilen.ru'
const ArmilenCookieMaxAge = 3600 * 24 * 30

export function setToken (token) {
  localStorage.setItem(`wc-option:local:access_token`, token)
  document.cookie = `${ArmilenCookie}=${encodeURIComponent(token)}; Path=/; ` +
    `Domain=${ArmilenCookieDomain}; Max-Age=${ArmilenCookieMaxAge}; Secure; SameSite=Lax`
  return localStorage.setItem(TokenKey, token)
}

export function removeToken () {
  document.cookie = `${ArmilenCookie}=; Path=/; Domain=${ArmilenCookieDomain}; Max-Age=0`
  return localStorage.removeItem(TokenKey)
}"""

APP_STORE = ROOT / "src/store/app.js"
UPSTREAM_DEFAULT_LANG = (
    "const defaultLang = localStorage.getItem('lang') || navigator.language || 'zh-CN'"
)
ARMILEN_DEFAULT_LANG = """// Armilen: панель русская по умолчанию, язык браузера на неё не влияет.
// Апстрим брал navigator.language, и это ломалось дважды. Браузер отдаёт
// региональный тег (ru-RU, en-US), которого в langs нет: словарь не находился,
// T() возвращал сам ключ, и страница входа писала Username и Password вместо
// подписей. А там, где тег совпадал, панель уходила в английский, хотя всё её
// наполнение (приветствие, заголовки, перевод) русское. Выбор человека из
// переключателя языков уважается: он лежит в localStorage и проверяется на
// принадлежность словарю, туда мог попасть тот же региональный тег.
const pickLang = (tag) => {
  if (langs[tag]) return tag
  const base = String(tag || '').split('-')[0]
  if (langs[base]) return base
  if (base === 'zh') return 'zh-CN'
  return 'ru'
}
const defaultLang = pickLang(localStorage.getItem('lang') || 'ru')"""

UPSTREAM_LOGIN_LOGO = 'src="@/assets/logo.png"'
ARMILEN_LOGIN_LOGO = 'src="@/assets/logo-light.png"'
UPSTREAM_HEADER_LOGO = '    <img :src="setting.logo" alt="" class="logo">\n'


def apply_logo() -> int:
    """Логотип в шапке панели и на странице входа.

    Апстрим импортирует его как модуль (`import logo from '@/assets/logo.png'`
    в store/app.js, плюс прямая ссылка в login.vue), то есть логотип это файл
    сборки, а не настройка сервера: подменить его на VPS нечем, только здесь.
    Глиф тот же, что у сайта, из public/favicon.svg, с прозрачным фоном.

    Логотип стоит только на странице входа. В шапке панели он убран: рядом с
    ним там название продукта тем же смыслом, а глиф в 30px на светлой полосе
    работал плашкой, а не знаком.

    Начертание для входа отдельное, светлое: карточка входа тёмная. Одна
    картинка на две подложки не работает, а медиазапрос внутри SVG отвечал бы
    на тему системы, а не на цвет подложки.
    """
    changed = 0
    src, dst = ROOT / "branding/logo-light.png", ROOT / "src/assets/logo-light.png"
    if not src.exists():
        print(f"ОШИБКА: нет {src}", file=sys.stderr)
        raise SystemExit(1)
    if not dst.exists() or dst.read_bytes() != src.read_bytes():
        dst.write_bytes(src.read_bytes())
        changed += 1

    login = LOGIN.read_text(encoding="utf-8")
    if ARMILEN_LOGIN_LOGO not in login:
        if UPSTREAM_LOGIN_LOGO not in login:
            print(f"ОШИБКА: в login.vue нет {UPSTREAM_LOGIN_LOGO}, апстрим изменил "
                  f"разметку, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)
        LOGIN.write_text(login.replace(UPSTREAM_LOGIN_LOGO, ARMILEN_LOGIN_LOGO),
                         encoding="utf-8")
        changed += 1

    header = HEADER.read_text(encoding="utf-8")
    if UPSTREAM_HEADER_LOGO in header:
        HEADER.write_text(header.replace(UPSTREAM_HEADER_LOGO, ""), encoding="utf-8")
        changed += 1
    elif "setting.logo" in header:
        print("ОШИБКА: в header.vue логотип есть, но разметка не та, апстрим её "
              "изменил, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)

    print(f"логотип: {changed} изменени(й)" if changed else "логотип: уже наш")
    return changed


def apply_default_lang() -> int:
    """Русский язык панели без зависимости от региона в navigator.language."""
    src = APP_STORE.read_text(encoding="utf-8")
    if "pickLang" in src:
        print("язык по умолчанию: уже наш")
        return 0
    if UPSTREAM_DEFAULT_LANG not in src:
        print("ОШИБКА: в store/app.js нет ожидаемой строки defaultLang, апстрим "
              "изменил код, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)
    APP_STORE.write_text(src.replace(UPSTREAM_DEFAULT_LANG, ARMILEN_DEFAULT_LANG),
                         encoding="utf-8")
    print("язык по умолчанию: русский")
    return 1


def apply_sso_cookie() -> int:
    """Кука armilen_token на домен второго уровня при входе в панель.

    Это была правка прежнего форка, и при переходе на тонкий форк она молча
    потерялась: в новых сборках admin-1…admin-6 куку не ставит никто. Внешне
    это выглядит как «вход проходит, а внутрь не пускает»: страница проверяет
    куку, не находит и отправляет обратно на вход, по кругу.
    """
    src = AUTH.read_text(encoding="utf-8")
    if "ArmilenCookie" in src:
        print("SSO-кука: уже наша")
        return 0
    if UPSTREAM_SET_TOKEN not in src:
        print("ОШИБКА: в utils/auth.js нет ожидаемых setToken/removeToken, "
              "апстрим изменил код, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)
    AUTH.write_text(src.replace(UPSTREAM_SET_TOKEN, ARMILEN_SET_TOKEN), encoding="utf-8")
    print("SSO-кука: добавлена")
    return 1


def apply_login_redirect() -> int:
    """Возврат на сайт после входа вместо падения на /404.

    Страницы `/services/cms/manage-reviews` и `/x-project/logs` уводят на
    `#/login?redirect=<полный адрес>`, потому что вход в панель служит им
    единственной проверкой прав. Апстримный router.push такой адрес не
    разбирает и уходит в catchAll.
    """
    src = LOGIN.read_text(encoding="utf-8")
    if "goAfterLogin" in src:
        print("возврат после входа: уже наш")
        return 0

    pushes = src.count(UPSTREAM_PUSH)
    if pushes != 2:
        print(f"ОШИБКА: в login.vue найдено {pushes} вызовов «{UPSTREAM_PUSH}» "
              f"вместо двух, апстрим изменил код, скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)
    if UPSTREAM_REDIRECT_ANCHOR not in src:
        print("ОШИБКА: в login.vue нет объявления redirect, апстрим изменил код, "
              "скрипт надо обновить", file=sys.stderr)
        raise SystemExit(1)

    # Сначала подменяем вызовы, потом вставляем помощник: он сам содержит
    # строку router.push, и обратный порядок переписал бы её внутри него
    src = src.replace(UPSTREAM_PUSH, "goAfterLogin()")
    src = src.replace(UPSTREAM_REDIRECT_ANCHOR, ARMILEN_REDIRECT, 1)
    LOGIN.write_text(src, encoding="utf-8")
    print("возврат после входа: заменён")
    return 1


LABEL_WIDTH_RE = re.compile(r'label-width="\d+px"')


def apply_form_labels() -> int:
    """Подписи полей по содержимому, а не по фиксированной ширине.

    Апстрим задаёт `label-width` числом под китайские подписи в два-три
    иероглифа. Русская «Имя пользователя» в 120px не влезает и ломается
    переносом посреди слова. `auto` это штатный режим Element Plus: он берёт
    самую широкую подпись формы и равняет колонку по ней.

    Полноширинное двоеточие `：` из китайской типографики после кириллицы
    даёт лишний пробел перед значением, поэтому заодно меняется на обычное.
    """
    changed = 0
    for path in sorted(VIEWS.rglob("*.vue")):
        text = path.read_text(encoding="utf-8")
        patched = LABEL_WIDTH_RE.sub('label-width="auto"', text)
        patched = patched.replace('label-suffix="："', 'label-suffix=":"')
        if patched != text:
            path.write_text(patched, encoding="utf-8")
            changed += 1
    print(f"подписи форм: {changed} файл(ов) обновлено")
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
             + apply_favicons() + apply_logo() + apply_default_lang()
             + apply_sso_cookie()
             + apply_login_redirect() + apply_form_labels()
             + apply_settings_headers())
    print("правки Armilen наложены" if total else "правки Armilen уже на месте")
