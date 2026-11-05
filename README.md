# TAS3D 2026 — сайт форума

Статичный сайт: `index.html`, папки `media/` и `fonts/`.
Публикуется через GitHub Pages: любое изменение в ветке `main` попадает на сайт примерно за минуту.

## Языки
- Русская версия: `https://tas3d.uz/` — файл `index.html`. Править только его.
- Английская и узбекская: `https://tas3d.uz/en/` и `https://tas3d.uz/uz/` — файлы `en/index.html` и `uz/index.html` **собираются автоматически**. Переводы лежат в `index.html` в `window.TAS3D_I18N`.
- После любой правки `index.html` выполнить из корня репозитория (нужны Python 3 и Node.js):

      python3 tools/build_lang.py

  Скрипт обновит `en/index.html`, `uz/index.html` и `sitemap.xml`.

## Ссылки
- Регистрация: https://luma.com/i6r44wo4
- Фото 2025 (все): https://drive.google.com/drive/folders/1lZOJY6GOSNlPPcEypep-JzIY0N3KchkF
