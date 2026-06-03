import os
import sys
from math import pi, sin

# High-DPI flags must be set before QApplication is created.
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import qtawesome as qta
from PyQt6.QtCore import (
    QDateTime,
    QEasingCurve,
    QLocale,
    QPoint,
    QPropertyAnimation,
    QSettings,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    pyqtProperty,
)
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from responsive_utils import (
    get_manager,
    center_window,
    control_min_height,
    margin_inner,
    margin_outer,
    scaled,
    scaled_font,
    screen_fraction,
    spacing_loose,
    spacing_tight,
)
# ============================================================
# Enterprise Banking Palette — red / white / black / soft pink
# No gradients, no neon, no playful accents.
# ============================================================
C_BLACK_CHROME = "#0A0A0B"
C_SURFACE_DARK = "#141416"
C_DARK_BORDER = "#2C2C30"
C_MAIN_BG = "#FFFFFF"
C_CARD_WHITE = "#FFFFFF"
C_LIGHT_BORDER = "#E5E7EB"
C_INPUT_BORDER = "#D7D7DC"
C_TEXT_PRIMARY = "#171717"
C_TEXT_STRONG = "#111111"
C_TEXT_SECONDARY = "#6B7280"
C_TEXT_MUTED = "#A1A1AA"
C_PLACEHOLDER = "#71717A"
C_PRIMARY_RED = "#B91C1C"
C_RED_HOVER = "#991B1B"
C_ACTIVE_RED = "#DC2626"
C_SOFT_PINK_SURFACE = "#FFF1F4"
C_SOFT_PINK_BORDER = "#FFD4DF"
C_SOFT_PINK_ACCENT = "#F4A7B9"
C_PALE_PINK_TRACK = "#F3D6DE"
C_TABLE_HEADER = "#111111"
C_TABLE_HEADER_SEPARATOR = "#333333"
C_ROW_ALT = "#FAFAFA"
C_ACTIVE_NAV_BG = "#231112"
C_INACTIVE_NAV_TEXT = "#B9B9C0"
C_REFRESH_ICON = "#3F3F46"
C_SECONDARY_BUTTON_BORDER = "#F2B8C6"
C_ERROR_RED = "#991B1B"
C_WHITE = "#FFFFFF"

# Refined UI layer colors for visual separation.
C_WORKSPACE_BG = "#FFFFFF"
C_MAIN_PANEL_BG = "#E6E8EB"
C_HELP_PANEL_BG = "#E6E8EB"
C_INNER_CARD_BG = "#FFFFFF"
C_NOTIFICATION_BG = "#1E2023"
C_NOTIFICATION_BORDER = "#F3F4F6"
C_MAIN_PANEL_CHARCOAL = "#E6E8EB"
C_MAIN_PANEL_CHARCOAL_BORDER = "#D7DCE2"
C_HEADER_RED = C_PRIMARY_RED  # solid header background
C_HEADER_RED_DARK = C_RED_HOVER
C_HEADER_SOFT = "#FFE7EC"
C_HEADER_TITLE = C_WHITE
C_HEADER_ACCENT = "#FFD6DE"
C_HEADER_REFRESH_ICON = C_PRIMARY_RED
C_HEADER_TIME_TEXT = C_BLACK_CHROME
C_HEADER_CHIP_BORDER = C_BLACK_CHROME

# White / gray hierarchy:
# Body is clean bright white. Main panels use a calm light-charcoal gray.
# Inner cards and content-filled boxes return to bright white for readability.
C_BODY_WHITE_LAYER = "#FFFFFF"
C_OUTER_WHITE_LAYER = "#EEF0F2"
C_PANEL_WHITE_LAYER = "#FFFFFF"
C_CONTENT_WHITE_LAYER = "#FFFFFF"
C_INPUT_WHITE_LAYER = "#FFFFFF"
C_SOFT_WHITE_BORDER = "#D7DCE2"
C_SUBTLE_WHITE_BORDER = "#E5E7EB"

# Backward-compatible aliases used by existing widgets.
C_SOIL_BODY = C_MAIN_BG
C_BARK = C_BLACK_CHROME
C_BARK_DARK = C_BLACK_CHROME
C_BARK_SOFT = C_SURFACE_DARK
C_BARK_LINE = C_DARK_BORDER
C_CANOPY_HEADER = C_MAIN_BG
C_PINE_BLACK = C_BLACK_CHROME
C_PINE_DEEP = C_SURFACE_DARK
C_PINE = C_TEXT_PRIMARY
C_PINE_SOFT = C_DARK_BORDER
C_PINE_TEXT = C_INACTIVE_NAV_TEXT
C_MOSS_DARK = C_LIGHT_BORDER
C_MOSS = C_SOFT_PINK_ACCENT
C_MOSS_LIGHT = C_INACTIVE_NAV_TEXT
C_MOSS_MIST = C_SOFT_PINK_SURFACE
C_FERN = C_PRIMARY_RED
C_FERN_LIGHT = C_SOFT_PINK_ACCENT
C_PANEL_SETTINGS = C_CARD_WHITE
C_PANEL_HELP = C_CARD_WHITE
C_CARD_GENERAL = C_CARD_WHITE
C_CARD_BEHAVIOR = C_SOFT_PINK_SURFACE
C_CARD_PATHS = C_CARD_WHITE
C_CARD_NEUTRAL = C_CARD_WHITE
C_INPUT_LEAF = C_CARD_WHITE
C_LEAF = C_PRIMARY_RED
C_LEAF_HOVER = C_RED_HOVER
C_LEAF_DARK = C_ERROR_RED
C_MIST = C_MAIN_BG
C_MIST_LIGHT = C_LIGHT_BORDER
C_PANEL_FOG = C_CARD_WHITE
C_PANEL_DEW = C_ROW_ALT
C_PAPER = C_CARD_WHITE
C_PAPER_ALT = C_SOFT_PINK_SURFACE
C_PAPER_EDGE = C_LIGHT_BORDER
C_INK = C_TEXT_PRIMARY
C_MUTED = C_TEXT_SECONDARY
C_ORANGE = C_PRIMARY_RED
C_ORANGE_HOVER = C_RED_HOVER
C_ORANGE_DARK = C_ERROR_RED
C_DARK = C_TEXT_PRIMARY
C_FOREST_DEEP = C_SURFACE_DARK
C_FOREST_TOP = C_DARK_BORDER
C_FOREST_BOTTOM = C_SURFACE_DARK
C_HEADER_BROWN = C_MAIN_BG
C_HEADER_BROWN_DARK = C_LIGHT_BORDER
C_HEADER_BROWN_SOFT = C_CARD_WHITE
C_MOSS_ACCENT = C_SOFT_PINK_ACCENT
C_HELP_PANEL = C_CARD_WHITE
C_HELP_PAPER = C_CARD_WHITE
C_HELP_INK = C_TEXT_PRIMARY
C_HELP_MUTED = C_TEXT_SECONDARY
C_LIGHT = C_MAIN_BG
C_SAGE = C_MAIN_BG
C_OLIVE = C_INPUT_BORDER
C_PANEL = C_CARD_WHITE
C_HEADER_TEXT = C_TEXT_STRONG
C_HEADER_MUTED = C_TEXT_SECONDARY

SIDEBAR_EXPANDED_WIDTH = 160
SIDEBAR_COLLAPSED_WIDTH = 52
SIDEBAR_CONTROL_HEIGHT = 26
HEADER_CONTROL_HEIGHT = 26
HEADER_YEAR_WIDTH = 86
SEARCH_WIDTH_NORMAL = 180
SEARCH_WIDTH_FOCUSED = 260
NOTIFICATION_MIN_HEIGHT = 190


def create_shadow(widget, blur_radius=20, x_offset=0, y_offset=4, alpha=50):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(scaled(blur_radius))
    shadow.setOffset(scaled(x_offset), scaled(y_offset))
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)
    return shadow


def create_button_shadow(button, blur_radius=10, y_offset=2, alpha=32):
    """Small, professional button shadow."""
    return create_shadow(
        button, blur_radius=blur_radius, x_offset=0, y_offset=y_offset, alpha=alpha
    )


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class SmoothShadowButtonMixin:
    """Smooth hover/press animation for QPushButton subclasses."""

    def setup_smooth_shadow(
        self,
        blur_idle=10,
        blur_hover=16,
        blur_pressed=7,
        y_idle=2,
        y_hover=4,
        y_pressed=1,
        alpha=32,
    ):
        self._shadow_blur_idle = scaled(blur_idle)
        self._shadow_blur_hover = scaled(blur_hover)
        self._shadow_blur_pressed = scaled(blur_pressed)
        self._shadow_y_idle = scaled(y_idle)
        self._shadow_y_hover = scaled(y_hover)
        self._shadow_y_pressed = scaled(y_pressed)

        self._button_shadow = QGraphicsDropShadowEffect(self)
        self._button_shadow.setBlurRadius(self._shadow_blur_idle)
        self._button_shadow.setOffset(0, self._shadow_y_idle)
        self._button_shadow.setColor(QColor(0, 0, 0, alpha))
        self.setGraphicsEffect(self._button_shadow)

        self._shadow_blur_anim = QPropertyAnimation(
            self._button_shadow, b"blurRadius", self
        )
        self._shadow_y_anim = QPropertyAnimation(self._button_shadow, b"yOffset", self)
        for anim in (self._shadow_blur_anim, self._shadow_y_anim):
            anim.setDuration(150)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def animate_shadow(self, blur, y_offset):
        if not hasattr(self, "_button_shadow"):
            return
        for anim, target in (
            (self._shadow_blur_anim, blur),
            (self._shadow_y_anim, y_offset),
        ):
            anim.stop()
            anim.setStartValue(
                anim.targetObject().property(anim.propertyName().data().decode())
            )
            anim.setEndValue(target)
            anim.start()

    def enterEvent(self, event):
        if hasattr(self, "_shadow_blur_hover"):
            self.animate_shadow(self._shadow_blur_hover, self._shadow_y_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if hasattr(self, "_shadow_blur_idle"):
            self.animate_shadow(self._shadow_blur_idle, self._shadow_y_idle)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if hasattr(self, "_shadow_blur_pressed"):
            self.animate_shadow(self._shadow_blur_pressed, self._shadow_y_pressed)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, "_shadow_blur_hover"):
            target_blur = (
                self._shadow_blur_hover if self.underMouse() else self._shadow_blur_idle
            )
            target_y = (
                self._shadow_y_hover if self.underMouse() else self._shadow_y_idle
            )
            self.animate_shadow(target_blur, target_y)
        super().mouseReleaseEvent(event)


class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(26))
        self.setMinimumWidth(scaled(80))
        self.view().setObjectName("modernComboPopup")
        self.view().setStyleSheet(f"""
            QListView#modernComboPopup {{
                background-color: {C_WHITE};
                color: {C_DARK};
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                padding: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
                outline: none;
            }}
            QListView#modernComboPopup::item {{
                min-height: {scaled(14)}px;
                padding: {scaled(4)}px {scaled(6)}px;
                color: {C_DARK};
                background: transparent;
                border-radius: {scaled(4)}px;
            }}
            QListView#modernComboPopup::item:hover {{
                background-color: {C_DARK};
                color: {C_LIGHT};
            }}
            QListView#modernComboPopup::item:selected {{
                background-color: {C_DARK};
                color: {C_LIGHT};
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        arrow_color = C_LIGHT if self.objectName() == "filterCombo" else C_DARK
        pen = QPen(QColor(arrow_color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        w = self.width()
        h = self.height()
        x = w - 22
        y = h // 2 - 2

        painter.drawLine(x, y, x + 4, y + 4)
        painter.drawLine(x + 4, y + 4, x + 8, y)
        painter.end()


class AnimatedSearch(QLineEdit):
    def __init__(self, placeholder="Search projects here...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumWidth(scaled(SEARCH_WIDTH_NORMAL))
        self.setMaximumWidth(scaled(SEARCH_WIDTH_NORMAL))
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.addAction(
            qta.icon("fa5s.search", color=C_DARK),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        self.anim_min = QPropertyAnimation(self, b"minimumWidth", self)
        self.anim_max = QPropertyAnimation(self, b"maximumWidth", self)
        for anim in (self.anim_min, self.anim_max):
            anim.setDuration(160)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def animate_width(self, width):
        for anim in (self.anim_min, self.anim_max):
            anim.stop()
            anim.setStartValue(self.width())
            anim.setEndValue(scaled(width))
            anim.start()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.animate_width(SEARCH_WIDTH_FOCUSED)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.animate_width(SEARCH_WIDTH_NORMAL)


class AnimatedPrimaryButton(SmoothShadowButtonMixin, QPushButton):
    def __init__(self, text, icon_name="fa5s.plus", parent=None):
        super().__init__(text, parent)
        self.setIcon(qta.icon(icon_name, color=C_WHITE))
        self.setIconSize(QSize(scaled(12), scaled(12)))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(30))
        self.setMinimumWidth(scaled(120))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setup_smooth_shadow(
            blur_idle=10,
            blur_hover=16,
            blur_pressed=7,
            y_idle=2,
            y_hover=4,
            y_pressed=1,
            alpha=34,
        )
        self._pad = scaled(16)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(120)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self.set_pad)
        self.update_style()

    @pyqtProperty(int)
    def pad(self):
        return self._pad

    def set_pad(self, value):
        self._pad = int(value)
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {C_LEAF};
                color: {C_WHITE};
                border: {scaled(1)}px solid {C_RED_HOVER};
                border-radius: {scaled(5)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                padding: 0 {self._pad}px;
            }}
            QPushButton:hover {{ background: {C_LEAF_HOVER}; }}
            QPushButton:pressed {{ background: {C_LEAF_DARK}; }}
        """)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._pad)
        self.anim.setEndValue(scaled(18))
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._pad)
        self.anim.setEndValue(scaled(16))
        self.anim.start()
        super().leaveEvent(event)


class SidebarButton(QPushButton):
    def __init__(self, text, icon_name, active=False, parent=None):
        super().__init__(text, parent)
        self.original_text = text
        self.icon_name = icon_name
        self.active = active
        self.collapsed = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setIconSize(QSize(scaled(12), scaled(12)))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_button_shadow(self, blur_radius=8, y_offset=1, alpha=24)
        self.update_style()

    def set_active(self, active: bool):
        self.active = active
        self.update_style()

    def set_collapsed(self, collapsed: bool):
        self.collapsed = collapsed
        self.setText("" if collapsed else self.original_text)
        self.setToolTip(self.original_text if collapsed else "")
        self.update_style()

    def update_style(self):
        icon_color = C_WHITE if self.active else C_INACTIVE_NAV_TEXT
        bg = C_ACTIVE_NAV_BG if self.active else "transparent"
        color = C_WHITE if self.active else C_INACTIVE_NAV_TEXT
        border_left = C_ACTIVE_RED if self.active else "transparent"
        align = "center" if self.collapsed else "left"
        pad_left = scaled(4) if self.collapsed else scaled(8)
        self.setIcon(qta.icon(self.icon_name, color=icon_color))
        self.setStyleSheet(f"""
            QPushButton {{
                text-align: {align};
                background: {bg};
                color: {color};
                border: none;
                border-left: {scaled(3)}px solid {border_left};
                border-radius: {scaled(5)}px;
                padding: {scaled(4)}px {scaled(6)}px {scaled(4)}px {pad_left}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: {C_ACTIVE_NAV_BG};
                color: {C_WHITE};
                border-left: {scaled(3)}px solid {C_ACTIVE_RED};
            }}
        """)


class DateTimeBadge(QFrame):
    """Live header clock using the locked dashboard date format."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dateTimeBadge")
        self.setMinimumHeight(scaled(HEADER_CONTROL_HEIGHT))
        self.setMinimumWidth(scaled(230))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        create_shadow(self, blur_radius=10, x_offset=0, y_offset=1, alpha=28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(10), 0, scaled(10), 0)
        layout.setSpacing(spacing_tight())
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel()
        icon.setObjectName("dateTimeIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(qta.icon("fa5s.calendar-alt", color=C_ORANGE).pixmap(scaled(12), scaled(12)))
        layout.addWidget(icon)

        self.label = QLabel()
        self.label.setObjectName("dateTimeLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)
        self.update_datetime()

    def update_datetime(self):
        """Refresh text every second: Fri, 22 May 2026 HH:MM:SS."""
        now = QDateTime.currentDateTime()
        self.label.setText(self.locale.toString(now, "ddd, dd MMM yyyy HH:mm:ss"))


class RefreshButton(SmoothShadowButtonMixin, QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerRefreshButton")
        self.icon_name = "fa5s.sync-alt"
        self.canvas_size = scaled(18)
        self.icon_draw_size = scaled(12)
        self.base_icon = qta.icon(self.icon_name, color=C_HEADER_REFRESH_ICON)
        self.setIconSize(QSize(scaled(12), scaled(12)))
        self.setText("")
        self.setMinimumWidth(scaled(28))
        self.setFixedHeight(scaled(HEADER_CONTROL_HEIGHT))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Refresh Data")
        self.setup_smooth_shadow(
            blur_idle=9,
            blur_hover=14,
            blur_pressed=6,
            y_idle=2,
            y_hover=3,
            y_pressed=1,
            alpha=30,
        )
        self._angle = 0
        self.update_rotated_icon(0)

        self.spin_anim = QVariantAnimation(self)
        self.spin_anim.setDuration(650)
        self.spin_anim.setStartValue(0)
        self.spin_anim.setEndValue(720)
        self.spin_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self.spin_anim.valueChanged.connect(self.update_rotated_icon)
        self.spin_anim.finished.connect(lambda: self.update_rotated_icon(0))
        self.clicked.connect(self.start_spin)

    def start_spin(self):
        self.spin_anim.stop()
        self.spin_anim.start()

    def update_rotated_icon(self, angle):
        self._angle = float(angle)
        canvas = QPixmap(self.canvas_size, self.canvas_size)
        canvas.fill(Qt.GlobalColor.transparent)
        source = self.base_icon.pixmap(self.icon_draw_size, self.icon_draw_size)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(self.canvas_size / 2, self.canvas_size / 2)
        painter.rotate(self._angle)
        painter.drawPixmap(-self.icon_draw_size // 2, -self.icon_draw_size // 2, source)
        painter.end()
        self.setIcon(QIcon(canvas))


class AnimatedPageButton(QPushButton):
    def __init__(self, icon_name, tooltip, parent=None):
        super().__init__(parent)
        self.base_size = 16
        self.max_extra_size = 8

        self.setIcon(qta.icon(icon_name, color=C_DARK))
        self.setIconSize(QSize(self.base_size, self.base_size))
        self.setObjectName("pageNavButton")
        self.setToolTip(tooltip)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumSize(scaled(26), scaled(26))

        self.pulse_anim = QVariantAnimation(self)
        self.pulse_anim.setDuration(360)
        self.pulse_anim.setStartValue(0.0)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pulse_anim.valueChanged.connect(self.update_pulse)
        self.pulse_anim.finished.connect(
            lambda: self.setIconSize(QSize(self.base_size, self.base_size))
        )
        self.clicked.connect(self.start_pulse)

    def start_pulse(self):
        self.pulse_anim.stop()
        self.pulse_anim.setStartValue(0.0)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.start()

    def update_pulse(self, progress):
        progress = float(progress)
        pulse = sin(pi * progress)
        icon_size = self.base_size + round(self.max_extra_size * pulse)
        self.setIconSize(QSize(icon_size, icon_size))


class TableStateCombo(QPushButton):
    """Locked v13-style custom dropdown: full-size shape, centered text, visible arrow."""

    def __init__(self, current_value, options=None, parent=None):
        super().__init__(parent)
        self.setObjectName("stateCombo")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(24))
        self.setMinimumWidth(scaled(100))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        base_options = options or [
            "UAT",
            "SIT",
            "UAT PREPARE",
            "PROD READY",
            "PENDING SUBMISSION",
            "IMPLEMENTED",
            "POSTPONED",
        ]

        self.options = []
        for value in [current_value, *base_options]:
            if value and value not in self.options:
                self.options.append(value)

        self._current_text = current_value or (self.options[0] if self.options else "")
        self.setToolTip(self._current_text)

        self.menu = QMenu(self)
        self.menu.setObjectName("stateDropdownMenu")
        self.menu.setStyleSheet(f"""
            QMenu#stateDropdownMenu {{
                background-color: {C_WHITE};
                color: {C_DARK};
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                padding: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            QMenu#stateDropdownMenu::item {{
                min-height: {scaled(14)}px;
                padding: {scaled(4)}px {scaled(6)}px;
                border-radius: {scaled(4)}px;
                color: {C_DARK};
                background: transparent;
            }}
            QMenu#stateDropdownMenu::item:selected {{
                background-color: rgba(188, 108, 44, 0.12);
                color: {C_ORANGE};
            }}
        """)

        for option in self.options:
            action = self.menu.addAction(option)
            action.triggered.connect(
                lambda checked=False, value=option: self.set_current_text(value)
            )

    def currentText(self):
        return self._current_text

    def setCurrentText(self, value):
        self.set_current_text(value)

    def set_current_text(self, value):
        self._current_text = value
        self.setToolTip(value)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_dropdown()
            event.accept()
            return

        super().mousePressEvent(event)

    def show_dropdown(self):
        popup_width = max(self.width() + 26, self.minimumWidth() + 34, 230)
        self.menu.setMinimumWidth(popup_width)
        self.menu.setMinimumWidth(popup_width)
        self.menu.popup(self.mapToGlobal(QPoint(0, self.height() + 4)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = self.property("rowSelected") is True
        hover = self.underMouse()

        if selected:
            bg = QColor(255, 255, 255, 46)
            border = QColor(255, 255, 255, 125)
            text_color = QColor(C_WHITE)
            arrow_color = QColor(C_WHITE)
        else:
            bg = QColor(C_ORANGE_DARK if hover else C_ORANGE)
            border = QColor(45, 61, 52, 35)
            text_color = QColor(C_WHITE)
            arrow_color = QColor(C_WHITE)

        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 8, 8)

        arrow_width = 30
        text_rect = rect.adjusted(14, 0, -arrow_width, 0)
        painter.setPen(text_color)
        painter.setFont(QFont("Inter", scaled_font(9), QFont.Weight.Black))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._current_text)

        pen = QPen(arrow_color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        cx = rect.right() - 16
        cy = rect.center().y() - 2
        painter.drawLine(cx - 4, cy, cx, cy + 4)
        painter.drawLine(cx, cy + 4, cx + 4, cy)
        painter.end()


class EditableLinkLineEdit(QLineEdit):
    """Auto-commit on Enter or click-out/focus-out."""

    def __init__(self, value="", parent=None, on_commit=None):
        super().__init__(parent)
        self.setObjectName("tableLinkEdit")
        self.setText(value)
        self.setToolTip(value)
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.setMinimumHeight(scaled(24))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setClearButtonEnabled(False)
        self.setFrame(False)
        self._last_committed_value = value
        self.on_commit = on_commit
        self.returnPressed.connect(self.commit_value)

    def focusOutEvent(self, event):
        self.commit_value()
        super().focusOutEvent(event)

    def commit_value(self):
        new_value = self.text().strip()
        if new_value == self._last_committed_value:
            return

        self._last_committed_value = new_value
        self.setText(new_value)
        self.setToolTip(new_value)
        self.setCursorPosition(0)

        if self.on_commit:
            self.on_commit(new_value)


class StatusBadge(QLabel):
    def __init__(self, text, state="warning", parent=None):
        super().__init__(text, parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Bold))
        self.setMinimumHeight(scaled(14))

        if state == "warning":
            bg, color = C_ORANGE, C_WHITE
        elif state == "success":
            bg, color = C_DARK, C_WHITE
        elif state == "danger":
            bg, color = "#B5382F", C_WHITE
        else:
            bg, color = C_SAGE, C_DARK

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {color};
                border-radius: {scaled(11)}px;
                padding: {scaled(3)}px {scaled(4)}px;
            }}
        """)


class MetricCard(QFrame):
    def __init__(
        self, label, value="0", icon_name="fa5s.chart-pie", helper="", parent=None
    ):
        super().__init__(parent)
        self.setObjectName("metricCard")
        create_shadow(self, blur_radius=18, y_offset=4, alpha=22)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        outer_layout.setSpacing(scaled(0))

        inner = QFrame()
        inner.setObjectName("metricInner")
        create_shadow(inner, blur_radius=16, x_offset=0, y_offset=5, alpha=42)

        layout = QHBoxLayout(inner)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())

        icon_box = QLabel()
        icon_box.setObjectName("metricIcon")
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setMinimumSize(scaled(26), scaled(26))
        icon_box.setPixmap(qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12)))
        layout.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setSpacing(scaled(3))

        val = QLabel(value)
        val.setObjectName("metricValue")
        text_col.addWidget(val)

        lbl = QLabel(label)
        lbl.setObjectName("metricLabel")
        text_col.addWidget(lbl)

        if helper:
            sub = QLabel(helper)
            sub.setObjectName("metricHelper")
            text_col.addWidget(sub)

        layout.addLayout(text_col, 1)
        outer_layout.addWidget(inner)


class PanelCard(QFrame):
    def __init__(self, title="", icon_name=None, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("panelCard")
        create_shadow(self, blur_radius=18, y_offset=4, alpha=24)
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        self.outer_layout.setSpacing(spacing_tight())

        if title:
            header = QHBoxLayout()
            header.setSpacing(spacing_tight())

            if icon_name:
                icon = QLabel()
                try:
                    icon_pixmap = qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12))
                except Exception:
                    icon_pixmap = qta.icon("fa5s.circle", color=C_ORANGE).pixmap(scaled(12), scaled(12))
                icon.setPixmap(icon_pixmap)
                header.addWidget(icon)

            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            header.addWidget(title_label)

            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("cardSubtitle")
                header.addWidget(subtitle_label)

            header.addStretch()
            self.header = header
            self.outer_layout.addLayout(header)


class ClearableSelectionTable(QTableWidget):
    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentItem(None)
            event.accept()
            return

        super().mousePressEvent(event)


class AutomationTabButton(QPushButton):
    def __init__(self, text, icon_name, active=False, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.active = active
        self._padding = 18 if active else 14

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(26))
        self.setIconSize(QSize(scaled(8), scaled(8)))

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self.set_padding)

        self.update_style()

    def set_active(self, active):
        self.active = active
        self._padding = 18 if active else 14
        self.update_style()

    def set_padding(self, value):
        self._padding = int(value)
        self.update_style()

    def update_style(self):
        if self.active:
            bg = C_ORANGE
            color = C_WHITE
            icon_color = C_WHITE
            border = "transparent"
            weight = "900"
        else:
            bg = "rgba(227, 230, 228, 0.68)"
            color = C_DARK
            icon_color = C_DARK
            border = "rgba(45, 61, 52, 0.18)"
            weight = "800"

        self.setIcon(qta.icon(self.icon_name, color=icon_color))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border};
                border-radius: {scaled(4)}px;
                padding: 9px {self._padding}px;
                font-size: {scaled_font(8)}pt;
                font-weight: {weight};
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {C_ORANGE if self.active else "rgba(188, 108, 44, 0.16)"};
                color: {C_WHITE if self.active else C_DARK};
            }}
        """)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._padding)
        self.anim.setEndValue(24 if self.active else 20)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._padding)
        self.anim.setEndValue(18 if self.active else 14)
        self.anim.start()
        super().leaveEvent(event)


class BaseProjectTrackerWindow(QMainWindow):
    PAGE_TITLE = "Project Tracker"
    ACTIVE_MENU = "Dashboard"
    SEARCH_PLACEHOLDER = "Search projects here..."

    def __init__(self):
        super().__init__()
        self.responsive_manager = get_manager(self)
        self.responsive_manager.profileChanged.connect(
            self._handle_responsive_profile_changed
        )
        self.setWindowTitle(f"Project Tracker DBS - {self.PAGE_TITLE}")
        self.resize(*screen_fraction(0.85, 0.90))
        self.setMinimumSize(*screen_fraction(0.50, 0.50))
        self.setFont(QFont("Inter", scaled_font(8)))
        self.setStyleSheet(self.get_stylesheet())
        center_window(self)

        QApplication.instance().installEventFilter(self)

        self.sidebar_expanded = True
        self.nav_buttons = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(scaled(0))

        self.sidebar = self.build_sidebar()
        main_layout.addWidget(self.sidebar)

        self.main_wrapper = QFrame()
        self.main_wrapper.setObjectName("mainWrapper")
        wrapper_layout = QVBoxLayout(self.main_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(scaled(0))

        create_shadow(
            self.main_wrapper, blur_radius=25, x_offset=-6, y_offset=0, alpha=60
        )
        self.build_main_content(wrapper_layout)

        main_layout.addWidget(self.main_wrapper, 1)

    def _handle_responsive_profile_changed(self, _profile) -> None:
        self.updateGeometry()
        self.update()

    def eventFilter(self, watched, event):
        """
        Permanent focus behavior:
        - If a QLineEdit/QTextEdit is focused and user clicks anywhere else,
          clear focus so the blinking cursor disappears.
        - AnimatedSearch naturally collapses on focusOutEvent.
        - Clicking another input still focuses that next input normally.

        Table selection behavior:
        - Click valid table data/cell area  -> keep/select row.
        - Click empty table area            -> clear selection.
        - Click anywhere outside the table  -> clear selection.
        """
        if event.type() != event.Type.MouseButtonPress:
            return super().eventFilter(watched, event)

        if not isinstance(watched, QWidget):
            return super().eventFilter(watched, event)

        if hasattr(event, "button") and event.button() != Qt.MouseButton.LeftButton:
            return super().eventFilter(watched, event)

        # Do not interfere with dropdown/menu selection.
        if isinstance(watched, QMenu) or (
            watched.parentWidget() and isinstance(watched.parentWidget(), QMenu)
        ):
            return super().eventFilter(watched, event)

        if isinstance(watched, QComboBox) or (
            watched.parentWidget() and isinstance(watched.parentWidget(), QComboBox)
        ):
            return super().eventFilter(watched, event)

        # Clear text focus when clicking outside the currently focused text widget.
        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            clicked_same_widget = watched is focused
            clicked_child_of_focused = focused.isAncestorOf(watched)

            if not clicked_same_widget and not clicked_child_of_focused:
                focused.clearFocus()

        # Keep existing report table selection behavior.
        if hasattr(self, "active_table"):
            table = self.active_table
            viewport = table.viewport()
            global_pos = event.globalPosition().toPoint()
            viewport_pos = viewport.mapFromGlobal(global_pos)

            clicked_inside_table_viewport = viewport.rect().contains(viewport_pos)
            clicked_index = table.indexAt(viewport_pos)

            if clicked_inside_table_viewport and clicked_index.isValid():
                table.setCurrentIndex(clicked_index)
                table.selectRow(clicked_index.row())
            else:
                table.clearSelection()
                table.setCurrentItem(None)

        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        if hasattr(self, "workspace_layout"):
            self.workspace_layout.setContentsMargins(
                scaled(16), scaled(16), scaled(16), scaled(16)
            )
            self.workspace_layout.setSpacing(scaled(12))

        if hasattr(self, "header_layout"):
            self.header_layout.setContentsMargins(
                margin_inner(), margin_inner(), margin_inner(), margin_inner()
            )
            self.header_layout.setSpacing(spacing_tight())

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sidebar.setMinimumWidth(scaled(SIDEBAR_EXPANDED_WIDTH))

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(scaled(4), scaled(0), scaled(4), scaled(0))
        title_layout.setSpacing(spacing_tight())

        self.logo = QLabel()
        self.logo.setMinimumSize(scaled(14), scaled(14))
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setPixmap(qta.icon("fa5s.layer-group", color=C_ORANGE).pixmap(scaled(14), scaled(14)))
        title_layout.addWidget(self.logo)

        self.app_title = QLabel("Project Tracker")
        self.app_title.setObjectName("appTitle")
        self.app_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_layout.addWidget(self.app_title)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addSpacing(scaled(14))

        nav_items = [
            ("Dashboard", "fa5s.chart-pie"),
            ("Project Details", "fa5s.folder-open"),
            ("Second Brain", "fa5s.brain"),
            ("Report", "fa5s.chart-bar"),
            ("Automations", "fa5s.robot"),
            ("Settings", "fa5s.cog"),
        ]

        for text, icon in nav_items:
            btn = SidebarButton(text, icon, text == self.ACTIVE_MENU)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        self.notification_icon_btn = SidebarButton(
            "Notifications", "fa5s.bell", False
        )
        self.notification_icon_btn.set_collapsed(True)
        self.notification_icon_btn.hide()
        layout.addWidget(self.notification_icon_btn)

        layout.addSpacing(scaled(6))

        self.notif_frame = self.build_notification_panel()
        layout.addWidget(self.notif_frame, 1)

        self.sidebar_bottom_spacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        layout.addItem(self.sidebar_bottom_spacer)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-left", color=C_LIGHT))
        self.collapse_btn.setIconSize(QSize(scaled(8), scaled(8)))
        self.collapse_btn.setObjectName("collapseButton")
        self.collapse_btn.setMinimumHeight(scaled(26))
        self.collapse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.collapse_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.collapse_btn)

        return sidebar

    def build_notification_panel(self):
        frame = QFrame()
        frame.setObjectName("notifFrame")
        frame.setMinimumHeight(scaled(NOTIFICATION_MIN_HEIGHT))
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        create_shadow(frame, blur_radius=35, x_offset=0, y_offset=10, alpha=95)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())

        header = QHBoxLayout()
        header.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.bell", color=C_ORANGE).pixmap(scaled(12), scaled(12)))
        header.addWidget(icon)

        title = QLabel("Notifications")
        title.setObjectName("notifTitle")
        header.addWidget(title)
        header.addStretch()

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("textButtonLight")
        dismiss_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        header.addWidget(dismiss_btn)

        layout.addLayout(header)

        self.notif_scroll = QScrollArea()
        self.notif_scroll.setObjectName("notifScroll")
        self.notif_scroll.setWidgetResizable(True)
        self.notif_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.notif_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.notif_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.notif_scroll.viewport().setObjectName("notifViewport")
        self.notif_scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("notifContent")
        content.setAutoFillBackground(False)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(scaled(0), scaled(0), scaled(4), scaled(0))
        content_layout.setSpacing(spacing_tight())
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        empty = QLabel("No notifications yet.")
        empty.setObjectName("emptyNotifText")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setWordWrap(True)
        empty.setMinimumHeight(scaled(80))
        content_layout.addWidget(empty)
        content_layout.addStretch(1)

        self.notif_scroll.setWidget(content)
        layout.addWidget(self.notif_scroll, 1)

        return frame

    def toggle_sidebar(self):
        expanded_before_toggle = self.sidebar_expanded
        new_width = (
            scaled(SIDEBAR_COLLAPSED_WIDTH)
            if expanded_before_toggle
            else scaled(SIDEBAR_EXPANDED_WIDTH)
        )

        self.sidebar_anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth", self)
        self.sidebar_anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        for anim in (self.sidebar_anim_min, self.sidebar_anim_max):
            anim.setDuration(220)
            anim.setStartValue(self.sidebar.width())
            anim.setEndValue(new_width)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
            anim.start()

        self.sidebar_expanded = not expanded_before_toggle
        collapsed = not self.sidebar_expanded

        for btn in self.nav_buttons:
            btn.set_collapsed(collapsed)

        if collapsed:
            self.app_title.hide()
            self.notif_frame.hide()
            self.notification_icon_btn.show()
            self.sidebar_bottom_spacer.changeSize(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
            )
            self.collapse_btn.setIcon(
                qta.icon("fa5s.angle-double-right", color=C_LIGHT)
            )
        else:
            self.app_title.show()
            self.notification_icon_btn.hide()
            self.notif_frame.show()
            self.sidebar_bottom_spacer.changeSize(
                0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
            )
            self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-left", color=C_LIGHT))

        self.sidebar.layout().invalidate()

    def build_main_content(self, parent_layout):
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        create_shadow(self.header_frame, blur_radius=20, y_offset=5, alpha=50)

        header_layout = QGridLayout(self.header_frame)
        self.header_layout = header_layout
        header_layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        header_layout.setHorizontalSpacing(spacing_tight())
        header_layout.setVerticalSpacing(0)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(2, 1)

        title_box = QFrame()
        title_box.setObjectName("headerTitleBox")
        title_layout = QHBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(spacing_tight())
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        marker = QFrame()
        marker.setObjectName("pageTitleDivider")
        marker.setMinimumWidth(scaled(4))
        marker.setMaximumWidth(scaled(4))
        marker.setMinimumHeight(scaled(26))
        marker.setMaximumHeight(scaled(26))
        title_layout.addWidget(marker)

        title = QLabel(f"{self.PAGE_TITLE}.")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Inter", scaled_font(16), QFont.Weight.Bold))
        title_layout.addWidget(title)

        header_layout.addWidget(
            title_box,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        header_layout.addWidget(
            DateTimeBadge(),
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        header_layout.addWidget(
            RefreshButton(),
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        parent_layout.addWidget(self.header_frame)

        self.workspace = QWidget()
        self.workspace.setObjectName("workspaceArea")
        self.workspace_layout = QVBoxLayout(self.workspace)
        self.workspace_layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        self.workspace_layout.setSpacing(scaled(12))

        self.build_page(self.workspace_layout)

        parent_layout.addWidget(self.workspace, 1)
        self.header_frame.raise_()
        self._apply_responsive_layout()

    def build_page(self, layout):
        raise NotImplementedError

    def secondary_button(self, text, icon_name=None):
        btn = QPushButton(text)
        btn.setObjectName("secondaryButton")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumHeight(scaled(36))
        if icon_name:
            btn.setIcon(qta.icon(icon_name, color=C_DARK))
        return btn

    def primary_button(self, text, icon_name="fa5s.plus"):
        btn = AnimatedPrimaryButton(f" {text}", icon_name)
        btn.setMinimumHeight(scaled(26))
        return btn

    def tiny_button(self, text, icon_name=None, danger=False):
        btn = QPushButton(text)
        btn.setObjectName("dangerButton" if danger else "tinyButton")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumHeight(scaled(14))
        if icon_name:
            btn.setIcon(qta.icon(icon_name, color=C_WHITE if danger else C_DARK))
        return btn

    def line_edit(self, placeholder="", text=""):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setText(text)
        edit.setMinimumHeight(scaled(26))
        return edit

    def field(self, label_text, widget):
        wrapper = QFrame()
        wrapper.setObjectName("fieldWrapper")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def aligned_control(self, widget):
        """Align action buttons with form controls that have labels above them."""
        wrapper = QFrame()
        wrapper.setObjectName("fieldWrapper")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        spacer_label = QLabel(" ")
        spacer_label.setObjectName("fieldLabel")
        layout.addWidget(spacer_label)
        layout.addWidget(widget)
        return wrapper

    def make_combo(self, items, width=150):
        combo = ModernComboBox()
        combo.addItems(items)
        combo.setMinimumWidth(width)
        return combo

    def make_filter_combo(self, items, width=150):
        combo = ModernComboBox()
        combo.setObjectName("filterCombo")
        combo.addItems(items)
        combo.setMinimumWidth(width)
        combo.setMinimumHeight(scaled(26))
        combo.view().setObjectName("filterComboPopup")
        combo.view().setStyleSheet(f"""
            QListView#filterComboPopup {{
                background-color: {C_WHITE};
                color: {C_DARK};
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                padding: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
                outline: none;
            }}
            QListView#filterComboPopup::item {{
                min-height: {scaled(14)}px;
                padding: {scaled(4)}px {scaled(6)}px;
                color: {C_DARK};
                background: transparent;
                border-radius: {scaled(4)}px;
            }}
            QListView#filterComboPopup::item:hover {{
                background-color: {C_DARK};
                color: {C_LIGHT};
            }}
            QListView#filterComboPopup::item:selected {{
                background-color: {C_DARK};
                color: {C_LIGHT};
            }}
        """)
        return combo

    def make_table(self, rows, columns, headers):
        table = ClearableSelectionTable(rows, columns)
        table.setHorizontalHeaderLabels(headers)
        table.setObjectName("dataTable")
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setWordWrap(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setMinimumSectionSize(scaled(72))
        for column in range(columns):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setDefaultSectionSize(scaled(56))
        return table

    def get_stylesheet(self):
        return f"""
            * {{
                font-family: "Inter", "Segoe UI", sans-serif;
            }}
            QMainWindow {{
                background-color: {C_DARK};
            }}
            #sidebar {{
                background-color: {C_BLACK_CHROME};
                border-right: 1px solid {C_DARK_BORDER};
            }}
            #mainWrapper {{
                background-color: {C_MAIN_BG};
            }}
            #workspaceArea {{
                background-color: {C_MAIN_BG};
            }}
            #headerFrame {{
                background-color: {C_ORANGE};
                border-bottom: 1px solid {C_RED_HOVER};
            }}
            #appTitle {{
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
                color: {C_LIGHT};
            }}
            #headerTitleBox {{
                background: transparent;
                border: none;
            }}
            #pageTitleDivider, #headerTitleMarker {{
                background-color: {C_DARK};
                border-radius: {scaled(2)}px;
            }}
            #pageTitle, #headerTitle {{
                color: {C_WHITE};
                font-size: {scaled_font(16)}pt;
                font-weight: 900;
                letter-spacing: {scaled(1)}px;
            }}
            #titleDateTimeBox {{
                background-color: transparent;
                border: none;
                border-radius: {scaled(6)}px;
            }}
            #titleDateTimeBox:hover {{
                background-color: transparent;
            }}
            #headerActionBox {{
                background-color: transparent;
                border: none;
                border-radius: {scaled(6)}px;
            }}
            #headerActionBox:hover {{
                background-color: transparent;
            }}
            #dateTimeBadge {{
                background-color: {C_WHITE};
                border-radius: {scaled(6)}px;
                border: {scaled(1)}px solid {C_DARK};
            }}
            #dateTimeIcon {{
                background: transparent;
            }}
            #dateTimeLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #notifFrame {{
                background-color: {C_NOTIFICATION_BG};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_NOTIFICATION_BORDER};
            }}
            #notifTitle {{
                color: {C_WHITE};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #emptyNotifText {{
                color: {C_TEXT_MUTED};
                font-size: {scaled_font(8)}pt;
                font-weight: 600;
                padding: {scaled(8)}px {scaled(4)}px;
            }}
            #notifScroll, #notifViewport, #notifContent {{
                background: transparent;
                border: none;
            }}
            #collapseButton {{
                padding: {scaled(4)}px;
                background-color: transparent;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
            }}
            #collapseButton:hover {{
                background-color: {C_OLIVE};
            }}
            #headerRefreshButton {{
                min-width: {scaled(26)}px;
                min-height: {scaled(26)}px;
                padding: {scaled(4)}px;
                background-color: {C_WHITE};
                border: 1px solid {C_DARK};
                border-radius: {scaled(4)}px;
            }}
            #headerRefreshButton:hover {{
                background-color: {C_MAIN_BG};
            }}
            #pageNavButton {{
                min-width: {scaled(26)}px;
                min-height: {scaled(26)}px;
                max-width: {scaled(26)}px;
                max-height: {scaled(26)}px;
                padding: {scaled(4)}px;
                background-color: transparent;
                border: none;
                border-radius: {scaled(21)}px;
            }}
            #pageNavButton:hover {{
                background-color: rgba(45, 61, 52, 0.10);
            }}
            #panelCard, #metricCard {{
                background-color: {C_INNER_CARD_BG};
                border-radius: {scaled(7)}px;
                border-top: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-right: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-bottom: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            #automationTabInner {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_LIGHT_BORDER};
            }}
            #emptyPanel {{
                background-color: rgba(227, 230, 228, 0.42);
                border-radius: {scaled(6)}px;
                border: 1px solid rgba(45, 61, 52, 0.08);
            }}
            #metricInner {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_LIGHT_BORDER};
            }}
            #metricInner:hover {{
                background-color: rgba(227, 230, 228, 0.74);
            }}
            #cardTitle {{
                background: transparent;
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #cardSubtitle {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #metricIcon {{
                background: {C_SOFT_PINK_SURFACE};
                border-radius: {scaled(6)}px;
            }}
            #metricValue {{
                color: {C_DARK};
                font-size: {scaled_font(12)}pt;
                font-weight: 900;
            }}
            #metricLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #metricHelper {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #chartPlaceholder {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border: 1px solid {C_LIGHT_BORDER};
                border-radius: {scaled(6)}px;
            }}
            #summaryRow {{
                min-height: {scaled(24)}px;
                max-height: {scaled(36)}px;
                background-color: {C_ORANGE};
                border-radius: {scaled(4)}px;
                border: 1px solid rgba(255, 255, 255, 0.22);
            }}
            #summaryRow:hover {{
                background-color: {C_DARK_BORDER};
            }}
            #summaryRowLabel {{
                color: {C_WHITE};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #summaryRowValue {{
                color: {C_WHITE};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                min-width: {scaled(14)}px;
            }}
            QLineEdit, QTextEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 600;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {C_ORANGE};
                background: {C_WHITE};
            }}
            QComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_DARK};
                font-weight: 700;
            }}
            QComboBox:hover {{
                background: {C_WHITE};
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
            QComboBox#filterCombo {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            QComboBox#filterCombo:hover {{
                background: {C_SOFT_PINK_SURFACE};
                border: 1px solid {C_SOFT_PINK_BORDER};
            }}
            QComboBox#filterCombo::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
            #reportTableInner {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_LIGHT_BORDER};
            }}
            #secondaryButton, #tinyButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            #secondaryButton:hover, #tinyButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            #dangerButton {{
                background: #B5382F;
                color: {C_WHITE};
                border: none;
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            #dangerButton:hover {{
                background: #942D26;
            }}
            #textButtonLight {{
                border: none;
                background: transparent;
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                padding: {scaled(1)}px {scaled(0)}px;
            }}
            #textButtonLight:hover {{
                color: {C_ORANGE};
                text-decoration: underline;
            }}
            #fieldLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                text-transform: uppercase;
            }}
            #fieldWrapper {{
                background: transparent;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: rgba(208, 212, 210, 0.82);
                color: {C_DARK};
                padding: {scaled(4)}px {scaled(8)}px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 800;
            }}
            QTabBar::tab:selected {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
            }}
            QTableWidget#dataTable {{
                border: 1px solid {C_INPUT_BORDER};
                border-left: 1px solid {C_OLIVE};
                background-color: rgba(227, 230, 228, 0.20);
                outline: none;
                border-radius: {scaled(4)}px;
                gridline-color: rgba(45, 61, 52, 0.20);
            }}
            QTableWidget#dataTable::item {{
                padding: {scaled(4)}px {scaled(4)}px;
                border-bottom: 1px solid rgba(148, 154, 137, 0.62);
                border-right: 1px solid rgba(148, 154, 137, 0.62);
                color: {C_DARK};
            }}
            QTableWidget#dataTable::item:selected {{
                background-color: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
            }}
            QHeaderView {{
                background-color: transparent;
            }}
            QHeaderView::section {{
                background-color: {C_TEXT_STRONG};
                padding: {scaled(4)}px {scaled(4)}px;
                border: none;
                border-right: 1px solid {C_DARK};
                border-bottom: 2px solid {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                color: {C_WHITE};
                text-transform: uppercase;
                qproperty-alignment: AlignCenter;
            }}
            #tableLinkEdit {{
                min-height: {scaled(24)}px;
                max-height: {scaled(24)}px;
                padding: {scaled(0)}px {scaled(6)}px;
                border: 1px solid rgba(45, 61, 52, 0.16);
                border-radius: {scaled(4)}px;
                background-color: rgba(255, 255, 255, 0.36);
                color: {C_ORANGE};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
                selection-background-color: {C_SOFT_PINK_ACCENT};
                selection-color: {C_WHITE};
            }}
            #tableLinkEdit:focus {{
                border: 1px solid {C_ORANGE};
                background-color: {C_WHITE};
                color: {C_DARK};
            }}
            QPushButton#stateCombo {{
                background: transparent;
                border: none;
                min-height: {scaled(24)}px;
                max-height: {scaled(24)}px;
            }}
            QListWidget, QTreeWidget {{
                background: {C_WHITE};
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                color: {C_DARK};
                padding: {scaled(4)}px;
                font-weight: 650;
            }}
            QListWidget::item, QTreeWidget::item {{
                min-height: {scaled(14)}px;
                padding: {scaled(4)}px;
                border-radius: {scaled(4)}px;
            }}
            QListWidget::item:selected, QTreeWidget::item:selected {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
            }}
            QCheckBox {{
                color: {C_DARK};
                font-weight: 700;
            }}
            QSpinBox {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 700;
            }}
            QSplitter#automationSplitter {{
                background: transparent;
                border: none;
            }}
            QSplitter#automationSplitter::handle {{
                background: transparent;
                border: none;
                image: none;
            }}
            QSplitter#automationSplitter::handle:horizontal {{
                width: {scaled(14)}px;
            }}
            QSplitter#automationSplitter::handle:hover,
            QSplitter#automationSplitter::handle:pressed {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: {scaled(4)}px;
                margin: 2px 0px 2px 0px;
                border-radius: {scaled(4)}px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(45, 61, 52, 0.35);
                min-height: {scaled(14)}px;
                border-radius: {scaled(4)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(45, 61, 52, 0.55);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                height: {scaled(0)}px;
            }}
        """


class EmailTemplateDialog(QDialog):
    CONDITION_OPERATORS = [
        "eq",
        "nq",
        "contains",
        "not contains",
        "starts with",
        "ends with",
        "is empty",
        "is not empty",
    ]

    def __init__(self, category, purpose, active_conditions, parent=None, is_new=False):
        super().__init__(parent)
        self.category = category
        self.is_new = is_new
        dialog_action = (
            "Add Outlook Send Category"
            if is_new
            else f"Edit Outlook Send Category - {category}"
        )
        self.setWindowTitle(dialog_action)
        self.setObjectName("templateDialog")
        screen_geo = (
            QApplication.primaryScreen().availableGeometry()
            if QApplication.primaryScreen()
            else None
        )
        if screen_geo:
            self.resize(
                min(1220, int(screen_geo.width() * 0.92)),
                min(820, int(screen_geo.height() * 0.88)),
            )
            self.setMinimumSize(
                min(920, int(screen_geo.width() * 0.74)),
                min(620, int(screen_geo.height() * 0.72)),
            )
        else:
            self.resize(1220, 820)
            self.setMinimumSize(scaled(920), scaled(620))
        QApplication.instance().installEventFilter(self)

        self.setStyleSheet(f"""
            QDialog#templateDialog {{
                background-color: {C_MAIN_BG};
            }}
            #dialogHeader {{
                background-color: {C_DARK};
                border-radius: {scaled(6)}px;
            }}
            #dialogTitle {{
                color: {C_LIGHT};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #dialogSubtitle {{
                color: rgba(208, 212, 210, 0.82);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #dialogCard {{
                background-color: {C_LIGHT};
                border: 1px solid rgba(45, 61, 52, 0.18);
                border-radius: {scaled(6)}px;
            }}
            #dialogInner {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_LIGHT_BORDER};
            }}
            #sectionTitle {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #hintText {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #modeOption {{
                background-color: rgba(227, 230, 228, 0.66);
                border: 1px solid rgba(45, 61, 52, 0.12);
                border-radius: {scaled(4)}px;
            }}
            #modeOption:hover {{
                background-color: rgba(188, 108, 44, 0.10);
                border: 1px solid rgba(188, 108, 44, 0.28);
            }}
            #placeholderChip {{
                background-color: rgba(188, 108, 44, 0.12);
                color: {C_ORANGE};
                border: 1px dashed rgba(188, 108, 44, 0.60);
                border-radius: {scaled(6)}px;
                padding: {scaled(4)}px {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #placeholderChip:hover {{
                background-color: rgba(188, 108, 44, 0.22);
            }}
            QLineEdit, QTextEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 700;
                min-height: {scaled(14)}px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {C_ORANGE};
                background: {C_WHITE};
            }}
            QCheckBox, QRadioButton {{
                color: {C_DARK};
                font-weight: 800;
            }}
            QPushButton#secondaryButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            QPushButton#secondaryButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            QPushButton#saveButton {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
                border: none;
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(4)}px {scaled(8)}px;
            }}
            QPushButton#saveButton:hover {{
                background: {C_ORANGE_DARK};
            }}
            QComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        root.setSpacing(spacing_tight())

        header = QFrame()
        header.setObjectName("dialogHeader")
        create_shadow(header, blur_radius=18, x_offset=0, y_offset=5, alpha=50)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        header_layout.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.envelope", color=C_ORANGE).pixmap(scaled(14), scaled(14)))
        header_layout.addWidget(icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(scaled(1))
        title = QLabel(dialog_action)
        title.setObjectName("dialogTitle")
        title_col.addWidget(title)

        subtitle = QLabel(purpose)
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col, 1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color=C_LIGHT))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumSize(scaled(36), scaled(36))
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(spacing_tight())

        left = QVBoxLayout()
        left.setSpacing(spacing_tight())

        template_card = self.build_dialog_card("Template", "fa5s.file-alt")
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(12)
        form_grid.setVerticalSpacing(12)

        self.category_code = QLineEdit()
        self.category_code.setPlaceholderText("Example: ACK_UAT")
        self.category_code.setText("" if is_new else category)

        self.to_edit = QLineEdit()
        self.to_edit.setPlaceholderText("manager@example.com; team@example.com")
        self.cc_edit = QLineEdit()
        self.cc_edit.setPlaceholderText("optional cc list")
        self.subject_edit = QLineEdit()
        self.subject_edit.setText(f"[{category}] <PROJECT_NAME> - <CR_NUMBER>")

        form_grid.addWidget(
            self.dialog_field("Category Code *", self.category_code), 0, 0
        )
        form_grid.addWidget(self.dialog_field("To *", self.to_edit), 0, 1)
        form_grid.addWidget(self.dialog_field("CC", self.cc_edit), 1, 0)
        form_grid.addWidget(self.dialog_field("Subject *", self.subject_edit), 1, 1)

        template_card.outer_layout.addLayout(form_grid)

        body_header = QHBoxLayout()
        body_title = QLabel("Body *")
        body_title.setObjectName("sectionTitle")
        body_header.addWidget(body_title)
        body_header.addStretch()

        self.use_html = QCheckBox("Use HTML file")
        self.use_html.toggled.connect(self.toggle_html_file)
        body_header.addWidget(self.use_html)
        template_card.outer_layout.addLayout(body_header)

        self.body_editor = QTextEdit()
        self.body_editor.setMinimumHeight(scaled(120))
        self.body_editor.setPlaceholderText("Write plain text body template here...")
        self.body_editor.setPlainText(
            "Dear Team,\n\nPlease review <PROJECT_NAME> for CR <CR_NUMBER>.\n\nRegards,\nProject Tracker"
        )
        template_card.outer_layout.addWidget(self.body_editor)

        self.html_file_row = QFrame()
        self.html_file_row.setObjectName("dialogInner")
        html_layout = QHBoxLayout(self.html_file_row)
        html_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        html_layout.setSpacing(spacing_tight())

        self.html_path = QLineEdit()
        self.html_path.setPlaceholderText("Select HTML template file...")
        self.html_path.setReadOnly(True)
        html_layout.addWidget(self.html_path, 1)

        browse_html = QPushButton("Browse HTML")
        browse_html.setObjectName("secondaryButton")
        browse_html.clicked.connect(self.browse_html_file)
        html_layout.addWidget(browse_html)

        self.html_file_row.setVisible(False)
        template_card.outer_layout.addWidget(self.html_file_row)

        placeholder_label = QLabel("Placeholders (click to insert):")
        placeholder_label.setObjectName("hintText")
        template_card.outer_layout.addWidget(placeholder_label)

        chips = QHBoxLayout()
        chips.setSpacing(spacing_tight())
        for placeholder in [
            "<PROJECT_NAME>",
            "<CR_NUMBER>",
            "<CR_LINK>",
            "<DRONE_TICKET>",
            "<DRONE_STATE>",
            "<START_DATETIME>",
            "<END_DATETIME>",
        ]:
            chip = QPushButton(placeholder)
            chip.setObjectName("placeholderChip")
            chip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            chip.clicked.connect(
                lambda checked=False, p=placeholder: self.insert_placeholder(p)
            )
            chips.addWidget(chip)
        chips.addStretch()
        template_card.outer_layout.addLayout(chips)

        left.addWidget(template_card, 3)

        file_card = self.build_dialog_card(
            "Attachment & Email Automation Mode", "fa5s.paperclip"
        )
        file_card.outer_layout.addWidget(
            self.attachment_field("Attachment Path", "Optional attachment path...")
        )

        mode_title = QLabel("Email Automation Mode")
        mode_title.setObjectName("sectionTitle")
        file_card.outer_layout.addWidget(mode_title)

        self.mode_group = QButtonGroup(self)
        self.draft_radio = QRadioButton("Draft Only")
        self.send_radio = QRadioButton("Send Immediately")
        self.draft_radio.setChecked(True)
        self.mode_group.addButton(self.draft_radio, 0)
        self.mode_group.addButton(self.send_radio, 1)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(spacing_tight())
        mode_row.addWidget(
            self.mode_option(
                self.draft_radio,
                "If condition meets, automatically show a draft email popup that you must check before clicking Send.",
            )
        )
        mode_row.addWidget(
            self.mode_option(
                self.send_radio,
                "If condition meets, automatically send this email without extra confirmation.",
            )
        )
        file_card.outer_layout.addLayout(mode_row)
        left.addWidget(file_card)

        content.addLayout(left, 6)

        right = QVBoxLayout()
        right.setSpacing(spacing_tight())

        condition_card = self.build_dialog_card("Active Conditions", "fa5s.filter")
        condition_hint = QLabel(
            "Rules are evaluated before draft/send automation runs."
        )
        condition_hint.setObjectName("hintText")
        condition_card.outer_layout.addWidget(condition_hint)

        condition_grid = QGridLayout()
        condition_grid.setHorizontalSpacing(10)
        condition_grid.setVerticalSpacing(10)

        self.cr_operator = self.condition_combo(self.CONDITION_OPERATORS)
        self.cr_state = self.condition_combo(
            [
                "PENDING SUBMISSION",
                "IN-PROGRESS",
                "APPROVED",
                "REJECTED",
                "IMPLEMENTED",
                "POSTPONED",
            ]
        )
        self.cr_state.setCurrentText("PENDING SUBMISSION")

        self.drone_operator = self.condition_combo(self.CONDITION_OPERATORS)
        self.drone_state = self.condition_combo(
            [
                "PENDING APPROVAL",
                "IN-PROGRESS",
                "APPROVED",
                "REJECTED",
                "UAT",
                "SIT",
                "PROD READY",
                "IGNORED",
            ]
        )
        self.drone_state.setCurrentText("PENDING APPROVAL")

        self.project_operator = self.condition_combo(self.CONDITION_OPERATORS)
        self.project_pattern = QLineEdit()
        self.project_pattern.setPlaceholderText("Pattern, regex, or project name...")

        condition_grid.addWidget(self.dialog_field("CR State", self.cr_operator), 0, 0)
        condition_grid.addWidget(self.dialog_field("Value", self.cr_state), 0, 1)
        condition_grid.addWidget(
            self.dialog_field("Drone State", self.drone_operator), 1, 0
        )
        condition_grid.addWidget(self.dialog_field("Value", self.drone_state), 1, 1)
        condition_grid.addWidget(
            self.dialog_field("Project Name", self.project_operator), 2, 0
        )
        condition_grid.addWidget(
            self.dialog_field("Pattern", self.project_pattern), 2, 1
        )

        condition_card.outer_layout.addLayout(condition_grid)

        condition_preview = QFrame()
        condition_preview.setObjectName("dialogInner")
        cp = QVBoxLayout(condition_preview)
        cp.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        cp.setSpacing(spacing_tight())

        preview_title = QLabel("Current Category Baseline")
        preview_title.setObjectName("sectionTitle")
        cp.addWidget(preview_title)

        self.condition_preview_body = QLabel(active_conditions)
        self.condition_preview_body.setObjectName("hintText")
        self.condition_preview_body.setWordWrap(True)
        cp.addWidget(self.condition_preview_body)

        condition_card.outer_layout.addWidget(condition_preview)

        for combo in [
            self.cr_operator,
            self.cr_state,
            self.drone_operator,
            self.drone_state,
            self.project_operator,
        ]:
            combo.currentTextChanged.connect(self.update_condition_preview)
        self.project_pattern.textChanged.connect(self.update_condition_preview)
        self.category_code.textChanged.connect(self.update_condition_preview)
        self.update_condition_preview()

        right.addWidget(condition_card)

        log_card = self.build_dialog_card("Email Automation Log", "fa5s.history")
        log_hint = QLabel(
            "Detailed activity log for this category: template edits, changed fields, condition matches, draft/send activity, and download-email triggers."
        )
        log_hint.setObjectName("hintText")
        log_hint.setWordWrap(True)
        log_card.outer_layout.addWidget(log_hint)

        log_lines = QListWidget()
        log_lines.addItems(
            [
                "Fri, 22 May 2026 05:41:02 | Template opened for editing",
                "Fri, 22 May 2026 05:38:44 | Condition matched: CR=PENDING SUBMISSION, Drone=PENDING APPROVAL",
                "Fri, 22 May 2026 05:38:45 | Draft email created and linked to Project Details activity history",
                "Fri, 22 May 2026 05:39:10 | Download email job started: waiting for matching reply pattern",
            ]
        )
        log_lines.setMinimumHeight(scaled(120))
        log_card.outer_layout.addWidget(log_lines, 1)
        right.addWidget(log_card, 1)

        content.addLayout(right, 4)
        root.addLayout(content, 1)

        footer = QHBoxLayout()
        footer.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setMinimumHeight(scaled(26))
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)

        save = QPushButton("Save")
        save.setObjectName("saveButton")
        save.setIcon(qta.icon("fa5s.save", color=C_WHITE))
        save.setMinimumHeight(scaled(26))
        save.clicked.connect(self.accept)
        footer.addWidget(save)

        root.addLayout(footer)

    def eventFilter(self, watched, event):
        if event.type() != event.Type.MouseButtonPress:
            return super().eventFilter(watched, event)
        if not isinstance(watched, QWidget):
            return super().eventFilter(watched, event)
        if hasattr(event, "button") and event.button() != Qt.MouseButton.LeftButton:
            return super().eventFilter(watched, event)
        if isinstance(watched, QMenu) or (
            watched.parentWidget() and isinstance(watched.parentWidget(), QMenu)
        ):
            return super().eventFilter(watched, event)
        if isinstance(watched, QComboBox) or (
            watched.parentWidget() and isinstance(watched.parentWidget(), QComboBox)
        ):
            return super().eventFilter(watched, event)

        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            clicked_same_widget = watched is focused
            clicked_child_of_focused = focused.isAncestorOf(watched)
            if not clicked_same_widget and not clicked_child_of_focused:
                focused.clearFocus()
        return super().eventFilter(watched, event)

    def build_dialog_card(self, title, icon_name):
        card = QFrame()
        card.setObjectName("dialogCard")
        create_shadow(card, blur_radius=16, x_offset=0, y_offset=5, alpha=32)
        card.outer_layout = QVBoxLayout(card)
        card.outer_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        card.outer_layout.setSpacing(spacing_tight())

        header = QHBoxLayout()
        header.setSpacing(spacing_tight())
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12)))
        header.addWidget(icon)

        label = QLabel(title)
        label.setObjectName("sectionTitle")
        header.addWidget(label)
        header.addStretch()
        card.outer_layout.addLayout(header)
        return card

    def dialog_field(self, label_text, widget):
        wrapper = QFrame()
        wrapper.setObjectName("fieldWrapper")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        if isinstance(widget, (QLineEdit, QComboBox)):
            widget.setMinimumHeight(scaled(8))
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(widget)
        return wrapper

    def attachment_field(self, label_text, placeholder):
        wrapper = QFrame()
        wrapper.setObjectName("fieldWrapper")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(spacing_tight())

        self.attachment_path = QLineEdit()
        self.attachment_path.setPlaceholderText(placeholder)
        self.attachment_path.setMinimumHeight(scaled(8))
        row.addWidget(self.attachment_path, 1)

        browse = QPushButton("Browse")
        browse.setObjectName("secondaryButton")
        browse.setMinimumSize(scaled(96), scaled(8))
        browse.clicked.connect(self.browse_attachment)
        row.addWidget(browse)

        layout.addLayout(row)
        return wrapper

    def mode_option(self, radio, description):
        frame = QFrame()
        frame.setObjectName("modeOption")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())
        layout.addWidget(radio)

        desc = QLabel(description)
        desc.setObjectName("hintText")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        return frame

    def condition_combo(self, values):
        combo = ModernComboBox()
        combo.addItems(values)
        combo.setMinimumHeight(scaled(26))
        combo.setMinimumWidth(scaled(180))
        return combo

    def update_condition_preview(self):
        category = self.category_code.text().strip() or self.category or "NEW_CATEGORY"
        project_pattern = self.project_pattern.text().strip() or "(any project)"
        self.condition_preview_body.setText(
            f"{category}: CR State {self.cr_operator.currentText()} {self.cr_state.currentText()}; "
            f"Drone State {self.drone_operator.currentText()} {self.drone_state.currentText()}; "
            f"Project Name {self.project_operator.currentText()} {project_pattern}"
        )

    def insert_placeholder(self, placeholder):
        if self.body_editor.isReadOnly():
            self.subject_edit.insert(placeholder)
            return

        cursor = self.body_editor.textCursor()
        cursor.insertText(placeholder)
        self.body_editor.setTextCursor(cursor)

    def toggle_html_file(self, checked):
        self.body_editor.setReadOnly(checked)
        self.body_editor.setEnabled(not checked)
        self.html_file_row.setVisible(checked)

        if checked:
            self.body_editor.setPlaceholderText(
                "HTML file mode enabled. Select an HTML file below."
            )
        else:
            self.body_editor.setPlaceholderText(
                "Write plain text body template here..."
            )

    def browse_html_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HTML Template",
            "",
            "HTML Files (*.html *.htm);;All Files (*)",
        )
        if path:
            self.html_path.setText(path)

    def browse_attachment(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Attachment",
            "",
            "All Files (*)",
        )
        if path:
            self.attachment_path.setText(path)


class TeamsRuleDialog(QDialog):
    CONDITION_OPERATORS = [
        "eq",
        "nq",
        "contains",
        "not contains",
        "starts with",
        "ends with",
    ]
    EXISTS_OPERATORS = ["exists", "not exists"]
    CR_STATES = [
        "PENDING SUBMISSION",
        "IN-PROGRESS",
        "APPROVED",
        "REJECTED",
        "IMPLEMENTED",
        "POSTPONED",
    ]
    DRONE_STATES = [
        "PENDING APPROVAL",
        "IN-PROGRESS",
        "APPROVED",
        "REJECTED",
        "UAT",
        "SIT",
        "PROD READY",
        "IGNORED",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Teams Rule")
        self.setObjectName("teamsRuleDialog")
        self.setMinimumSize(scaled(820), scaled(420))

        self.setStyleSheet(f"""
            QDialog#teamsRuleDialog {{
                background-color: {C_MAIN_BG};
            }}
            #teamsRuleHeader {{
                background-color: {C_DARK};
                border-radius: {scaled(6)}px;
            }}
            #teamsRuleTitle {{
                color: {C_LIGHT};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #teamsRuleSubtitle {{
                color: rgba(208, 212, 210, 0.82);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #teamsRuleCard {{
                background-color: {C_INNER_CARD_BG};
                border-radius: {scaled(7)}px;
                border-top: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-right: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-bottom: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            QLineEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 700;
            }}
            QLineEdit:focus {{
                border: 2px solid {C_ORANGE};
                background: {C_WHITE};
            }}
            QPushButton#secondaryButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            QPushButton#secondaryButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            QPushButton#saveButton {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
                border: none;
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(4)}px {scaled(8)}px;
            }}
            QPushButton#saveButton:hover {{
                background: {C_ORANGE_DARK};
            }}
            QComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        root.setSpacing(spacing_tight())

        header = QFrame()
        header.setObjectName("teamsRuleHeader")
        create_shadow(header, blur_radius=18, x_offset=0, y_offset=5, alpha=50)
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        header_l.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.filter", color=C_ORANGE).pixmap(scaled(14), scaled(14)))
        header_l.addWidget(icon)

        titles = QVBoxLayout()
        title = QLabel("Add Teams Rule")
        title.setObjectName("teamsRuleTitle")
        titles.addWidget(title)
        subtitle = QLabel("Create a dynamic rule set for Teams automation.")
        subtitle.setObjectName("teamsRuleSubtitle")
        titles.addWidget(subtitle)
        header_l.addLayout(titles, 1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color=C_LIGHT))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumSize(scaled(36), scaled(36))
        close_btn.clicked.connect(self.reject)
        header_l.addWidget(close_btn)

        root.addWidget(header)

        card = QFrame()
        card.setObjectName("teamsRuleCard")
        create_shadow(card, blur_radius=16, x_offset=0, y_offset=4, alpha=30)
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        card_l.setSpacing(spacing_tight())

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.cr_operator = ModernComboBox()
        self.cr_operator.addItems(self.CONDITION_OPERATORS)
        self.cr_value = ModernComboBox()
        self.cr_value.addItems(self.CR_STATES)
        self.cr_value.setCurrentText("PENDING SUBMISSION")

        self.file_operator = ModernComboBox()
        self.file_operator.addItems(self.EXISTS_OPERATORS)
        self.file_pattern = QLineEdit()
        self.file_pattern.setPlaceholderText("Example: *.xlsx or approval_*.pdf")

        self.drone_operator = ModernComboBox()
        self.drone_operator.addItems(self.CONDITION_OPERATORS)
        self.drone_value = ModernComboBox()
        self.drone_value.addItems(self.DRONE_STATES)
        self.drone_value.setCurrentText("PENDING APPROVAL")

        grid.addWidget(self._field("CR State", self.cr_operator), 0, 0)
        grid.addWidget(self._field("CR Value", self.cr_value), 0, 1)
        grid.addWidget(self._field("File Pattern", self.file_operator), 1, 0)
        grid.addWidget(self._field("Pattern", self.file_pattern), 1, 1)
        grid.addWidget(self._field("Drone State", self.drone_operator), 2, 0)
        grid.addWidget(self._field("Drone Value", self.drone_value), 2, 1)

        card_l.addLayout(grid)
        root.addWidget(card, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setMinimumHeight(scaled(26))
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)

        save = QPushButton("Save")
        save.setObjectName("saveButton")
        save.setMinimumHeight(scaled(26))
        save.clicked.connect(self.accept)
        footer.addWidget(save)
        root.addLayout(footer)

    def _field(self, label_text, widget):
        wrapper = QFrame()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(spacing_tight())
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        lay.addWidget(label)
        lay.addWidget(widget)
        return wrapper

    def summary(self):
        pattern = self.file_pattern.text().strip() or "(no pattern)"
        return (
            f"CR State {self.cr_operator.currentText()} {self.cr_value.currentText()} | "
            f"File Pattern {self.file_operator.currentText()} {pattern} | "
            f"Drone State {self.drone_operator.currentText()} {self.drone_value.currentText()}"
        )


class TeamsRuleRow(QFrame):
    RULE_FIELDS = ["CR State", "Drone State", "Project State", "Is File Exist"]
    CONDITIONS = ["conditions", "equals", "is not equals", "true", "false"]
    CR_STATES = [
        "PENDING SUBMISSION",
        "IN-PROGRESS",
        "APPROVED",
        "REJECTED",
        "IMPLEMENTED",
        "POSTPONED",
    ]
    DRONE_STATES = [
        "PENDING APPROVAL",
        "IN-PROGRESS",
        "APPROVED",
        "REJECTED",
        "UAT",
        "SIT",
        "PROD READY",
        "IGNORED",
    ]
    PROJECT_STATES = [
        "UAT PREPARE",
        "PROD READY",
        "IMPLEMENTED",
        "POSTPONED",
        "ON HOLD",
    ]

    def __init__(self, index=1, parent=None):
        super().__init__(parent)
        self.setObjectName("teamsRuleRow")
        create_shadow(self, blur_radius=12, x_offset=0, y_offset=3, alpha=22)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())

        idx_label = QLabel(f"{index:02d}")
        idx_label.setObjectName("ruleIndex")
        idx_label.setMinimumWidth(scaled(26))
        idx_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(idx_label)

        self.field_combo = ModernComboBox()
        self.field_combo.addItems(self.RULE_FIELDS)
        self.field_combo.setMinimumWidth(scaled(135))
        layout.addWidget(self.field_combo, 2)

        self.condition_combo = ModernComboBox()
        self.condition_combo.addItems(self.CONDITIONS)
        self.condition_combo.setMinimumWidth(scaled(145))
        layout.addWidget(self.condition_combo, 2)

        self.value_stack = QStackedWidget()
        self.value_stack.setMinimumHeight(scaled(8))
        self.cr_value = ModernComboBox()
        self.cr_value.addItems(self.CR_STATES)
        self.drone_value = ModernComboBox()
        self.drone_value.addItems(self.DRONE_STATES)
        self.project_value = ModernComboBox()
        self.project_value.addItems(self.PROJECT_STATES)
        self.file_pattern = QLineEdit()
        self.file_pattern.setPlaceholderText("File pattern, e.g. approval_*.pdf")
        self.file_pattern.setMinimumHeight(scaled(8))

        for widget in [
            self.cr_value,
            self.drone_value,
            self.project_value,
            self.file_pattern,
        ]:
            widget.setMinimumHeight(scaled(8))
            self.value_stack.addWidget(widget)
        layout.addWidget(self.value_stack, 5)

        self.field_combo.currentTextChanged.connect(self.update_value_widget)
        self.update_value_widget(self.field_combo.currentText())

    def update_value_widget(self, value):
        if value == "CR State":
            self.value_stack.setCurrentWidget(self.cr_value)
        elif value == "Drone State":
            self.value_stack.setCurrentWidget(self.drone_value)
        elif value == "Project State":
            self.value_stack.setCurrentWidget(self.project_value)
        else:
            self.value_stack.setCurrentWidget(self.file_pattern)

    def summary(self):
        field = self.field_combo.currentText()
        condition = self.condition_combo.currentText()
        if field == "Is File Exist":
            value = self.file_pattern.text().strip() or "(empty pattern)"
        elif field == "CR State":
            value = self.cr_value.currentText()
        elif field == "Drone State":
            value = self.drone_value.currentText()
        else:
            value = self.project_value.currentText()
        return f"{field} {condition} {value}"


class TeamsAutomationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rule_rows = []
        self.setWindowTitle("Teams Message Automation")
        self.setObjectName("teamsAutomationDialog")

        screen_geo = (
            QApplication.primaryScreen().availableGeometry()
            if QApplication.primaryScreen()
            else None
        )
        if screen_geo:
            self.resize(
                min(1280, int(screen_geo.width() * 0.94)),
                min(820, int(screen_geo.height() * 0.90)),
            )
            self.setMinimumSize(
                min(980, int(screen_geo.width() * 0.72)),
                min(620, int(screen_geo.height() * 0.70)),
            )
        else:
            self.resize(1280, 820)
            self.setMinimumSize(scaled(980), scaled(620))

        self.setStyleSheet(f"""
            QDialog#teamsAutomationDialog {{
                background-color: {C_MAIN_BG};
            }}
            #teamsDialogHeader {{
                background-color: {C_DARK};
                border-radius: {scaled(6)}px;
            }}
            #teamsDialogTitle {{
                color: {C_LIGHT};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #teamsDialogSubtitle {{
                color: rgba(208, 212, 210, 0.82);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #teamsDialogCard {{
                background-color: {C_INNER_CARD_BG};
                border-radius: {scaled(7)}px;
                border-top: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-right: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-bottom: {scaled(1)}px solid {C_LIGHT_BORDER};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            #sectionTitle {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #hintText {{
                color: rgba(45, 61, 52, 0.76);
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #teamsModeOption, #teamsRuleRow {{
                background-color: rgba(227, 230, 228, 0.74);
                border: 1px solid rgba(45, 61, 52, 0.14);
                border-radius: {scaled(6)}px;
            }}
            #teamsModeOption:hover, #teamsRuleRow:hover {{
                background-color: rgba(188, 108, 44, 0.08);
                border: 1px solid rgba(188, 108, 44, 0.22);
            }}
            #ruleIndex {{
                color: {C_LIGHT};
                background-color: {C_ORANGE};
                border-radius: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                padding: {scaled(4)}px;
            }}
            QLineEdit, QTextEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 700;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {C_ORANGE};
                background: {C_WHITE};
            }}
            QCheckBox, QRadioButton {{
                color: {C_DARK};
                font-weight: 800;
            }}
            QPushButton#secondaryButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            QPushButton#secondaryButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            QPushButton#dangerButton {{
                background: rgba(160, 50, 40, 0.12);
                color: #8F2A20;
                border: 1px solid rgba(160, 50, 40, 0.26);
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(4)}px {scaled(8)}px;
            }}
            QPushButton#dangerButton:hover {{
                background: #A03228;
                color: {C_WHITE};
            }}
            QPushButton#saveButton, QPushButton#addRulesButton {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_TEXT_PRIMARY};
                border: none;
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(4)}px {scaled(8)}px;
            }}
            QPushButton#saveButton:hover, QPushButton#addRulesButton:hover {{
                background: {C_ORANGE_DARK};
            }}
            QComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget,
            QScrollArea > QWidget > QWidget,
            QWidget#teamsScrollContent,
            QWidget#teamsRulesScrollContent {{
                background: transparent;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        root.setSpacing(spacing_tight())

        header = QFrame()
        header.setObjectName("teamsDialogHeader")
        create_shadow(header, blur_radius=18, x_offset=0, y_offset=5, alpha=50)
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        header_l.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.comments", color=C_ORANGE).pixmap(scaled(14), scaled(14)))
        header_l.addWidget(icon)

        titles = QVBoxLayout()
        title = QLabel("Teams Message Automation")
        title.setObjectName("teamsDialogTitle")
        titles.addWidget(title)
        subtitle = QLabel(
            "Configure Teams message purpose, delivery behavior, attachment, and dynamic rules in one professional workspace."
        )
        subtitle.setObjectName("teamsDialogSubtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(subtitle)
        header_l.addLayout(titles, 1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color=C_LIGHT))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumSize(scaled(36), scaled(36))
        close_btn.clicked.connect(self.reject)
        header_l.addWidget(close_btn)

        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }"
        )
        scroll.viewport().setAutoFillBackground(False)
        scroll_content = QWidget()
        scroll_content.setObjectName("teamsScrollContent")
        scroll_content.setAutoFillBackground(False)
        content = QHBoxLayout(scroll_content)
        content.setContentsMargins(scaled(0), scaled(0), scaled(4), scaled(0))
        content.setSpacing(spacing_tight())

        left_card = QFrame()
        left_card.setObjectName("teamsDialogCard")
        create_shadow(left_card, blur_radius=16, x_offset=0, y_offset=5, alpha=32)
        left_l = QVBoxLayout(left_card)
        left_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        left_l.setSpacing(spacing_tight())

        self.purpose_edit = QLineEdit()
        self.purpose_edit.setText(
            "Notify operation team when a CR or drone condition requires action."
        )
        self.webhook_edit = QLineEdit()
        self.webhook_edit.setPlaceholderText("https://outlook.office.com/webhook/...")
        left_l.addWidget(self._field("Automation Purpose", self.purpose_edit))
        left_l.addWidget(self._field("Webhook URL", self.webhook_edit))

        self.attachment_edit = QLineEdit()
        self.attachment_edit.setPlaceholderText("Optional attachment path...")
        left_l.addWidget(self._attachment_field())

        mode_title = QLabel("Teams Automation Mode")
        mode_title.setObjectName("sectionTitle")
        left_l.addWidget(mode_title)

        self.mode_group = QButtonGroup(self)
        self.preview_radio = QRadioButton("Preview First")
        self.send_radio = QRadioButton("Send Immediately")
        self.preview_radio.setChecked(True)
        self.mode_group.addButton(self.preview_radio, 0)
        self.mode_group.addButton(self.send_radio, 1)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(spacing_tight())
        mode_row.addWidget(
            self._mode_option(
                self.preview_radio,
                "Create a preview first so you can check the Teams message before sending.",
            )
        )
        mode_row.addWidget(
            self._mode_option(
                self.send_radio,
                "Send the Teams message immediately when the automation conditions are matched.",
            )
        )
        left_l.addLayout(mode_row)

        self.message_body = QTextEdit()
        self.message_body.setMinimumHeight(scaled(160))
        self.message_body.setPlaceholderText("Write Teams message body...")
        left_l.addWidget(self._field("Message Body", self.message_body), 1)

        content.addWidget(left_card, 6)

        right_card = QFrame()
        right_card.setObjectName("teamsDialogCard")
        create_shadow(right_card, blur_radius=16, x_offset=0, y_offset=5, alpha=32)
        right_l = QVBoxLayout(right_card)
        right_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        right_l.setSpacing(spacing_tight())

        rules_title = QLabel("Rules")
        rules_title.setObjectName("sectionTitle")
        right_l.addWidget(rules_title)

        hint = QLabel(
            "Rules work like email automation conditions. Add rows using the button below, then choose the condition field, operator, and value/pattern."
        )
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        right_l.addWidget(hint)

        add_rules_btn = QPushButton("+ Add Rules")
        add_rules_btn.setObjectName("addRulesButton")
        add_rules_btn.setMinimumHeight(scaled(8))
        add_rules_btn.clicked.connect(self._add_rule)
        right_l.addWidget(add_rules_btn)

        rules_scroll = QScrollArea()
        rules_scroll.setWidgetResizable(True)
        rules_scroll.setFrameShape(QFrame.Shape.NoFrame)
        rules_scroll.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }"
        )
        rules_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        rules_scroll.viewport().setAutoFillBackground(False)
        rules_scroll_content = QWidget()
        rules_scroll_content.setObjectName("teamsRulesScrollContent")
        rules_scroll_content.setAutoFillBackground(False)
        self.rules_layout = QVBoxLayout(rules_scroll_content)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_layout.setSpacing(spacing_tight())
        self.rules_layout.addStretch(1)
        rules_scroll.setWidget(rules_scroll_content)
        right_l.addWidget(rules_scroll, 1)

        self._add_rule()

        content.addWidget(right_card, 5)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()

        delete = QPushButton("Delete")
        delete.setObjectName("dangerButton")
        delete.setMinimumHeight(scaled(26))
        footer.addWidget(delete)

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.setMinimumHeight(scaled(26))
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)

        save = QPushButton("Save")
        save.setObjectName("saveButton")
        save.setMinimumHeight(scaled(26))
        save.clicked.connect(self.accept)
        footer.addWidget(save)
        root.addLayout(footer)

    def _field(self, label_text, widget):
        wrapper = QFrame()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(spacing_tight())
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        lay.addWidget(label)
        if isinstance(widget, (QLineEdit, QComboBox)):
            widget.setMinimumHeight(scaled(8))
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay.addWidget(widget)
        return wrapper

    def _attachment_field(self):
        wrapper = QFrame()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(spacing_tight())
        label = QLabel("Attachment")
        label.setObjectName("fieldLabel")
        lay.addWidget(label)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(spacing_tight())
        self.attachment_edit.setMinimumHeight(scaled(8))
        row.addWidget(self.attachment_edit, 1)
        browse = QPushButton("Browse")
        browse.setObjectName("secondaryButton")
        browse.setMinimumSize(scaled(96), scaled(8))
        browse.clicked.connect(self._browse_attachment)
        row.addWidget(browse, 0, Qt.AlignmentFlag.AlignBottom)
        lay.addLayout(row)
        return wrapper

    def _mode_option(self, radio, description):
        frame = QFrame()
        frame.setObjectName("teamsModeOption")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        lay.setSpacing(spacing_tight())
        lay.addWidget(radio)
        desc = QLabel(description)
        desc.setObjectName("hintText")
        desc.setWordWrap(True)
        lay.addWidget(desc)
        return frame

    def _browse_attachment(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Attachment", "", "All Files (*)"
        )
        if path:
            self.attachment_edit.setText(path)

    def _add_rule(self):
        insert_index = max(0, self.rules_layout.count() - 1)
        row = TeamsRuleRow(index=len(self.rule_rows) + 1, parent=self)
        self.rule_rows.append(row)
        self.rules_layout.insertWidget(insert_index, row)


class DownloadedEmailsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloaded Emails")
        self.setObjectName("downloadedEmailsDialog")
        self.setMinimumSize(scaled(900), scaled(650))

        self.setStyleSheet(f"""
            QDialog#downloadedEmailsDialog {{
                background-color: {C_MAIN_BG};
            }}
            #downloadDialogHeader {{
                background-color: {C_DARK};
                border-radius: {scaled(6)}px;
            }}
            #downloadDialogTitle {{
                color: {C_LIGHT};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #downloadDialogSubtitle {{
                color: rgba(208, 212, 210, 0.82);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #downloadEmailCard {{
                background-color: {C_LIGHT};
                border: 1px solid rgba(45, 61, 52, 0.18);
                border-radius: {scaled(6)}px;
            }}
            #downloadEmailInner {{
                background-color: rgba(227, 230, 228, 0.62);
                border-radius: {scaled(6)}px;
                border: 1px solid rgba(255, 255, 255, 0.30);
            }}
            #emailSubject {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #emailMeta {{
                color: rgba(45, 61, 52, 0.75);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #emailTag {{
                color: {C_WHITE};
                background-color: {C_ORANGE};
                border-radius: {scaled(4)}px;
                padding: {scaled(4)}px {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget,
            QScrollArea > QWidget > QWidget,
            QWidget#teamsScrollContent,
            QWidget#teamsRulesScrollContent {{
                background: transparent;
            }}
            QLineEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 700;
            }}
            QPushButton#secondaryButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px;
            }}
            QPushButton#secondaryButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            QComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        root.setSpacing(spacing_tight())

        header = QFrame()
        header.setObjectName("downloadDialogHeader")
        create_shadow(header, blur_radius=18, x_offset=0, y_offset=5, alpha=50)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        header_layout.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.inbox", color=C_ORANGE).pixmap(scaled(14), scaled(14)))
        header_layout.addWidget(icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(scaled(1))

        title = QLabel("Downloaded Emails")
        title.setObjectName("downloadDialogTitle")
        title_col.addWidget(title)

        subtitle = QLabel(
            "Downloaded reply emails sorted newest first by default. Related files are grouped by detected CR Number."
        )
        subtitle.setObjectName("downloadDialogSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(subtitle)

        header_layout.addLayout(title_col, 1)

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color=C_LIGHT))
        close_btn.setObjectName("secondaryButton")
        close_btn.setMinimumSize(scaled(36), scaled(36))
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        root.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(spacing_tight())

        search = QLineEdit()
        search.setPlaceholderText("Search downloaded email, CR number, subject...")
        controls.addWidget(search, 1)

        sort_combo = ModernComboBox()
        sort_combo.addItems(
            ["Newest first", "Oldest first", "CR Number A-Z", "Category A-Z"]
        )
        sort_combo.setMinimumWidth(scaled(120))
        controls.addWidget(sort_combo)

        root.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setAutoFillBackground(False)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(scaled(0), scaled(0), scaled(4), scaled(0))
        content_layout.setSpacing(spacing_tight())
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        emails = [
            {
                "subject": "Re: ACK_UAT - SOP CR - CR202604209900114",
                "meta": "Fri, 22 May 2026 05:52:18 | From: manager@example.com | CR: CR202604209900114",
                "body": "Acknowledgement reply detected. Email and attachments downloaded into folder based on detected CR Number.",
                "tag": "ACK_UAT",
            },
            {
                "subject": "Re: Technical Approval - APRVL_CR - CR202604209900114",
                "meta": "Fri, 22 May 2026 05:49:42 | From: techlead@example.com | CR: CR202604209900114",
                "body": "Technical approval reply matched by subject pattern. Evidence stored in project activity history.",
                "tag": "APRVL_CR",
            },
            {
                "subject": "Re: Routine SOP Acknowledgement - ACK_SOP",
                "meta": "Fri, 22 May 2026 05:44:31 | From: ops@example.com | CR: CR202604209900088",
                "body": "Routine SOP acknowledgement reply downloaded and linked to the matching project folder.",
                "tag": "ACK_SOP",
            },
            {
                "subject": "Re: Routine SOP Closure Approval - APRVL_SOP",
                "meta": "Fri, 22 May 2026 05:41:03 | From: approver@example.com | CR: CR202604209900076",
                "body": "Closure approval reply downloaded. Attachments indexed for later audit review.",
                "tag": "APRVL_SOP",
            },
        ]

        for email in emails:
            content_layout.addWidget(self.build_email_card(email))

        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()

        close = QPushButton("Close")
        close.setObjectName("secondaryButton")
        close.setMinimumHeight(scaled(26))
        close.clicked.connect(self.accept)
        footer.addWidget(close)

        root.addLayout(footer)

    def build_email_card(self, email):
        card = QFrame()
        card.setObjectName("downloadEmailCard")
        create_shadow(card, blur_radius=14, x_offset=0, y_offset=4, alpha=32)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        outer.setSpacing(scaled(0))

        inner = QFrame()
        inner.setObjectName("downloadEmailInner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        layout.setSpacing(spacing_tight())

        top = QHBoxLayout()
        subject = QLabel(email["subject"])
        subject.setObjectName("emailSubject")
        top.addWidget(subject, 1)

        tag = QLabel(email["tag"])
        tag.setObjectName("emailTag")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(tag)

        layout.addLayout(top)

        meta = QLabel(email["meta"])
        meta.setObjectName("emailMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        body = QLabel(email["body"])
        body.setObjectName("emailMeta")
        body.setWordWrap(True)
        layout.addWidget(body)

        outer.addWidget(inner)
        return card


class AutomationsWindow(BaseProjectTrackerWindow):
    PAGE_TITLE = "Automations"
    ACTIVE_MENU = "Automations"
    SEARCH_PLACEHOLDER = "Search automation rules..."

    SEND_CATEGORIES = [
        (
            "ACK_UAT",
            "Ask manager acknowledgement for non-SOP/per-application UAT/package readiness",
            "CR PENDING SUBMISSION; Drone PENDING APPROVAL for projects using Drone",
        ),
        (
            "ACK_SOP",
            "Ask acknowledgement for routine weekly SOP",
            "CR PENDING SUBMISSION; Drone ignored",
        ),
        (
            "APRVL_CR",
            "Ask technical approval after PROD execution for non-SOP/per-application work",
            "CR IN-PROGRESS; Drone IN-PROGRESS for projects using Drone",
        ),
        (
            "APRVL_SOP",
            "Ask technical approval for routine weekly SOP closure",
            "CR IN-PROGRESS; Drone ignored",
        ),
    ]

    def build_page(self, layout):
        self.automation_tabs = []
        self.automation_stack = QStackedWidget()
        self.automation_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        tab_inner = QFrame()
        tab_inner.setObjectName("automationTabInner")
        tab_inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_shadow(tab_inner, blur_radius=16, x_offset=0, y_offset=5, alpha=38)

        tab_layout = QHBoxLayout(tab_inner)
        tab_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        tab_layout.setSpacing(spacing_tight())

        workspace_icon = QLabel()
        workspace_icon.setPixmap(
            qta.icon("fa5s.robot", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        tab_layout.addWidget(workspace_icon)

        workspace_title = QLabel("Automation Workspace")
        workspace_title.setObjectName("cardTitle")
        workspace_title.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Black))
        tab_layout.addWidget(workspace_title)

        workspace_subtitle = QLabel("Outlook, Teams, and Reminder rules")
        workspace_subtitle.setObjectName("cardSubtitle")
        workspace_subtitle.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Bold))
        tab_layout.addWidget(workspace_subtitle)

        tab_layout.addStretch(1)

        tabs = [
            ("Outlook", "fa5s.envelope"),
            ("Teams", "fa5s.comments"),
            ("Reminder", "fa5s.bell"),
        ]

        for index, (name, icon) in enumerate(tabs):
            btn = AutomationTabButton(name, icon, active=index == 0)
            btn.clicked.connect(
                lambda checked=False, i=index: self.set_automation_tab(i)
            )
            self.automation_tabs.append(btn)
            tab_layout.addWidget(btn, 0)

        layout.addWidget(tab_inner, 0)

        self.automation_stack.addWidget(self.wrap_tab_page(self.build_outlook_tab()))
        self.automation_stack.addWidget(self.wrap_tab_page(self.build_teams_tab()))
        self.automation_stack.addWidget(self.wrap_tab_page(self.build_reminder_tab()))

        layout.addWidget(self.automation_stack, 1)

    def wrap_tab_page(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget { background: transparent; border: none; }"
        )
        scroll.viewport().setAutoFillBackground(False)
        widget.setAutoFillBackground(False)
        scroll.setWidget(widget)
        return scroll

    def set_automation_tab(self, index):
        self.automation_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.automation_tabs):
            btn.set_active(i == index)

    def build_outlook_tab(self):
        page = QWidget()
        main = QVBoxLayout(page)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(spacing_tight())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("automationSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(spacing_tight())

        send_card = PanelCard("Outlook Send Automation", "fa5s.paper-plane", "")
        send_card.outer_layout.setSpacing(spacing_tight())

        send_hint = QLabel("Double-click any row to open the automation editor.")
        send_hint.setObjectName("cardSubtitle")
        send_hint.setWordWrap(True)
        send_card.outer_layout.addWidget(send_hint)

        self.send_table = self.make_table(
            4, 3, ["CATEGORY", "PURPOSE", "ACTIVE CONDITIONS"]
        )
        self.active_table = self.send_table
        self.send_table.setMinimumHeight(scaled(120))
        self.send_table.setWordWrap(True)
        self.send_table.verticalHeader().setDefaultSectionSize(scaled(28))
        self.send_table.horizontalHeader().setMinimumSectionSize(scaled(52))
        self.send_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.send_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.send_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.send_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.send_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.send_table.cellDoubleClicked.connect(self.open_send_category_dialog)

        for row, (category, purpose, conditions) in enumerate(self.SEND_CATEGORIES):
            category_item = QTableWidgetItem(category)
            category_item.setForeground(QColor(C_ORANGE))
            category_item.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Black))
            self.send_table.setItem(row, 0, category_item)
            self.send_table.setItem(row, 1, QTableWidgetItem(purpose))
            self.send_table.setItem(row, 2, QTableWidgetItem(conditions))

        send_card.outer_layout.addWidget(self.send_table, 1)

        send_button_row = QHBoxLayout()
        send_button_row.addStretch(1)
        add_send = self.primary_button("Add Send Category", "fa5s.plus")
        add_send.clicked.connect(self.open_new_send_category_dialog)
        send_button_row.addWidget(add_send)
        send_card.outer_layout.addLayout(send_button_row)

        left.addWidget(send_card, 2)

        send_log = self.build_log_panel(
            "Send Email Automation Log",
            "fa5s.history",
            [
                "Fri, 22 May 2026 05:48:10 | ACK_UAT template edited by user",
                "Fri, 22 May 2026 05:49:02 | APRVL_CR condition matched for SOP CR",
                "Fri, 22 May 2026 05:49:04 | Draft email generated and linked to project activity history",
                "Fri, 22 May 2026 05:50:11 | Send category saved: mode Draft Only",
            ],
            min_height=scaled(170),
        )
        left.addWidget(send_log, 1)

        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(spacing_tight())

        download_card = PanelCard("Outlook Download Automation", "fa5s.download", "")
        download_card.outer_layout.setSpacing(spacing_tight())

        relation_note = QLabel(
            "Download jobs are tied to the Outlook Automation sending email."
        )
        relation_note.setObjectName("cardSubtitle")
        relation_note.setWordWrap(True)
        download_card.outer_layout.addWidget(relation_note)

        download_table = self.make_table(2, 2, ["DOWNLOAD CATEGORY", "DETAILS"])
        download_table.setMinimumHeight(scaled(120))
        download_table.setWordWrap(True)
        download_table.verticalHeader().setDefaultSectionSize(scaled(76))
        download_table.horizontalHeader().setMinimumSectionSize(scaled(52))
        download_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        download_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        download_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        download_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        download_rows = [
            (
                "ACK_REPLY_DOWNLOAD",
                "This job is triggered when ACK_UAT or ACK_SOP is triggered. It automatically downloads the received reply email into a folder based on the CR Number detected in the incoming email.",
            ),
            (
                "TECH_APPROVAL_DOWNLOAD",
                "This job is triggered when APRVL_CR or APRVL_SOP is triggered. It automatically downloads the received technical approval email into a folder based on the CR Number detected in the incoming email.",
            ),
        ]

        for r, row_data in enumerate(download_rows):
            for c, value in enumerate(row_data):
                item = QTableWidgetItem(value)
                if c == 0:
                    item.setForeground(QColor(C_ORANGE))
                    item.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Black))
                download_table.setItem(r, c, item)

        download_card.outer_layout.addWidget(download_table, 1)

        download_button_row = QHBoxLayout()
        download_button_row.addStretch(1)
        downloaded_email_btn = self.primary_button("Downloaded Email", "fa5s.inbox")
        downloaded_email_btn.clicked.connect(self.open_downloaded_emails_dialog)
        download_button_row.addWidget(downloaded_email_btn)
        download_card.outer_layout.addLayout(download_button_row)

        right.addWidget(download_card, 2)

        download_log = self.build_log_panel(
            "Download Email Tool Log",
            "fa5s.inbox",
            [
                "Fri, 22 May 2026 05:50:02 | ACK_REPLY_DOWNLOAD started: waiting for CR202604209900114 reply",
                "Fri, 22 May 2026 05:50:32 | Outlook polling cycle completed: no matching reply yet",
                "Fri, 22 May 2026 05:51:02 | Pattern checked: subject/body contains detected CR Number",
                "Fri, 22 May 2026 05:51:32 | Next poll scheduled by automation interval",
            ],
            min_height=scaled(170),
        )
        right.addWidget(download_log, 1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 5)
        main.addWidget(splitter, 1)

        health_row = QGridLayout()
        health_row.setHorizontalSpacing(scaled(6))
        health_row.setVerticalSpacing(scaled(6))
        metric_cards = [
            MetricCard("Send Categories", "4", "fa5s.paper-plane", "Ready"),
            MetricCard("Download Jobs", "0", "fa5s.download", "Waiting trigger"),
            MetricCard("HTML Templates", "0", "fa5s.file-alt", "Optional"),
            MetricCard("On Going ACK", "0", "fa5s.lock", "Acknowledgement flow"),
            MetricCard("On Going Tech LV", "0", "fa5s.history", "Tech approval flow"),
        ]
        for index, card in enumerate(metric_cards):
            health_row.addWidget(card, 0, index)
        main.addLayout(health_row, 0)

        return page

    def build_log_panel(self, title, icon_name, items, min_height=180):
        card = PanelCard(title, icon_name, "latest activity")
        log_list = QListWidget()
        log_list.setWordWrap(True)
        log_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        log_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        log_list.setMinimumHeight(scaled(min_height))
        log_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for item_text in items:
            item = QListWidgetItem(item_text)
            item.setToolTip(item_text)
            item.setSizeHint(QSize(0, control_min_height()))
            log_list.addItem(item)
        card.outer_layout.addWidget(log_list, 1)
        return card

    def open_send_category_dialog(self, row, column):
        category, purpose, conditions = self.SEND_CATEGORIES[row]
        dialog = EmailTemplateDialog(category, purpose, conditions, self, is_new=False)
        dialog.exec()

    def open_new_send_category_dialog(self):
        dialog = EmailTemplateDialog(
            "NEW_CATEGORY",
            "Create a new Outlook send automation category.",
            "Define CR/Drone/Project conditions before saving.",
            self,
            is_new=True,
        )
        dialog.exec()

    def open_downloaded_emails_dialog(self):
        dialog = DownloadedEmailsDialog(self)
        dialog.exec()

    def open_teams_automation_dialog(self):
        dialog = TeamsAutomationDialog(self)
        dialog.exec()

    def build_teams_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        launcher = PanelCard("Teams Message Automation", "fa5s.comments", "")
        purpose = QLabel(
            "Use this automation to deliver Teams notifications when CR, drone, and file rules are matched."
        )
        purpose.setObjectName("cardSubtitle")
        purpose.setWordWrap(True)
        launcher.outer_layout.addWidget(purpose)

        table_card = QFrame()
        table_card.setObjectName("metricInner")
        create_shadow(table_card, blur_radius=14, x_offset=0, y_offset=4, alpha=24)
        table_l = QVBoxLayout(table_card)
        table_l.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        table_l.setSpacing(spacing_tight())

        title = QLabel("Saved Teams Automation")
        title.setObjectName("sectionTitle")
        title.setStyleSheet(f"color: {C_DARK}; font-size: {scaled_font(8)}pt; font-weight: 900;")
        table_l.addWidget(title)

        teams_table = self.make_table(
            3, 5, ["AUTOMATION", "PURPOSE", "MODE", "ACTIVE", "LAST UPDATED"]
        )
        teams_table.setMinimumHeight(scaled(120))
        teams_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        teams_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        teams_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        teams_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        teams_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        rows = [
            (
                "ACK_TO_TEAMS",
                "Notify team when acknowledgement workflow starts",
                "Preview First",
                True,
                "Fri, 22 May 2026 05:56",
            ),
            (
                "TECH_APPROVAL_ALERT",
                "Notify technical team when approval email is required",
                "Send Immediately",
                True,
                "Fri, 22 May 2026 05:41",
            ),
            (
                "FILE_READY_BROADCAST",
                "Broadcast when required project files are detected",
                "Preview First",
                False,
                "Thu, 21 May 2026 18:22",
            ),
        ]
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                if c == 3:
                    checkbox = QCheckBox()
                    checkbox.setChecked(bool(value))
                    checkbox.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    holder = QWidget()
                    holder_layout = QHBoxLayout(holder)
                    holder_layout.setContentsMargins(0, 0, 0, 0)
                    holder_layout.addStretch(1)
                    holder_layout.addWidget(checkbox)
                    holder_layout.addStretch(1)
                    teams_table.setCellWidget(r, c, holder)
                    continue
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setForeground(QColor(C_ORANGE))
                    item.setFont(QFont("Inter", scaled_font(9), QFont.Weight.Black))
                teams_table.setItem(r, c, item)
        teams_table.cellDoubleClicked.connect(
            lambda *_: self.open_teams_automation_dialog()
        )
        table_l.addWidget(teams_table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        open_btn = self.primary_button(
            "Open Teams Automation", "fa5s.external-link-alt"
        )
        open_btn.clicked.connect(self.open_teams_automation_dialog)
        btn_row.addWidget(open_btn)
        table_l.addLayout(btn_row)
        launcher.outer_layout.addWidget(table_card)

        preview_log = self.build_log_panel(
            "Teams Automation Log",
            "fa5s.history",
            [
                "Fri, 22 May 2026 05:55:10 | Teams automation popup opened",
                "Fri, 22 May 2026 05:55:35 | Rule saved: CR State equals PENDING SUBMISSION",
                "Fri, 22 May 2026 05:56:02 | Active flag updated for FILE_READY_BROADCAST",
                "Fri, 22 May 2026 05:56:28 | Webhook configuration saved",
            ],
            min_height=260,
        )
        launcher.outer_layout.addWidget(preview_log, 1)
        layout.addWidget(launcher, 7)

        status = PanelCard("Teams Status", "fa5s.signal", "")
        status.outer_layout.addWidget(
            MetricCard("Saved Automation", "3", "fa5s.archive", "Configured flows")
        )
        status.outer_layout.addWidget(
            MetricCard("Active Automation", "2", "fa5s.toggle-on", "Ready to run")
        )
        status.outer_layout.addWidget(
            MetricCard("Deactive Automation", "1", "fa5s.toggle-off", "Paused flow")
        )
        status.outer_layout.addWidget(
            MetricCard("Last Trigger", "—", "fa5s.clock", "Waiting event")
        )
        status.outer_layout.addStretch(1)
        layout.addWidget(status, 3)

        return page

    def build_reminder_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())

        top = QHBoxLayout()
        top.setSpacing(spacing_tight())
        top.addWidget(
            MetricCard("Due Soon", "0", "fa5s.hourglass-half", "Next 10 days")
        )
        top.addWidget(
            MetricCard("Overdue", "0", "fa5s.exclamation-triangle", "Needs attention")
        )
        top.addWidget(
            MetricCard("Postponed", "0", "fa5s.pause-circle", "Deferred items")
        )
        top.addWidget(MetricCard("Reminder Rules", "0", "fa5s.bell", "No rules yet"))
        layout.addLayout(top)

        rules = PanelCard(
            "Reminder Rules", "fa5s.bell", "scheduled prompts and due date monitoring"
        )
        table = self.make_table(
            0,
            6,
            ["RULE", "PROJECT FILTER", "STATE FILTER", "SCHEDULE", "CHANNEL", "STATUS"],
        )
        table.setMinimumHeight(scaled(160))
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        rules.outer_layout.addWidget(table)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.secondary_button("Import Rule", "fa5s.file-import"))
        actions.addWidget(self.primary_button("Add Reminder", "fa5s.plus"))
        rules.outer_layout.addLayout(actions)

        layout.addWidget(rules, 1)
        return page


def create_app():
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", scaled_font(9)))
    return app


if __name__ == "__main__":
    app = create_app()
    window = AutomationsWindow()
    window.show()
    sys.exit(app.exec())
