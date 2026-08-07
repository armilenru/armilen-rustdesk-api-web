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
REGISTER = ROOT / "src/views/register/index.vue"
# Вход и регистрация это одна оболочка: одинаковые классы, одинаковый логотип,
# одинаковая пара литералов в фоне. Разные у них только поля формы
AUTH_PAGES = (LOGIN, REGISTER)
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
MAIN = ROOT / "src/main.js"

UPSTREAM_MAIN_ANCHOR = "import '@/styles/style.scss'\n"
# Наш файл идёт ПОСЛЕ style.scss и после dark/css-vars.css апстрима: он
# переопределяет их токены, а не соревнуется с ними за порядок.
ARMILEN_MAIN = "import '@/styles/style.scss'\nimport '@/styles/armilen.css'\n"

# Тема выбирается ДО отрисовки, инлайн-скриптом в <head>. Через Vue это дало бы
# вспышку светлой темы на каждой загрузке: приложение монтируется позже первого
# кадра. Класс `dark` на <html> понимают и Element Plus, и наш armilen.css.
#
# Ключ хранения НЕ наш: панель переключает тему через useDark() из @vueuse/core
# (src/layout/components/setting/index.vue), а он помнит выбор в
# `vueuse-color-scheme` и понимает три значения, dark, light и auto. Пока
# бутстрап держал собственный ключ `armilen-theme`, про одну и ту же тему
# существовало два независимых мнения, и они спорили на каждой загрузке.
# Единственный источник правды теперь панельный, бутстрап только читает его
# раньше, чем успевает смонтироваться Vue.
#
# Второй кусок гасит переходы на кадр переключения. У компонентов Element Plus
# свои длительности перехода на фоне и рамках, и при смене темы каждый блок
# доезжал до нового цвета в своём темпе: это и читалось как моргание вразнобой.
# Наблюдатель ловит смену класса кем угодно, и панельным переключателем, и нашим
# на странице входа, поэтому лечит оба случая одним правилом.
THEME_BOOTSTRAP = """
    <script>
      (function () {
        var KEY = "vueuse-color-scheme";
        var root = document.documentElement;

        function prefersDark() {
          return window.matchMedia("(prefers-color-scheme: dark)").matches;
        }
        function isDark(saved) {
          if (saved === "dark") return true;
          if (saved === "light") return false;
          return prefersDark();
        }
        function apply(saved) {
          root.classList.toggle("dark", isDark(saved));
        }

        var saved = null;
        try { saved = localStorage.getItem(KEY); } catch (e) {}
        apply(saved);

        window.armilenToggleTheme = function () {
          var next = root.classList.contains("dark") ? "light" : "dark";
          root.classList.toggle("dark", next === "dark");
          try {
            localStorage.setItem(KEY, next);
            // Свою же запись localStorage в этой вкладке не видит никто: событие
            // storage адресовано соседним вкладкам. Поэтому шлём его руками,
            // иначе useDark() останется при старом мнении до перезагрузки.
            window.dispatchEvent(new StorageEvent("storage", {
              key: KEY, newValue: next, storageArea: localStorage
            }));
          } catch (e) {}
        };

        var pending = null;
        new MutationObserver(function () {
          if (pending) return;
          var style = document.createElement("style");
          style.textContent = "*,*::before,*::after{transition:none!important}";
          document.head.appendChild(style);
          pending = requestAnimationFrame(function () {
            requestAnimationFrame(function () {
              style.remove();
              pending = null;
            });
          });
        }).observe(root, { attributes: true, attributeFilter: ["class"] });
      })();
    </script>"""

THEME_TOGGLE_BUTTON = (
    '<button type="button" class="armilen-theme-toggle" onclick="armilenToggleTheme()"'
    ' aria-label="Переключить тему" title="Переключить тему">'
    '<svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none"'
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
    '<svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none"'
    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41'
    'M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'
    "</svg></button>"
)

# В шапке панели своего переключателя мы не ставим: там уже стоит родной,
# el-switch на useDark() в setting/index.vue. Две иконки смены темы рядом это
# не украшение, а вопрос «которая из них настоящая». Наша кнопка живёт только
# на странице входа, куда шапка панели ещё не смонтирована.

UPSTREAM_LOGIN_CARD = '    <div class="login-card">\n'
ARMILEN_LOGIN_CARD = f'    <div class="login-card">\n      {THEME_TOGGLE_BUTTON}\n'

# Оформление страницы входа апстрим задаёт литералами прямо в scoped-стилях:
# тёмно-синий фон, белые подписи, радиус 4px. Тема панели их не перебивает,
# scoped-селектор специфичнее. Поэтому литералы заменяются на токены точечно,
# каждый со своим якорем: так правка переживает мелкие изменения апстрима и
# честно падает при крупных.
#
# Первые два якоря вынесены отдельно, потому что страница регистрации это та же
# оболочка: те же классы `.login-container` и `.login-card`, те же два литерала,
# но собственные scoped-стили. Общее держится в одном месте, иначе достаточно
# поправить палитру входа и забыть про регистрацию, что уже и произошло.
AUTH_SHELL_PATCHES = [
    (
        "  height: 100vh;\n  background-color: #2d3a4b;\n",
        "  min-height: 100vh;\n  background-color: var(--armilen-surface-page);\n",
    ),
    (
        "  background-color: #283342;\n  padding: 40px;\n  border-radius: 8px;\n"
        "  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);\n",
        "  background-color: var(--armilen-surface-card);\n  padding: 40px;\n"
        "  border: 1px solid var(--armilen-border);\n  border-radius: 1rem;\n"
        "  box-shadow: var(--armilen-shadow);\n",
    ),
]

LOGIN_STYLE_PATCHES = AUTH_SHELL_PATCHES + [
    (
        "  background-color: white;\n  border: 1px solid #ddd;\n  border-radius: 4px;\n"
        "  color: black;\n",
        "  background-color: var(--armilen-surface-inset);\n"
        "  border: 1px solid var(--armilen-border);\n"
        "  border-radius: var(--el-border-radius-base);\n"
        "  color: var(--armilen-text-heading);\n",
    ),
    (
        "  font-size: 14px;\n  color: #888;\n",
        "  font-size: 14px;\n  color: var(--armilen-text-muted);\n",
    ),
    (
        "    background-color: #ddd;\n",
        "    background-color: var(--armilen-border);\n",
    ),
    (
        "  ::v-deep(.el-form-item__label) {\n    color: #fff;\n  }\n",
        "  ::v-deep(.el-form-item__label) {\n"
        "    color: var(--armilen-text-secondary);\n  }\n",
    ),
    (
        "      border: 1px solid rgba(255, 255, 255, 0.1);\n      background: transparent;\n",
        "      background-color: var(--armilen-surface-inset);\n"
        "      box-shadow: 0 0 0 1px var(--armilen-border) inset;\n",
    ),
    (
        "    ::v-deep(input) {\n      color: #fff;\n    }\n",
        "    ::v-deep(input) {\n      color: var(--armilen-text-heading);\n    }\n",
    ),
]
# Страницы подтверждения OAuth: вход клиента RustDesk в адресную книгу
# (`#/oauth/:code`) и привязка стороннего аккаунта в панели
# (`#/oauth/bind/:code`). Обе достаются человеку из клиента или из профиля,
# минуя шапку панели, и обе апстрим красит тем же тёмно-синим литералом, что и
# прежнюю страницу входа.
#
# Список один на оба файла, потому что scoped-стили у них побайтово совпадают.
# Разойдутся в апстриме, скрипт упадёт на первом же якоре и назовёт файл.
OAUTH_PAGES = (ROOT / "src/views/oauth/login.vue", ROOT / "src/views/oauth/bind.vue")

UPSTREAM_OAUTH_CARD = '    <el-card class="card">\n'
ARMILEN_OAUTH_CARD = f'    <el-card class="card">\n      {THEME_TOGGLE_BUTTON}\n'

OAUTH_STYLE_PATCHES = [
    # `width: 100vw` шире области просмотра ровно на ширину вертикальной полосы
    # прокрутки, и страница получала горизонтальную прокрутку на пустом месте.
    # `height` заменён на `min-height` по той же причине, что и на входе:
    # карточка не должна обрезаться, когда содержимое выше экрана.
    (
        "  width: 100vw;\n  height: 100vh;\n  background-color: #2d3a4b;\n",
        "  width: 100%;\n  min-height: 100vh;\n"
        "  background-color: var(--armilen-surface-page);\n",
    ),
    # Карточка апстрима тёмная всегда и без рамки: на светлой теме она читалась
    # чужеродным пятном. Радиус и тень взяты те же, что у карточки входа.
    (
        "    max-width: 500px;\n    background-color: #283342;\n    color: #fff;\n"
        "    border: none;\n",
        "    max-width: 500px;\n"
        "    background-color: var(--armilen-surface-card);\n"
        "    color: var(--armilen-text-heading);\n"
        "    border: 1px solid var(--armilen-border);\n"
        "    border-radius: 1rem;\n"
        "    box-shadow: var(--armilen-shadow);\n",
    ),
    (
        "      ::v-deep(.el-form-item__label) {\n        color: #fff;\n      }\n",
        "      ::v-deep(.el-form-item__label) {\n"
        "        color: var(--armilen-text-secondary);\n      }\n",
    ),
]

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

UPSTREAM_LOGIN_LOGO = '<img src="@/assets/logo.png" alt="logo" class="login-logo"/>'
# Две картинки вместо одной: карточка входа светлая в светлой теме и тёмная в
# тёмной, а PNG не умеет отвечать на подложку. Показ переключает CSS по классу
# `dark` на <html>, тем же признаком, что и вся тема
ARMILEN_LOGIN_LOGO = (
    '<img src="@/assets/logo.png" alt="Armilen" class="login-logo logo-day"/>\n'
    '      <img src="@/assets/logo-light.png" alt="" aria-hidden="true"'
    ' class="login-logo logo-night"/>'
)

# Менеджер паролей должен узнавать форму входа. Апстрим ставит полю имени
# `type="username"`, а такого типа в HTML нет: браузер отдаёт обычный text без
# единой подсказки, и Bitwarden предлагал вход только в поле пароля. Тип и
# autocomplete это ровно те два признака, по которым форму опознают.
LOGIN_AUTOCOMPLETE = [
    (
        '<el-input v-model="form.username" type="username" class="login-input"></el-input>',
        '<el-input v-model="form.username" type="text" autocomplete="username"\n'
        '                    name="username" class="login-input"></el-input>',
    ),
    (
        '<el-input v-model="form.password" type="password" @keyup.enter.native="login" show-password\n'
        '                    class="login-input"></el-input>',
        '<el-input v-model="form.password" type="password" @keyup.enter.native="login" show-password\n'
        '                    autocomplete="current-password" name="password"\n'
        '                    class="login-input"></el-input>',
    ),
    # Капча оставалась единственным полем формы без токена, и это ровно тот
    # случай, ради которого токены и ставят: короткое текстовое поле рядом с
    # паролем менеджер вправе принять за второй пароль или за поле кода.
    # `off` говорит прямо, что подставлять сюда нечего, значение живёт одну
    # попытку входа.
    (
        '<el-input v-model="form.captcha" @keyup.enter.native="login"  class="login-input captcha-input">',
        '<el-input v-model="form.captcha" @keyup.enter.native="login"\n'
        '                    autocomplete="off" name="captcha"\n'
        '                    class="login-input captcha-input">',
    ),
]
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
    for name in ("logo.png", "logo-light.png"):
        src, dst = ROOT / "branding" / name, ROOT / "src/assets" / name
        if not src.exists():
            print(f"ОШИБКА: нет {src}", file=sys.stderr)
            raise SystemExit(1)
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            dst.write_bytes(src.read_bytes())
            changed += 1

    # Регистрация несёт тот же логотип и ту же карточку, что и вход, поэтому
    # пара «тёмный на светлой, светлый на тёмной» нужна ей ровно так же:
    # одиночный тёмный глиф на тёмной карточке пропадает целиком
    for path in AUTH_PAGES:
        src = path.read_text(encoding="utf-8")
        if ARMILEN_LOGIN_LOGO in src:
            continue
        if UPSTREAM_LOGIN_LOGO not in src:
            print(f"ОШИБКА: в {path.name} нет {UPSTREAM_LOGIN_LOGO}, апстрим "
                  f"изменил разметку, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)
        path.write_text(src.replace(UPSTREAM_LOGIN_LOGO, ARMILEN_LOGIN_LOGO),
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


def apply_theme() -> int:
    """Фирменная тема панели: палитра, шрифт, скругления и переключение тем.

    Перекрашиваются токены Element Plus, а не исходники компонентов: так вся
    панель меняет вид одним файлом, и расхождение с апстримом не растёт.
    """
    changed = 0

    src_dir = ROOT / "branding"
    styles = ROOT / "src/styles"
    fonts_dst = styles / "fonts"
    fonts_dst.mkdir(parents=True, exist_ok=True)

    for name in ("armilen.css",):
        s, d = src_dir / name, styles / name
        if not s.exists():
            print(f"ОШИБКА: нет {s}", file=sys.stderr)
            raise SystemExit(1)
        if not d.exists() or d.read_bytes() != s.read_bytes():
            d.write_bytes(s.read_bytes())
            changed += 1

    for font in sorted((src_dir / "fonts").glob("*.woff2")):
        d = fonts_dst / font.name
        if not d.exists() or d.read_bytes() != font.read_bytes():
            d.write_bytes(font.read_bytes())
            changed += 1

    main = MAIN.read_text(encoding="utf-8")
    if "armilen.css" not in main:
        if UPSTREAM_MAIN_ANCHOR not in main:
            print("ОШИБКА: в main.js нет импорта style.scss, апстрим изменил "
                  "порядок импортов, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)
        MAIN.write_text(main.replace(UPSTREAM_MAIN_ANCHOR, ARMILEN_MAIN, 1), encoding="utf-8")
        changed += 1

    html = INDEX.read_text(encoding="utf-8")
    if "armilenToggleTheme" not in html:
        if "</head>" not in html:
            print("ОШИБКА: в index.html нет </head>", file=sys.stderr)
            raise SystemExit(1)
        INDEX.write_text(html.replace("</head>", THEME_BOOTSTRAP + "\n  </head>", 1),
                         encoding="utf-8")
        changed += 1

    # Прошлые версии скрипта вставляли нашу кнопку в шапку. Если правка уже
    # лежит в рабочем дереве, снимаем её: иначе в панели остаются два
    # переключателя темы, наш и родной el-switch.
    header = HEADER.read_text(encoding="utf-8")
    if "armilen-theme-toggle" in header:
        HEADER.write_text(header.replace(f"  {THEME_TOGGLE_BUTTON}\n", "", 1), encoding="utf-8")
        changed += 1

    # Вход и регистрация правятся одинаково, различаются только списком якорей:
    # у входа есть поля, капча и подписи, у регистрации только оболочка
    for path in AUTH_PAGES:
        src = path.read_text(encoding="utf-8")
        patches = LOGIN_STYLE_PATCHES if path == LOGIN else AUTH_SHELL_PATCHES

        if "armilen-theme-toggle" not in src:
            if UPSTREAM_LOGIN_CARD not in src:
                print(f"ОШИБКА: в {path.name} нет карточки входа, апстрим изменил "
                      f"разметку, скрипт надо обновить", file=sys.stderr)
                raise SystemExit(1)
            src = src.replace(UPSTREAM_LOGIN_CARD, ARMILEN_LOGIN_CARD, 1)
            changed += 1

        if "--armilen-surface-page" not in src:
            for old, new in patches:
                if old not in src:
                    print(f"ОШИБКА: в стилях {path.name} нет фрагмента "
                          f"{old.strip()[:48]!r}, апстрим их изменил, скрипт надо "
                          f"обновить", file=sys.stderr)
                    raise SystemExit(1)
                src = src.replace(old, new, 1)
                changed += 1

        path.write_text(src, encoding="utf-8")

    print(f"фирменная тема: {changed} изменени(й)" if changed else "фирменная тема: уже наша")
    return changed


def apply_oauth_pages() -> int:
    """Страницы подтверждения OAuth в фирменной теме, с переключателем.

    Эти две страницы человек видит, не заходя в панель: одну открывает клиент
    RustDesk при входе в адресную книгу, вторую профиль при привязке аккаунта.
    Шапки панели с родным переключателем темы там нет, поэтому кнопка нужна
    своя, как на странице входа, иначе сменить тему негде вовсе.

    Проверка «уже наше» идёт по токену в стилях, а не по факту вставки кнопки:
    кнопка и стили правятся вместе, и половинчатое состояние означало бы, что
    апстрим сдвинул один из якорей, а это должно падать, а не молча чиниться.
    """
    changed = 0

    for path in OAUTH_PAGES:
        src = path.read_text(encoding="utf-8")
        if "--armilen-surface-page" in src:
            continue

        if UPSTREAM_OAUTH_CARD not in src:
            print(f"ОШИБКА: в {path.name} нет карточки OAuth, апстрим изменил "
                  f"разметку, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)
        src = src.replace(UPSTREAM_OAUTH_CARD, ARMILEN_OAUTH_CARD, 1)
        changed += 1

        for old, new in OAUTH_STYLE_PATCHES:
            if old not in src:
                print(f"ОШИБКА: в стилях {path.name} нет фрагмента "
                      f"{old.strip()[:48]!r}, апстрим их изменил, скрипт надо "
                      f"обновить", file=sys.stderr)
                raise SystemExit(1)
            src = src.replace(old, new, 1)
            changed += 1

        path.write_text(src, encoding="utf-8")

    print(f"страницы OAuth: {changed} изменени(й)" if changed else "страницы OAuth: уже наши")
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


def apply_login_autocomplete() -> int:
    """Признаки формы входа для менеджеров паролей."""
    src = LOGIN.read_text(encoding="utf-8")
    if 'autocomplete="username"' in src:
        print("автозаполнение входа: уже наше")
        return 0
    changed = 0
    for old, new in LOGIN_AUTOCOMPLETE:
        if old not in src:
            print("ОШИБКА: в login.vue нет ожидаемого поля формы входа, апстрим "
                  "изменил разметку, скрипт надо обновить", file=sys.stderr)
            raise SystemExit(1)
        src = src.replace(old, new, 1)
        changed += 1
    LOGIN.write_text(src, encoding="utf-8")
    print(f"автозаполнение входа: {changed} пол(я) размечено")
    return changed


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
             + apply_favicons() + apply_logo() + apply_theme() + apply_oauth_pages()
             + apply_default_lang()
             + apply_login_autocomplete() + apply_sso_cookie()
             + apply_login_redirect() + apply_form_labels()
             + apply_settings_headers())
    print("правки Armilen наложены" if total else "правки Armilen уже на месте")
