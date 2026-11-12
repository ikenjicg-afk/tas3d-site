# TAS3D 2026 — сайт форума

Статичный сайт: `index.html`, папки `media/` и `fonts/`.
Публикуется через GitHub Pages: любое изменение в ветке `main` попадает на сайт примерно за минуту.

## Языки
- Русская версия: `https://tas3d.uz/` — файл `index.html`. Править только его.
- Английская и узбекская: `https://tas3d.uz/en/` и `https://tas3d.uz/uz/` — файлы `en/index.html` и `uz/index.html` **собираются автоматически**. Переводы лежат в `index.html` в `window.TAS3D_I18N`.
- После любой правки `index.html` выполнить из корня репозитория (нужны Python 3 и Node.js):

      python3 tools/build_lang.py

  Скрипт обновит `en/index.html`, `uz/index.html` и `sitemap.xml`.

## Ежедневная проверка сайта
Каждый день в 08:17 по Ташкенту GitHub запускает `tools/site_check.py` (вкладка Actions → «Site check»). Скрипт проверяет, что:
- tas3d.uz и www.tas3d.uz ведут на GitHub Pages;
- http:// переводит на https://;
- сертификат HTTPS действителен ещё минимум 14 дней;
- страницы `/`, `/en/`, `/uz/` на живом сайте байт в байт совпадают с файлами в репозитории.

Если что-то не так, проверка падает и GitHub присылает письмо владельцу аккаунта. Запустить вручную: Actions → Site check → Run workflow.

## Ссылки
- Регистрация: https://luma.com/i6r44wo4
- Фото 2025 (все): https://drive.google.com/drive/folders/1lZOJY6GOSNlPPcEypep-JzIY0N3KchkF
