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
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
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
# ==========================================
# ENTERPRISE BANKING DESIGN TOKENS
# ==========================================
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


# ==========================================
# HELPERS
# ==========================================
def create_shadow(widget, blur_radius=20, x_offset=0, y_offset=4, alpha=50):
    """Attach a drop shadow to one widget."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(scaled(blur_radius))
    shadow.setOffset(scaled(x_offset), scaled(y_offset))
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)
    return shadow


def create_button_shadow(button, blur_radius=10, y_offset=2, alpha=32):
    return create_shadow(
        button, blur_radius=blur_radius, x_offset=0, y_offset=y_offset, alpha=alpha
    )


class SmoothShadowButtonMixin:
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
            target_y = self._shadow_y_hover if self.underMouse() else self._shadow_y_idle
            self.animate_shadow(target_blur, target_y)
        super().mouseReleaseEvent(event)


def repolish(widget):
    """Force Qt stylesheet refresh after objectName/property changes."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ==========================================
# CUSTOM WIDGETS
# ==========================================
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
    """Header search with smooth width animation.

    The old search animation changed too abruptly because min/max width started
    from inconsistent values. This version animates both width limits from their
    current values using OutCubic for a stable, non-laggy feel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search projects...")
        # Match Settings header control proportions.
        self._collapsed_width = scaled(SEARCH_WIDTH_NORMAL)
        self._expanded_width = scaled(SEARCH_WIDTH_FOCUSED)
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)
        self.setMinimumHeight(scaled(28))
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
        width = int(width)
        self.anim_min.stop()
        self.anim_max.stop()

        self.anim_min.setStartValue(self.minimumWidth())
        self.anim_min.setEndValue(width)
        self.anim_max.setStartValue(self.maximumWidth())
        self.anim_max.setEndValue(width)

        self.anim_min.start()
        self.anim_max.start()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.animate_width(self._expanded_width)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.animate_width(self._collapsed_width)


class AnimatedPrimaryButton(SmoothShadowButtonMixin, QPushButton):
    def __init__(self, text, icon_name, parent=None):
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
        self._padding = scaled(8) if is_active else scaled(6)

        self.setText(text)
        self.setIconSize(QSize(scaled(8), scaled(8)))
        self.setMinimumHeight(scaled(SIDEBAR_CONTROL_HEIGHT))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        self.setText("" if collapsed else self.original_text)
        self.setToolTip(self.original_text if collapsed else "")
        self.update_style()

    @pyqtProperty(int)
    def padding(self):
        return self._padding

    def set_padding(self, val):
        self._padding = int(val)
        self.update_style()

    def update_style(self):
        icon_color = C_WHITE if self.is_active else C_INACTIVE_NAV_TEXT
        self.setIcon(qta.icon(self.icon_name, color=icon_color))

        bg = C_ACTIVE_NAV_BG if self.is_active else "transparent"
        color = C_WHITE if self.is_active else C_INACTIVE_NAV_TEXT
        weight = "900" if self.is_active else "800"
        border_left = C_ACTIVE_RED if self.is_active else "transparent"
        pad_left = scaled(4) if self.is_collapsed else scaled(8)
        text_align = "center" if self.is_collapsed else "left"

        self.setStyleSheet(f"""
            QPushButton {{
                text-align: {text_align};
                padding: {scaled(4)}px {scaled(6)}px {scaled(4)}px {pad_left}px;
                background-color: {bg};
                color: {color};
                font-weight: {weight};
                border: none;
                border-left: {scaled(3)}px solid {border_left};
                border-radius: {scaled(5)}px;
                font-size: {scaled_font(8)}pt;
            }}
            QPushButton:hover {{
                background-color: {C_ACTIVE_NAV_BG};
                color: {C_WHITE};
                border-left: {scaled(3)}px solid {C_ACTIVE_RED};
            }}
        """)

    def enterEvent(self, event):
        if not self.is_active:
            self.setIcon(qta.icon(self.icon_name, color=C_WHITE))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.setIcon(qta.icon(self.icon_name, color=C_INACTIVE_NAV_TEXT))
        super().leaveEvent(event)


class ClearableSelectionTable(QTableWidget):
    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentItem(None)
            event.accept()
            return

        super().mousePressEvent(event)


class EditableLinkLineEdit(QLineEdit):
    def __init__(self, value="", parent=None, on_commit=None):
        super().__init__(parent)
        normalized_value = "" if value is None else str(value).strip()

        self.setObjectName("tableLinkEdit")
        self.setText(normalized_value)
        self.setToolTip(normalized_value)
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        self.setMinimumHeight(scaled(28))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setClearButtonEnabled(False)
        self.setFrame(False)

        self._last_committed_value = normalized_value
        self.on_commit = on_commit

        # Enter is still supported, but no longer required.
        self.returnPressed.connect(self.commit_and_clear_focus)

    def focusOutEvent(self, event):
        # Auto-save/commit when user clicks anywhere else.
        self.commit_value()
        super().focusOutEvent(event)

    def commit_and_clear_focus(self):
        self.commit_value()
        self.clearFocus()

    def commit_value(self):
        new_value = self.text().strip()
        self.setText(new_value)
        self.setToolTip(new_value)
        self.setCursorPosition(0)

        # Avoid duplicate updates when Enter triggers focusOut afterwards.
        if new_value == self._last_committed_value:
            return

        self._last_committed_value = new_value

        if callable(self.on_commit):
            self.on_commit(new_value)


class TableStateCombo(QPushButton):
    def __init__(self, current_value, options=None, parent=None):
        super().__init__(parent)
        self.setObjectName("stateCombo")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(scaled(30))
        self.setMinimumWidth(scaled(128))
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

        # Inset the rounded rectangle so no corner gets clipped by the cell viewport.
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(border, 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 6, 6)

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


class StatusBadge(QLabel):
    def __init__(self, text, state="warning", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Inter", scaled_font(8), QFont.Weight.Bold))
        self.setMinimumHeight(scaled(14))

        if state == "warning":
            bg, color = C_ORANGE, C_WHITE
        elif state == "success":
            bg, color = C_DARK, C_WHITE
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


class DateTimeBadge(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dateTimeBadge")
        self.setMinimumHeight(scaled(26))
        self.setMinimumWidth(scaled(230))

        # Subtle shadow + darker top/left border in stylesheet gives an inset feel.
        create_shadow(self, blur_radius=10, x_offset=0, y_offset=1, alpha=28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(6), scaled(0), scaled(6), scaled(0))
        layout.setSpacing(spacing_tight())
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel()
        icon.setObjectName("dateTimeIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(
            qta.icon("fa5s.calendar-alt", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
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


# ==========================================
# MAIN APP
# ==========================================
class ProjectTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.responsive_manager = get_manager(self)
        self.responsive_manager.profileChanged.connect(
            self._handle_responsive_profile_changed
        )
        self.setWindowTitle("Project Tracker DBS - Clean PyQt6 Layout")
        w, h = screen_fraction(0.85, 0.90)
        self.resize(w, h)
        self.setMinimumSize(*screen_fraction(0.50, 0.50))
        center_window(self)
        self.setFont(QFont("Inter", scaled_font(8)))
        self.setStyleSheet(self.get_stylesheet())

        # Clear selected table row when user clicks anywhere outside row data.
        QApplication.instance().installEventFilter(self)

        self.sidebar_expanded = True
        self.nav_buttons = []
        self.status_buttons = []
        self.notifications = []
        self.projects = self.build_sample_projects()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(scaled(0))

        self.sidebar = self.build_sidebar()
        main_layout.addWidget(self.sidebar)

        self.main_wrapper = QFrame()
        self.main_wrapper.setObjectName("mainWrapper")
        main_wrapper_layout = QVBoxLayout(self.main_wrapper)
        main_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        main_wrapper_layout.setSpacing(scaled(0))

        create_shadow(
            self.main_wrapper, blur_radius=25, x_offset=-6, y_offset=0, alpha=60
        )
        self.build_main_content(main_wrapper_layout)

        # Example: call self.set_notifications([...]) if you want seeded items.
        self.set_notifications([])

        main_layout.addWidget(self.main_wrapper, 1)

    def _handle_responsive_profile_changed(self, _profile) -> None:
        self.updateGeometry()
        self.update()

    def build_sample_projects(self):
        return [
            {
                "no": "1",
                "main": "SOP CR",
                "sub_projects": ["a", "b", "c", "sub project a"],
                "start": "1999-12-15 00:00:00",
                "end": "2026-01-10 00:00:00",
                "drone_tickets": [
                    "https://drone.local/ticket/DRN-001",
                    "https://drone.local/ticket/DRN-002",
                    "https://drone.local/ticket/DRN-003",
                    "https://drone.local/ticket/DRN-004",
                ],
                "drone_states": ["UAT", "UAT", "UAT", "UAT"],
                "cr_number": "https://drone.local/cr/CR202604209900114",
                "cr_state": "PENDING SUBMISSION",
            },
            {
                "no": "2",
                "main": "project_tracker",
                "sub_projects": ["—"],
                "start": "—",
                "end": "—",
                "drone_tickets": ["—"],
                "drone_states": ["UAT"],
                "cr_number": "—",
                "cr_state": "PENDING SUBMISSION",
            },
        ]

    def update_drone_ticket_value(self, row_index, line_index, new_value):
        if row_index is None or line_index is None:
            return

        if row_index < 0 or row_index >= len(self.projects):
            return

        tickets = self.projects[row_index].setdefault("drone_tickets", [])
        while len(tickets) <= line_index:
            tickets.append("—")

        tickets[line_index] = new_value
        print(
            f"Drone Ticket updated | row={row_index}, "
            f"line={line_index}, value={new_value}"
        )

    def update_cr_number_value(self, row_index, new_value):
        if row_index is None:
            return

        if row_index < 0 or row_index >= len(self.projects):
            return

        self.projects[row_index]["cr_number"] = new_value
        print(f"CR Number updated | row={row_index}, value={new_value}")

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

        # Dashboard table does not show row selection anymore.
        # Clicking empty table space only clears any accidental/current index.
        if hasattr(self, "table"):
            global_pos = event.globalPosition().toPoint()
            viewport = self.table.viewport()
            viewport_pos = viewport.mapFromGlobal(global_pos)
            clicked_inside_table_viewport = viewport.rect().contains(viewport_pos)
            clicked_index = self.table.indexAt(viewport_pos)

            if not clicked_inside_table_viewport or not clicked_index.isValid():
                self.table.clearSelection()
                self.table.setCurrentItem(None)
                self.table.setCurrentIndex(self.table.model().index(-1, -1))

        return super().eventFilter(watched, event)

    # --------------------------------------
    # SIDEBAR
    # --------------------------------------
    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sidebar.setMinimumWidth(scaled(SIDEBAR_EXPANDED_WIDTH))

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        layout.setSpacing(spacing_tight())
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(scaled(4), scaled(0), scaled(4), scaled(0))
        title_layout.setSpacing(spacing_tight())

        self.logo = QLabel()
        self.logo.setMinimumSize(scaled(14), scaled(14))
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setPixmap(
            qta.icon("fa5s.layer-group", color=C_ORANGE).pixmap(scaled(14), scaled(14))
        )
        title_layout.addWidget(self.logo)

        self.app_title = QLabel("Project Tracker")
        self.app_title.setObjectName("appTitle")
        self.app_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        title_layout.addWidget(self.app_title)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addSpacing(scaled(14))

        nav_items = [
            ("Dashboard", "fa5s.chart-pie", True),
            ("Project Details", "fa5s.folder-open", False),
            ("Second Brain", "fa5s.brain", False),
            ("Report", "fa5s.chart-bar", False),
            ("Automations", "fa5s.robot", False),
            ("Settings", "fa5s.cog", False),
        ]

        for text, icon, active in nav_items:
            btn = SidebarButton(text, icon, active)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        # Muncul hanya saat sidebar collapsed, tepat di bawah Settings.
        self.notification_icon_btn = SidebarButton(
            "Notifications", "fa5s.bell", False
        )
        self.notification_icon_btn.set_collapsed(True)
        self.notification_icon_btn.hide()
        layout.addWidget(self.notification_icon_btn)

        layout.addSpacing(scaled(6))

        self.notif_frame = self.build_notification_panel()
        layout.addWidget(self.notif_frame, 1)

        # Expanded mode: notification panel fills this area.
        # Collapsed mode: this spacer expands, so the collapse button stays at the bottom.
        self.sidebar_bottom_spacer = QSpacerItem(
            0,
            0,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
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
        layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        layout.setSpacing(spacing_tight())

        header = QHBoxLayout()
        header.setSpacing(spacing_tight())

        icon = QLabel()
        icon.setPixmap(
            qta.icon("fa5s.bell", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        header.addWidget(icon)

        title = QLabel("Notifications")
        title.setObjectName("notifTitle")
        header.addWidget(title)
        header.addStretch()

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setObjectName("textButtonLight")
        dismiss_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        dismiss_btn.clicked.connect(self.clear_notifications)
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

        self.notif_content = QWidget()
        self.notif_content.setObjectName("notifContent")
        self.notif_content.setAutoFillBackground(False)
        self.notif_list_layout = QVBoxLayout(self.notif_content)
        self.notif_list_layout.setContentsMargins(
            scaled(0), scaled(0), scaled(4), scaled(0)
        )
        self.notif_list_layout.setSpacing(spacing_tight())
        self.notif_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.notif_scroll.setWidget(self.notif_content)
        layout.addWidget(self.notif_scroll, 1)

        self.render_notifications()
        return frame

    def build_notification_item(self, title, message, time_text="Just now"):
        item = QFrame()
        item.setObjectName("notifItem")

        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        item_layout.setSpacing(spacing_tight())

        top_row = QHBoxLayout()
        top_row.setSpacing(spacing_tight())

        dot = QLabel()
        dot.setMinimumSize(scaled(8), scaled(8))
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setPixmap(
            qta.icon("fa5s.bell", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        top_row.addWidget(dot)

        title_label = QLabel(title)
        title_label.setObjectName("notifItemTitle")
        top_row.addWidget(title_label)
        top_row.addStretch()

        time_label = QLabel(time_text)
        time_label.setObjectName("notifItemTime")
        top_row.addWidget(time_label)

        item_layout.addLayout(top_row)

        message_label = QLabel(message)
        message_label.setObjectName("notifItemMessage")
        message_label.setWordWrap(True)
        item_layout.addWidget(message_label)

        return item

    def render_notifications(self):
        while self.notif_list_layout.count():
            child = self.notif_list_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.notifications:
            empty = QLabel("No notifications yet.")
            empty.setObjectName("emptyNotifText")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            empty.setMinimumHeight(scaled(80))
            self.notif_list_layout.addWidget(empty)
            self.notif_list_layout.addStretch(1)
            return

        for notif in self.notifications:
            self.notif_list_layout.addWidget(
                self.build_notification_item(
                    notif.get("title", "Notification"),
                    notif.get("message", ""),
                    notif.get("time", "Just now"),
                )
            )

        self.notif_list_layout.addStretch(1)

    def set_notifications(self, notifications):
        self.notifications = notifications or []
        if hasattr(self, "notif_list_layout"):
            self.render_notifications()

    def clear_notifications(self):
        self.notifications = []
        self.render_notifications()

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
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
            self.collapse_btn.setIcon(
                qta.icon("fa5s.angle-double-right", color=C_LIGHT)
            )
        else:
            self.app_title.show()
            self.notification_icon_btn.hide()
            self.notif_frame.show()
            self.sidebar_bottom_spacer.changeSize(
                0,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )
            self.collapse_btn.setIcon(qta.icon("fa5s.angle-double-left", color=C_LIGHT))

        self.sidebar.layout().invalidate()

    # --------------------------------------
    # MAIN CONTENT
    # --------------------------------------
    def build_main_content(self, parent_layout):
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        create_shadow(self.header_frame, blur_radius=20, y_offset=5, alpha=50)

        # Header uses a 3-column grid:
        # left = page title, center = live datetime, right = actions.
        # This keeps the datetime visually centered instead of attached to the title.
        header_layout = QGridLayout(self.header_frame)
        header_layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        header_layout.setHorizontalSpacing(spacing_tight())
        header_layout.setVerticalSpacing(0)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(2, 1)

        header_title_box = QFrame()
        header_title_box.setObjectName("headerTitleBox")
        title_layout = QHBoxLayout(header_title_box)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(spacing_tight())
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_marker = QFrame()
        title_marker.setObjectName("pageTitleDivider")
        title_marker.setMinimumWidth(scaled(4))
        title_marker.setMaximumWidth(scaled(4))
        title_marker.setMinimumHeight(scaled(26))
        title_marker.setMaximumHeight(scaled(26))
        title_layout.addWidget(title_marker)

        dashboard_title = QLabel("Dashboard.")
        dashboard_title.setObjectName("dashboardHeaderTitle")
        dashboard_title.setFont(QFont("Inter", scaled_font(16), QFont.Weight.Black))
        title_layout.addWidget(dashboard_title)

        header_layout.addWidget(
            header_title_box,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        self.header_datetime_badge = DateTimeBadge()
        header_layout.addWidget(
            self.header_datetime_badge,
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

        header_action_box = QFrame()
        header_action_box.setObjectName("headerActionBox")

        header_action_layout = QHBoxLayout(header_action_box)
        header_action_layout.setContentsMargins(0, 0, 0, 0)
        header_action_layout.setSpacing(spacing_tight())

        year_combo = ModernComboBox()
        year_combo.addItems(["2026", "2025", "2024"])
        header_action_layout.addWidget(year_combo)

        search_bar = AnimatedSearch()
        header_action_layout.addWidget(search_bar)

        cr_combo = ModernComboBox()
        cr_combo.addItem("All CR")
        header_action_layout.addWidget(cr_combo)

        add_btn = AnimatedPrimaryButton(" Add Project", "fa5s.plus")
        header_action_layout.addWidget(add_btn)

        refresh_btn = RefreshButton()
        header_action_layout.addWidget(refresh_btn)

        header_layout.addWidget(
            header_action_box,
            0,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        parent_layout.addWidget(self.header_frame)

        content_widget = QWidget()
        content_widget.setObjectName("workspaceArea")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(
            scaled(16), scaled(16), scaled(16), scaled(16)
        )
        content_layout.setSpacing(scaled(12))

        filter_frame = self.build_filter_panel()
        content_layout.addWidget(filter_frame)

        self.table_card = self.build_table_card()
        content_layout.addWidget(self.table_card, 1)

        # Pagination footer removed.
        # The dashboard table now uses native vertical scrolling for large datasets.
        parent_layout.addWidget(content_widget, 1)
        self.header_frame.raise_()

    def build_filter_panel(self):
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        create_shadow(filter_frame, blur_radius=15, y_offset=4, alpha=30)

        outer_layout = QVBoxLayout(filter_frame)
        outer_layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        outer_layout.setSpacing(scaled(0))

        status_inner = QFrame()
        status_inner.setObjectName("statusFilterInner")
        create_shadow(status_inner, blur_radius=16, x_offset=0, y_offset=5, alpha=42)

        tabs_layout = QHBoxLayout(status_inner)
        tabs_layout.setContentsMargins(
            margin_inner(), margin_inner(), margin_inner(), margin_inner()
        )
        tabs_layout.setSpacing(spacing_tight())

        statuses = [
            "All (2)",
            "UAT Prepare (2)",
            "Prod Ready (0)",
            "Implemented (0)",
            "Postponed (0)",
        ]

        for index, status in enumerate(statuses):
            btn = QPushButton(status)
            btn.setObjectName("statusTabActive" if index == 0 else "statusTab")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.clicked.connect(lambda checked=False, b=btn: self.set_active_status(b))
            self.status_buttons.append(btn)
            tabs_layout.addWidget(btn)

        tabs_layout.addStretch()

        self.project_count = QLabel("2 project(s)")
        self.project_count.setObjectName("projectCount")
        tabs_layout.addWidget(self.project_count)

        outer_layout.addWidget(status_inner)
        return filter_frame

    def set_active_status(self, active_button):
        """
        Update active tab safely.
        No opacity effect is attached to QTableWidget, so the table viewport stays stable.
        """
        for btn in self.status_buttons:
            is_active = btn is active_button
            btn.setChecked(is_active)
            btn.setObjectName("statusTabActive" if is_active else "statusTab")
            repolish(btn)

        # Placeholder count behavior for this static sample.
        self.project_count.setText(
            "2 project(s)" if "(2)" in active_button.text() else "0 project(s)"
        )
        self.table.clearSelection()
        self.table.viewport().update()

    def build_table_card(self):
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        create_shadow(table_card, blur_radius=25, y_offset=6, alpha=20)

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(scaled(14), scaled(14), scaled(14), scaled(14))
        table_layout.setSpacing(scaled(12))

        table_title_row = QHBoxLayout()
        table_title_row.setContentsMargins(0, 0, 0, 0)
        table_title_row.setSpacing(spacing_tight())

        table_icon = QLabel()
        table_icon.setObjectName("tableTitleIcon")
        table_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_icon.setPixmap(
            qta.icon("fa5s.table", color=C_ORANGE).pixmap(scaled(12), scaled(12))
        )
        table_title_row.addWidget(table_icon)

        table_title = QLabel("CR - Project Summary Table")
        table_title.setObjectName("tableCardTitle")
        table_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        table_title_row.addWidget(table_title)

        table_title_row.addStretch()
        table_layout.addLayout(table_title_row)

        table_inner = QFrame()
        table_inner.setObjectName("dashboardTableInner")
        create_shadow(table_inner, blur_radius=18, x_offset=0, y_offset=5, alpha=36)

        table_inner_layout = QVBoxLayout(table_inner)
        table_inner_layout.setContentsMargins(
            scaled(10), scaled(10), scaled(10), scaled(10)
        )
        table_inner_layout.setSpacing(scaled(0))

        self.table = ClearableSelectionTable(0, 10)
        self.configure_table()
        self.populate_table()

        table_inner_layout.addWidget(self.table)
        table_layout.addWidget(table_inner, 1)
        return table_card

    def configure_table(self):
        self.table.setHorizontalHeaderLabels(
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
                "",
            ]
        )

        self.table.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        self.table.setWordWrap(True)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(False)
        # No row selection effect on click. Cell widgets remain interactive.
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setMinimumHeight(scaled(420))
        self.table.setColumnWidth(0, scaled(42))
        self.table.setColumnWidth(9, scaled(52))
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        vertical_header = self.table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        vertical_header.setDefaultSectionSize(scaled(46))

        header = self.table.horizontalHeader()
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(scaled(32))
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col in (1, 2, 5, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        for col in (0, 3, 4, 6, 8, 9):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.resizeSection(0, scaled(42))
        header.resizeSection(9, scaled(52))

        self.table.itemSelectionChanged.connect(self.sync_row_widget_styles)

    def table_display_datetime(self, value):
        """
        Dashboard-compatible display format:
        Fri, 22 May 2026 HH:mm:ss
        """
        if not value or value == "—":
            return "—"

        known_formats = [
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-ddTHH:mm:ss",
            "dd MMM yyyy HH:mm:ss",
            "dd MMM yyyy",
        ]

        for fmt in known_formats:
            parsed = QDateTime.fromString(value, fmt)
            if parsed.isValid():
                locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
                return locale.toString(parsed, "ddd, dd MMM yyyy HH:mm:ss")

        return value

    def normalize_row_lines(self, row):
        """
        Line-level data only applies to:
        - SUB PROJECT
        - DRONE TICKET
        - DRONE STATE

        Project-level data stays single:
        - CR NUMBER
        - CR STATE
        """
        sub_projects = row.get("sub_projects") or ["—"]
        line_count = max(1, len(sub_projects))

        def normalize(values, fallback="—"):
            values = values or [fallback]
            if not isinstance(values, list):
                values = [values]
            if len(values) < line_count:
                values = values + [fallback] * (line_count - len(values))
            return values[:line_count]

        return {
            **row,
            "sub_projects": normalize(sub_projects),
            "drone_tickets": normalize(row.get("drone_tickets"), "—"),
            "drone_states": normalize(row.get("drone_states"), "UAT"),
            "cr_state": row.get("cr_state") or "PENDING SUBMISSION",
            "line_count": line_count,
        }

    def populate_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(2)

        def create_item(text, color=C_DARK, is_bold=False, alignment=None):
            item = QTableWidgetItem(text)
            item.setForeground(QColor(color))
            item.setTextAlignment(
                alignment
                or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            )
            if is_bold:
                font = QFont("Inter", scaled_font(10), QFont.Weight.Bold)
                item.setFont(font)
            return item

        rows = self.projects

        for row_index, raw_row in enumerate(rows):
            row = self.normalize_row_lines(raw_row)

            self.table.setItem(
                row_index,
                0,
                create_item(
                    row["no"],
                    C_DARK,
                    True,
                    Qt.AlignmentFlag.AlignCenter,
                ),
            )
            self.table.setItem(
                row_index,
                1,
                create_item(row["main"], C_ORANGE if row_index == 0 else C_DARK, True),
            )
            self.table.setCellWidget(
                row_index, 2, self.create_line_text_cell(row["sub_projects"])
            )
            self.table.setItem(
                row_index, 3, create_item(self.table_display_datetime(row["start"]))
            )
            self.table.setItem(
                row_index, 4, create_item(self.table_display_datetime(row["end"]))
            )
            self.table.setCellWidget(
                row_index,
                5,
                self.create_line_edit_stack(row["drone_tickets"], row_index),
            )
            self.table.setCellWidget(
                row_index,
                6,
                self.create_line_combo_stack(
                    row["drone_states"],
                    [
                        "UAT",
                        "SIT",
                        "UAT PREPARE",
                        "PROD READY",
                        "IMPLEMENTED",
                        "POSTPONED",
                    ],
                ),
            )
            self.table.setCellWidget(
                row_index,
                7,
                self.create_project_link_cell(row["cr_number"], row_index),
            )
            self.table.setCellWidget(
                row_index,
                8,
                self.create_project_combo_cell(
                    row["cr_state"],
                    [
                        "PENDING SUBMISSION",
                        "APPROVED",
                        "REJECTED",
                        "IMPLEMENTED",
                        "POSTPONED",
                    ],
                ),
            )
            self.table.setCellWidget(row_index, 9, self.create_action_cell())

            row_height = max(66, 38 * row["line_count"] + 34)
            self.table.setRowHeight(row_index, scaled(row_height))

        self.table.setUpdatesEnabled(True)
        self.sync_row_widget_styles()
        self.table.viewport().update()

    def create_separator(self):
        line = QFrame()
        line.setObjectName("cellSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setMinimumHeight(scaled(1))
        return line

    def create_cell_stack(self, object_name="tableStackCell"):
        container = QFrame()
        container.setObjectName(object_name)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout(container)
        # More breathing room for stacked widgets inside table cells.
        # This prevents link edits and state buttons from touching each other.
        layout.setContentsMargins(scaled(11), scaled(8), scaled(11), scaled(8))
        layout.setSpacing(scaled(7))
        return container, layout

    def create_line_text_cell(self, values):
        container, layout = self.create_cell_stack("tableStackCell")
        container.setProperty("cellType", "lineText")

        for index, value in enumerate(values):
            label = QLabel(value)
            label.setObjectName("tableStackLabel")
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            label.setWordWrap(True)
            label.setMinimumHeight(scaled(24))
            label.setToolTip(value)
            layout.addWidget(label)

            if index < len(values) - 1:
                layout.addWidget(self.create_separator())

        return container

    def create_line_edit_stack(self, values, row_index=None):
        container, layout = self.create_cell_stack("tableStackCell")
        container.setProperty("cellType", "lineEditStack")
        container.setProperty("stackKind", "link")

        for line_index, value in enumerate(values):
            edit = EditableLinkLineEdit(
                value,
                on_commit=lambda new_value, line=line_index: (
                    self.update_drone_ticket_value(
                        row_index,
                        line,
                        new_value,
                    )
                ),
            )
            edit.setMinimumHeight(scaled(28))
            layout.addWidget(edit)

            if line_index < len(values) - 1:
                layout.addWidget(self.create_separator())

        return container

    def create_line_combo_stack(self, values, options):
        container, layout = self.create_cell_stack("tableStackCell")
        container.setProperty("cellType", "lineComboStack")
        container.setProperty("stackKind", "combo")

        for index, value in enumerate(values):
            combo = TableStateCombo(value, options)
            combo.setMinimumWidth(scaled(128))
            layout.addWidget(combo)

            if index < len(values) - 1:
                layout.addWidget(self.create_separator())

        return container

    def create_project_link_cell(self, value, row_index=None):
        container, layout = self.create_cell_stack("projectCell")
        container.setProperty("cellType", "projectLink")

        edit = EditableLinkLineEdit(
            value,
            on_commit=lambda new_value: self.update_cr_number_value(
                row_index,
                new_value,
            ),
        )
        edit.setMinimumHeight(scaled(28))
        layout.addStretch(1)
        layout.addWidget(edit)
        layout.addStretch(1)
        return container

    def create_project_combo_cell(self, value, options):
        container, layout = self.create_cell_stack("projectCell")
        container.setProperty("cellType", "projectCombo")

        combo = TableStateCombo(value, options)
        combo.setMinimumHeight(scaled(30))
        combo.setMinimumWidth(scaled(190))
        layout.addStretch(1)
        layout.addWidget(combo)
        layout.addStretch(1)
        return container

    def sync_row_widget_styles(self):
        selected_rows = (
            {index.row() for index in self.table.selectionModel().selectedRows()}
            if self.table.selectionModel()
            else set()
        )

        def apply_recursive(widget, selected):
            widget.setProperty("rowSelected", selected)
            repolish(widget)
            widget.update()

            for child in widget.findChildren(QWidget):
                child.setProperty("rowSelected", selected)
                repolish(child)
                child.update()

        for row in range(self.table.rowCount()):
            selected = row in selected_rows
            for col in range(self.table.columnCount()):
                widget = self.table.cellWidget(row, col)
                if widget is not None:
                    apply_recursive(widget, selected)

    def create_action_cell(self):
        wrapper = QFrame()
        wrapper.setObjectName("actionCell")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton()
        btn.setIcon(qta.icon("fa5s.ellipsis-v", color=C_DARK))
        btn.setIconSize(QSize(scaled(8), scaled(8)))
        btn.setObjectName("actionButton")
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMinimumSize(scaled(28), scaled(28))
        layout.addWidget(btn)
        return wrapper

    def build_footer(self):
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        prev_btn = AnimatedPageButton("fa5s.chevron-left", "Previous Page")
        footer_layout.addWidget(prev_btn)

        page_info = QLabel("Showing 1-2 of 2 projects")
        page_info.setObjectName("pageInfo")
        footer_layout.addWidget(page_info)

        next_btn = AnimatedPageButton("fa5s.chevron-right", "Next Page")
        footer_layout.addWidget(next_btn)

        footer_layout.addStretch()
        return footer_layout

    # --------------------------------------
    # STYLESHEET
    # --------------------------------------
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
                border-bottom: {scaled(2)}px solid {C_RED_HOVER};
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
            #pageTitleDivider {{
                background-color: {C_BLACK_CHROME};
                border-radius: {scaled(2)}px;
            }}
            #dashboardHeaderTitle {{
                color: {C_WHITE};
                font-size: {scaled_font(16)}pt;
                font-weight: 900;
                letter-spacing: {scaled(1)}px;
            }}

            #titleDateTimeBox {{
                background-color: rgba(227, 230, 228, 0.42);
                border: 1px solid rgba(45, 61, 52, 0.16);
                border-radius: {scaled(6)}px;
            }}
            #titleDateTimeBox:hover {{
                background-color: rgba(227, 230, 228, 0.56);
            }}
            #headerActionBox {{
                background-color: transparent;
                border: none;
            }}
            #dateTimeBadge {{
                background-color: {C_WHITE};
                border-radius: {scaled(6)}px;
                border: {scaled(1)}px solid {C_BLACK_CHROME};
            }}
            #dateTimeIcon {{
                background: transparent;
            }}
            #dateTimeLabel {{
                color: {C_BLACK_CHROME};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}

            #filterFrame {{
                background-color: {C_MAIN_PANEL_BG};
                border-radius: {scaled(8)}px;
                border: {scaled(1)}px solid {C_SOFT_WHITE_BORDER};
            }}
            #statusFilterInner {{
                background-color: {C_WHITE};
                border-radius: {scaled(6)}px;
                border: {scaled(1)}px solid {C_SOFT_WHITE_BORDER};
            }}
            #statusFilterInner:hover {{
                background-color: {C_WHITE};
            }}
            #projectCount {{
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
                padding-left: {scaled(6)}px;
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
            #notifScroll,
            #notifViewport,
            #notifContent {{
                background: transparent;
                border: none;
            }}
            #notifItem {{
                background-color: rgba(255, 255, 255, 0.58);
                border: 1px solid rgba(45, 61, 52, 0.10);
                border-radius: {scaled(6)}px;
            }}
            #notifItemTitle {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            #notifItemTime {{
                color: rgba(45, 61, 52, 0.75);
                font-size: {scaled_font(8)}pt;
                font-weight: 700;
            }}
            #notifItemMessage {{
                color: rgba(45, 61, 52, 0.92);
                font-size: {scaled_font(8)}pt;
                font-weight: 600;
                line-height: 1.3em;
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

            QLineEdit {{
                padding: {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_SAGE};
                border-radius: {scaled(4)}px;
                background: {C_LIGHT};
                color: {C_DARK};
                font-weight: 600;
            }}
            QLineEdit:focus {{
                border: 2px solid {C_ORANGE};
                background: {C_WHITE};
            }}

            ModernComboBox {{
                padding: {scaled(4)}px {scaled(14)}px {scaled(4)}px {scaled(6)}px;
                border: 1px solid {C_INPUT_BORDER};
                border-radius: {scaled(4)}px;
                background: {C_WHITE};
                color: {C_DARK};
                font-weight: 700;
            }}
            ModernComboBox:hover {{
                background: {C_WHITE};
            }}
            ModernComboBox::drop-down {{
                border: none;
                width: {scaled(14)}px;
            }}

            #collapseButton {{
                padding: {scaled(4)}px;
                background-color: {C_SURFACE_DARK};
                border: {scaled(1)}px solid {C_DARK_BORDER};
                border-radius: {scaled(5)}px;
            }}
            #collapseButton:hover {{
                background-color: #231112;
                border-color: {C_ACTIVE_RED};
            }}

            #headerRefreshButton {{
                min-width: {scaled(28)}px;
                min-height: {scaled(26)}px;
                padding: {scaled(4)}px;
                background-color: {C_WHITE};
                border: {scaled(1)}px solid {C_BLACK_CHROME};
                border-radius: {scaled(5)}px;
            }}
            #headerRefreshButton:hover {{
                background-color: {C_SOFT_PINK_SURFACE};
                border-color: {C_BLACK_CHROME};
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
            #pageNavButton:pressed {{
                background-color: rgba(45, 61, 52, 0.18);
            }}

            #actionButton {{
                background: transparent;
                border: none;
                border-radius: {scaled(4)}px;
            }}
            #actionButton:hover {{
                background: {C_SAGE};
            }}

            #statusTab {{
                border-radius: {scaled(5)}px;
                padding: {scaled(4)}px {scaled(8)}px;
                background: {C_WHITE};
                border: {scaled(1)}px solid {C_SOFT_WHITE_BORDER};
                color: {C_TEXT_PRIMARY};
                font-weight: 800;
            }}
            #statusTab:hover {{
                background: {C_SOFT_PINK_SURFACE};
                color: {C_PRIMARY_RED};
                border-color: {C_SOFT_PINK_BORDER};
            }}
            #statusTabActive {{
                border-radius: {scaled(5)}px;
                padding: {scaled(4)}px {scaled(8)}px;
                background: {C_ORANGE};
                border: {scaled(1)}px solid {C_RED_HOVER};
                color: {C_WHITE};
                font-weight: 900;
            }}

            #textButtonLight {{
                border: none;
                background: transparent;
                color: {C_TEXT_MUTED};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                padding: {scaled(1)}px {scaled(0)}px;
            }}
            #textButtonLight:hover {{
                color: {C_ORANGE};
                text-decoration: underline;
            }}

            #tableCard {{
                background-color: {C_MAIN_PANEL_BG};
                border-radius: {scaled(8)}px;
                border: 1px solid {C_SOFT_WHITE_BORDER};
                border-top: none;
            }}
            #dashboardTableInner {{
                background-color: {C_WHITE};
                border-radius: {scaled(12)}px;
                border: 1px solid {C_TEXT_STRONG};
            }}
            #dashboardTableInner:hover {{
                background-color: {C_WHITE};
            }}
            #tableTitleIcon {{
                background: transparent;
                min-width: {scaled(8)}px;
                max-width: {scaled(8)}px;
                min-height: {scaled(8)}px;
                max-height: {scaled(8)}px;
            }}
            #tableCardTitle {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
            }}
            QTableWidget {{
                border: 1px solid {C_TEXT_STRONG};
                background-color: {C_WHITE};
                alternate-background-color: {C_WHITE};
                outline: none;
                border-radius: {scaled(12)}px;
                gridline-color: {C_TEXT_STRONG};
            }}
            QTableWidget::viewport {{
                background-color: {C_WHITE};
                border-radius: {scaled(12)}px;
            }}
            QTableWidget::item {{
                padding: {scaled(6)}px {scaled(6)}px;
                border-bottom: 1px solid {C_TEXT_STRONG};
                border-right: 1px solid {C_TEXT_STRONG};
            }}
            QTableWidget::item:selected {{
                background-color: {C_WHITE};
                color: {C_TEXT_PRIMARY};
            }}

            QHeaderView {{
                background-color: transparent;
            }}
            QHeaderView::section {{
                background-color: {C_TEXT_STRONG};
                padding: {scaled(6)}px {scaled(6)}px;
                border: none;
                border-top: none;
                border-right: 1px solid {C_TEXT_STRONG};
                border-bottom: 2px solid {C_TEXT_STRONG};
                font-size: {scaled_font(8)}pt;
                font-weight: 900;
                color: {C_WHITE};
                text-transform: uppercase;
                qproperty-alignment: AlignCenter;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: {scaled(12)}px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: {scaled(12)}px;
                border-right: none;
            }}

            #pageInfo {{
                color: {C_DARK};
                padding: 0 10px;
                font-weight: 700;
            }}

            #tableStackCell,
            #projectCell,
            #actionCell {{
                background-color: transparent;
            }}
            #tableStackCell[rowSelected="true"],
            #projectCell[rowSelected="true"],
            #actionCell[rowSelected="true"] {{
                background-color: transparent;
            }}
            #tableStackLabel {{
                color: {C_DARK};
                font-size: {scaled_font(8)}pt;
                font-weight: 600;
                background: transparent;
                padding-left: {scaled(1)}px;
            }}
            #tableStackLabel[rowSelected="true"] {{
                color: {C_DARK};
                font-weight: 700;
            }}
            #cellSeparator {{
                background-color: rgba(45, 61, 52, 0.18);
                border: none;
                margin-top: 1px;
                margin-bottom: 1px;
            }}
            #cellSeparator[rowSelected="true"] {{
                background-color: rgba(255, 255, 255, 0.32);
            }}
            #tableLinkEdit {{
                min-height: {scaled(30)}px;
                max-height: {scaled(30)}px;
                padding: {scaled(0)}px {scaled(10)}px;
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
            #tableLinkEdit[rowSelected="true"] {{
                border: 1px solid rgba(45, 61, 52, 0.16);
                background-color: {C_WHITE};
                color: {C_ORANGE};
            }}
            QPushButton#stateCombo {{
                background: transparent;
                border: none;
                min-height: {scaled(30)}px;
                max-height: {scaled(30)}px;
            }}
        """


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", scaled_font(9)))
    window = ProjectTrackerApp()
    window.show()
    sys.exit(app.exec())
