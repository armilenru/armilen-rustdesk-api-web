# ARMILEN admin panel

[Русская версия](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/.github/README.ru.md)

This is the web admin panel of the API server behind
[ArmDesk](https://github.com/armilenru/armdesk), the remote desktop client of
the IT studio [ARMILEN](https://www.armilen.ru). The server is
[rustdesk-api](https://github.com/lejianwen/rustdesk-api), and this repository
is a fork of its panel,
[rustdesk-api-web](https://github.com/lejianwen/rustdesk-api-web). It is an
independent build, not affiliated with or endorsed by either project.

The `README.md` in the repository root is upstream's, unchanged, so that
merging upstream never conflicts. This file is the fork's own.

## What differs from upstream

The fork doesn't edit upstream's source files. One script,
[`scripts/apply-armilen.py`](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/scripts/apply-armilen.py),
applies every change on top of them at build time:

- **Look.** Colors, fonts, logo, favicons, and the tab title follow
  www.armilen.ru, in a light and a dark theme
  ([`branding/`](https://github.com/armilenru/armilen-rustdesk-api-web/tree/master/branding)).
- **Theme.** The panel opens in the theme chosen on the site. The choice lives
  in a `theme` cookie on `.armilen.ru`: the panel reads it before Vue mounts
  and writes it back on every switch. The sign-in, sign-up, and OAuth pages
  have no panel header, so they get a theme switch of their own.
- **Language.** Russian is the default, whatever region the browser reports.
  [`i18n/ru-armilen.json`](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/i18n/ru-armilen.json)
  adds the strings upstream's Russian translation lacks and rewords three:
  `PeerManage`, `AddressBookName`, and `AddressBookNameManage`.
- **Server settings.** Each settings page shows a readable title and a
  paragraph on what the option does, instead of its raw name such as
  `ALWAYS_USE_RELAY`.
- **Sign-in.** It's shared with www.armilen.ru, and a return address on the
  site opens after sign-in instead of a 404 page. Password managers recognize
  the form, and form labels take the width of their text.

## Local build

```
npm ci
python3 scripts/apply-armilen.py
npm run build
```

The script edits upstream's files in place, so don't commit what it changes.
Running it again changes nothing.

## Releases

GitHub Actions builds the panel on every push to `master`, every Sunday at
22:00 UTC, and on demand. It merges the latest upstream `master`, runs the
script, checks that every change took hold, and attaches
`armilen-admin-dist.tgz` to a release named `admin-<UTC time>`. The server
takes the archive from the latest release.

## License

MIT, the same as upstream: see
[LICENSE](https://github.com/armilenru/armilen-rustdesk-api-web/blob/master/LICENSE).
