
import os
import sys
import re
import traceback
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal, QRunnable, QThreadPool, QObject

# Markdown -> HTML
import markdown
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter

# HTML/CSS -> PDF
from weasyprint import HTML, CSS


# --------------------------
# Markdown conversion engine
# --------------------------

MD_EXTENSIONS = [
    # Common + GitHub-like
    "extra",                  # tables, fenced_code, etc.
    "abbr",
    "attr_list",
    "def_list",
    "sane_lists",
    "smarty",
    "nl2br",
    # Useful bits
    "admonition",
    "codehilite",             # Pygments classes
    "toc",
    # Front matter (strip)

    # Task lists, details, better fences, caret/mark, etc.
    "pymdownx.tasklist",
    "pymdownx.details",
    "pymdownx.superfences",
    "pymdownx.tilde",
    "pymdownx.mark",
    "pymdownx.emoji",
]

MD_EXT_CONFIGS = {
    "codehilite": {
        "guess_lang": False,
        "pygments_style": "default",
        "linenums": False,
        "noclasses": False,  # keep classes, we add CSS
    },
    "toc": {
        "permalink": True,
    },
    "pymdownx.tasklist": {
        "custom_checkbox": True
    },
    "pymdownx.emoji": {
        "emoji_generator": "github",
    }
}


def load_text(p: Path) -> str:
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def preprocess_obsidian(text: str) -> str:
    """
    Минимальный препроцессинг под Obsidian:
    - Превращаем callouts (> [!note] ...) в улучшенные blockquote.
    - Нормализуем табы/концы строк.
    """
    # Нормализуем переводы строк
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Простейшая обработка callouts: оставляем как blockquote,
    # но добавляем CSS класс через HTML-комментарий-признак.
    # Пример:
    # > [!note] Заголовок
    # > текст...
    # превратим в
    # > <!--callout:note title="Заголовок"-->
    # > текст...
    def repl_callout(match):
        t = match.group("type").lower()
        title = (match.group("title") or "").strip()
        # Вставим маркер классa
        if title:
            return f'> <!--callout:{t} title="{title}"-->'
        else:
            return f"> <!--callout:{t}-->"

    text = re.sub(
        r"^[ \t]*>[ \t]*\[\!(?P<type>[A-Za-z]+)\][ \t]*(?P<title>.*)?$",
        repl_callout,
        text,
        flags=re.MULTILINE,
    )

    return text


def build_markdown_html(md_text: str) -> str:
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_EXT_CONFIGS)
    html = md.convert(md_text)
    return html


def pygments_css() -> str:
    fmt = HtmlFormatter(style="default")
    return fmt.get_style_defs(".codehilite")


# --------------------------
# PDF CSS themes (Obsidian-like)
# --------------------------

def pdf_css_base(font_family: str) -> str:
    return f"""
/* Page & typography */
@page {{
  size: A4;
  margin: 18mm 16mm 20mm 16mm;
}}

html, body {{
  font-family: '{font_family}', 'JetBrains Mono', system-ui, -apple-system, Segoe UI, Roboto, 'DejaVu Sans', Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  -weasy-hyphens: auto;
  word-wrap: break-word;
}}

h1, h2, h3, h4, h5, h6 {{
  font-weight: 700;
  line-height: 1.25;
  margin: 1.2em 0 0.5em;
}}

p, ul, ol, dl, blockquote, pre, table, figure {{
  margin: 0.7em 0;
}}

a {{
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}}

/* ... остальной твой CSS без изменений ... */

/* Fix spacing between table and next block */
table {{ margin-bottom: 0.3em; }}
table + h1,
table + h2,
table + h3,
table + h4,
table + h5,
table + h6,
table + p {{ margin-top: 0.3em; }}

p, ul, ol, dl, blockquote, pre, table, figure {{
  margin: 0.7em 0;
}}

a {{
  text-decoration: none;
  border-bottom: 1px dashed currentColor;
}}

hr {{
  border: none;
  border-top: 1px solid var(--divider);
  margin: 1.4em 0;
}}

/* Code & inline code */
code, pre, kbd {{
  font-family: 'JetBrains Mono', {font_family}, ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace;
  font-size: 0.92em;
}}

pre {{
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  border: 1px solid var(--border);
  background: var(--code-bg);
  padding: 10px 12px;
  border-radius: 8px;
}}

.codehilite {{
  background: var(--code-bg);
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border);
}}

/* Blockquotes & callouts */
blockquote {{
  border-left: 3px solid var(--accent);
  background: var(--blockquote-bg);
  padding: 8px 12px;
  border-radius: 6px;
}}

blockquote > p:first-child {{
  margin-top: 0;
}}

blockquote > p:last-child {{
  margin-bottom: 0;
}}

/* Callout marker styling: allow accent containers */
blockquote:has(> :first-child[data-callout]) {{
  border-left-color: var(--callout-accent);
  background: var(--callout-bg);
}}

[data-callout] {{
  display: inline-block;
  font-weight: 600;
  margin-bottom: 4px;
  opacity: 0.9;
}}

/* Lists */
ul, ol {{
  padding-left: 1.25em;
}}

li + li {{
  margin-top: 0.2em;
}}

.task-list-item input[type="checkbox"] {{
  transform: translateY(1px) scale(0.9);
}}

/* Tables */
table {{
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
  background: var(--table-bg);
}}

th, td {{
  border: 1px solid var(--table-border);
  padding: 8px 10px;
  vertical-align: top;
}}

thead th {{
  background: var(--thead-bg);
  font-weight: 700;
}}

tbody tr:nth-child(even) {{
  background: var(--row-alt);
}}

caption {{
  caption-side: bottom;
  font-size: 0.9em;
  opacity: 0.8;
  margin-top: 4px;
}}

/* Images & figures */
img, svg {{
  max-width: 100%;
  height: auto;
}}

figure > img {{
  display: block;
  margin: 0 auto;
}}

figcaption {{
  text-align: center;
  font-size: 0.9em;
  opacity: 0.8;
}}

/* TOC */
.toc {{
  border: 1px dashed var(--border);
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--toc-bg);
}}

/* Fine tweaks */
mark {{ background: var(--mark-bg); }}
kbd {{
  background: var(--kbd-bg);
  border: 1px solid var(--border);
  border-bottom-width: 2px;
  border-radius: 4px;
  padding: 0 4px;
  font-size: 0.9em;
}}

.small {{ font-size: 0.9em; opacity: 0.9; }}
.muted {{ opacity: 0.7; }}

/* Avoid awkward breaks */
h2, h3, h4 {{ page-break-after: avoid; }}
table, pre, blockquote {{  }}

/* Injected attributes (JS-less) for callouts */
span[data-callout]::before {{
  content: attr(data-callout);
  text-transform: uppercase;
  font-size: 0.78em;
  letter-spacing: 0.04em;
  margin-right: 0.4em;
  opacity: 0.8;
}}
table {{
    margin: 0;
}}
/* Utility to transform our comment markers into attributes via CSS Generated Content is limited in PDF.
   Instead, we will inject a tiny JS-less hint in HTML builder. We'll parse comment markers and wrap first <p> in a span. */
"""


def pdf_css_theme_light() -> str:
    return """
:root {
  --bg: #ffffff;
  --fg: #2f3338;
  --muted: #5a6069;
  --accent: #5b6ee1;
  --divider: #e5e7eb;
  --border: #d6d9df;

  --code-bg: #f6f8fa;
  --blockquote-bg: #f8f9fb;
  --table-bg: #ffffff;
  --thead-bg: #f3f4f6;
  --row-alt: #fafbfc;
  --toc-bg: #f8fafd;

  --mark-bg: #fff59d;
  --kbd-bg: #f3f4f6;

  --callout-accent: #5b6ee1;
  --callout-bg: #eff2ff;
}

body { background: var(--bg); color: var(--fg); }
a { color: #3a74ff; }
"""


def pdf_css_theme_dark() -> str:
    return """
:root {
  --bg: #1e1f22;
  --fg: #d7d9df;
  --muted: #aab0bb;
  --accent: #7f8cff;
  --divider: #2b2d31;
  --border: #33363d;

  --code-bg: #17181b;
  --blockquote-bg: #1b1c20;
  --table-bg: #202226;
  --thead-bg: #2a2d33;
  --row-alt: #23262b;
  --toc-bg: #1b1c20;

  --mark-bg: #5b6ee14a;
  --kbd-bg: #16181c;

  --callout-accent: #7f8cff;
  --callout-bg: #23273b;
}

body { background: var(--bg); color: var(--fg); }
a { color: #8aa2ff; }
"""


def wrap_html_document(body_html: str, theme: str, font_family: str, title: str = "") -> str:
    theme_css = pdf_css_theme_dark() if theme == "Dark" else pdf_css_theme_light()
    css_base = pdf_css_base(font_family)
    pyg_css = pygments_css()

    # Преобразуем комментарии callout в data-атрибут на первом параграфе цитаты.
    # Ищем pattern <!--callout:type title="...--> внутри blockquote.
    def transform_callouts(html: str) -> str:
        def repl(m):
            inner = m.group(1)
            # ищем первый комментарий callout
            cm = re.search(r"<!--\s*callout:([a-z]+)(?:\s+title=\"([^\"]*)\")?\s*-->", inner)
            if not cm:
                return m.group(0)
            ctype = cm.group(1)
            ctitle = cm.group(2) or ""
            # добавим span в начало внутреннего контента
            badge = (
                f'<span data-callout="{ctype}">{ctitle}</span>'
                if ctitle
                else f'<span data-callout="{ctype}"></span>'
            )
            inner2 = re.sub(r"<!--\s*callout:[^>]*-->\s*", "", inner, count=1)
            # вставим бейдж перед первым блочным элементом
            inner2_new = re.sub(r"^(<p[^>]*>)", r"\1" + badge + " ", inner2, count=1)
            # если нет <p>, вставим просто в начало
            if inner2_new == inner2:
                inner2_new = badge + inner2
            return f"<blockquote>{inner2_new}</blockquote>"

        return re.sub(r"<blockquote>(.*?)</blockquote>", repl, html, flags=re.DOTALL)

    body_with_callouts = transform_callouts(body_html)

    # добавляем заголовок файла в HTML
    header_html = f'<h1 class="doc-title">{title}</h1>'

    return f"""<!DOCTYPE html>
    <html lang="ru">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{title}</title>
      <style>
        {css_base}
        {theme_css}
        /* Pygments */
        {pyg_css}

        /* стиль заголовка документа */
        h1.doc-title {{
          text-align: center;
          font-size: 2em;
          margin-bottom: 1em;
          border-bottom: 2px solid var(--divider);
          padding-bottom: 0.3em;
        }}
      </style>
    </head>
    <body>
      {header_html}
      {body_with_callouts}
    </body>
    </html>
    """


# --------------------------
# Conversion worker (thread)
# --------------------------

class WorkerSignals(QObject):
    progress = Signal(int, int)         # current, total
    message = Signal(str)               # log lines
    done = Signal(list)                 # list of (src, dest, ok, err)
    error = Signal(str)


class ConvertTask(QRunnable):
    def __init__(
        self,
        files: List[Path],
        out_dir: Path,
        theme: str,
        font_family: str,
        preserve_structure: bool = False,
        base_root: Optional[Path] = None,
    ):
        super().__init__()
        self.files = files
        self.out_dir = out_dir
        self.theme = theme
        self.font_family = font_family
        self.preserve_structure = preserve_structure
        self.base_root = base_root
        self.signals = WorkerSignals()

    def run(self):
        results = []
        total = len(self.files)
        for i, md_path in enumerate(self.files, start=1):
            try:
                self.signals.progress.emit(i, total)
                self.signals.message.emit(f"Конвертация: {md_path}")
                html, output_pdf = self.convert_one(md_path)
                self.render_pdf(html, md_path.parent, output_pdf)
                results.append((str(md_path), str(output_pdf), True, ""))
                self.signals.message.emit(f"✓ Готово: {output_pdf}")
            except Exception as e:
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                results.append((str(md_path), "", False, err))
                self.signals.message.emit(f"✗ Ошибка: {md_path}\n  {err}")
        self.signals.done.emit(results)

    def _compute_out_path(self, md_path: Path) -> Path:
        # Базовое имя файла
        safe_name = md_path.stem + ".pdf"

        if self.preserve_structure and self.base_root:
            try:
                rel_parent = md_path.parent.relative_to(self.base_root)
            except Exception:
                rel_parent = Path()
            return (self.out_dir / rel_parent / safe_name)
        else:
            return self.out_dir / safe_name

    def convert_one(self, md_path: Path):
        text = load_text(md_path)
        text = preprocess_obsidian(text)
        body_html = build_markdown_html(text)
        doc_title = md_path.stem
        full_html = wrap_html_document(
            body_html, theme=self.theme, font_family=self.font_family, title=doc_title
        )

        out_pdf = self._compute_out_path(md_path)
        return full_html, out_pdf

    def render_pdf(self, html_str: str, base_url: Path, out_pdf: Path):
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html_str, base_url=str(base_url)).write_pdf(str(out_pdf))


# --------------------------
# GUI
# --------------------------

APP_QSS = """
QMainWindow {
  background: #101114;
}

QWidget {
  color: #e8eaee;
  font-size: 12.5pt;
}

QGroupBox {
  border: 1px solid #2a2d33;
  border-radius: 8px;
  margin-top: 12px;
  padding: 10px;
}

QGroupBox::title {
  subcontrol-origin: margin;
  subcontrol-position: top left;
  padding: 0 6px;
  color: #aab0bb;
}

QPushButton {
  background: #2a2d33;
  border: 1px solid #343841;
  padding: 8px 12px;
  border-radius: 8px;
}

QPushButton:hover {
  background: #323641;
}

QPushButton:pressed {
  background: #3a3f4b;
}

QLineEdit, QComboBox, QListWidget, QTextEdit {
  background: #16181c;
  border: 1px solid #2a2d33;
  border-radius: 8px;
  padding: 6px 8px;
  selection-background-color: #4a68ff;
}

QProgressBar {
  border: 1px solid #2a2d33;
  border-radius: 6px;
  text-align: center;
  background: #16181c;
}

QProgressBar::chunk {
  background-color: #4a68ff;
  border-radius: 6px;
}
"""


def pick_files(parent) -> List[Path]:
    files, _ = QtWidgets.QFileDialog.getOpenFileNames(
        parent,
        "Выбери Markdown файлы",
        str(Path.home()),
        "Markdown (*.md);;Все файлы (*.*)",
    )
    return [Path(f) for f in files]


def pick_folder(parent) -> Optional[Path]:
    d = QtWidgets.QFileDialog.getExistingDirectory(
        parent,
        "Выбери папку (вольт Obsidian)",
        str(Path.home()),
        QtWidgets.QFileDialog.Option.ShowDirsOnly
    )
    return Path(d) if d else None


def pick_out_dir(parent) -> Optional[Path]:
    d = QtWidgets.QFileDialog.getExistingDirectory(
        parent,
        "Выбери папку для PDF",
        str(Path.home()),
        QtWidgets.QFileDialog.Option.ShowDirsOnly
    )
    return Path(d) if d else None


def collect_md_in_dir(root: Path) -> List[Path]:
    res = []
    for p in root.rglob("*.md"):
        # игнорируем .obsidian и скрытые каталоги
        parts = set(part.lower() for part in p.parts)
        if ".obsidian" in parts:
            continue
        if any(seg.startswith(".") for seg in p.parts):
            continue
        res.append(p)
    return res


class DropListWidget(QtWidgets.QListWidget):
    filesDropped = Signal(list)  # List[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(False)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        urls = event.mimeData().urls()
        paths: List[Path] = []
        for url in urls:
            if url.isLocalFile():
                p = Path(url.toLocalFile())
                if p.is_dir():
                    paths.extend(collect_md_in_dir(p))
                elif p.is_file() and p.suffix.lower() == ".md":
                    paths.append(p)
        if paths:
            self.filesDropped.emit(paths)
        event.acceptProposedAction()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Obsidian MD → PDF (WeasyPrint)")
        self.setMinimumSize(980, 680)

        # State
        self.files: List[Path] = []
        self.out_dir: Path = Path.home() / "Desktop"
        self.theme = "Light"  # 'Light'|'Dark'
        self.font_family = "JetBrains Mono"

        # Сохранение структуры
        self.preserve_structure: bool = True
        self.base_root: Optional[Path] = None

        # Thread pool
        self.pool = QThreadPool.globalInstance()

        self._build_ui()
        self._connect()
        self._toggle_preserve_ui(self.preserve_structure)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)

        # Top controls
        row = QtWidgets.QHBoxLayout()
        self.btn_add_files = QtWidgets.QPushButton("Добавить файлы…")
        self.btn_add_folder = QtWidgets.QPushButton("Добавить папку…")
        self.btn_clear = QtWidgets.QPushButton("Очистить")
        row.addWidget(self.btn_add_files)
        row.addWidget(self.btn_add_folder)
        row.addStretch(1)
        row.addWidget(self.btn_clear)
        layout.addLayout(row)

        # File list (с Drag & Drop)
        self.list_files = DropListWidget()
        layout.addWidget(self.list_files, 1)

        # Options group
        opts = QtWidgets.QGroupBox("Параметры")
        g = QtWidgets.QGridLayout(opts)

        self.lbl_out = QtWidgets.QLabel("Папка вывода:")
        self.ed_out = QtWidgets.QLineEdit(str(self.out_dir))
        self.btn_out = QtWidgets.QPushButton("Выбрать…")

        self.lbl_theme = QtWidgets.QLabel("Тема PDF:")
        self.cb_theme = QtWidgets.QComboBox()
        self.cb_theme.addItems(["Light", "Dark"])

        self.lbl_font = QtWidgets.QLabel("Шрифт:")
        self.ed_font = QtWidgets.QLineEdit(self.font_family)
        self.btn_font = QtWidgets.QPushButton("Системный/свой…")

        # Preserve structure controls
        self.chk_preserve = QtWidgets.QCheckBox("Сохранять структуру папок")
        self.chk_preserve.setChecked(self.preserve_structure)
        self.lbl_base = QtWidgets.QLabel("Базовая папка:")
        self.ed_base = QtWidgets.QLineEdit()
        self.ed_base.setPlaceholderText("Автоопределение по общему пути…")
        self.btn_base = QtWidgets.QPushButton("Выбрать…")

        g.addWidget(self.lbl_out, 0, 0)
        g.addWidget(self.ed_out, 0, 1)
        g.addWidget(self.btn_out, 0, 2)

        g.addWidget(self.lbl_theme, 1, 0)
        g.addWidget(self.cb_theme, 1, 1)

        g.addWidget(self.lbl_font, 2, 0)
        g.addWidget(self.ed_font, 2, 1)
        g.addWidget(self.btn_font, 2, 2)

        g.addWidget(self.chk_preserve, 3, 0, 1, 3)

        g.addWidget(self.lbl_base, 4, 0)
        g.addWidget(self.ed_base, 4, 1)
        g.addWidget(self.btn_base, 4, 2)

        layout.addWidget(opts)

        # Convert row
        conv = QtWidgets.QHBoxLayout()
        self.btn_remove_sel = QtWidgets.QPushButton("Удалить выбранные")
        self.btn_convert = QtWidgets.QPushButton("Конвертировать → PDF")
        conv.addWidget(self.btn_remove_sel)
        conv.addStretch(1)
        conv.addWidget(self.btn_convert)
        layout.addLayout(conv)

        # Progress & log
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Лог выполнения…")
        layout.addWidget(self.log, 1)

        # Style
        self.setStyleSheet(APP_QSS)

    def _connect(self):
        self.btn_add_files.clicked.connect(self.on_add_files)
        self.btn_add_folder.clicked.connect(self.on_add_folder)
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_remove_sel.clicked.connect(self.on_remove_selected)
        self.btn_out.clicked.connect(self.on_pick_out)
        self.btn_font.clicked.connect(self.on_pick_font)
        self.btn_convert.clicked.connect(self.on_convert)
        self.cb_theme.currentTextChanged.connect(self.on_theme)

        self.chk_preserve.toggled.connect(self.on_toggle_preserve)
        self.btn_base.clicked.connect(self.on_pick_base_root)

        # Drag & Drop
        self.list_files.filesDropped.connect(self._add_files)

    # Actions

    def on_add_files(self):
        files = pick_files(self)
        self._add_files(files)

    def on_add_folder(self):
        d = pick_folder(self)
        if not d:
            return
        files = collect_md_in_dir(d)
        self._add_files(files)
        # Если структура включена и базовая папка не задана — используем выбранную
        if self.chk_preserve.isChecked() and not self.ed_base.text().strip():
            self._set_base_root(d)

    def _add_files(self, paths: List[Path]):
        added = 0
        for p in paths:
            p = p.resolve()
            if not p.exists() or p.suffix.lower() != ".md":
                continue
            if p in self.files:
                continue
            self.files.append(p)
            self.list_files.addItem(str(p))
            added += 1
        if added:
            self._log(f"Добавлено файлов: {added} (итого: {len(self.files)})")
            # Автообновление базовой папки при включённой опции
            if self.chk_preserve.isChecked() and not self.ed_base.text().strip():
                self._update_base_root_autodetect()

    def on_clear(self):
        self.files.clear()
        self.list_files.clear()
        self._log("Список очищен.")

    def on_remove_selected(self):
        selected = self.list_files.selectedItems()
        for it in selected:
            p = Path(it.text())
            if p in self.files:
                self.files.remove(p)
            row = self.list_files.row(it)
            self.list_files.takeItem(row)
        self._log(f"Удалено: {len(selected)} (итого: {len(self.files)})")
        if self.chk_preserve.isChecked() and not self.ed_base.text().strip():
            self._update_base_root_autodetect()

    def on_pick_out(self):
        d = pick_out_dir(self)
        if not d:
            return
        self.out_dir = d
        self.ed_out.setText(str(d))

    def on_pick_font(self):
        # Позволим выбрать установленный шрифт (по имени) или указать TTF/OTF — WeasyPrint увидит системный семейство.
        name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Шрифт",
            "Введите семейство шрифта (например, JetBrains Mono):",
            text=self.ed_font.text(),
        )
        if ok and name.strip():
            self.font_family = name.strip()
            self.ed_font.setText(self.font_family)

    def on_pick_base_root(self):
        d = pick_folder(self)
        if not d:
            return
        self._set_base_root(d)

    def on_theme(self, t: str):
        self.theme = t

    def on_toggle_preserve(self, checked: bool):
        self.preserve_structure = checked
        self._toggle_preserve_ui(checked)
        if checked and not self.ed_base.text().strip():
            self._update_base_root_autodetect()

    def on_convert(self):
        if not self.files:
            self._log("Нет файлов для конвертации.")
            return

        out = Path(self.ed_out.text().strip())
        out.mkdir(parents=True, exist_ok=True)
        self.out_dir = out

        # Определяем базовую папку для структуры, если нужно
        base_root: Optional[Path] = None
        if self.chk_preserve.isChecked():
            base_text = self.ed_base.text().strip()
            if base_text:
                base_root = Path(base_text)
            else:
                base_root = self._common_base(self.files)
            if base_root:
                self._log(f"Базовая папка для структуры: {base_root}")

        self._set_busy(True)
        self.progress.setValue(0)

        task = ConvertTask(
            self.files.copy(),
            self.out_dir,
            self.theme,
            self.font_family,
            preserve_structure=self.chk_preserve.isChecked(),
            base_root=base_root,
        )
        task.signals.progress.connect(self._on_progress)
        task.signals.message.connect(self._log)
        task.signals.done.connect(self._on_done)
        task.signals.error.connect(self._on_error)

        self.pool.start(task)

    # Helpers

    def _on_progress(self, cur: int, total: int):
        pct = int(cur * 100 / max(1, total))
        self.progress.setValue(pct)

    def _on_error(self, msg: str):
        self._log("Ошибка: " + msg)
        self._set_busy(False)

    def _on_done(self, results):
        ok = sum(1 for _, _, s, _ in results if s)
        fail = len(results) - ok
        self._log(f"Готово. Успешно: {ok}, ошибок: {fail}")
        self._set_busy(False)

    def _set_busy(self, busy: bool):
        widgets = [
            self.btn_add_files, self.btn_add_folder, self.btn_clear,
            self.btn_remove_sel, self.btn_out, self.btn_font, self.btn_convert,
            self.cb_theme, self.ed_out, self.ed_font, self.list_files,
            self.chk_preserve, self.ed_base, self.btn_base
        ]
        for w in widgets:
            w.setEnabled(not busy)

    def _log(self, text: str):
        self.log.append(text)

    def _toggle_preserve_ui(self, enabled: bool):
        self.lbl_base.setEnabled(enabled)
        self.ed_base.setEnabled(enabled)
        self.btn_base.setEnabled(enabled)

    def _set_base_root(self, path: Path):
        self.base_root = path.resolve()
        self.ed_base.setText(str(self.base_root))

    def _update_base_root_autodetect(self):
        if not self.files:
            return
        base = self._common_base(self.files)
        if base:
            self._set_base_root(base)

    @staticmethod
    def _common_base(paths: List[Path]) -> Optional[Path]:
        try:
            common = os.path.commonpath([str(p.resolve()) for p in paths])
            return Path(common)
        except Exception:
            return None


def main():
    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("JetBrains Mono", 10)
    app.setFont(font)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
