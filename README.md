# PanoPatcher

PanoPatcher is a desktop tool for working with 360° equirectangular panoramas. It helps you quickly create a perspective patch from a panorama, edit it in Photoshop or another editor, and apply the edited area back to the original panorama.

The app is built for photographers and virtual tour creators who need a fast way to retouch nadirs, tripods, reflections, small defects, or other local areas in panoramic images.

## Features

- Open JPG, PNG, TIFF and supported Linear DNG panoramas.
- Rotate the panorama preview and choose the exact view to patch.
- Create a patch and open it in Photoshop or another editor.
- Automatically apply saved patch changes back to the panorama.
- Save the patched panorama into a `pathed` subfolder.
- Save snapshots from the current view, including DNG snapshots for DNG sources.
- Batch processing with Photoshop actions.
- Favorites for frequently used panorama views.
- Direct upload to ipano.ru with existing/new tour selection and upload progress.
- Fast preview and optimized patch workflow.
- HiDPI-friendly interface.
- Interface localization for multiple languages.

## Installation

### Windows release

Download one of the release builds:

- Portable version: unpack the archive and run `PanoPatcher.exe`.
- Installer version: run the installer and launch PanoPatcher from the Start menu.

The portable version stores settings next to the app. The installed version stores settings in the user profile.

## Basic Workflow

1. Click **Add panoramas** and select one or more panorama files.
2. Rotate the preview to the area you want to edit.
3. Click **Make patch**.
4. Edit the patch in Photoshop or another configured editor.
5. Save the patch in the editor.
6. Return to PanoPatcher and apply the patch if it was not applied automatically.
7. Click **Save the result** to write the patched panorama.

Patched files are saved into the `pathed` subfolder next to the original panorama.

## Upload to ipano.ru

1. Click **Upload to ipano.ru**.
2. Sign in with your ipano.ru account.
3. Choose an existing tour or create a new one.
4. Start upload and wait for completion.

If a patched version exists in the `pathed` subfolder, PanoPatcher uploads it. Otherwise it uploads the original file. DNG upload to ipano.ru is currently skipped because the service does not accept DNG files yet.

## DNG Notes

PanoPatcher supports supported Linear DNG panoramas for opening, previewing, rotating and saving DNG snapshots. DNG preview uses LibRaw/rawpy for better color rendering.

## License

See [LICENSE](LICENSE).

---

# PanoPatcher на русском

PanoPatcher - настольное приложение для работы с 360° панорамами в эквидистантной проекции. Оно помогает быстро создать перспективный патч из панорамы, отредактировать его в Photoshop или другом редакторе и применить измененную область обратно к исходной панораме.

Программа рассчитана на фотографов и авторов виртуальных туров, которым нужно быстро ретушировать надир, штатив, отражения, мелкие дефекты и другие локальные области панорамы.

## Возможности

- Открытие панорам JPG, PNG, TIFF и поддерживаемых Linear DNG.
- Вращение превью и выбор точного вида для патча.
- Создание патча и открытие его в Photoshop или другом редакторе.
- Автоматическое применение сохраненных изменений патча.
- Сохранение итоговой панорамы в подпапку `pathed`.
- Сохранение снимка текущего вида, включая DNG-снимки для DNG-исходников.
- Пакетная обработка через Photoshop actions.
- Избранные позиции для часто используемых видов.
- Прямая выгрузка на ipano.ru с выбором существующего или нового тура и прогрессом загрузки.
- Быстрое превью и оптимизированная работа с патчами.
- Корректное отображение на HiDPI-экранах.
- Локализация интерфейса на несколько языков.

## Установка

### Готовая сборка для Windows

Скачайте один из вариантов релиза:

- Portable-версия: распакуйте архив и запустите `PanoPatcher.exe`.
- Инсталлятор: запустите установщик и откройте PanoPatcher из меню Пуск.

Portable-версия хранит настройки рядом с приложением. Установленная версия хранит настройки в профиле пользователя.

## Как пользоваться

1. Нажмите **Добавить панорамы** и выберите один или несколько файлов.
2. Поверните превью к области, которую нужно отредактировать.
3. Нажмите **Сделать патч**.
4. Отредактируйте патч в Photoshop или другом выбранном редакторе.
5. Сохраните патч в редакторе.
6. Вернитесь в PanoPatcher и примените патч, если он не применился автоматически.
7. Нажмите **Сохранить результат**, чтобы записать итоговую панораму.

Готовые файлы сохраняются в подпапку `pathed` рядом с исходной панорамой.

## Выгрузка на ipano.ru

1. Нажмите **Выгрузить на ipano.ru**.
2. Войдите в аккаунт ipano.ru.
3. Выберите существующий тур или создайте новый.
4. Запустите выгрузку и дождитесь завершения.

Если в папке `pathed` уже есть сохраненная версия панорамы, PanoPatcher выгрузит ее. Если нет - будет выгружен исходный файл. DNG пока пропускается при выгрузке, потому что ipano.ru еще не принимает DNG-файлы.

## Заметки про DNG

PanoPatcher поддерживает открытие, просмотр, вращение и сохранение снимков для поддерживаемых Linear DNG-панорам. Для более корректного цвета DNG-превью используется LibRaw/rawpy.

## Лицензия

См. [LICENSE](LICENSE).
