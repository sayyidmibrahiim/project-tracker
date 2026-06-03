from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication

# ─── DESIGN REFERENCE ─────────────────────────────────────────────────────────
# All UI sizes are authored at 1920×1080 physical pixels (96 DPI, 100% scale).
_REF_PHYS_W: float = 1920.0
_REF_PHYS_H: float = 1080.0


@dataclass(frozen=True)
class ScreenSnapshot:
    platform: str
    logical_width: int
    logical_height: int
    physical_width: float
    physical_height: float
    device_pixel_ratio: float
    logical_dpi: float
    screen_name: str


@dataclass(frozen=True)
class ResponsiveTokens:
    margin_outer: int
    margin_inner: int
    spacing_tight: int
    spacing_normal: int
    spacing_loose: int
    radius_small: int
    radius_medium: int
    radius_large: int
    sidebar_collapsed_width: int
    sidebar_expanded_width: int
    header_height: int
    toolbar_gap: int
    row_height_tree: int
    card_padding: int
    control_min_height: int
    icon_tiny: int
    icon_compact: int
    icon_button: int
    tree_indentation: int


@dataclass(frozen=True)
class ResponsiveProfile:
    scale: float
    font_scale: float
    icon_scale: float
    density: str
    device_class: str
    platform: str
    snapshot: ScreenSnapshot
    tokens: ResponsiveTokens


_FALLBACK_SNAPSHOT = ScreenSnapshot(
    platform=sys.platform,
    logical_width=1536,
    logical_height=864,
    physical_width=1920.0,
    physical_height=1080.0,
    device_pixel_ratio=1.25 if sys.platform.startswith("win") else 1.0,
    logical_dpi=96.0,
    screen_name="fallback",
)

_cached_profile: ResponsiveProfile | None = None
_manager: "ResponsiveManager | None" = None


def _safe_dpr(screen: QScreen | None) -> float:
    if screen is None:
        return _FALLBACK_SNAPSHOT.device_pixel_ratio
    dpr = float(screen.devicePixelRatio())
    if dpr <= 0:
        return 1.0
    return dpr


def _safe_dpi(screen: QScreen | None) -> float:
    if screen is None:
        return _FALLBACK_SNAPSHOT.logical_dpi
    dpi = float(screen.logicalDotsPerInch())
    if dpi <= 0:
        return 96.0
    return dpi


def _screen_for_window(window: Any | None = None) -> QScreen | None:
    app = QApplication.instance()
    if app is None:
        return None
    if window is not None:
        try:
            geo = window.frameGeometry()
            center = geo.center()
            screen = QApplication.screenAt(QPoint(center.x(), center.y()))
            if screen is not None:
                return screen
        except Exception:
            pass
    return QApplication.primaryScreen()


def capture_screen_snapshot(window: Any | None = None) -> ScreenSnapshot:
    screen = _screen_for_window(window)
    if screen is None:
        return _FALLBACK_SNAPSHOT

    geo = screen.availableGeometry()
    dpr = _safe_dpr(screen)
    dpi = _safe_dpi(screen)
    logical_width = max(320, int(geo.width()))
    logical_height = max(240, int(geo.height()))

    return ScreenSnapshot(
        platform=sys.platform,
        logical_width=logical_width,
        logical_height=logical_height,
        physical_width=logical_width * dpr,
        physical_height=logical_height * dpr,
        device_pixel_ratio=dpr,
        logical_dpi=dpi,
        screen_name=screen.name() or "unknown",
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def _platform_clamp(platform: str) -> tuple[float, float]:
    if platform.startswith("win"):
        return 0.90, 1.12
    if platform == "darwin":
        return 0.82, 1.08
    if platform.startswith("linux"):
        return 0.86, 1.10
    return 0.86, 1.08


def _device_class(snapshot: ScreenSnapshot) -> str:
    if snapshot.device_pixel_ratio >= 1.8 and snapshot.platform == "darwin":
        return "retina"
    if snapshot.logical_width < 1400 or snapshot.logical_height < 820:
        return "small_laptop"
    if snapshot.logical_width >= 3000:
        return "ultrawide"
    if snapshot.logical_width >= 1900 and snapshot.logical_height >= 1000:
        return "desktop"
    return "laptop"


def _density(snapshot: ScreenSnapshot, device_class: str) -> str:
    if device_class == "small_laptop":
        return "compact"
    if device_class in {"desktop", "ultrawide"}:
        return "spacious"
    return "comfortable"


def _density_multiplier(density: str) -> float:
    if density == "compact":
        return 0.86
    if density == "spacious":
        return 1.08
    return 1.0


def _scaled_value(px: int, scale: float, minimum: int = 1) -> int:
    if px == 0:
        return 0
    value = int(round(px * scale))
    if px > 0:
        return max(minimum, value)
    return min(-minimum, value)


def _build_tokens(scale: float, font_scale: float, icon_scale: float, density: str) -> ResponsiveTokens:
    density_scale = _density_multiplier(density)
    spacing_scale = scale * density_scale
    return ResponsiveTokens(
        margin_outer=_scaled_value(18, spacing_scale),
        margin_inner=_scaled_value(14, spacing_scale),
        spacing_tight=_scaled_value(6, spacing_scale),
        spacing_normal=_scaled_value(10, spacing_scale),
        spacing_loose=_scaled_value(18, spacing_scale),
        radius_small=_scaled_value(5, scale),
        radius_medium=_scaled_value(8, scale),
        radius_large=_scaled_value(14, scale),
        sidebar_collapsed_width=_scaled_value(72, scale, 48),
        sidebar_expanded_width=_scaled_value(260, scale, 210),
        header_height=_scaled_value(64, scale, 48),
        toolbar_gap=_scaled_value(8, spacing_scale),
        row_height_tree=_scaled_value(22, font_scale, 18),
        card_padding=_scaled_value(14, spacing_scale),
        control_min_height=_scaled_value(34, font_scale, 28),
        icon_tiny=_scaled_value(12, icon_scale, 12),
        icon_compact=_scaled_value(14, icon_scale, 12),
        icon_button=_scaled_value(16, icon_scale, 12),
        tree_indentation=_scaled_value(10, spacing_scale, 6),
    )


def build_responsive_profile(window: Any | None = None) -> ResponsiveProfile:
    snapshot = capture_screen_snapshot(window)
    dpr = snapshot.device_pixel_ratio if snapshot.device_pixel_ratio > 0 else 1.0
    physical_scale = min(snapshot.physical_width / _REF_PHYS_W, snapshot.physical_height / _REF_PHYS_H)
    logical_scale = physical_scale / dpr
    low, high = _platform_clamp(snapshot.platform)
    scale = _clamp(logical_scale, low, high)
    device_class = _device_class(snapshot)
    density = _density(snapshot, device_class)

    font_floor = 0.92 if density == "compact" else 0.90
    font_scale = _clamp(scale, font_floor, 1.12)
    icon_scale = _clamp(scale, 0.86, 1.14)
    tokens = _build_tokens(scale, font_scale, icon_scale, density)

    return ResponsiveProfile(
        scale=scale,
        font_scale=font_scale,
        icon_scale=icon_scale,
        density=density,
        device_class=device_class,
        platform=snapshot.platform,
        snapshot=snapshot,
        tokens=tokens,
    )


def reset_cache() -> None:
    """Invalidate cached profile. Call if window moves to a different monitor."""
    global _cached_profile
    _cached_profile = None


def get_profile(window: Any | None = None) -> ResponsiveProfile:
    global _cached_profile
    if window is not None:
        return build_responsive_profile(window)
    if _cached_profile is None:
        _cached_profile = build_responsive_profile()
    return _cached_profile


def get_scale_factor() -> float:
    """Return design-canvas px → current screen logical px scale."""
    return get_profile().scale


def get_device_pixel_ratio() -> float:
    """Return current primary screen DPR."""
    return get_profile().snapshot.device_pixel_ratio


def scaled(px: int) -> int:
    """Map design-canvas px → logical px for current screen, preserving true zero."""
    return _scaled_value(px, get_profile().scale)


def scaled_font(pt: int) -> int:
    """Map design-canvas font pt → current screen, floor 8 pt for laptop comfort."""
    return max(8, int(round(pt * get_profile().font_scale)))


def scaled_icon(px: int) -> int:
    """Map icon size → current screen logical px."""
    return _scaled_value(px, get_profile().icon_scale, 12)


def screen_fraction(w_frac: float, h_frac: float) -> tuple[int, int]:
    """Return (width, height) as fraction of primary screen available geometry."""
    snapshot = get_profile().snapshot
    return int(snapshot.logical_width * w_frac), int(snapshot.logical_height * h_frac)


def center_window(window: Any) -> None:
    """Center window on its current screen's available area."""
    screen = _screen_for_window(window)
    if screen is None:
        return
    geo = screen.availableGeometry()
    window.move(
        geo.x() + (geo.width() - window.width()) // 2,
        geo.y() + (geo.height() - window.height()) // 2,
    )


def current_tokens() -> ResponsiveTokens:
    return get_profile().tokens


def margin_outer() -> int:
    return current_tokens().margin_outer


def margin_inner() -> int:
    return current_tokens().margin_inner


def spacing_tight() -> int:
    return current_tokens().spacing_tight


def spacing_normal() -> int:
    return current_tokens().spacing_normal


def spacing_loose() -> int:
    return current_tokens().spacing_loose


def radius_small() -> int:
    return current_tokens().radius_small


def radius_medium() -> int:
    return current_tokens().radius_medium


def radius_large() -> int:
    return current_tokens().radius_large


def sidebar_collapsed_width() -> int:
    return current_tokens().sidebar_collapsed_width


def sidebar_expanded_width() -> int:
    return current_tokens().sidebar_expanded_width


def header_height() -> int:
    return current_tokens().header_height


def toolbar_gap() -> int:
    return current_tokens().toolbar_gap


def card_padding() -> int:
    return current_tokens().card_padding


def control_min_height() -> int:
    return current_tokens().control_min_height


def row_height_tree() -> int:
    return current_tokens().row_height_tree


def icon_size_button() -> int:
    return current_tokens().icon_button


def icon_size_compact() -> int:
    return current_tokens().icon_compact


def icon_size_tiny() -> int:
    return current_tokens().icon_tiny


def tree_indentation() -> int:
    return current_tokens().tree_indentation


class ResponsiveManager(QObject):
    profileChanged = pyqtSignal(object)

    def __init__(self, window: Any | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._profile = build_responsive_profile(window)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self.refresh)
        self._connect_screen_signals()

    @property
    def profile(self) -> ResponsiveProfile:
        return self._profile

    @property
    def tokens(self) -> ResponsiveTokens:
        return self._profile.tokens

    def set_window(self, window: Any | None) -> None:
        self._window = window
        self.schedule_refresh()

    def schedule_refresh(self) -> None:
        self._timer.start()

    def refresh(self) -> None:
        global _cached_profile
        new_profile = build_responsive_profile(self._window)
        if new_profile == self._profile:
            return
        self._profile = new_profile
        if self._window is None:
            _cached_profile = new_profile
        self.profileChanged.emit(new_profile)

    def _connect_screen_signals(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.screenAdded.connect(self._handle_screen_added)
        app.screenRemoved.connect(lambda _screen: self.schedule_refresh())
        for screen in app.screens():
            self._connect_single_screen(screen)

    def _handle_screen_added(self, screen: QScreen) -> None:
        self._connect_single_screen(screen)
        self.schedule_refresh()

    def _connect_single_screen(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(lambda _geo: self.schedule_refresh())
        screen.logicalDotsPerInchChanged.connect(lambda _dpi: self.schedule_refresh())


def get_manager(window: Any | None = None) -> ResponsiveManager:
    global _manager
    if _manager is None:
        _manager = ResponsiveManager(window)
    elif window is not None:
        _manager.set_window(window)
    return _manager
