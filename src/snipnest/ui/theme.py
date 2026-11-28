"""Тема окраски приложения: тёмная, светлая и «как в системе».

Тему задаёт сама Qt: стиль Fusion и схема окраски. Палитру под схему
собирает Qt же, поэтому своих таблиц цветов здесь нет — таблица стилей
собирается из ролей палитры, чтобы тёмная и светлая темы не разъехались.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

__all__ = ["ACCENT", "THEMES", "THEME_LABELS", "Theme", "apply_theme", "stylesheet"]

#: Акцент приложения — бирюзовый цвет из логотипа.
ACCENT = "#14B8A6"

#: Текст на акценте: тёмный, на бирюзовом он читается в обеих темах.
ACCENT_TEXT = "#1b1f24"


class Theme(StrEnum):
    """Тема окраски приложения."""

    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"

    @classmethod
    def parse(cls, value: str) -> Theme:
        """Тема из значения в настройках; неизвестное значение — «как в системе»."""
        for theme in cls:
            if theme.value == value:
                return theme
        return cls.SYSTEM


#: Темы в порядке показа: тёмная, светлая, «как в системе».
THEMES: tuple[Theme, ...] = (Theme.DARK, Theme.LIGHT, Theme.SYSTEM)

#: Названия тем для интерфейса.
THEME_LABELS: dict[Theme, str] = {
    Theme.DARK: "Тёмная",
    Theme.LIGHT: "Светлая",
    Theme.SYSTEM: "Как в системе",
}

#: Схема окраски Qt для каждой темы.
_SCHEMES: dict[Theme, Qt.ColorScheme] = {
    Theme.DARK: Qt.ColorScheme.Dark,
    Theme.LIGHT: Qt.ColorScheme.Light,
    Theme.SYSTEM: Qt.ColorScheme.Unknown,
}

#: Роли-поверхности: их цвет переворачивается вместе с темой.
_SURFACE_ROLES: tuple[QPalette.ColorRole, ...] = (
    QPalette.ColorRole.Window,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.AlternateBase,
    QPalette.ColorRole.Button,
    QPalette.ColorRole.ToolTipBase,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Midlight,
    QPalette.ColorRole.Dark,
    QPalette.ColorRole.Shadow,
)

#: Роли-текст: их цвет переворачивается вместе с темой.
_TEXT_ROLES: tuple[QPalette.ColorRole, ...] = (
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.ButtonText,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.BrightText,
    QPalette.ColorRole.ToolTipText,
    QPalette.ColorRole.PlaceholderText,
)


def _flipped(color: QColor) -> QColor:
    """Цвет наоборот по яркости: тёмное становится светлым и наоборот.

    Оттенок и насыщенность сохраняются — меняется только яркость.
    """
    lightness = color.lightnessF()
    result = QColor(color)
    result.setHslF(
        color.hueF(),
        color.saturationF(),
        min(1.0, max(0.0, 0.5 + (0.5 - lightness) * 0.8)),
    )
    return result


def _flipped_palette(palette: QPalette) -> QPalette:
    """Палитра наоборот: те же роли, перевёрнутая яркость.

    Нужна платформам без схемы окраски (headless-сборка, offscreen): там Qt
    просьбу «сделай тёмной» игнорирует, а тема переключаться должна.
    """
    result = QPalette(palette)
    for role in (*_SURFACE_ROLES, *_TEXT_ROLES):
        result.setColor(role, _flipped(palette.color(role)))
    return result


def _color(palette: QPalette, role: QPalette.ColorRole) -> str:
    """Цвет роли палитры в виде строки для таблицы стилей."""
    return palette.color(role).name()


def stylesheet(palette: QPalette) -> str:
    """Таблица стилей под палитру.

    Цвета берутся из ролей палитры, а не вписываются вручную: иначе тёмная
    и светлая темы разъедутся.
    """
    window = _color(palette, QPalette.ColorRole.Window)
    base = _color(palette, QPalette.ColorRole.Base)
    alternate = _color(palette, QPalette.ColorRole.AlternateBase)
    text = _color(palette, QPalette.ColorRole.WindowText)
    button = _color(palette, QPalette.ColorRole.Button)
    button_text = _color(palette, QPalette.ColorRole.ButtonText)
    mid = _color(palette, QPalette.ColorRole.Mid)
    highlight = _color(palette, QPalette.ColorRole.Highlight)
    highlighted_text = _color(palette, QPalette.ColorRole.HighlightedText)
    return f"""
QWidget {{
    background-color: {window};
    color: {text};
}}
QMenuBar {{
    background-color: {window};
    border-bottom: 1px solid {mid};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 5px 11px;
    border-radius: 6px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background-color: {highlight};
    color: {highlighted_text};
}}
QMenu {{
    background-color: {base};
    border: 1px solid {mid};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 26px 6px 12px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {highlight};
    color: {highlighted_text};
}}
QMenu::separator {{
    height: 1px;
    background: {mid};
    margin: 5px 9px;
}}
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QListWidget {{
    background-color: {base};
    color: {text};
    border: 1px solid {mid};
    border-radius: 7px;
    padding: 6px 8px;
    selection-background-color: {highlight};
    selection-color: {highlighted_text};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {base};
    color: {text};
    border: 1px solid {mid};
    selection-background-color: {highlight};
    selection-color: {highlighted_text};
}}
QPushButton {{
    background-color: {button};
    color: {button_text};
    border: 1px solid {mid};
    border-radius: 7px;
    padding: 6px 15px;
}}
QPushButton:hover {{
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {mid};
}}
QPushButton:disabled {{
    color: {mid};
    border-color: {mid};
}}
QPushButton#primaryButton {{
    background-color: {ACCENT};
    color: {ACCENT_TEXT};
    border-color: {ACCENT};
    font-weight: 600;
    padding: 7px 20px;
}}
QToolButton {{
    border: none;
    border-radius: 6px;
    padding: 4px 9px;
    color: {button_text};
}}
QToolButton:hover {{
    background-color: {highlight};
    color: {highlighted_text};
}}
QTableWidget {{
    background-color: {base};
    alternate-background-color: {alternate};
    border: 1px solid {mid};
    border-radius: 8px;
    gridline-color: {mid};
    selection-background-color: {highlight};
    selection-color: {highlighted_text};
}}
QHeaderView::section {{
    background-color: {window};
    color: {text};
    border: none;
    border-bottom: 1px solid {mid};
    padding: 7px 6px;
}}
QProgressBar {{
    background-color: {base};
    border: 1px solid {mid};
    border-radius: 6px;
    height: 9px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}
QGroupBox {{
    border: 1px solid {mid};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 11px;
    padding: 0 5px;
}}
QSplitter::handle {{
    background-color: {mid};
}}
"""


def _application() -> QApplication | None:
    """Приложение, если оно уже создано."""
    instance = QApplication.instance()
    if isinstance(instance, QApplication):
        return instance
    return None


def _palette_for(theme: Theme, application: QApplication) -> QPalette:
    """Палитра темы.

    Схему окраски и палитру собирает сама Qt: стиль Fusion плюс схема
    окраски. Если платформа схему игнорирует (headless-сборка), тёмная и
    светлая палитры получаются из светлой переворотом яркости — своих
    таблиц цветов у приложения нет.
    """
    hints = QGuiApplication.styleHints()
    hints.setColorScheme(_SCHEMES[theme])
    palette = application.style().standardPalette()
    wanted_dark = theme is Theme.DARK
    is_dark = palette.color(QPalette.ColorRole.Window).lightnessF() < 0.5
    if wanted_dark != is_dark:
        palette = _flipped_palette(palette)
    return palette


def apply_theme(theme: Theme, app: QApplication | None = None) -> None:
    """Применить тему: стиль Fusion, схема окраски и таблица стилей.

    Тема применяется целиком: сначала схема окраски, потом палитра и таблица
    стилей. Точечная правка оставила бы часть оформления от прежней темы.
    """
    application = app if app is not None else _application()
    if application is None:
        return
    application.setStyle("Fusion")
    palette = _palette_for(theme, application)
    application.setPalette(palette)
    application.setStyleSheet(stylesheet(palette))
