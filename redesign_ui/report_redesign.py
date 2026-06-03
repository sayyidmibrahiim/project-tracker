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
    QCheckBox,
    QComboBox,
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
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
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
    """Small, professional button shadow.

    Buttons need a lighter shadow than panels. This keeps the UI elevated
    without making the banking-style interface look flashy.
    """
    return create_shadow(
        button, blur_radius=blur_radius, x_offset=0, y_offset=y_offset, alpha=alpha
    )


class SmoothShadowButtonMixin:
    """Smooth hover/press animation for QPushButton subclasses.

    The animation only changes shadow blur and vertical offset. It avoids
    laggy geometry jumps, so the button feels responsive but stable.
    """

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


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


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
    def __init__(self, text, icon_name, is_active=False, parent=None):
        super().__init__(parent)
        self.original_text = text
        self.icon_name = icon_name
        self.is_active = is_active
        self.is_collapsed = False

        self.setText(text)
        self.setIconSize(QSize(scaled(12), scaled(12)))
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_button_shadow(self, blur_radius=8, y_offset=1, alpha=24)

        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self.setText("" if collapsed else self.original_text)
        self.setToolTip(self.original_text if collapsed else "")
        self.update_style()

    def update_style(self):
        icon_color = C_WHITE if self.is_active else C_INACTIVE_NAV_TEXT
        self.setIcon(qta.icon(self.icon_name, color=icon_color))

        bg = C_ACTIVE_NAV_BG if self.is_active else "transparent"
        color = C_WHITE if self.is_active else C_INACTIVE_NAV_TEXT
        border_left = C_ACTIVE_RED if self.is_active else "transparent"
        align = "center" if self.is_collapsed else "left"
        pad_left = scaled(4) if self.is_collapsed else scaled(8)

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dateTimeBadge")
        self.setMinimumHeight(scaled(26))
        self.setMinimumWidth(scaled(230))

        create_shadow(self, blur_radius=10, x_offset=0, y_offset=1, alpha=28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(6), scaled(0), scaled(6), scaled(0))
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
        self.label.setMinimumWidth(scaled(170))
        layout.addWidget(self.label)

        self.locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)
        self.update_datetime()

    def update_datetime(self):
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
        icon_pixmap = qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(10), scaled(10))
        if icon_pixmap.isNull():
            icon_pixmap = qta.icon("fa5s.circle", color=C_ORANGE).pixmap(scaled(10), scaled(10))
        icon_box.setPixmap(icon_pixmap)
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
                    icon_pixmap = qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(10), scaled(10))
                except Exception:
                    icon_pixmap = qta.icon("fa5s.circle", color=C_ORANGE).pixmap(scaled(10), scaled(10))
                if icon_pixmap.isNull():
                    icon_pixmap = qta.icon("fa5s.circle", color=C_ORANGE).pixmap(scaled(10), scaled(10))
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
        w, h = screen_fraction(0.85, 0.90)
        self.resize(w, h)
        self.setMinimumSize(*screen_fraction(0.50, 0.50))
        center_window(self)
        self.setFont(QFont("Inter", scaled_font(8)))
        self.setStyleSheet(self.get_stylesheet())

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
        table.setShowGrid(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
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
                border: none;
                background-color: transparent;
                outline: none;
                border-radius: {scaled(6)}px;
            }}
            QTableWidget#dataTable::item {{
                padding: {scaled(4)}px {scaled(4)}px;
                border-bottom: 1px solid {C_OLIVE};
                border-right: 1px solid {C_OLIVE};
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
                padding: {scaled(6)}px {scaled(4)}px;
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


class ReportWindow(BaseProjectTrackerWindow):
    PAGE_TITLE = "Report"
    ACTIVE_MENU = "Report"
    SEARCH_PLACEHOLDER = "Search report data..."

    def build_page(self, layout):
        filters = PanelCard("Report Filters", "fa5s.filter", "")
        filter_row = QHBoxLayout()
        filter_row.setSpacing(spacing_tight())
        filter_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        current_year = QDateTime.currentDateTime().toString("yyyy")
        previous_year = str(int(current_year) - 1)
        next_year = str(int(current_year) + 1)

        search_box = self.line_edit("Search project, CR, ticket...")
        search_box.setMinimumWidth(scaled(180))

        search_group = QFrame()
        search_group.setObjectName("fieldWrapper")
        search_group_layout = QVBoxLayout(search_group)
        search_group_layout.setContentsMargins(0, 0, 0, 0)
        search_group_layout.setSpacing(spacing_tight())

        search_label = QLabel("Search")
        search_label.setObjectName("fieldLabel")
        search_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        search_group_layout.addWidget(search_label)

        search_action_row = QHBoxLayout()
        search_action_row.setContentsMargins(0, 0, 0, 0)
        search_action_row.setSpacing(spacing_tight())
        search_action_row.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        search_action_row.addWidget(search_box)

        clear_btn = AnimatedPrimaryButton(" Clear", "fa5s.eraser")
        clear_btn.setMinimumWidth(scaled(96))
        clear_btn.setMinimumHeight(scaled(26))
        search_action_row.addWidget(clear_btn)

        search_group_layout.addLayout(search_action_row)

        filter_row.addWidget(
            self.field(
                "Year",
                self.make_filter_combo([current_year, next_year, previous_year], 110),
            )
        )
        filter_row.addWidget(
            self.field(
                "Month",
                self.make_filter_combo(
                    ["All Months", "January", "February", "March"], 150
                ),
            )
        )
        filter_row.addWidget(
            self.field(
                "Folder State",
                self.make_filter_combo(
                    [
                        "All Folder States",
                        "UAT_PREPARE",
                        "PROD_READY",
                        "IMPLEMENTED",
                        "POSTPONED",
                    ],
                    170,
                ),
            )
        )
        filter_row.addWidget(
            self.field(
                "CR State",
                self.make_filter_combo(
                    ["All CR States", "PENDING SUBMISSION", "APPROVED"], 170
                ),
            )
        )
        filter_row.addWidget(
            self.field(
                "Drone State",
                self.make_filter_combo(
                    ["All Drone States", "UAT", "SIT", "PROD READY"], 170
                ),
            )
        )
        filter_row.addWidget(search_group)

        filter_row.addStretch()

        export_btn = self.primary_button("Export CSV", "fa5s.file-export")
        export_btn.setMinimumWidth(scaled(135))
        filter_row.addWidget(self.aligned_control(export_btn))

        filters.outer_layout.addLayout(filter_row)
        layout.addWidget(filters)

        metrics = QHBoxLayout()
        metrics.setSpacing(spacing_tight())
        metrics.addWidget(
            MetricCard(
                "Total CR", "0", "fa5s.chart-pie", "All tracked change requests"
            )
        )
        metrics.addWidget(
            MetricCard(
                "Folder: UAT_PREPARE", "0", "fa5s.folder-open", "Preparation queue"
            )
        )
        metrics.addWidget(
            MetricCard("Folder: PROD_READY", "0", "fa5s.flag", "Ready for release")
        )
        metrics.addWidget(
            MetricCard(
                "Folder: IMPLEMENTED", "0", "fa5s.check-circle", "Completed delivery"
            )
        )
        metrics.addWidget(
            MetricCard("Folder: POSTPONED", "0", "fa5s.clock", "Deferred delivery")
        )
        layout.addLayout(metrics)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(spacing_tight())

        for title, icon, lines in [
            (
                "CR States",
                "fa5s.tasks",
                ["Pending Submission", "Approved", "Rejected", "Implemented"],
            ),
            (
                "Drone States",
                "fa5s.signal",
                ["UAT", "SIT", "Prod Ready", "Postponed"],
            ),
            ("Monthly Activity", "fa5s.chart-line", ["Jan", "Feb", "Mar", "Apr"]),
        ]:
            card = PanelCard(title, icon, "")
            placeholder = QFrame()
            placeholder.setObjectName("chartPlaceholder")
            pl = QVBoxLayout(placeholder)
            pl.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
            pl.setSpacing(spacing_tight())
            pl.addStretch()
            for line in lines:
                row_frame = QFrame()
                row_frame.setObjectName("summaryRow")
                create_shadow(
                    row_frame, blur_radius=14, x_offset=0, y_offset=4, alpha=38
                )
                row_layout = QHBoxLayout(row_frame)
                row_layout.setContentsMargins(scaled(6), scaled(0), scaled(6), scaled(0))
                row_layout.setSpacing(spacing_tight())

                label = QLabel(line)
                label.setObjectName("summaryRowLabel")
                value = QLabel("0")
                value.setObjectName("summaryRowValue")
                value.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )

                row_layout.addWidget(label, 1)
                row_layout.addWidget(value)

                pl.addWidget(row_frame)
            pl.addStretch()
            card.outer_layout.addWidget(placeholder, 1)
            chart_row.addWidget(card)

        layout.addLayout(chart_row)

        table_card = PanelCard("Report Table", "fa5s.table", "export-ready view")

        table_inner = QFrame()
        table_inner.setObjectName("reportTableInner")
        create_shadow(table_inner, blur_radius=18, x_offset=0, y_offset=5, alpha=36)

        table_inner_layout = QVBoxLayout(table_inner)
        table_inner_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        table_inner_layout.setSpacing(spacing_tight())

        table = self.make_table(
            0,
            10,
            [
                "NO",
                "MAIN PROJECT",
                "SUB PROJECT",
                "START DATETIME",
                "END DATETIME",
                "DRONE TICKET",
                "DRONE STATE",
                "CR NUMBER",
                "CR STATE",
                "FOLDER STATE",
            ],
        )
        self.active_table = table
        table.setMinimumHeight(scaled(310))
        table_inner_layout.addWidget(table)

        # Report table uses native vertical scrolling for large data.
        # Pagination footer intentionally removed for a cleaner reporting workspace.
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table_card.outer_layout.addWidget(table_inner, 1)
        layout.addWidget(table_card, 1)


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", scaled_font(9)))
    window = ReportWindow()
    window.show()
    sys.exit(app.exec())
