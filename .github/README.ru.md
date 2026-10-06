# Админка ARMILEN

[English version](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/.github/README.md)

Это веб-админка сервера API, с которым работает
[ArmDesk](https://github.com/armilenru/armdesk), клиент удалённого рабочего
стола ИТ-студии [ARMILEN](https://www.armilen.ru). Сервер это
[rustdesk-api](https://github.com/lejianwen/rustdesk-api), а этот репозиторий
форк его админки,
[rustdesk-api-web](https://github.com/lejianwen/rustdesk-api-web). Сборка
независимая: авторы обоих проектов с ней не связаны и её не одобряли.

`README.md` в корне репозитория принадлежит апстриму и не меняется, чтобы
слияние с апстримом не давало конфликтов. Этот файл описывает сам форк.

## Отличия от апстрима

Исходники апстрима в форке не правятся. Все изменения вносит при сборке один
скрипт,
[`scripts/apply-armilen.py`](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/scripts/apply-armilen.py):

- **Оформление.** Цвета, шрифты, логотип, значки и заголовок вкладки как на
  www.armilen.ru, в светлой и тёмной теме
  ([`branding/`](https://github.com/armilenru/armilen-rustdesk-api-web/tree/master/branding)).
- **Тема.** Панель открывается в теме, выбранной на сайте. Выбор хранится в
  куке `theme` на `.armilen.ru`: панель читает её до запуска Vue и записывает
  при каждом переключении. У страниц входа, регистрации и OAuth нет шапки
  панели, поэтому у них свой переключатель темы.
- **Язык.** Русский по умолчанию, какой бы регион ни сообщал браузер.
  [`i18n/ru-armilen.json`](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/i18n/ru-armilen.json)
  добавляет строки, которых нет в русском переводе апстрима, и меняет
  формулировку трёх: `PeerManage`, `AddressBookName` и `AddressBookNameManage`.
- **Настройки сервера.** На каждой странице настроек у опции понятное
  название и абзац о том, что она делает, а не системное имя вроде
  `ALWAYS_USE_RELAY`.
- **Вход.** Он общий с www.armilen.ru. Адрес возврата на сайт после входа
  открывается, а не ведёт на страницу 404. Менеджеры паролей узнают форму, а
  подписи полей занимают ширину своего текста.

## Сборка у себя

```
npm ci
python3 scripts/apply-armilen.py
npm run build
```

Скрипт правит файлы апстрима на месте, поэтому изменённое им не коммитится.
Повторный запуск ничего не меняет.

## Релизы

GitHub Actions собирает админку на каждый push в `master`, по воскресеньям в
22:00 UTC и по запросу. Сборка вливает свежий `master` апстрима, запускает
скрипт, проверяет, что все правки легли, и прикладывает
`armilen-admin-dist.tgz` к релизу `admin-<время UTC>`. Сервер берёт архив из
последнего релиза.

## Лицензия

MIT, как у апстрима: см.
[LICENSE](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/LICENSE).
