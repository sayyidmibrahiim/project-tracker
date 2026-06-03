# ============================================================
# Project Tracker DBS - Settings UI
# Cleaned from the user-edited Settings file.
# Notes:
# - Keeps the current layout/display sizing that already works.
# - Restores missing notification panel and header datetime.
# - Uses a 50/50 Settings + Help body layout.
# - Keeps responsive/high-DPI helpers and avoids changing unrelated UI.
# ============================================================

import os
import sys
from math import pi, sin

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
    QApplication,
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QSplitter,
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
# ------------------------------------------------------------
# Centralized palette and layout constants.
# ------------------------------------------------------------
# ============================================================
# Enterprise palette — solid colors only, no gradients.
# ============================================================
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


def create_shadow(widget, blur_radius=20, x_offset=0, y_offset=4, alpha=45):
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


class ModernComboBox(QComboBox):
    def __init__(self, items=None, min_width=120, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setMinimumWidth(scaled(min_width))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if items:
            self.addItems(items)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(C_DARK))
        pen.setWidth(max(1, scaled(1)))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        x = self.width() - scaled(18)
        y = self.height() // 2 - scaled(2)
        painter.drawLine(x, y, x + scaled(4), y + scaled(4))
        painter.drawLine(x + scaled(4), y + scaled(4), x + scaled(8), y)
        painter.end()


class AnimatedSearch(QLineEdit):
    def __init__(self, placeholder="Search settings...", parent=None):
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
    def __init__(self, text, icon_name="fa5s.save", parent=None):
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

        clock_icon = QLabel()
        clock_icon.setPixmap(
            qta.icon("fa5s.calendar-alt", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        layout.addWidget(clock_icon)

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


class MetricCard(QFrame):
    def __init__(self, label, value, icon_name, helper, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        create_shadow(self, blur_radius=14, y_offset=3, alpha=20)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        layout.setSpacing(scaled(12))

        icon = QLabel()
        icon.setObjectName("metricIcon")
        icon.setMinimumSize(scaled(28), scaled(28))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(0)

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        text_col.addWidget(value_label)

        label_text = QLabel(label)
        label_text.setObjectName("metricLabel")
        text_col.addWidget(label_text)

        helper_text = QLabel(helper)
        helper_text.setObjectName("metricHelper")
        helper_text.setWordWrap(True)
        text_col.addWidget(helper_text)

        layout.addLayout(text_col, 1)


class PanelCard(QFrame):
    def __init__(self, title, icon_name, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("panelCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        create_shadow(self, blur_radius=14, x_offset=0, y_offset=3, alpha=24)
        self.outer_layout = QVBoxLayout(self)
        # Slightly larger padding/spacing so cards do not feel too cramped.
        self.outer_layout.setContentsMargins(
            scaled(14), scaled(12), scaled(14), scaled(12)
        )
        self.outer_layout.setSpacing(scaled(10))

        header = QHBoxLayout()
        header.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(
            qta.icon(icon_name, color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        header.addWidget(icon)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        header.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("cardSubtitle")
            subtitle_label.setWordWrap(True)
            header.addWidget(subtitle_label, 1)
        else:
            header.addStretch(1)

        self.outer_layout.addLayout(header)


class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.responsive_manager = get_manager(self)
        self.responsive_manager.profileChanged.connect(
            self._handle_responsive_profile_changed
        )
        self.setWindowTitle("Project Tracker DBS - Settings")
        self.resize(*screen_fraction(0.85, 0.90))
        self.setMinimumSize(*screen_fraction(0.50, 0.50))
        center_window(self)
        self.setFont(QFont("Inter", scaled_font(8)))
        self.setStyleSheet(self.get_stylesheet())
        self.sidebar_expanded = True
        self.nav_buttons = []

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = self.build_sidebar()
        root.addWidget(self.sidebar)

        self.main_wrapper = QFrame()
        self.main_wrapper.setObjectName("mainWrapper")
        main_layout = QVBoxLayout(self.main_wrapper)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.build_header(main_layout)
        self.build_content(main_layout)
        root.addWidget(self.main_wrapper, 1)

    def _handle_responsive_profile_changed(self, _profile) -> None:
        self.updateGeometry()
        self.update()

    def build_sidebar(self):
        """Build left navigation, notification panel, and collapse control."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(scaled(SIDEBAR_EXPANDED_WIDTH))
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        layout.setSpacing(spacing_tight())

        # Brand row. Store layout/widgets so collapsed mode can keep the logo centered.
        self.title_row = QHBoxLayout()
        self.title_row.setSpacing(spacing_tight())

        self.logo = QLabel()
        self.logo.setObjectName("logoBlock")
        self.logo.setFixedSize(scaled(22), scaled(22))
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setPixmap(
            qta.icon("fa5s.layer-group", color=C_WHITE).pixmap(scaled(13), scaled(13))
        )
        self.title_row.addWidget(self.logo)

        self.app_title = QLabel("Project Tracker")
        self.app_title.setObjectName("appTitle")
        self.title_row.addWidget(self.app_title, 1)
        layout.addLayout(self.title_row)
        layout.addSpacing(scaled(10))

        items = [
            ("Dashboard", "fa5s.chart-pie"),
            ("Project Details", "fa5s.folder-open"),
            ("Second Brain", "fa5s.brain"),
            ("Report", "fa5s.chart-bar"),
            ("Automations", "fa5s.robot"),
            ("Settings", "fa5s.cog"),
        ]
        for text, icon_name in items:
            button = SidebarButton(text, icon_name, text == "Settings")
            self.nav_buttons.append(button)
            layout.addWidget(button)

        # Collapsed-only notification shortcut, positioned under Settings.
        self.notification_icon_btn = SidebarButton("Notifications", "fa5s.bell", False)
        self.notification_icon_btn.set_collapsed(True)
        self.notification_icon_btn.hide()
        layout.addWidget(self.notification_icon_btn)

        # Expanded notification panel. It stretches above the collapse button and scrolls when crowded.
        self.notif_frame = self.build_notification_panel()
        layout.addWidget(self.notif_frame, 1)

        layout.addStretch(0)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("collapseButton")
        self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-left", color=C_LIGHT))
        self.collapse_btn.setIconSize(QSize(scaled(12), scaled(12)))
        self.collapse_btn.setMinimumHeight(scaled(26))
        self.collapse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        create_button_shadow(self.collapse_btn, blur_radius=8, y_offset=1, alpha=28)
        self.collapse_btn.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.collapse_btn)
        return sidebar

    def build_notification_panel(self):
        """Scrollable notification panel restored from the dashboard sidebar behavior."""
        frame = QFrame()
        frame.setObjectName("notifFrame")
        frame.setMinimumHeight(scaled(NOTIFICATION_MIN_HEIGHT))
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        create_shadow(frame, blur_radius=28, x_offset=0, y_offset=8, alpha=80)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        layout.setSpacing(spacing_tight())

        header = QHBoxLayout()
        header.setSpacing(spacing_tight())

        bell = QLabel()
        bell.setPixmap(
            qta.icon("fa5s.bell", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        header.addWidget(bell)

        title = QLabel("Notifications")
        title.setObjectName("notifTitle")
        header.addWidget(title)
        header.addStretch(1)

        dismiss = QPushButton("Dismiss")
        dismiss.setObjectName("textButtonLight")
        dismiss.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        create_button_shadow(dismiss, blur_radius=6, y_offset=1, alpha=18)
        header.addWidget(dismiss)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("notifScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.viewport().setObjectName("notifViewport")
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("notifContent")
        content.setAutoFillBackground(False)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, scaled(4), 0)
        content_layout.setSpacing(spacing_tight())
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        empty = QLabel("No notifications yet.")
        empty.setObjectName("emptyNotifText")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setWordWrap(True)
        empty.setMinimumHeight(scaled(80))
        content_layout.addWidget(empty)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return frame

    def toggle_sidebar(self):
        """Collapse/expand sidebar while keeping all icons visually aligned."""
        new_width = (
            scaled(SIDEBAR_COLLAPSED_WIDTH)
            if self.sidebar_expanded
            else scaled(SIDEBAR_EXPANDED_WIDTH)
        )
        self.sidebar_anim_min = QPropertyAnimation(self.sidebar, b"minimumWidth", self)
        self.sidebar_anim_max = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        for anim in (self.sidebar_anim_min, self.sidebar_anim_max):
            anim.setDuration(220)
            anim.setStartValue(self.sidebar.width())
            anim.setEndValue(new_width)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            anim.start()

        self.sidebar_expanded = not self.sidebar_expanded
        collapsed = not self.sidebar_expanded

        for button in self.nav_buttons:
            button.set_collapsed(collapsed)

        self.app_title.setVisible(not collapsed)
        self.notif_frame.setVisible(not collapsed)
        self.notification_icon_btn.setVisible(collapsed)
        self.title_row.setAlignment(
            self.logo,
            (Qt.AlignmentFlag.AlignCenter if collapsed else Qt.AlignmentFlag.AlignLeft)
            | Qt.AlignmentFlag.AlignVCenter,
        )
        self.collapse_btn.setIcon(
            qta.icon(
                "fa5s.angle-double-right" if collapsed else "fa5s.angle-double-left",
                color=C_LIGHT,
            )
        )

    def build_header(self, parent_layout):
        """Build red header with title at left, datetime centered, refresh at right."""
        header = QFrame()
        header.setObjectName("headerFrame")
        create_shadow(header, blur_radius=20, y_offset=5, alpha=50)

        layout = QGridLayout(header)
        layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        layout.setHorizontalSpacing(spacing_tight())
        layout.setVerticalSpacing(0)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

        title_box = QFrame()
        title_box.setObjectName("headerTitleBox")
        title_layout = QHBoxLayout(title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(spacing_tight())
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        divider = QFrame()
        divider.setObjectName("pageTitleDivider")
        divider.setMinimumWidth(scaled(4))
        divider.setMaximumWidth(scaled(4))
        divider.setMinimumHeight(scaled(26))
        divider.setMaximumHeight(scaled(26))
        title_layout.addWidget(divider)

        title = QLabel("Settings.")
        title.setObjectName("pageTitle")
        title.setFont(QFont("Inter", scaled_font(16), QFont.Weight.Bold))
        title_layout.addWidget(title)

        layout.addWidget(
            title_box,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        layout.addWidget(
            DateTimeBadge(),
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        layout.addWidget(
            RefreshButton(),
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        parent_layout.addWidget(header)

    def build_content(self, parent_layout):
        """Build a clean 50/50 body: Settings panel on the left, Help reader on the right."""
        workspace = QFrame()
        workspace.setObjectName("workspaceArea")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        layout.setSpacing(scaled(12))

        # Two equal panels. QSplitter keeps the 50/50 default but lets the user resize when needed.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("settingsSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.build_settings_panel())
        splitter.addWidget(self.build_help_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(scaled(14))
        splitter.setSizes([scaled(520), scaled(520)])
        layout.addWidget(splitter, 1)

        parent_layout.addWidget(workspace, 1)

    def apply_outer_panel_header_style(self, panel):
        """Style only the main panel header; inner-card typography stays unchanged."""
        for label in panel.findChildren(QLabel):
            if label.objectName() == "cardTitle":
                label.setStyleSheet(f"color: {C_TEXT_STRONG};")
            elif label.objectName() == "cardSubtitle":
                label.setStyleSheet(f"color: {C_HEADER_RED};")

    def build_settings_panel(self):
        """Left 50% body area.

        The settings content is intentionally compact. The splitter child still
        owns the full left half, but the actual Settings card only takes the
        height required by its fields, so we do not get a huge empty white card.
        """
        # Wrapper keeps the 50% splitter area while letting the card stay compact
        # at the top. The remaining vertical space stays as workspace background.
        wrapper = QWidget()
        wrapper.setObjectName("settingsPanelWrapper")
        wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        outer = PanelCard("Settings", "fa5s.cog", "application configuration")
        outer.setObjectName("mainBodyPanel")
        outer.setProperty("panelRole", "settings")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        create_shadow(outer, blur_radius=22, y_offset=5, alpha=42)
        self.apply_outer_panel_header_style(outer)

        # Directly place the three cards instead of putting them in an expanding
        # scroll area. This keeps the panel height equal to the real content.
        outer.outer_layout.addWidget(self.build_general_card())
        outer.outer_layout.addWidget(self.build_behavior_card())
        outer.outer_layout.addWidget(self.build_paths_card())

        # One icon only: the button icon. Avoid emoji + icon duplication.
        save_row = QHBoxLayout()
        save_row.setContentsMargins(0, spacing_tight(), 0, 0)
        save_row.addStretch(1)
        save_row.addWidget(AnimatedPrimaryButton("Save Settings", "fa5s.save"))
        outer.outer_layout.addLayout(save_row)

        wrapper_layout.addWidget(outer, 0, Qt.AlignmentFlag.AlignTop)
        wrapper_layout.addStretch(1)
        return wrapper

    def build_help_panel(self):
        """Right 50% body panel: searchable white-paper help reader with long dummy content."""
        outer = PanelCard("Help Center", "fa5s.question-circle", "application guide")
        outer.setObjectName("mainBodyPanel")
        outer.setProperty("panelRole", "help")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        create_shadow(outer, blur_radius=22, y_offset=5, alpha=42)
        self.apply_outer_panel_header_style(outer)

        # Search stays in body, above the help reader.
        help_search = AnimatedSearch("Search help topics...")
        help_search.setObjectName("bodyHelpSearch")
        help_search.setMinimumWidth(scaled(SEARCH_WIDTH_NORMAL))
        help_search.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        outer.outer_layout.addWidget(help_search)

        paper_scroll = QScrollArea()
        paper_scroll.setObjectName("helpPaperScroll")
        paper_scroll.setWidgetResizable(True)
        paper_scroll.setFrameShape(QFrame.Shape.NoFrame)
        paper_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        paper_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        paper_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        paper_scroll.viewport().setObjectName("helpPaperViewport")
        paper_scroll.viewport().setAutoFillBackground(False)

        paper = QWidget()
        paper.setObjectName("helpPaper")
        paper.setAutoFillBackground(False)
        paper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        paper_layout = QVBoxLayout(paper)
        paper_layout.setContentsMargins(scaled(14), scaled(14), scaled(14), scaled(14))
        paper_layout.setSpacing(scaled(10))
        paper_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Project Tracker DBS — Help Guide")
        title.setObjectName("helpDocumentTitle")
        title.setWordWrap(True)
        paper_layout.addWidget(title)

        intro = QLabel(
            "This help page is dummy documentation for testing scroll behavior. Later, this area can be connected "
            "to real markdown, PDF-like documents, or internal project tracker manuals. The layout is intentionally "
            "white like a document reader so it feels closer to reading Word/PDF documentation."
        )
        intro.setObjectName("helpDocumentParagraph")
        intro.setWordWrap(True)
        paper_layout.addWidget(intro)

        topics = [
            (
                "1. General Settings",
                "Root Folder controls where project data, generated documents, and local workspace files are stored. Display Name can be used later for personalized headers, exports, or automation signatures. Language and datetime format affect how information is shown across the application.",
            ),
            (
                "2. Behavior",
                "T-10 Threshold is used for reminder logic and operational alerts. Auto Refresh controls whether the application should reload project data periodically. Startup Behavior decides which workspace opens first when the application starts.",
            ),
            (
                "3. Paths",
                "Second Brain Folder points to long-form notes and operational knowledge. File Template Folder should point to reusable templates used by Project Details, automation menus, and documentation workflows.",
            ),
            (
                "4. Notifications",
                "The sidebar notification panel is designed for lightweight alerts. It stays visible in expanded mode and switches to an icon shortcut under Settings when the sidebar is collapsed.",
            ),
            (
                "5. Automations",
                "Automation menus can later manage Outlook, Teams, reminders, download-email jobs, and status-based triggers. Each automation should write activity into project history so every important action is traceable.",
            ),
            (
                "6. Project Details",
                "Project Details is intended to be the operational center for CR numbers, drone tickets, project state, sub-projects, files, notes, and activity history.",
            ),
            (
                "7. Report",
                "The report workspace summarizes CR state, drone state, monthly activity, folder status, and export-ready project data. Filters should stay compact and readable across monitor sizes.",
            ),
            (
                "8. Responsive UI",
                "The interface should avoid fixed major container sizes. It should use layouts, scroll areas, splitters, and scaled values so PopOS, Windows 125%, Windows 150%, laptop screens, and external monitors stay usable.",
            ),
            (
                "9. Troubleshooting",
                "If something looks clipped, first check display scale, DPI behavior, hardcoded sizes, missing stretch factors, and scrollable containers. UI components should be allowed to resize naturally whenever possible.",
            ),
            (
                "10. Future Documentation",
                "This dummy content can be replaced with real help articles such as setup guide, shortcut guide, folder structure guide, automation guide, backup strategy, and deployment guide.",
            ),
        ]

        for heading, body in topics:
            paper_layout.addWidget(self.build_help_topic(heading, body))

        # Extra dummy paragraphs so scroll behavior can be tested immediately.
        for idx in range(1, 9):
            paragraph = QLabel(
                f"Additional guide note {idx}: This is placeholder documentation text for scroll testing. "
                "In production, this can contain longer operational instructions, screenshots, version notes, "
                "FAQ entries, or internal SOP details related to Project Tracker DBS workflows."
            )
            paragraph.setObjectName("helpDocumentParagraph")
            paragraph.setWordWrap(True)
            paper_layout.addWidget(paragraph)

        paper_layout.addStretch(1)
        paper_scroll.setWidget(paper)
        outer.outer_layout.addWidget(paper_scroll, 1)
        return outer

    def make_scroll_column(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.viewport().setObjectName("scrollViewport")
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("scrollContent")
        content.setAutoFillBackground(False)
        column = QVBoxLayout(content)
        column.setContentsMargins(0, 0, spacing_tight(), 0)
        column.setSpacing(spacing_tight())
        column.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        return scroll, column

    def make_form(self):
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(scaled(10))
        form.setVerticalSpacing(scaled(5))
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return form

    def add_form_row(self, form, label_text, widget):
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        label.setMinimumWidth(scaled(140))
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        widget.setMinimumHeight(scaled(26))
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form.addRow(label, widget)

    def line_edit(self, placeholder="", text=""):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setText(text)
        edit.setMinimumHeight(scaled(26))
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return edit

    def browse_field(self, edit):
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing_tight())
        layout.addWidget(edit, 1)

        button = QPushButton("Browse")
        button.setObjectName("secondaryButton")
        button.setIcon(qta.icon("fa5s.folder-open", color=C_DARK))
        button.setIconSize(QSize(scaled(12), scaled(12)))
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setMinimumHeight(scaled(26))
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        create_button_shadow(button, blur_radius=8, y_offset=1, alpha=26)
        layout.addWidget(button)
        return row

    def build_general_card(self):
        card = PanelCard("General", "fa5s.sliders-h", "application identity")
        card.setProperty("cardRole", "general")
        form = self.make_form()
        self.add_form_row(
            form,
            "Root Folder",
            self.browse_field(
                self.line_edit("Root folder", "/home/sayyidmibrahim/Documents")
            ),
        )
        self.add_form_row(form, "Display Name", self.line_edit("Display name", ""))
        self.add_form_row(form, "Language", ModernComboBox(["en", "id"], 120))
        self.add_form_row(
            form,
            "Datetime Format",
            self.line_edit("Datetime format", "ddd, dd MMM yyyy HH:mm:ss"),
        )
        card.outer_layout.addLayout(form)
        return card

    def build_behavior_card(self):
        card = PanelCard("Behavior", "fa5s.bolt", "operational preferences")
        card.setProperty("cardRole", "behavior")
        form = self.make_form()

        threshold = QSpinBox()
        threshold.setValue(10)
        threshold.setMinimum(0)
        threshold.setMaximum(999)

        self.add_form_row(form, "T-10 Threshold", threshold)
        self.add_form_row(
            form,
            "Auto Refresh",
            ModernComboBox(["off", "15 seconds", "30 seconds", "1 minute"], 150),
        )
        self.add_form_row(
            form,
            "Theme",
            ModernComboBox(["locked-dashboard-v13", "dark", "light"], 190),
        )
        self.add_form_row(
            form,
            "Startup Behavior",
            ModernComboBox(
                ["current_year_dashboard", "project_details", "second_brain"], 220
            ),
        )
        card.outer_layout.addLayout(form)
        return card

    def build_paths_card(self):
        card = PanelCard("Paths", "fa5s.folder-open", "second brain and templates")
        card.setProperty("cardRole", "paths")
        form = self.make_form()
        self.add_form_row(
            form,
            "Second Brain Folder",
            self.browse_field(
                self.line_edit(
                    "Second Brain Folder", "/home/sayyidmibrahim/Documents/DOCUMENT"
                )
            ),
        )
        self.add_form_row(
            form,
            "File Template Folder",
            self.browse_field(self.line_edit("File Template Folder", "")),
        )
        card.outer_layout.addLayout(form)
        return card

    def build_help_topic(self, title_text, description_text):
        """Small reusable help topic row used inside the Help Center card."""
        topic = QFrame()
        topic.setObjectName("helpTopic")
        create_shadow(topic, blur_radius=10, y_offset=2, alpha=18)

        layout = QVBoxLayout(topic)
        layout.setContentsMargins(scaled(12), scaled(10), scaled(12), scaled(10))
        layout.setSpacing(scaled(6))

        title = QLabel(title_text)
        title.setObjectName("helpTopicTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        description = QLabel(description_text)
        description.setObjectName("helpTopicText")
        description.setWordWrap(True)
        layout.addWidget(description)
        return topic

    def get_stylesheet(self):
        """Centralized QSS: enterprise red / white / black / soft-pink palette."""
        return f"""
            * {{
                font-family: "Inter", "Segoe UI", sans-serif;
            }}
            QMainWindow {{
                background-color: {C_BLACK_CHROME};
            }}
            #sidebar {{
                background-color: {C_BLACK_CHROME};
                border-right: {scaled(1)}px solid {C_DARK_BORDER};
            }}
            #logoBlock {{
                background-color: {C_PRIMARY_RED};
                border-radius: {scaled(5)}px;
            }}
            #mainWrapper, #workspaceArea {{
                background-color: {C_BODY_WHITE_LAYER};
            }}
            #headerFrame {{
                background-color: {C_HEADER_RED};
                border-bottom: {scaled(1)}px solid {C_HEADER_RED_DARK};
            }}
            #headerTitleBox {{
                background: transparent;
                border: none;
            }}
            #pageTitleDivider {{
                background-color: {C_BLACK_CHROME};
                border-radius: {scaled(2)}px;
            }}
            #pageTitle {{
                color: {C_HEADER_TITLE};
                font-size: {scaled_font(16)}pt;
                font-weight: 900;
                letter-spacing: {scaled(1)}px;
            }}
            #pageSubtitle {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #appTitle {{
                color: {C_WHITE};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #headerRefreshButton {{
                background-color: {C_INPUT_WHITE_LAYER};
                border: {scaled(1)}px solid {C_BLACK_CHROME};
                border-radius: {scaled(5)}px;
                color: {C_HEADER_REFRESH_ICON};
                padding: 0 {scaled(6)}px;
            }}
            #headerRefreshButton:hover {{
                background-color: {C_OUTER_WHITE_LAYER};
                border-color: {C_BLACK_CHROME};
            }}
            #headerRefreshButton:pressed {{
                background-color: {C_PANEL_WHITE_LAYER};
            }}
            #dateTimeBadge {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-radius: {scaled(6)}px;
                border: {scaled(1)}px solid {C_HEADER_CHIP_BORDER};
            }}
            #dateTimeLabel {{
                color: {C_HEADER_TIME_TEXT};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #notifFrame {{
                background-color: {C_NOTIFICATION_BG};
                border-radius: {scaled(8)}px;
                border: {scaled(1)}px solid {C_NOTIFICATION_BORDER};
            }}
            #notifTitle {{
                color: {C_WHITE};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #emptyNotifText {{
                color: {C_TEXT_MUTED};
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
                padding: {scaled(8)}px;
            }}
            #notifScroll, #notifContent {{
                background-color: transparent;
                border: none;
            }}
            #textButtonLight {{
                background-color: transparent;
                color: {C_TEXT_MUTED};
                border: none;
                font-size: {scaled_font(7)}pt;
                font-weight: 900;
            }}
            #textButtonLight:hover {{
                color: {C_WHITE};
            }}
            #collapseButton {{
                padding: {scaled(4)}px;
                background-color: {C_SURFACE_DARK};
                border: {scaled(1)}px solid {C_DARK_BORDER};
                border-radius: {scaled(5)}px;
            }}
            #collapseButton:hover {{
                background-color: {C_ACTIVE_NAV_BG};
                border-color: {C_ACTIVE_RED};
            }}
            #settingsPanelWrapper {{
                background-color: transparent;
            }}
            #mainBodyPanel {{
                background-color: {C_MAIN_PANEL_CHARCOAL};
                border-radius: {scaled(8)}px;
                border: {scaled(1)}px solid {C_MAIN_PANEL_CHARCOAL_BORDER};
            }}
            #mainBodyPanel[panelRole="settings"] {{
                background-color: {C_MAIN_PANEL_CHARCOAL};
                border-color: {C_MAIN_PANEL_CHARCOAL_BORDER};
            }}
            #mainBodyPanel[panelRole="help"] {{
                background-color: {C_MAIN_PANEL_CHARCOAL};
                border-color: {C_MAIN_PANEL_CHARCOAL_BORDER};
            }}
            #mainBodyPanel:hover {{
                border-color: {C_SOFT_PINK_BORDER};
            }}
            #helpPaperScroll {{
                background-color: transparent;
                border: none;
            }}
            #helpPaper {{
                background-color: {C_PANEL_WHITE_LAYER};
                border: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-radius: {scaled(7)}px;
            }}
            #helpDocumentTitle {{
                color: {C_TEXT_STRONG};
                font-size: {scaled_font(12)}pt;
                font-weight: 900;
            }}
            #helpDocumentParagraph {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 650;
                line-height: 130%;
            }}
            #panelCard, #metricCard {{
                background-color: {C_PANEL_WHITE_LAYER};
                border-radius: {scaled(7)}px;
                border: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
            }}
            #panelCard[cardRole="general"] {{
                background-color: {C_PANEL_WHITE_LAYER};
                border-top: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-right: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-bottom: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-left: {scaled(3)}px solid {C_HEADER_RED};
            }}
            #panelCard[cardRole="behavior"] {{
                background-color: {C_PANEL_WHITE_LAYER};
                border-top: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-right: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-bottom: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-left: {scaled(3)}px solid {C_HEADER_RED};
            }}
            #panelCard[cardRole="paths"] {{
                background-color: {C_PANEL_WHITE_LAYER};
                border-top: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-right: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-bottom: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-left: {scaled(3)}px solid {C_HEADER_RED};
            }}
            #cardTitle {{
                background: transparent;
                color: {C_TEXT_PRIMARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #cardSubtitle {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #helpTopic {{
                background-color: {C_CONTENT_WHITE_LAYER};
                border-top: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-right: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-bottom: {scaled(1)}px solid {C_SUBTLE_WHITE_BORDER};
                border-left: {scaled(3)}px solid {C_HEADER_RED};
                border-radius: {scaled(7)}px;
            }}
            #helpTopicTitle {{
                color: {C_TEXT_PRIMARY};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #helpTopicText {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 650;
            }}
            #metricIcon {{
                background-color: {C_SOFT_PINK_SURFACE};
                border-radius: {scaled(6)}px;
            }}
            #metricValue {{
                color: {C_TEXT_STRONG};
                font-size: {scaled_font(9)}pt;
                font-weight: 900;
            }}
            #metricLabel {{
                color: {C_TEXT_PRIMARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
            }}
            #metricHelper {{
                color: {C_TEXT_SECONDARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 650;
            }}
            #fieldLabel {{
                color: {C_TEXT_PRIMARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            QLineEdit, QSpinBox, QComboBox {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                border-radius: {scaled(5)}px;
                background-color: {C_INPUT_WHITE_LAYER};
                color: {C_TEXT_PRIMARY};
                font-size: {scaled_font(8)}pt;
                font-weight: 750;
                selection-background-color: {C_SOFT_PINK_ACCENT};
                selection-color: {C_TEXT_PRIMARY};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: {scaled(1)}px solid {C_PRIMARY_RED};
                background-color: {C_CARD_WHITE};
            }}
            QLineEdit::placeholder {{
                color: {C_PLACEHOLDER};
            }}
            QComboBox::drop-down {{
                border: none;
                width: {scaled(18)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {C_CARD_WHITE};
                color: {C_TEXT_PRIMARY};
                border: {scaled(1)}px solid {C_INPUT_BORDER};
                selection-background-color: {C_SOFT_PINK_SURFACE};
                selection-color: {C_TEXT_PRIMARY};
            }}
            #bodyHelpSearch {{
                background-color: {C_INPUT_WHITE_LAYER};
                border-color: {C_INPUT_BORDER};
            }}
            #secondaryButton {{
                background-color: {C_CARD_WHITE};
                color: {C_PRIMARY_RED};
                border: {scaled(1)}px solid {C_SECONDARY_BUTTON_BORDER};
                border-radius: {scaled(5)}px;
                font-size: {scaled_font(8)}pt;
                font-weight: 800;
                padding: 0 {scaled(8)}px;
            }}
            #secondaryButton:hover {{
                background-color: {C_SOFT_PINK_SURFACE};
                border-color: {C_SOFT_PINK_BORDER};
            }}
            QSplitter::handle {{
                background-color: {C_BODY_WHITE_LAYER};
                width: {scaled(10)}px;
                margin: 0px;
                border-left: {scaled(1)}px solid {C_SOFT_WHITE_BORDER};
                border-right: {scaled(1)}px solid {C_SOFT_WHITE_BORDER};
            }}
            QSplitter::handle:hover {{
                background-color: {C_SOFT_PINK_SURFACE};
                border-left: {scaled(1)}px solid {C_HEADER_RED};
                border-right: {scaled(1)}px solid {C_HEADER_RED};
            }}
            QScrollArea,
            QScrollArea > QWidget,
            #notifViewport,
            #notifContent,
            #helpPaperViewport,
            #helpPaper,
            #scrollViewport,
            #scrollContent {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: {scaled(5)}px;
                margin: {scaled(2)}px 0px {scaled(2)}px 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {C_SOFT_PINK_ACCENT};
                min-height: {scaled(14)}px;
                border-radius: {scaled(4)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {C_PRIMARY_RED};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background-color: transparent;
                height: 0px;
            }}
        """


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", scaled_font(9)))
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
