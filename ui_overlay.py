"""
ui_overlay.py
Nexovian animated sound-wave overlay.

Replaces the old pulsing circle with a multi-layered, glowing waveform
visualizer rendered in Cairo — inspired by plasma / audio-spectrum aesthetics.

States:
  listening → fast cyan/blue wave with high amplitude
  speaking  → rhythmic purple/magenta wave
  standby   → flat, barely-moving dim wave
"""

import math
import time
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo

# ─── Window geometry ──────────────────────────────────────────────────────────
# OVERLAY_W is resolved dynamically from the primary monitor at runtime.
OVERLAY_H = 140   # height of the wave strip (px)

# ─── Wave configuration ───────────────────────────────────────────────────────
WAVE_STEPS = 300  # path resolution (higher = smoother curve)

# Each entry: (relative_freq, relative_amp, phase_shift_mult)
WAVE_LAYERS = [
    (1.00, 1.00, 0.00),
    (1.15, 0.70, 0.55),
    (0.85, 0.55, 1.10),
    (1.30, 0.40, 1.70),
    (0.70, 0.30, 2.30),
    (1.50, 0.20, 2.90),
]


def _lerp_color(c1, c2, t):
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


class NexovianUI(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.set_title("Nexovian Overlay")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)

        # Compositing / transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        # ── Full-width positioning ─────────────────────────────────────────
        display  = Gdk.Display.get_default()
        monitor  = display.get_primary_monitor() or display.get_monitor(0)
        geom     = monitor.get_geometry()
        scale    = monitor.get_scale_factor()
        screen_w = geom.width  * scale
        screen_h = geom.height * scale

        # Place horizontally centred vertically (upper-middle of screen)
        overlay_y = geom.y + int(screen_h * 0.38)
        self.set_default_size(screen_w, OVERLAY_H)
        self.move(geom.x, overlay_y)

        # Drawing area
        self.darea = Gtk.DrawingArea()
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)

        # Animation state
        self.active = False
        self.start_time = 0.0
        self.state = "standby"   # 'listening' | 'speaking' | 'standby'
        self.anim_source_id = None

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _wave_params(self, elapsed):
        """Return (base_amplitude, scroll_speed, color_a, color_b) for current state."""
        if self.state == "listening":
            # Breathing amplitude, fast scroll, cyan → blue
            breath = 1.0 + 0.28 * math.sin(elapsed * 3.8)
            return (
                OVERLAY_H * 0.30 * breath,   # amplitude
                2.8,                          # horizontal scroll speed
                (0.00, 0.75, 1.00),           # cyan
                (0.35, 0.10, 1.00),           # violet
            )
        elif self.state == "speaking":
            # Sharper pulse rhythm, magenta → purple
            pulse = 1.0 + 0.38 * abs(math.sin(elapsed * 5.5))
            return (
                OVERLAY_H * 0.34 * pulse,
                4.2,
                (0.85, 0.10, 1.00),           # hot magenta
                (0.20, 0.00, 1.00),           # deep blue-violet
            )
        else:
            # Standby — almost flat, dim steel-blue
            drift = 0.06 + 0.04 * math.sin(elapsed * 0.6)
            return (
                OVERLAY_H * drift,
                0.4,
                (0.20, 0.30, 0.65),
                (0.15, 0.20, 0.55),
            )

    def _draw_wave(self, cr, width, center_y,
                   freq, amplitude, phase,
                   r, g, b, alpha, line_width):
        """Draw a single sine-composite wave path."""
        cr.set_source_rgba(r, g, b, alpha)
        cr.set_line_width(line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        first = True
        for i in range(WAVE_STEPS + 1):
            t = i / WAVE_STEPS
            x = t * width

            # Composite of three harmonics for an organic, complex wave shape
            y = center_y + amplitude * (
                0.55 * math.sin(freq * 2.0 * math.pi * t * 1.8 + phase) +
                0.28 * math.sin(freq * 2.0 * math.pi * t * 3.3 + phase * 1.6) +
                0.17 * math.sin(freq * 2.0 * math.pi * t * 6.7 + phase * 2.4)
            )

            if first:
                cr.move_to(x, y)
                first = False
            else:
                cr.line_to(x, y)

        cr.stroke()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear to full transparency
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if not self.active:
            return False

        elapsed = time.time() - self.start_time
        center_y = height / 2.0

        base_amp, speed, color_a, color_b = self._wave_params(elapsed)

        # Draw each wave layer — outermost (glow) first, sharpest on top
        for idx, (freq_mult, amp_mult, phase_mult) in enumerate(WAVE_LAYERS):
            # Scroll phase
            phase = -elapsed * speed + phase_mult

            amplitude = base_amp * amp_mult

            # Interpolate color along the layer stack
            t = idx / max(len(WAVE_LAYERS) - 1, 1)
            r, g, b = _lerp_color(color_a, color_b, t)

            # ── Outer glow pass (wide, transparent) ──────────────────────
            glow_alpha = (0.12 - idx * 0.015) * (1.0 if self.state != "standby" else 0.5)
            if glow_alpha > 0:
                self._draw_wave(
                    cr, width, center_y,
                    freq_mult, amplitude * 1.05, phase,
                    r, g, b,
                    max(glow_alpha, 0.0),
                    (9.0 - idx * 0.8)
                )

            # ── Mid glow pass ─────────────────────────────────────────────
            mid_alpha = (0.28 - idx * 0.03) * (1.0 if self.state != "standby" else 0.5)
            if mid_alpha > 0:
                self._draw_wave(
                    cr, width, center_y,
                    freq_mult, amplitude, phase,
                    r, g, b,
                    max(mid_alpha, 0.0),
                    (4.5 - idx * 0.4)
                )

            # ── Core (sharp) pass ─────────────────────────────────────────
            core_alpha = (0.75 - idx * 0.08) * (1.0 if self.state != "standby" else 0.45)
            if core_alpha > 0:
                self._draw_wave(
                    cr, width, center_y,
                    freq_mult, amplitude * 0.95, phase,
                    r, g, b,
                    max(core_alpha, 0.0),
                    max(1.8 - idx * 0.22, 0.6)
                )

        return False

    # ── Animation loop ────────────────────────────────────────────────────────

    def trigger_redraw(self):
        if self.active:
            self.darea.queue_draw()
            return True
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def show_ui(self, state="listening"):
        self.state = state
        self.start_time = time.time()

        if not self.active:
            self.active = True
            self.show_all()
            if self.anim_source_id is None:
                # ~60 fps
                self.anim_source_id = GLib.timeout_add(16, self.trigger_redraw)
        else:
            # Already visible — just update the state (no restart needed)
            pass

    def hide_ui(self):
        self.active = False
        self.hide()
        if self.anim_source_id is not None:
            GLib.source_remove(self.anim_source_id)
            self.anim_source_id = None


# ─── Global instance ──────────────────────────────────────────────────────────
_ui_instance = None


def get_ui():
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = NexovianUI()
    return _ui_instance


def show_state(state):
    """Thread-safe: update and show the wave overlay."""
    GLib.idle_add(lambda: get_ui().show_ui(state) or False)


def hide():
    """Thread-safe: hide the wave overlay."""
    GLib.idle_add(lambda: get_ui().hide_ui() or False)
