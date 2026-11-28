"""Строка меню окна: «Файл», «Вид», «Справка».

Меню собрано в отдельном классе, чтобы главное окно не разрасталось: здесь
только пункты и переходы, а действия живут в окне и в SettingsActions.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from .theme import THEME_LABELS, THEMES, Theme

__all__ = ["AppMenuBar"]


class AppMenuBar(QMenuBar):
    """Меню приложения: настройки, тема, лог и справка."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_destination: Callable[[], None],
        on_settings: Callable[[], None],
        on_token: Callable[[], None],
        on_cookies: Callable[[], None],
        on_gallery_dl: Callable[[], None],
        on_yt_dlp: Callable[[], None],
        on_components: Callable[[], None],
        on_exit: Callable[[], None],
        on_theme: Callable[[Theme], None],
        on_log_toggled: Callable[[bool], None],
        on_about: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._on_theme = on_theme
        self._theme_actions: dict[Theme, QAction] = {}

        self._build_file_menu(
            on_destination=on_destination,
            on_settings=on_settings,
            on_token=on_token,
            on_cookies=on_cookies,
            on_gallery_dl=on_gallery_dl,
            on_yt_dlp=on_yt_dlp,
            on_components=on_components,
            on_exit=on_exit,
        )
        self._build_view_menu(on_theme=on_theme, on_log_toggled=on_log_toggled)
        self._build_help_menu(on_about=on_about)

    # -- построение меню ---------------------------------------------------

    def _build_file_menu(
        self,
        *,
        on_destination: Callable[[], None],
        on_settings: Callable[[], None],
        on_token: Callable[[], None],
        on_cookies: Callable[[], None],
        on_gallery_dl: Callable[[], None],
        on_yt_dlp: Callable[[], None],
        on_components: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """Меню «Файл»: настройки, компоненты, выход."""
        menu = self.addMenu("Файл")
        self._add_action(menu, "Выбрать папку сохранения…", on_destination)
        self._add_action(menu, "Настройки…", on_settings)
        menu.addSeparator()
        self._add_action(menu, "Токен Pinterest…", on_token)
        self._add_action(menu, "Cookies YouTube…", on_cookies)
        self._add_action(menu, "Путь к gallery-dl…", on_gallery_dl)
        self._add_action(menu, "Путь к yt-dlp…", on_yt_dlp)
        menu.addSeparator()
        self._add_action(menu, "Компоненты…", on_components)
        menu.addSeparator()
        self._add_action(menu, "Выход", on_exit)

    def _build_view_menu(
        self,
        *,
        on_theme: Callable[[Theme], None],
        on_log_toggled: Callable[[bool], None],
    ) -> None:
        """Меню «Вид»: тема окраски и лог."""
        menu = self.addMenu("Вид")
        theme_menu = menu.addMenu("Тема")
        group = QActionGroup(self)
        group.setExclusive(True)
        for theme in THEMES:
            action = QAction(THEME_LABELS[theme], self)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, value=theme: on_theme(value))
            group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[theme] = action

        self._log_action = QAction("Показать лог", self)
        self._log_action.setCheckable(True)
        self._log_action.setChecked(True)
        self._log_action.toggled.connect(on_log_toggled)
        menu.addAction(self._log_action)

    def _build_help_menu(self, *, on_about: Callable[[], None]) -> None:
        """Меню «Справка»: о программе."""
        menu = self.addMenu("Справка")
        self._add_action(menu, "О программе…", on_about)

    def _add_action(self, menu: QMenu, title: str, handler: Callable[[], None]) -> QAction:
        """Добавить пункт меню, вызывающий обработчик."""
        action = QAction(title, self)
        action.triggered.connect(lambda _checked=False: handler())
        menu.addAction(action)
        return action

    # -- состояние ---------------------------------------------------------

    def set_theme(self, theme: Theme) -> None:
        """Отметить выбранную тему."""
        action = self._theme_actions.get(theme)
        if action is not None:
            action.setChecked(True)

    def set_log_visible(self, visible: bool) -> None:
        """Отметить, показан ли лог."""
        self._log_action.setChecked(visible)
