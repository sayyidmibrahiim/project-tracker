
import os
import sys
from math import pi, sin

# High-DPI flags must be set before QApplication is created.
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

import qtawesome as qta
from PyQt6.QtCore import (
    QDate,
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
    pyqtSignal,
)
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QApplication,
    QCalendarWidget,
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
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from responsive_utils import (
    get_manager,
    center_window,
    icon_size_button,
    icon_size_compact,
    icon_size_tiny,
    margin_inner,
    margin_outer,
    row_height_tree,
    scaled,
    scaled_font,
    scaled_icon,
    screen_fraction,
    spacing_loose,
    spacing_normal,
    spacing_tight,
    tree_indentation,
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

SIDEBAR_EXPANDED_WIDTH = 208
SIDEBAR_COLLAPSED_WIDTH = 52
SIDEBAR_CONTROL_HEIGHT = 30
HEADER_CONTROL_HEIGHT = 28
HEADER_YEAR_WIDTH = 76
SEARCH_WIDTH_NORMAL = 150
SEARCH_WIDTH_FOCUSED = 220
SEARCH_WIDTH_COMPACT = 124
COMPACT_CONTROL_HEIGHT = 30
NOTIFICATION_MIN_HEIGHT = 168
EDITABLE_EXTENSIONS = {".md", ".txt", ".py", ".sh", ".ps1", ".sql", ".json", ".csv", ".log", ".yml", ".yaml"}
PREVIEW_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf"}


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

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(C_DARK))
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
    def __init__(
        self,
        placeholder="Search projects here...",
        normal_width=SEARCH_WIDTH_NORMAL,
        focused_width=SEARCH_WIDTH_FOCUSED,
        parent=None,
    ):
        super().__init__(parent)
        self.normal_width = scaled(normal_width)
        self.focused_width = scaled(focused_width)
        self.setPlaceholderText(placeholder)
        self.setMinimumWidth(self.normal_width)
        self.setMaximumWidth(self.normal_width)
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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
            anim.setEndValue(width)
            anim.start()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.animate_width(self.focused_width)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.animate_width(self.normal_width)


class AnimatedPrimaryButton(SmoothShadowButtonMixin, QPushButton):
    def __init__(self, text, icon_name="fa5s.plus", parent=None):
        super().__init__(text, parent)
        self.setIcon(qta.icon(icon_name, color=C_WHITE))
        self.setIconSize(QSize(icon_size_compact(), icon_size_compact()))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(26))
        self.setMinimumWidth(scaled(96))
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
        self.setIconSize(QSize(icon_size_compact(), icon_size_compact()))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_button_shadow(self, blur_radius=8, y_offset=1, alpha=24)
        self.update_style()

    def set_collapsed(self, collapsed):
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dateTimeBadge")
        self.setMinimumHeight(scaled(28))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(8), scaled(2), scaled(8), scaled(2))
        layout.setSpacing(scaled(6))

        icon = QLabel()
        icon.setFixedSize(icon_size_button(), icon_size_button())
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(qta.icon("fa5s.calendar-alt", color=C_ORANGE).pixmap(icon_size_button(), icon_size_button()))
        layout.addWidget(icon)

        self.label = QLabel()
        self.label.setObjectName("dateTimeLabel")
        self.label.setMinimumWidth(scaled(156))
        self.label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
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
        self.setIconSize(QSize(icon_size_compact(), icon_size_compact()))
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
                padding: {scaled(3)}px {scaled(5)}px;
                border-radius: {scaled(4)}px;
                color: {C_DARK};
                background: transparent;
            }}
            QMenu#stateDropdownMenu::item:selected {{
                background-color: rgba(188, 108, 44, 0.12);
                color: {C_ORANGE};
            }}
            QMenu#compactPopupMenu {{
                background: {C_WHITE};
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(5)}px;
                padding: {scaled(5)}px;
            }}
            QMenu#compactPopupMenu::item {{
                color: {C_DARK};
                padding: {scaled(5)}px {scaled(18)}px {scaled(5)}px {scaled(8)}px;
                border-radius: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            QMenu#compactPopupMenu::item:selected {{
                background: {C_SOFT_PINK_SURFACE};
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
        self.setMinimumHeight(scaled(12))

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
    def __init__(self, label, value="0", icon_name="fa5s.chart-pie", helper="", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        create_shadow(self, blur_radius=18, y_offset=4, alpha=22)

        layout = QHBoxLayout(self)
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


class PanelCard(QFrame):
    def __init__(self, title="", icon_name=None, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("panelCard")
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        self.outer_layout.setSpacing(spacing_tight())

        if title:
            header = QHBoxLayout()
            header.setSpacing(spacing_tight())

            if icon_name:
                icon = QLabel()
                icon.setPixmap(qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12)))
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


class ClearableSelectionTree(QTreeWidget):
    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentItem(None)
            event.accept()
            return

        super().mousePressEvent(event)


class ClearableSelectionList(QListWidget):
    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentItem(None)
            event.accept()
            return

        super().mousePressEvent(event)


class DateFilterButton(QPushButton):
    dateChanged = pyqtSignal(str)
    currentTextChanged = dateChanged

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dateFilterButton")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        self.setMaximumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        self.setMinimumWidth(scaled(38))
        self.setMaximumWidth(scaled(42))
        self.setIcon(qta.icon("fa5s.calendar-alt", color=C_DARK))
        self.setIconSize(QSize(icon_size_button(), icon_size_button()))
        self._popup = QMenu(self)
        self.calendar = QCalendarWidget(self._popup)
        self.calendar.setObjectName("dateFilterCalendar")
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setSelectedDate(QDate.currentDate())
        self._popup.setMinimumWidth(scaled(300))
        self._popup.setMinimumHeight(scaled(264))
        self.all_dates_action = self._popup.addAction("All dates")
        self._date_text = "All dates"
        self.calendar.clicked.connect(self.select_date)
        self.all_dates_action.triggered.connect(lambda: self.set_current_text("All dates"))
        self.clicked.connect(self._show_popup)

    def _show_popup(self):
        self.calendar.setParent(self._popup)
        self.calendar.setGeometry(scaled(6), scaled(6), scaled(288), scaled(222))
        self._popup.popup(self.mapToGlobal(QPoint(0, self.height())))
        self.calendar.show()

    def currentText(self):
        return self._date_text

    def update_text(self):
        self.setText("")
        self.setToolTip(f"Date filter: {self._date_text}")

    def set_current_text(self, text):
        if self._date_text == text:
            self.update_text()
            return
        self._date_text = text
        self.update_text()
        self.dateChanged.emit(text)

    def select_date(self, date):
        self.set_current_text(date.toString("yyyyMMdd"))
        self._popup.close()


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
        w, h = screen_fraction(0.94, 0.92)
        self.resize(w, h)
        self.setMinimumSize(*screen_fraction(0.42, 0.42))
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

        create_shadow(self.main_wrapper, blur_radius=25, x_offset=-6, y_offset=0, alpha=60)
        self.build_main_content(wrapper_layout)

        main_layout.addWidget(self.main_wrapper, 1)

    def _handle_responsive_profile_changed(self, _profile) -> None:
        self.updateGeometry()
        self.update()

    def eventFilter(self, watched, event):
        if (
            hasattr(self, "active_table")
            and event.type() == event.Type.MouseButtonPress
            and isinstance(watched, QWidget)
        ):
            if isinstance(watched, QMenu) or (watched.parentWidget() and isinstance(watched.parentWidget(), QMenu)):
                return super().eventFilter(watched, event)

            table = self.active_table
            viewport = table.viewport()
            global_pos = event.globalPosition().toPoint()
            viewport_pos = viewport.mapFromGlobal(global_pos)

            inside = viewport.rect().contains(viewport_pos)
            index = table.indexAt(viewport_pos)

            if inside and index.isValid():
                table.setCurrentIndex(index)
                table.selectRow(index.row())
            else:
                table.clearSelection()
                table.setCurrentItem(None)

        return super().eventFilter(watched, event)

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        expanded_width = scaled(SIDEBAR_EXPANDED_WIDTH)
        sidebar.setMinimumWidth(expanded_width)
        sidebar.setMaximumWidth(expanded_width)

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

        self.notification_icon_btn = SidebarButton("Notifications", "fa5s.bell", False)
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

        dismiss_btn = QPushButton()
        dismiss_btn.setObjectName("notifDismissButton")
        dismiss_btn.setToolTip("Dismiss notifications")
        dismiss_btn.setIcon(qta.icon("fa5s.times", color=C_WHITE))
        dismiss_btn.setIconSize(QSize(icon_size_tiny(), icon_size_tiny()))
        dismiss_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        dismiss_btn.setMinimumHeight(scaled(26))
        dismiss_btn.setMinimumWidth(scaled(30))
        dismiss_btn.setMaximumWidth(scaled(34))
        header.addWidget(dismiss_btn)

        layout.addLayout(header)

        self.notif_scroll = QScrollArea()
        self.notif_scroll.setObjectName("notifScroll")
        self.notif_scroll.setWidgetResizable(True)
        self.notif_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.notif_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notif_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
        self.sidebar_anim_max.finished.connect(lambda: self.sidebar.setFixedWidth(new_width))

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
            self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-right", color=C_LIGHT))
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
        self.workspace_layout.setContentsMargins(margin_outer(), margin_outer(), margin_outer(), margin_outer())
        self.workspace_layout.setSpacing(spacing_loose())

        self.build_page(self.workspace_layout)

        parent_layout.addWidget(self.workspace, 1)
        self.header_frame.raise_()

    def build_page(self, layout):
        raise NotImplementedError

    def secondary_button(self, text, icon_name=None):
        btn = QPushButton(text)
        btn.setObjectName("secondaryButton")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumHeight(scaled(24))
        if icon_name:
            btn.setIcon(qta.icon(icon_name, color=C_DARK))
            btn.setIconSize(QSize(icon_size_button(), icon_size_button()))
        btn.clicked.connect(lambda checked=False, label=text: self.show_flow_message(f"{label} clicked"))
        return btn

    def primary_button(self, text, icon_name="fa5s.plus"):
        btn = AnimatedPrimaryButton(f" {text}", icon_name)
        btn.setMinimumHeight(scaled(26))
        btn.clicked.connect(lambda checked=False, label=text: self.show_flow_message(f"{label} clicked"))
        return btn

    def tiny_button(self, text, icon_name=None, danger=False):
        btn = QPushButton(text)
        btn.setObjectName("dangerButton" if danger else "tinyButton")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumHeight(scaled(24))
        btn.clicked.connect(lambda checked=False, label=text: self.show_flow_message(f"{label} clicked"))
        if icon_name:
            btn.setIcon(qta.icon(icon_name, color=C_WHITE if danger else C_DARK))
            btn.setIconSize(QSize(icon_size_button(), icon_size_button()))
        return btn

    def icon_menu_button(self, icon_name, tooltip, actions):
        btn = QPushButton()
        btn.setObjectName("filterMenuButton")
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumSize(scaled(40), scaled(COMPACT_CONTROL_HEIGHT))
        btn.setMaximumWidth(scaled(44))
        btn.setIcon(qta.icon(icon_name, color=C_DARK))
        btn.setIconSize(QSize(icon_size_button(), icon_size_button()))
        menu = QMenu(btn)
        menu.setObjectName("compactPopupMenu")
        for label, callback in actions:
            action = QAction(label, menu)
            action.triggered.connect(callback)
            menu.addAction(action)
        btn.clicked.connect(lambda: menu.popup(btn.mapToGlobal(QPoint(0, btn.height() + scaled(4)))))
        return btn

    def link_tag(self, text):
        tag = QLabel(text)
        tag.setObjectName("linkTag")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return tag

    def show_flow_message(self, message):
        self.latest_flow_message = message
        if hasattr(self, "flow_status_label"):
            self.flow_status_label.setText(message)
        if hasattr(self, "notes_flow_status_label"):
            self.notes_flow_status_label.setText(message)

    def line_edit(self, placeholder="", text=""):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setText(text)
        edit.setMinimumHeight(scaled(26))
        edit.returnPressed.connect(lambda: self.show_flow_message(f"Input submitted: {edit.text()}"))
        edit.textChanged.connect(lambda value: self.show_flow_message(f"Typing: {value}"))
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

    def make_combo(self, items, width=150):
        combo = ModernComboBox()
        combo.addItems(items)
        combo.setMinimumWidth(width)
        combo.currentTextChanged.connect(lambda text: self.show_flow_message(f"Dropdown selected: {text}"))
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
            #dateTimeBadge {{
                background-color: {C_WHITE};
                border: 1px solid {C_DARK};
                border-radius: {scaled(4)}px;
            }}
            #dateTimeLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #dateFilterButton {{
                padding: 0px;
                margin: 0px;
                background: {C_WHITE};
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
            }}
            #dateFilterButton::menu-indicator {{
                image: none;
                width: 0px;
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
            #notifDismissButton {{
                color: {C_WHITE};
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.38);
                border-radius: {scaled(4)}px;
                font-size: {scaled_font(7)}pt;
                font-weight: 900;
                padding: {scaled(2)}px {scaled(8)}px;
            }}
            #notifDismissButton:hover {{
                color: {C_WHITE};
                background: {C_PRIMARY_RED};
                border: 1px solid {C_PRIMARY_RED};
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
                border: {scaled(2)}px solid {C_INPUT_BORDER};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            #automationTabInner {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: 1px solid {C_LIGHT_BORDER};
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
                font-size: {scaled_font(9)}pt;
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
                font-weight: 600;
            }}
            QLineEdit, QTextEdit {{
                padding: {scaled(5)}px {scaled(7)}px;
                border: {scaled(2)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_TEXT_PRIMARY};
                font-weight: 600;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: {scaled(2)}px solid {C_ORANGE};
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
            #secondaryButton, #tinyButton {{
                background: {C_WHITE};
                color: {C_ORANGE};
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
                padding: {scaled(5)}px {scaled(10)}px;
            }}
            #secondaryButton:hover, #tinyButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            #filterMenuButton {{
                background: {C_WHITE};
                color: {C_DARK};
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                font-weight: 800;
                padding: {scaled(4)}px {scaled(6)}px {scaled(4)}px {scaled(8)}px;
                text-align: left;
            }}
            #filterMenuButton:hover {{
                background: {C_SOFT_PINK_SURFACE};
            }}
            #filterMenuButton::menu-indicator {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            #dangerButton {{
                background: #B5382F;
                color: {C_WHITE};
                border: none;
                border-radius: {scaled(4)}px;
                font-weight: 900;
                padding: {scaled(3)}px {scaled(5)}px;
            }}
            #dangerButton:hover {{
                background: #942D26;
            }}
            #linkRow {{
                background: {C_WHITE};
                border: 1px solid {C_LIGHT_BORDER};
                border-radius: {scaled(7)}px;
            }}
            #linkRow:hover {{
                background: {C_SOFT_PINK_SURFACE};
                border: 1px solid {C_SOFT_PINK_BORDER};
            }}
            #linkRow[selected="true"] {{
                background: {C_SOFT_PINK_SURFACE};
                border: 1px solid {C_ORANGE};
            }}
            QSplitter#secondBrainSplitter {{
                background: transparent;
                border: none;
            }}
            QSplitter#secondBrainSplitter::handle {{
                background: {C_SOFT_WHITE_BORDER};
                border: none;
                border-radius: {scaled(3)}px;
                image: none;
            }}
            QSplitter#secondBrainSplitter::handle:horizontal {{
                width: {scaled(10)}px;
                margin: {scaled(8)}px {scaled(3)}px;
            }}
            QSplitter#secondBrainSplitter::handle:hover,
            QSplitter#secondBrainSplitter::handle:pressed {{
                background: {C_SOFT_PINK_ACCENT};
                border: none;
            }}
            QSplitter#linkContentSplitter {{
                background: transparent;
                border: none;
            }}
            QSplitter#linkContentSplitter::handle {{
                background: {C_SOFT_WHITE_BORDER};
                border: none;
                border-radius: {scaled(3)}px;
                image: none;
            }}
            QSplitter#linkContentSplitter::handle:horizontal {{
                width: {scaled(8)}px;
                margin: {scaled(8)}px {scaled(2)}px;
            }}
            QSplitter#linkContentSplitter::handle:hover,
            QSplitter#linkContentSplitter::handle:pressed {{
                background: {C_SOFT_PINK_ACCENT};
                border: none;
            }}
            QTreeWidget#notesTree,
            QListWidget#linkCategoryList,
            QListWidget#searchResultList,
            QTextEdit#notesEditor,
            QTextEdit#linkDescriptionEdit,
            QScrollArea#linkListArea {{
                background: {C_INPUT_WHITE_LAYER};
                border: {scaled(2)}px solid {C_DARK_BORDER};
                border-radius: {scaled(6)}px;
            }}
            QFrame#selectedLinkBody {{
                background: {C_INPUT_WHITE_LAYER};
                border: {scaled(2)}px solid {C_DARK_BORDER};
                border-radius: {scaled(6)}px;
            }}
            QTreeWidget#notesTree::item,
            QListWidget#linkCategoryList::item {{
                min-height: {row_height_tree()}px;
                padding: {scaled(1)}px {scaled(4)}px;
                border-radius: {scaled(3)}px;
            }}
            QFrame#linkRow {{
                background: {C_WHITE};
                border: {scaled(2)}px solid {C_DARK_BORDER};
                border-radius: {scaled(5)}px;
            }}
            QFrame#linkRow[selected="true"] {{
                background: {C_SOFT_PINK_SURFACE};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            QFrame[detailBox="true"] {{
                background-color: {C_INNER_CARD_BG};
                border-radius: {scaled(7)}px;
                border-top: {scaled(1)}px solid {C_INPUT_BORDER};
                border-right: {scaled(1)}px solid {C_INPUT_BORDER};
                border-bottom: {scaled(1)}px solid {C_INPUT_BORDER};
                border-left: {scaled(3)}px solid {C_ORANGE};
            }}
            QWidget#linkListViewport,
            QWidget#linkListContent {{
                background: transparent;
                border: none;
            }}
            #linkTag {{
                background: {C_ROW_ALT};
                color: {C_TEXT_SECONDARY};
                border: 1px solid {C_LIGHT_BORDER};
                border-radius: {scaled(3)}px;
                font-size: {scaled_font(7)}pt;
                font-weight: 800;
                padding: {scaled(1)}px {scaled(4)}px;
            }}
            #clickableLink {{
                color: {C_ORANGE};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #linkModifiedLabel {{
                color: {C_TEXT_MUTED};
                font-size: {scaled_font(7)}pt;
                font-weight: 700;
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
            #stateLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                min-width: {scaled(44)}px;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: rgba(208, 212, 210, 0.82);
                color: {C_DARK};
                padding: {scaled(3)}px {scaled(6)}px;
                border-top-left-radius: {scaled(6)}px;
                border-top-right-radius: {scaled(6)}px;
                margin-right: {scaled(3)}px;
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
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                color: {C_DARK};
                padding: {scaled(2)}px;
                font-weight: 650;
                outline: none;
            }}
            QListWidget::item, QTreeWidget::item {{
                min-height: {row_height_tree()}px;
                padding: {scaled(1)}px {scaled(4)}px;
                border-radius: {scaled(3)}px;
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
                padding: {scaled(3)}px {scaled(5)}px;
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
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: {scaled(6)}px;
                margin: 0px 2px 0px 2px;
                border-radius: {scaled(4)}px;
            }}
            QScrollBar::handle:horizontal {{
                background: rgba(45, 61, 52, 0.35);
                min-width: {scaled(18)}px;
                border-radius: {scaled(4)}px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: rgba(45, 61, 52, 0.55);
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
                width: 0px;
            }}
        """



class SecondBrainTabButton(QPushButton):
    def __init__(self, text, icon_name, active=False, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.active = active
        self._padding = 12 if active else 10
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
        self._padding = 12 if active else 10
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
                padding: {scaled(4)}px {scaled(self._padding)}px;
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
        self.anim.setEndValue(16 if self.active else 14)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._padding)
        self.anim.setEndValue(12 if self.active else 10)
        self.anim.start()
        super().leaveEvent(event)


class SecondBrainWindow(BaseProjectTrackerWindow):
    PAGE_TITLE = "Second Brain"
    ACTIVE_MENU = "Second Brain"
    SEARCH_PLACEHOLDER = "Search notes or links..."

    def build_page(self, layout):
        self.second_brain_tabs = []
        self.second_brain_stack = QStackedWidget()
        self.second_brain_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        tab_inner = QFrame()
        tab_inner.setObjectName("automationTabInner")
        tab_inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_shadow(tab_inner, blur_radius=16, x_offset=0, y_offset=5, alpha=38)

        tab_layout = QHBoxLayout(tab_inner)
        tab_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        tab_layout.setSpacing(spacing_tight())

        workspace_icon = QLabel()
        workspace_icon.setPixmap(qta.icon("fa5s.brain", color=C_ORANGE).pixmap(scaled(12), scaled(12)))
        tab_layout.addWidget(workspace_icon)

        workspace_title = QLabel("Second Brain Workspace")
        workspace_title.setObjectName("cardTitle")
        workspace_title.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Black))
        tab_layout.addWidget(workspace_title)

        workspace_subtitle = QLabel("Notes, documents, and reusable links")
        workspace_subtitle.setObjectName("cardSubtitle")
        workspace_subtitle.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Bold))
        workspace_subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        tab_layout.addWidget(workspace_subtitle, 1)

        for index, (name, icon) in enumerate([
            ("Notes", "fa5s.sticky-note"),
            ("Link Bank", "fa5s.link"),
        ]):
            btn = SecondBrainTabButton(name, icon, active=index == 0)
            btn.clicked.connect(lambda checked=False, i=index: self.set_second_brain_tab(i))
            self.second_brain_tabs.append(btn)
            tab_layout.addWidget(btn, 0)

        layout.addWidget(tab_inner, 0)
        self.second_brain_stack.addWidget(self.build_notes_page())
        self.second_brain_stack.addWidget(self.build_link_bank_page())
        layout.addWidget(self.second_brain_stack, 1)

    def set_second_brain_tab(self, index):
        self.second_brain_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.second_brain_tabs):
            btn.set_active(i == index)

    def sample_notes(self):
        return [
            {
                "type": "note",
                "open_mode": "editor",
                "title": "Deployment evidence follow-up",
                "date": "20260529",
                "path": "Second Brain Notes/Daily/Deployment Evidence Follow-up.md",
                "tags": ["daily", "deployment", "evidence"],
                "content": "Ask team for screenshot before PROD closure.",
                "pinned": True,
                "favorite": True,
            },
            {
                "type": "note",
                "open_mode": "editor",
                "title": "UAT Screenshot Request",
                "date": "20260529",
                "path": "Second Brain Notes/UAT/UAT Screenshot Request.md",
                "tags": ["daily", "uat", "screenshot"],
                "content": "Collect latest UAT evidence screenshots from project owner.",
                "pinned": False,
                "favorite": True,
            },
            {
                "type": "note",
                "open_mode": "editor",
                "title": "Release Board Cleanup",
                "date": "20260528",
                "path": "Second Brain Notes/Release/Release Board Cleanup.md",
                "tags": ["daily", "release"],
                "content": "Clean stale items from release board before weekly checkpoint.",
                "pinned": True,
                "favorite": False,
            },
            {
                "type": "note",
                "open_mode": "editor",
                "title": "UAT Checklist",
                "date": "20260529",
                "path": "Second Brain Notes/UAT Checklist.md",
                "tags": ["uat", "release"],
                "content": "# UAT Checklist\n\n- Validate project files are detected\n- Attach evidence screenshot\n- Confirm deployment window\n",
                "pinned": True,
                "favorite": False,
            },
        ]

    def sample_search_files(self):
        return [
            *self.sample_notes(),
            {
                "type": "document",
                "open_mode": "preview",
                "title": "Rollback Query.sql",
                "date": "20260528",
                "path": "Project Documents/Rollback Query.sql",
                "tags": ["sql", "rollback"],
                "content": "-- rollback query preview\nselect * from release_audit where status = 'FAILED';",
            },
            {
                "type": "document",
                "open_mode": "external",
                "title": "CR Evidence.xlsx",
                "date": "20260529",
                "path": "Project Documents/CR Evidence.xlsx",
                "tags": ["evidence", "spreadsheet"],
                "content": "Spreadsheet evidence index and CR approval data.",
            },
        ]

    def make_note_item(self, note):
        item = QTreeWidgetItem([note["path"].split("/")[-1]])
        item.setData(0, Qt.ItemDataRole.UserRole, note)
        return item

    def set_note_mode(self, preview_mode):
        if preview_mode:
            self._edit_buffer = self.note_content_box.toPlainText()
            self.note_content_box.setReadOnly(True)
            self.note_mode_label.setText("Preview mode · read-only")
            self.show_flow_message("Preview mode enabled")
        else:
            self.note_content_box.setReadOnly(False)
            if hasattr(self, "_edit_buffer"):
                self.note_content_box.setPlainText(self._edit_buffer)
            self.note_mode_label.setText("Edit mode · editable prototype")
            self.show_flow_message("Edit mode enabled")

    def note_open_mode_for_name(self, filename):
        _, ext = os.path.splitext(filename.casefold())
        if ext in EDITABLE_EXTENSIONS:
            return "editor"
        if ext in PREVIEW_EXTENSIONS:
            return "preview"
        return "external"

    def apply_note_open_mode(self, data):
        mode = data.get("open_mode") or self.note_open_mode_for_name(data.get("title", ""))
        if mode == "editor":
            self.note_content_box.setReadOnly(False)
            self.note_mode_label.setText("Edit mode · editable in Project Tracker")
            return
        if mode == "preview":
            self.note_content_box.setReadOnly(True)
            self.note_mode_label.setText("Preview only · edit blocked · use default app if needed")
            return
        self.note_content_box.setReadOnly(True)
        self.note_mode_label.setText("External app · Project Tracker cannot preview/edit")

    def open_search_result(self, item):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        mode = data.get("open_mode") or self.note_open_mode_for_name(data.get("title", ""))
        data["open_mode"] = mode
        if mode in {"editor", "preview"}:
            self.load_note_into_editor(data)
            self.apply_note_open_mode(data)
            return
        self.note_breadcrumb.setText(f"{data.get('path', 'Unknown path')} · open with default app")
        self.note_title_edit.setText(data.get("title", "External File"))
        self.note_tags_edit.setText(" ".join(f"#{tag}" for tag in data.get("tags", [])))
        self.note_content_box.setReadOnly(True)
        self.note_content_box.setPlainText(
            f"Cannot preview or edit this file in prototype.\n\nWould open with default app:\n{data.get('path', '')}"
        )
        self.note_mode_label.setText("External app · Project Tracker cannot preview/edit")
        self.show_flow_message(f"Open with default app: {data.get('title', 'file')}")

    def handle_note_tree_click(self, item, column):
        data = item.data(column, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("type") in {"note", "document"}:
            self.open_search_result(item)
            return
        self.show_flow_message(f"Folder selected: {item.text(column)}")

    def load_note_into_editor(self, note):
        self.current_note = note
        self.note_title_edit.setText(note.get("title", "Untitled Note"))
        self.note_tags_edit.setText(" ".join(f"#{tag}" for tag in note.get("tags", [])))
        mode = note.get("open_mode") or self.note_open_mode_for_name(note.get("title", ""))
        note["open_mode"] = mode
        mode_text = {
            "editor": "editable in-app",
            "preview": "preview only",
            "external": "open with default app",
        }.get(mode, "open")
        self.note_breadcrumb.setText(f"{note.get('path', 'Unknown path')} · {mode_text}")
        self.note_content_box.setPlainText(note.get("content", ""))
        self.apply_note_open_mode(note)
        self.show_flow_message(f"Loaded note: {note.get('title', 'Untitled Note')}")

    def sort_note_items(self, items, mode):
        if mode == "Oldest":
            return sorted(items, key=lambda item: item.get("date", ""))
        if mode == "A-Z":
            return sorted(items, key=lambda item: item.get("title", "").casefold())
        if mode == "Type":
            return sorted(items, key=lambda item: (item.get("type", "").casefold(), item.get("title", "").casefold()))
        return sorted(items, key=lambda item: item.get("date", ""), reverse=True)

    def sort_link_items(self, items, mode):
        if mode == "Oldest":
            return sorted(items, key=lambda item: item.get("date", ""))
        if mode == "A-Z":
            return sorted(items, key=lambda item: item.get("title", "").casefold())
        if mode == "Favorite":
            return sorted(items, key=lambda item: (not item.get("favorite", False), item.get("title", "").casefold()))
        if mode == "Pinned":
            return sorted(items, key=lambda item: (not item.get("pinned", False), item.get("title", "").casefold()))
        return sorted(items, key=lambda item: item.get("date", ""), reverse=True)

    def update_link_card_sort(self, *_):
        if not hasattr(self, "link_items") or not hasattr(self, "link_list_layout"):
            return
        if hasattr(self, "link_header_sort_combo") and self.link_header_sort_combo.hasFocus():
            mode = self.link_header_sort_combo.currentText()
        elif hasattr(self, "link_search_sort_combo"):
            mode = self.link_search_sort_combo.currentText()
        else:
            mode = "Newest"
        self.render_link_cards(self.sort_link_items(self.link_items, mode))

    def update_notes_search_preview(self, *_):
        if not hasattr(self, "notes_tree"):
            return
        query = self.notes_search_edit.text().strip()
        date_filter = self.notes_date_filter.currentText()
        query_cf = query.casefold()
        self.search_results_root.takeChildren()
        matches = []
        for entry in self.sample_search_files():
            haystack = " ".join(
                [
                    entry.get("title", ""),
                    entry.get("path", ""),
                    entry.get("content", ""),
                    " ".join(entry.get("tags", [])),
                ]
            ).casefold()
            date_match = date_filter == "All dates" or entry.get("date") == date_filter
            query_match = not query_cf or query_cf in haystack
            if date_match and query_match:
                matches.append(entry)
        sort_mode = self.notes_sort_combo.currentText() if hasattr(self, "notes_sort_combo") else "Newest"
        matches = self.sort_note_items(matches, sort_mode)
        active_search = bool(query_cf) or date_filter != "All dates"
        if active_search:
            if self.notes_tree.indexOfTopLevelItem(self.search_results_root) < 0:
                self.notes_tree.insertTopLevelItem(0, self.search_results_root)
            self.search_results_root.setHidden(False)
            for entry in matches:
                mode = {"editor": "edit", "preview": "preview", "external": "default app"}.get(entry.get("open_mode"), "open")
                item = QTreeWidgetItem([f"{entry['path']} · {mode}"])
                item.setData(0, Qt.ItemDataRole.UserRole, entry)
                self.search_results_root.addChild(item)
            self.search_results_root.setExpanded(True)
            self.show_flow_message(f"Search: {len(matches)} result(s) · pattern='{query_cf or '*'}' · date={date_filter}")
        else:
            index = self.notes_tree.indexOfTopLevelItem(self.search_results_root)
            if index >= 0:
                self.notes_tree.takeTopLevelItem(index)
            self.show_flow_message("Search cleared")

    def update_link_search_preview(self, *_):
        if not hasattr(self, "category_list"):
            return
        query = self.link_search_edit.text().strip()
        date_filter = self.link_date_filter.currentText()
        sort_mode = self.link_search_sort_combo.currentText() if hasattr(self, "link_search_sort_combo") else "Newest"
        query_cf = query.casefold()
        active_search = bool(query_cf) or date_filter != "All dates"
        self.category_list.clear()
        if active_search and hasattr(self, "link_items"):
            matches = []
            for link in self.link_items:
                haystack = " ".join(
                    [
                        link.get("title", ""),
                        link.get("url", ""),
                        link.get("details", ""),
                        link.get("category", ""),
                        link.get("path", ""),
                        " ".join(link.get("tags", [])),
                    ]
                ).casefold()
                date_match = date_filter == "All dates" or link.get("date") == date_filter
                query_match = not query_cf or query_cf in haystack
                if date_match and query_match:
                    matches.append(link)
            matches = self.sort_link_items(matches, sort_mode)
            header = QListWidgetItem(f"Search Results · {len(matches)} match(es)")
            header.setData(Qt.ItemDataRole.UserRole, {"type": "folder"})
            self.category_list.addItem(header)
            for link in matches:
                item = QListWidgetItem(f"{link['path']} · open detail")
                item.setData(Qt.ItemDataRole.UserRole, link)
                self.category_list.addItem(item)
            self.show_flow_message(f"Link search: {len(matches)} result(s) · pattern='{query_cf or '*'}' · date={date_filter}")
            return
        for item in self.link_category_items:
            self.category_list.addItem(QListWidgetItem(item))
        self.category_list.setCurrentRow(0)
        self.show_flow_message("Link search cleared · showing categories")

    def select_link_card(self, row, link):
        self.current_link_row = row
        self.current_link = link
        if hasattr(self, "link_rows"):
            for link_row in self.link_rows:
                link_row.setProperty("selected", link_row is row)
                repolish(link_row)
        if hasattr(self, "selected_link_title"):
            self.selected_link_title.setText(link["title"])
        if hasattr(self, "selected_link_url"):
            self.selected_link_url.setText(f'<a href="{link["url"]}">{link["url"]}</a>')
            self.selected_link_url.setToolTip(link["url"])
        if hasattr(self, "selected_link_meta"):
            self.selected_link_meta.setText(
                f"Tags: {' · '.join(link['tags'])}\nDetails: {link['details']}\nCategory: {link['category']}\nPath: {link['path']}\nDate: {link['date']} · status: selected for toolbar actions"
            )
        self.show_flow_message(f"Selected link: {link['title']}")

    def populate_link_edit_panel(self):
        link = getattr(self, "current_link", None)
        if not link:
            self.show_flow_message("Select link before edit")
            return
        self.link_title_edit.setText(link["title"])
        self.link_url_edit.setText(link["url"])
        self.link_tags_edit.setText(", ".join(link["tags"]))
        self.link_details_edit.setPlainText(link["details"])
        self.show_flow_message(f"Editing link: {link['title']}")

    def save_link_from_panel(self):
        title = self.link_title_edit.text().strip() or "Untitled Link"
        url = self.link_url_edit.text().strip() or "https://example.local/"
        tags = [tag.strip().lstrip("#") for tag in self.link_tags_edit.text().split(",") if tag.strip()]
        details = self.link_details_edit.toPlainText().strip() or "No details yet."
        link = getattr(self, "current_link", None)
        if link:
            link.update({"title": title, "url": url, "tags": tags, "details": details})
            self.select_link_card(self.current_link_row, link)
            self.show_flow_message(f"Saved edits: {title}")
        else:
            self.show_flow_message(f"Saved new link prototype: {title}")

    def selected_notes_folder(self):
        selected = self.notes_tree.currentItem() if hasattr(self, "notes_tree") else None
        if not selected:
            return None
        data = selected.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("type") == "folder":
            return selected
        return selected.parent()

    def add_notes_folder_prototype(self):
        parent = self.selected_notes_folder()
        item = QTreeWidgetItem(["New Folder"])
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if parent:
            parent.addChild(item)
            parent.setExpanded(True)
        else:
            self.notes_tree.addTopLevelItem(item)
        self.notes_tree.setCurrentItem(item)
        self.notes_tree.editItem(item, 0)
        self.show_flow_message("Inline folder draft created")

    def handle_notes_item_changed(self, item, column):
        data = item.data(column, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        name = item.text(column).strip() or "Untitled.md"
        data["title"] = name
        if data.get("type") in {"note", "document"}:
            data["open_mode"] = self.note_open_mode_for_name(name)
            data["path"] = name if item.parent() is None else f"{item.parent().text(0)}/{name}"
            self.open_search_result(item)
        self.show_flow_message(f"Saved name: {name}")

    def handle_link_category_click(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("title"):
            self.select_link_card(getattr(self, "current_link_row", None), data)
            self.show_flow_message(f"Link search result selected: {data['title']}")
            return
        self.show_flow_message(f"Category selected: {item.text()}")

    def add_notes_file_prototype(self):
        parent = self.selected_notes_folder()
        filename = "New Note.md"
        mode = self.note_open_mode_for_name(filename)
        item = QTreeWidgetItem([filename])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "note",
            "title": filename,
            "path": filename if parent is None else f"{parent.text(0)}/{filename}",
            "content": "",
            "tags": [],
            "date": QDate.currentDate().toString("yyyyMMdd"),
            "open_mode": mode,
        })
        if parent:
            parent.addChild(item)
            parent.setExpanded(True)
        else:
            self.notes_tree.addTopLevelItem(item)
        self.notes_tree.setCurrentItem(item)
        self.notes_tree.editItem(item, 0)
        self.show_flow_message("Type filename with extension, then press Enter or click away")

    def add_link_category_prototype(self):
        item = QListWidgetItem(qta.icon("fa5s.folder", color=C_ORANGE), "New Category")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.category_list.addItem(item)
        self.category_list.setCurrentItem(item)
        self.category_list.editItem(item)
        self.show_flow_message("Inline category draft created")

    def handle_selected_link_url(self, url):
        self.show_flow_message(f"Prototype link clicked: {url}")

    def build_notes_page(self):
        notes_page = QWidget()
        notes_layout = QVBoxLayout(notes_page)
        notes_layout.setContentsMargins(0, spacing_tight(), 0, 0)
        notes_layout.setSpacing(spacing_tight())

        notes_splitter = QSplitter(Qt.Orientation.Horizontal)
        notes_splitter.setObjectName("secondBrainSplitter")
        notes_splitter.setChildrenCollapsible(False)
        notes_splitter.setHandleWidth(scaled(8))

        library = PanelCard("Notes & Documents", "fa5s.folder-open", "daily captures, files, and fast indexed search")
        library.setMinimumWidth(scaled(240))
        library.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        search_row = QHBoxLayout()
        self.notes_search_edit = self.line_edit("Search notes, docs, tags, paths, content...")
        self.notes_date_filter = DateFilterButton()
        self.notes_date_filter.currentTextChanged.connect(self.update_notes_search_preview)
        self.notes_sort_combo = QComboBox()
        self.notes_sort_combo.addItems(["Newest", "Oldest", "A-Z", "Type"])
        self.notes_sort_combo.setMinimumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        self.notes_sort_combo.setMinimumWidth(scaled(86))
        self.notes_sort_combo.currentTextChanged.connect(self.update_notes_search_preview)
        clear_search_btn = self.tiny_button("Clear", "fa5s.times")
        clear_search_btn.clicked.connect(lambda: (self.notes_search_edit.clear(), self.notes_date_filter.set_current_text("All dates"), self.show_flow_message("Search cleared")))
        search_row.addWidget(self.notes_search_edit, 1)
        search_row.addWidget(self.notes_date_filter)
        search_row.addWidget(clear_search_btn)
        library.outer_layout.addLayout(search_row)
        self.notes_search_edit.textChanged.connect(self.update_notes_search_preview)

        lib_actions = QHBoxLayout()
        add_folder_btn = self.secondary_button("Add Folder", "fa5s.folder-plus")
        add_folder_btn.clicked.connect(self.add_notes_folder_prototype)
        add_file_btn = self.secondary_button("Add File", "fa5s.file-medical")
        add_file_btn.clicked.connect(self.add_notes_file_prototype)
        filter_btn = self.icon_menu_button(
            "fa5s.filter",
            "Filter notes",
            [
                ("Pinned", lambda: self.show_flow_message("Filter: Pinned")),
                ("Favorites", lambda: self.show_flow_message("Filter: Favorites")),
                ("Recent", lambda: self.show_flow_message("Filter: Recent")),
                ("Mostly Viewed", lambda: self.show_flow_message("Filter: Mostly Viewed")),
            ],
        )
        lib_actions.addWidget(add_folder_btn)
        lib_actions.addWidget(add_file_btn)
        lib_actions.addWidget(filter_btn)
        lib_actions.addStretch()
        library.outer_layout.addLayout(lib_actions)

        tree = ClearableSelectionTree()
        tree.setObjectName("notesTree")
        tree.setHeaderHidden(True)
        tree.setIndentation(tree_indentation())
        tree.setUniformRowHeights(True)
        tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        tree.setMinimumHeight(scaled(220))
        tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.notes_tree = tree
        self.search_results_root = QTreeWidgetItem(["Search Results"])
        self.search_results_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        self.search_results_root.setHidden(True)
        pinned_root = QTreeWidgetItem(["Pinned"])
        pinned_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        favorites_root = QTreeWidgetItem(["Favorites"])
        favorites_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        notes_root = QTreeWidgetItem(["Second Brain Notes"])
        notes_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        for note in self.sample_notes():
            notes_root.addChild(self.make_note_item(note))
            if note.get("pinned"):
                pinned_root.addChild(self.make_note_item(note))
            if note.get("favorite"):
                favorites_root.addChild(self.make_note_item(note))
        docs_root = QTreeWidgetItem(["Project Documents"])
        docs_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder"})
        for entry in [e for e in self.sample_search_files() if e.get("type") == "document"]:
            child = QTreeWidgetItem([entry["title"]])
            child.setData(0, Qt.ItemDataRole.UserRole, entry)
            docs_root.addChild(child)
        # Search Results is inserted only while search/date filter is active.
        tree.addTopLevelItem(pinned_root)
        tree.addTopLevelItem(favorites_root)
        tree.addTopLevelItem(notes_root)
        tree.addTopLevelItem(docs_root)
        tree.expandAll()
        tree.itemClicked.connect(self.handle_note_tree_click)
        tree.itemChanged.connect(self.handle_notes_item_changed)
        library.outer_layout.addWidget(tree, 1)

        review_actions = QHBoxLayout()
        for label, icon in [("Move", "fa5s.folder-open"), ("Archive", "fa5s.archive"), ("Remove", "fa5s.trash-alt")]:
            review_actions.addWidget(self.secondary_button(label, icon))
        review_actions.addStretch()
        library.outer_layout.addLayout(review_actions)

        file_hint = QLabel("Text-like files edit in-app. Images preview only. Unsupported files open with Windows default app.")
        file_hint.setObjectName("cardSubtitle")
        file_hint.setWordWrap(True)
        library.outer_layout.addWidget(file_hint)
        notes_splitter.addWidget(library)

        editor_side = QWidget()
        editor_side.setMinimumWidth(scaled(560))
        editor_side.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        editor_layout = QVBoxLayout(editor_side)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(spacing_tight())

        editor_card = PanelCard("Editor / Preview", "fa5s.pen-nib", "autosave draft · UAT Checklist.md")
        editor_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        meta_grid = QGridLayout()
        meta_grid.setContentsMargins(0, 0, 0, 0)
        meta_grid.setHorizontalSpacing(spacing_tight())
        meta_grid.setVerticalSpacing(spacing_tight())
        self.note_title_edit = self.line_edit("Note title", "UAT Checklist")
        self.note_tags_edit = self.line_edit("#uat #release #evidence", "#uat #release")
        meta_grid.addWidget(self.field("Title", self.note_title_edit), 0, 0)
        meta_grid.addWidget(self.field("Tags", self.note_tags_edit), 0, 1)
        editor_card.outer_layout.addLayout(meta_grid)

        self.note_breadcrumb = QLabel("Second Brain Notes / UAT Checklist.md · editable prototype")
        self.note_breadcrumb.setObjectName("cardSubtitle")
        editor_card.outer_layout.addWidget(self.note_breadcrumb)

        state_row = QHBoxLayout()
        state_row.setSpacing(spacing_tight())
        state_label = QLabel("State:")
        state_label.setObjectName("stateLabel")
        state_label.setMinimumWidth(scaled(52))
        state_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        state_row.addWidget(state_label)
        for label in ["Editable", "Image", "External"]:
            state_row.addWidget(self.tiny_button(label))
        state_row.addStretch()
        editor_card.outer_layout.addLayout(state_row)

        mode_toolbar = QHBoxLayout()
        edit_btn = self.secondary_button("Edit", "fa5s.pen")
        preview_btn = self.secondary_button("Preview", "fa5s.eye")
        edit_btn.clicked.connect(lambda: self.set_note_mode(False))
        preview_btn.clicked.connect(lambda: self.set_note_mode(True))
        for btn in [edit_btn, preview_btn]:
            mode_toolbar.addWidget(btn)
        mode_toolbar.addStretch()
        editor_card.outer_layout.addLayout(mode_toolbar)

        text_toolbar = QHBoxLayout()
        for label, action in [("Undo", "undo"), ("Redo", "redo")]:
            btn = self.tiny_button(label)
            btn.clicked.connect(
                lambda checked=False, editor_action=action: (
                    getattr(self.note_content_box, editor_action)()
                    if hasattr(self, "note_content_box")
                    else None,
                    self.show_flow_message(f"{editor_action.title()} clicked"),
                )
            )
            text_toolbar.addWidget(btn)
        for label in ["B", "I", "U", "H1", "H2", "Code", "Link", "HR", "Quote"]:
            text_toolbar.addWidget(self.tiny_button(label))
        text_toolbar.addStretch()
        text_toolbar.addWidget(self.tiny_button("Pin", "fa5s.thumbtack"))
        text_toolbar.addWidget(self.tiny_button("Favorite", "fa5s.star"))
        editor_card.outer_layout.addLayout(text_toolbar)

        self.note_mode_label = QLabel("Edit mode · autosave draft")
        self.note_mode_label.setObjectName("cardSubtitle")
        editor_card.outer_layout.addWidget(self.note_mode_label)

        self.note_content_box = QTextEdit()
        self.note_content_box.setObjectName("notesEditor")
        self.note_content_box.setPlaceholderText("Select or create a .md note to edit...")
        self.note_content_box.setPlainText("# UAT Checklist\n\n- Validate project files are detected\n- Attach evidence screenshot\n- Confirm deployment window\n")
        self.note_content_box.setMinimumHeight(scaled(260))
        self.note_content_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.note_content_box.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.note_content_box.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor_card.outer_layout.addWidget(self.note_content_box, 1)
        editor_layout.addWidget(editor_card, 1)

        insight_row = QHBoxLayout()
        insight_row.setSpacing(spacing_tight())
        related_card = PanelCard("Backlinks / Related Notes", "fa5s.project-diagram", "matched by tags and [[links]]")
        for text in ["[[Release Playbook.md]] · #release", "[[Meeting Notes.md]] · mentions UAT", "Rollback Query.sql · same project"]:
            label = QLabel(text)
            label.setObjectName("cardSubtitle")
            label.setWordWrap(True)
            related_card.outer_layout.addWidget(label)
        insight_row.addWidget(related_card, 1)

        activity_card = PanelCard("Recent Activity", "fa5s.history", "last touched items")
        for text in ["08:42 · edited UAT Checklist.md", "08:15 · opened CR Evidence.xlsx", "Yesterday · captured deployment note"]:
            label = QLabel(text)
            label.setObjectName("cardSubtitle")
            label.setWordWrap(True)
            activity_card.outer_layout.addWidget(label)
        insight_row.addWidget(activity_card, 1)
        editor_layout.addLayout(insight_row, 0)

        self.notes_flow_status_label = QLabel("Ready · select note, search, pin, favorite, or preview file")
        self.notes_flow_status_label.setObjectName("cardSubtitle")
        self.notes_flow_status_label.setWordWrap(True)
        editor_layout.addWidget(self.notes_flow_status_label, 0)
        notes_splitter.addWidget(editor_side)
        notes_splitter.setStretchFactor(0, 3)
        notes_splitter.setStretchFactor(1, 7)
        notes_splitter.setSizes([scaled(320), scaled(760)])
        notes_layout.addWidget(notes_splitter, 1)
        return notes_page

    def render_link_cards(self, links):
        if not hasattr(self, "link_list_layout"):
            return
        while self.link_list_layout.count():
            item = self.link_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.link_rows = []
        self.current_link_row = None
        for index, link in enumerate(links):
            row = QFrame()
            row.setObjectName("linkRow")
            row.setProperty("selected", index == 0)
            row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            row_l = QVBoxLayout(row)
            row_l.setContentsMargins(margin_inner(), spacing_tight(), margin_inner(), spacing_tight())
            row_l.setSpacing(scaled(4))
            name = QLabel(link["title"])
            name.setObjectName("cardTitle")
            name.setMinimumHeight(scaled(18))
            name.setWordWrap(True)
            name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row_l.addWidget(name)
            badge_row = QHBoxLayout()
            badge_row.setSpacing(scaled(4))
            for badge in link["tags"]:
                badge_row.addWidget(self.link_tag(badge))
            badge_row.addStretch()
            row_l.addLayout(badge_row)
            modified = QLabel(f"Last modified: {link.get('last_modified', link.get('date', '20260529'))}")
            modified.setObjectName("linkModifiedLabel")
            modified.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_l.addWidget(modified)
            row.mousePressEvent = lambda event, link_row=row, link_data=link: self.select_link_card(link_row, link_data)
            self.link_rows.append(row)
            self.link_list_layout.addWidget(row)
            if index == 0:
                self.current_link_row = row
                self.current_link = link
        self.link_list_layout.addStretch(1)
        if self.current_link_row and self.current_link:
            self.select_link_card(self.current_link_row, self.current_link)

    def build_link_bank_page(self):
        link_page = QWidget()
        link_layout = QVBoxLayout(link_page)
        link_layout.setContentsMargins(0, spacing_tight(), 0, 0)
        link_layout.setSpacing(spacing_tight())

        link_splitter = QSplitter(Qt.Orientation.Horizontal)
        link_splitter.setObjectName("secondBrainSplitter")
        link_splitter.setChildrenCollapsible(False)
        link_splitter.setHandleWidth(scaled(8))

        category_card = PanelCard("Link Categories", "fa5s.folder", "category-first link bank")
        category_card.setMinimumWidth(scaled(230))
        category_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        link_search_row = QHBoxLayout()
        self.link_search_edit = self.line_edit("Search title, link, tags, details, path, content...")
        self.link_date_filter = DateFilterButton()
        self.link_date_filter.currentTextChanged.connect(self.update_link_search_preview)
        self.link_search_sort_combo = QComboBox()
        self.link_search_sort_combo.addItems(["Newest", "Oldest", "A-Z", "Favorite", "Pinned"])
        self.link_search_sort_combo.setMinimumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        self.link_search_sort_combo.setMinimumWidth(scaled(86))
        self.link_search_sort_combo.currentTextChanged.connect(self.update_link_search_preview)
        self.link_search_sort_combo.currentTextChanged.connect(self.update_link_card_sort)
        clear_link_search_btn = self.tiny_button("Clear", "fa5s.times")
        clear_link_search_btn.clicked.connect(lambda: (self.link_search_edit.clear(), self.link_date_filter.set_current_text("All dates"), self.show_flow_message("Link search cleared")))
        link_search_row.addWidget(self.link_search_edit, 1)
        link_search_row.addWidget(self.link_date_filter)
        link_search_row.addWidget(clear_link_search_btn)
        category_card.outer_layout.addLayout(link_search_row)

        self.link_search_edit.textChanged.connect(self.update_link_search_preview)
        category_actions = QHBoxLayout()
        add_category_btn = self.secondary_button("Add Category", "fa5s.folder-plus")
        add_category_btn.clicked.connect(self.add_link_category_prototype)
        link_filter_btn = self.icon_menu_button(
            "fa5s.filter",
            "Filter links",
            [
                ("Pinned", lambda: self.show_flow_message("Link filter: Pinned")),
                ("Favorites", lambda: self.show_flow_message("Link filter: Favorites")),
                ("Recent", lambda: self.show_flow_message("Link filter: Recent")),
                ("Mostly Viewed", lambda: self.show_flow_message("Link filter: Mostly Viewed")),
            ],
        )
        category_actions.addWidget(add_category_btn)
        category_actions.addWidget(self.secondary_button("Rename", "fa5s.edit"))
        category_actions.addWidget(self.secondary_button("Archive", "fa5s.archive"))
        category_actions.addWidget(link_filter_btn)
        category_actions.addStretch()
        category_card.outer_layout.addLayout(category_actions)

        category_list = ClearableSelectionList()
        category_list.setObjectName("linkCategoryList")
        category_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.link_category_items = [
            "PROD · 3 links · red badge",
            "UAT · 3 links · blue badge",
            "CR & ITSM Tools · 2 links · tool badge",
            "Personal · 0 links · gray badge",
            "Archived · 4 links · restore available",
        ]
        for item in self.link_category_items:
            category_list.addItem(QListWidgetItem(item))
        category_list.setCurrentRow(0)
        self.category_list = category_list
        category_list.itemClicked.connect(self.handle_link_category_click)
        category_list.itemChanged.connect(lambda item: self.show_flow_message(f"Category saved: {item.text()}"))
        category_card.outer_layout.addWidget(category_list, 1)

        import_export = QHBoxLayout()
        import_export.addWidget(self.secondary_button("Import", "fa5s.file-import"))
        import_export.addWidget(self.secondary_button("Export", "fa5s.file-export"))
        import_export.addStretch()
        category_card.outer_layout.addLayout(import_export)
        link_splitter.addWidget(category_card)

        right_side = QWidget()
        right_side.setMinimumWidth(scaled(640))
        right_side.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_side)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(spacing_tight())

        quick_add = PanelCard("Add/Edit Link", "fa5s.edit", "create or update selected link")
        quick_grid = QGridLayout()
        quick_grid.setContentsMargins(0, 0, 0, 0)
        quick_grid.setHorizontalSpacing(spacing_tight())
        quick_grid.setVerticalSpacing(spacing_tight())
        self.link_title_edit = self.line_edit("Link title", "PROD Portal")
        self.link_url_edit = self.line_edit("Link", "https://prod.example.local/")
        self.link_tags_edit = self.line_edit("Tags, comma separated", "PROD, Portal, Working")
        self.link_details_edit = QTextEdit()
        self.link_details_edit.setPlaceholderText("Description")
        self.link_details_edit.setPlainText("Daily PROD validation and release checks")
        self.link_details_edit.setObjectName("linkDescriptionEdit")
        self.link_details_edit.setMinimumHeight(scaled(64))
        self.link_details_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        quick_grid.setColumnStretch(0, 1)
        quick_grid.setColumnStretch(1, 1)
        quick_grid.addWidget(self.field("Link Title", self.link_title_edit), 0, 0)
        quick_grid.addWidget(self.field("Link", self.link_url_edit), 1, 0)
        quick_grid.addWidget(self.field("Tags", self.link_tags_edit), 2, 0)
        quick_grid.addWidget(self.field("Description", self.link_details_edit), 0, 1, 3, 1)
        link_action_row = QHBoxLayout()
        link_action_row.setSpacing(spacing_tight())
        pin_link_btn = self.tiny_button("Pin", "fa5s.thumbtack")
        pin_link_btn.clicked.connect(lambda: self.show_flow_message(f"Pinned link flow: {self.link_title_edit.text()}"))
        favorite_link_btn = self.tiny_button("Favorite", "fa5s.star")
        favorite_link_btn.clicked.connect(lambda: self.show_flow_message(f"Favorite link flow: {self.link_title_edit.text()}"))
        save_link_btn = AnimatedPrimaryButton(" Save", "fa5s.save")
        save_link_btn.setMinimumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        save_link_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        save_link_btn.clicked.connect(self.save_link_from_panel)
        link_action_row.addStretch(1)
        link_action_row.addWidget(pin_link_btn)
        link_action_row.addWidget(favorite_link_btn)
        link_action_row.addWidget(save_link_btn)
        quick_add.outer_layout.addLayout(quick_grid)
        quick_add.outer_layout.addLayout(link_action_row)
        right_layout.addWidget(quick_add, 0)

        detail_card = PanelCard("PROD", "fa5s.link", "3 saved links")
        detail_top = QHBoxLayout()
        detail_top.addWidget(self.line_edit("Search title, URL, tags, details, path, or pattern..."), 1)
        self.link_header_sort_combo = QComboBox()
        self.link_header_sort_combo.addItems(["Newest", "Oldest", "A-Z", "Favorite", "Pinned"])
        self.link_header_sort_combo.setMinimumHeight(scaled(COMPACT_CONTROL_HEIGHT))
        self.link_header_sort_combo.setMinimumWidth(scaled(86))
        self.link_header_sort_combo.currentTextChanged.connect(self.link_search_sort_combo.setCurrentText)
        self.link_header_sort_combo.currentTextChanged.connect(self.update_link_card_sort)
        detail_top.addWidget(self.link_header_sort_combo)
        detail_card.outer_layout.addLayout(detail_top)

        shared_actions = QHBoxLayout()
        shared_actions.addWidget(self.secondary_button("Copy URL", "fa5s.copy"))
        edit_link_btn = self.secondary_button("Edit", "fa5s.edit")
        edit_link_btn.clicked.connect(self.populate_link_edit_panel)
        shared_actions.addWidget(edit_link_btn)
        shared_actions.addWidget(self.secondary_button("Remove", "fa5s.archive"))
        shared_actions.addStretch()
        detail_card.outer_layout.addLayout(shared_actions)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setObjectName("linkContentSplitter")
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(scaled(10))

        link_list_area = QScrollArea()
        link_list_area.setObjectName("linkListArea")
        link_list_area.setWidgetResizable(True)
        link_list_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        link_list_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        link_list_area.setFrameShape(QFrame.Shape.NoFrame)
        link_list_area.viewport().setObjectName("linkListViewport")
        link_list_area.viewport().setAutoFillBackground(False)
        link_list_content = QWidget()
        link_list_content.setObjectName("linkListContent")
        link_list_content.setAutoFillBackground(False)
        link_list_layout = QVBoxLayout(link_list_content)
        link_list_layout.setContentsMargins(spacing_tight(), spacing_tight(), spacing_tight(), spacing_tight())
        link_list_layout.setSpacing(spacing_tight())
        self.link_list_layout = link_list_layout

        link_items = [
            {"title": "PROD Portal", "tags": ["PROD", "Portal", "Working"], "url": "https://prod.example.local/", "details": "Daily PROD validation and release checks", "category": "PROD", "path": "PROD/PROD Portal", "date": "20260529", "last_modified": "20260529", "pinned": True, "favorite": True},
            {"title": "Weekly SOP", "tags": ["SOP", "Login Needed"], "url": "https://sop.example.local/weekly", "details": "Weekly operational SOP and login checklist", "category": "PROD", "path": "PROD/Weekly SOP", "date": "20260528", "last_modified": "20260528", "pinned": False, "favorite": False},
            {"title": "Release Board", "tags": ["Dashboard", "Internal Only"], "url": "https://release-board.example.local/", "details": "Release tracking dashboard with deployment pattern notes", "category": "PROD", "path": "PROD/Release Board", "date": "20260529", "last_modified": "20260529", "pinned": False, "favorite": False},
            {"title": "Evidence Folder", "tags": ["Evidence", "Working"], "url": "https://files.example.local/evidence", "details": "Shared evidence folder with capture documents", "category": "UAT", "path": "UAT/Evidence Folder", "date": "20260529", "last_modified": "20260529", "pinned": False, "favorite": False},
            {"title": "Deployment Calendar", "tags": ["Release", "Internal Only"], "url": "https://calendar.example.local/deploy", "details": "Deployment windows and blackout dates", "category": "PROD", "path": "PROD/Deployment Calendar", "date": "20260528", "last_modified": "20260528", "pinned": False, "favorite": False},
            {"title": "Rollback Checklist", "tags": ["SOP", "Release"], "url": "https://sop.example.local/rollback", "details": "Rollback checklist content and SQL path references", "category": "PROD", "path": "PROD/Rollback Checklist", "date": "20260527", "last_modified": "20260527", "pinned": False, "favorite": False},
            {"title": "CR Portal", "tags": ["CR", "Portal"], "url": "https://cr.example.local/", "details": "Change request portal and approval data", "category": "CR & ITSM Tools", "path": "CR & ITSM Tools/CR Portal", "date": "20260529", "last_modified": "20260529", "pinned": False, "favorite": False},
            {"title": "ITSM Queue", "tags": ["ITSM", "Login Needed"], "url": "https://itsm.example.local/queue", "details": "ITSM queue and incident link data", "category": "CR & ITSM Tools", "path": "CR & ITSM Tools/ITSM Queue", "date": "20260528", "last_modified": "20260528", "pinned": False, "favorite": False},
            {"title": "UAT Evidence", "tags": ["UAT", "Evidence"], "url": "https://uat.example.local/evidence", "details": "UAT evidence document content", "category": "UAT", "path": "UAT/UAT Evidence", "date": "20260529", "last_modified": "20260529", "pinned": False, "favorite": False},
            {"title": "SIT Dashboard", "tags": ["SIT", "Dashboard"], "url": "https://sit.example.local/dashboard", "details": "SIT status and defect pattern dashboard", "category": "UAT", "path": "UAT/SIT Dashboard", "date": "20260527", "last_modified": "20260527", "pinned": False, "favorite": False},
            {"title": "VPN Guide", "tags": ["Access", "Internal Only"], "url": "https://access.example.local/vpn", "details": "VPN guide for protected internal links", "category": "Personal", "path": "Personal/VPN Guide", "date": "20260528", "last_modified": "20260528", "pinned": False, "favorite": False},
            {"title": "Monitoring Board", "tags": ["Dashboard", "Working"], "url": "https://monitoring.example.local/", "details": "Monitoring board for release validation", "category": "PROD", "path": "PROD/Monitoring Board", "date": "20260529", "last_modified": "20260529", "pinned": False, "favorite": False},
        ]
        self.link_items = link_items
        self.render_link_cards(self.sort_link_items(link_items, "Newest"))
        link_list_area.setWidget(link_list_content)
        content_splitter.addWidget(link_list_area)

        link_detail = PanelCard("Selected Link Detail", "fa5s.info-circle", "PROD Portal")
        link_detail.setProperty("detailBox", True)
        self.selected_link_title = QLabel("PROD Portal")
        self.selected_link_title.setObjectName("cardTitle")
        link_detail.outer_layout.addWidget(self.selected_link_title)

        self.selected_link_url = QLabel('<a href="https://prod.example.local/">https://prod.example.local/</a>')
        self.selected_link_url.setObjectName("clickableLink")
        self.selected_link_url.setTextFormat(Qt.TextFormat.RichText)
        self.selected_link_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.selected_link_url.setOpenExternalLinks(False)
        self.selected_link_url.linkActivated.connect(self.handle_selected_link_url)
        link_detail.outer_layout.addWidget(self.selected_link_url)

        detail_body = QFrame()
        detail_body.setObjectName("selectedLinkBody")
        detail_body_layout = QVBoxLayout(detail_body)
        detail_body_layout.setContentsMargins(margin_inner(), margin_inner(), margin_inner(), margin_inner())
        detail_body_layout.setSpacing(spacing_tight())

        self.selected_link_meta = QLabel("Tags: PROD · Portal · Working\nDetails: Daily PROD validation and release checks\nCategory: PROD\nPath: PROD/PROD Portal\nDate: 20260529 · status: selected for toolbar actions")
        self.selected_link_meta.setObjectName("cardSubtitle")
        self.selected_link_meta.setWordWrap(True)
        detail_body_layout.addWidget(self.selected_link_meta)

        detail_hint = QLabel("Select link card body on the left, then use toolbar actions above. Click URL above for prototype open flow.")
        detail_hint.setObjectName("cardSubtitle")
        detail_hint.setWordWrap(True)
        detail_body_layout.addWidget(detail_hint)

        self.flow_status_label = QLabel("Ready · select link, click toolbar action, or click detail URL")
        self.flow_status_label.setObjectName("cardSubtitle")
        self.flow_status_label.setWordWrap(True)
        detail_body_layout.addWidget(self.flow_status_label)
        detail_body_layout.addStretch(1)
        link_detail.outer_layout.addWidget(detail_body, 1)
        content_splitter.addWidget(link_detail)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 3)
        content_splitter.setSizes([scaled(340), scaled(380)])
        detail_card.outer_layout.addWidget(content_splitter, 1)
        right_layout.addWidget(detail_card, 2)
        self.update_link_search_preview()

        link_splitter.addWidget(right_side)
        link_splitter.setStretchFactor(0, 2)
        link_splitter.setStretchFactor(1, 8)
        link_splitter.setSizes([scaled(280), scaled(860)])
        link_layout.addWidget(link_splitter, 1)
        return link_page


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", scaled_font(9)))
    window = SecondBrainWindow()
    window.show()
    sys.exit(app.exec())
