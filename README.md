
# 📄 Obsidian MD → PDF Converter  
*Пакетная конвертация Markdown в PDF с темами, подсветкой и сохранением структуры папок*

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## ✨ Возможности
- 🖼 **Темы PDF** — светлая и тёмная, оформленные в стиле Obsidian.  
- 🎨 **Подсветка кода** через Pygments.  
- 💬 **Поддержка callouts** (`> [!note]`) с красивыми стилями.  
- 📂 **Сохранение структуры папок** при экспорте.  
- 🖱 **Drag & Drop** файлов и папок прямо в окно.  
- 🛠 **Гибкие настройки** шрифта, темы и папки вывода.  
- 🚀 **Многопоточная конвертация** для быстроты.

---

## 📦 Установка

### 1. Установите Python
- **Windows** — [python.org](https://www.python.org/downloads/windows/) (отметьте *Add Python to PATH*).  
- **macOS** — `brew install python` *(если установлен Homebrew)*.  
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install python3 python3-pip

### 2. Клонируйте проект

```bash
git clone https://github.com/username/obsidian-md-to-pdf.git
cd obsidian-md-to-pdf
```

### 3. Установите зависимости

```bash
pip install PySide6 markdown pymdown-extensions pygments weasyprint
```

---

## ⚙ Системные зависимости для WeasyPrint

### Windows

Обычно всё ставится вместе с `pip install weasyprint`.  
Если есть ошибки сборки — установите [MS Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).

### macOS

```bash
brew install cairo pango gdk-pixbuf libffi
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

---

## ▶ Запуск

```bash
python main.py
```

---

## 📚 Использование

1. Запустите программу.
2. Добавьте файлы `.md` или целые папки (кнопками или перетаскиванием).
3. Укажите папку для вывода PDF.
4. Выберите тему (**Light** или **Dark**) и шрифт.
5. Если нужно — включите **Сохранять структуру папок** и задайте базовую директорию.
6. Нажмите **Конвертировать → PDF**.

---

## 🔨 Сборка в исполняемый файл

Установите PyInstaller:

```bash
pip install pyinstaller
```

Соберите:

```bash
pyinstaller --name "MD2PDF" --onefile --windowed main.py
```

Результат:

- **Windows**: `dist\MD2PDF.exe`
- **macOS/Linux**: `dist/MD2PDF`

---

## 📄 Лицензия

Проект распространяется под лицензией **MIT** — см. файл [LICENSE](LICENSE).
