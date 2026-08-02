# RustDesk API Web
# 基于 Vue3 + Element Plus 的后台, 适用于 [RustDesk API](https://github.com/lejianwen/rustdesk-api)

<a href="https://github.com/vuejs/vue-next">
    <img src="https://img.shields.io/badge/vue-^3.2.16-brightgreen.svg" alt="vue3">
  </a>
  <a href="https://github.com/element-plus/element-plus">
    <img src="https://img.shields.io/badge/element--plus-^2.8.2-brightgreen.svg" alt="element-plus">
  </a>
  <a href="https://github.com/lejianwen/Gwen-admin/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/mashape/apistatus.svg" alt="license">
  </a>

# 安装步骤

```shell
git clone https://github.com/lejianwen/rustdesk-api-web
cd rustdesk-api-web   
npm install

// 本地开发
npm run dev

// 打包
npm run build

```

---

## Форк Armilen

Расхождение с апстримом сведено к одному скрипту правок, сами исходники не
трогаются. Тот же принцип, что у `apply-branding` в форке клиента RustDesk:
слияние с апстримом не конфликтует, потому что конфликтовать нечему.

```
python3 scripts/apply-armilen.py   # идемпотентно
npm run build
```

| Что | Где |
| --- | --- |
| 61 недостающий ключ русского перевода и 3 переформулировки | `i18n/ru-armilen.json` |
| Фавиконки | `branding/` |
| Заголовок вкладки | правится скриптом в `index.html` |

Переформулировки намеренные: `PeerManage` «Пиры» → «Все партнёры»,
`AddressBookName` → «Раздел адресной книги», `AddressBookNameManage` →
«Категории». В апстрим они не отдаются, в отличие от 61 недостающего ключа.

Перевод восстановлен из собранного бандла на боевом сервере: исходники
прежнего форка были потеряны, а карта ключей i18n пережила минификацию.
Инструмент восстановления и исходные бандлы лежат в `rustdesk-admin-recovery`.

Сборку и публикацию артефакта делает `.github/workflows/build-admin.yml`:
подтягивает апстрим, накладывает правки, проверяет что они применились,
собирает и кладёт `armilen-admin-dist.tgz` в релиз. VPS скачивает этот ассет
тем же способом, каким уже качает релизы `rustdesk-api`.
