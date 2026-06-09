"""
text_input_ui.py
Raycast-style floating bottom bar for Nexovian.

Features:
  - Anchored to the bottom of the screen, full width
  - Scrollable chat history (typed + spoken commands unified)
  - Ctrl+Space or Escape to show/hide
  - Submits typed commands to llm_brain.process_intent() in a background thread
  - Spoken aloud via audio_engine.speak() after text response is shown
"""

import threading
import time
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

# Lazy imports to avoid circular dependencies at module load time
_llm_brain = None
_audio_engine = None

def _get_llm():
    global _llm_brain
    if _llm_brain is None:
        import llm_brain
        _llm_brain = llm_brain
    return _llm_brain

def _get_audio():
    global _audio_engine
    if _audio_engine is None:
        import audio_engine
        _audio_engine = audio_engine
    return _audio_engine


# ─── Colours ─────────────────────────────────────────────────────────────────
BG_COLOR          = (0.08, 0.08, 0.12, 0.96)   # near-black, slightly blue
USER_BUBBLE_BG    = "#1e2a3a"                    # deep navy
ASSISTANT_BUBBLE_BG = "#151820"                  # darker slate
USER_TEXT_COLOR   = "#7dd3fc"                    # sky-blue
ASSISTANT_TEXT_COLOR = "#c4b5fd"                 # soft purple
LABEL_COLOR       = "#94a3b8"                    # muted slate for role label
INPUT_BG          = "#1e2030"
INPUT_TEXT        = "#e2e8f0"
BORDER_COLOR      = "#334155"
ACCENT_COLOR      = "#7c3aed"                    # vivid purple accent
BAR_HEIGHT        = 320                          # px (including input row)
INPUT_HEIGHT      = 48
CHAT_HEIGHT       = BAR_HEIGHT - INPUT_HEIGHT - 16


# ─── CSS ─────────────────────────────────────────────────────────────────────
CSS = b"""
window.nexovian-bar {
    background-color: rgba(8, 8, 18, 0.97);
    border-top: 1px solid #334155;
}

scrolledwindow {
    background-color: transparent;
}

viewport {
    background-color: transparent;
}

box.chat-box {
    background-color: transparent;
    padding: 12px 16px 4px 16px;
}

box.msg-row {
    margin-bottom: 10px;
}

box.bubble {
    border-radius: 10px;
    padding: 8px 14px;
}

box.bubble.user-bubble {
    background-color: #1e2a3a;
    border: 1px solid #2d3f55;
}

box.bubble.assistant-bubble {
    background-color: #151820;
    border: 1px solid #252a3b;
}

label.role-label {
    font-size: 10px;
    font-weight: bold;
    color: #94a3b8;
    margin-bottom: 2px;
}

label.msg-text {
    font-size: 13px;
    color: #e2e8f0;
}

label.msg-text.user-text {
    color: #7dd3fc;
}

label.msg-text.assistant-text {
    color: #c4b5fd;
}

box.input-row {
    background-color: #1e2030;
    border-top: 1px solid #334155;
    padding: 8px 14px;
}

entry.cmd-entry {
    background-color: #0f1117;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    caret-color: #7c3aed;
}

entry.cmd-entry:focus {
    border-color: #7c3aed;
}

button.send-btn {
    background-color: #7c3aed;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: bold;
    min-width: 56px;
}

button.send-btn:hover {
    background-color: #6d28d9;
}

button.send-btn:active {
    background-color: #5b21b6;
}

label.hint-label {
    font-size: 10px;
    color: #475569;
    margin-left: 8px;
}

label.thinking-label {
    font-size: 12px;
    color: #64748b;
    font-style: italic;
    margin: 4px 16px;
}
"""


class NexovianBar(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        # ── Window properties ──────────────────────────────────────────────
        self.set_title("Nexovian")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(True)
        self.get_style_context().add_class("nexovian-bar")

        # Apply CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Position: full width, bottom of screen
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor is None:
            monitor = display.get_monitor(0)
        geom = monitor.get_geometry()
        scale = monitor.get_scale_factor()
        screen_w = geom.width * scale
        screen_h = geom.height * scale

        self.set_default_size(screen_w, BAR_HEIGHT)
        self.move(geom.x, geom.y + geom.height * scale - BAR_HEIGHT)

        # ── Layout ────────────────────────────────────────────────────────
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer_box)

        # Chat history scroll area
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_min_content_height(CHAT_HEIGHT)
        self._scroll.set_max_content_height(CHAT_HEIGHT)
        outer_box.pack_start(self._scroll, True, True, 0)

        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._chat_box.get_style_context().add_class("chat-box")
        self._scroll.add(self._chat_box)

        # Thinking indicator (hidden by default)
        self._thinking_label = Gtk.Label(label="⏳ Nexovian is thinking…")
        self._thinking_label.get_style_context().add_class("thinking-label")
        self._thinking_label.set_halign(Gtk.Align.START)
        self._thinking_label.set_no_show_all(True)
        outer_box.pack_start(self._thinking_label, False, False, 0)

        # Input row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_row.get_style_context().add_class("input-row")
        outer_box.pack_end(input_row, False, False, 0)

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Type a command for Nexovian…")
        self._entry.get_style_context().add_class("cmd-entry")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)
        self._entry.connect("key-press-event", self._on_key_press)
        input_row.pack_start(self._entry, True, True, 0)

        send_btn = Gtk.Button(label="Send ▶")
        send_btn.get_style_context().add_class("send-btn")
        send_btn.connect("clicked", self._on_send)
        input_row.pack_start(send_btn, False, False, 0)

        hint = Gtk.Label(label="Esc / Ctrl+Space to close")
        hint.get_style_context().add_class("hint-label")
        input_row.pack_start(hint, False, False, 0)

        # Conversation context for multi-turn chats
        self._context = None
        self._busy = False

        # Keyboard: Escape hides the bar
        self.connect("key-press-event", self._on_window_key)

        self.show_all()
        self.hide()

    # ── Message helpers ───────────────────────────────────────────────────

    def _add_message(self, role: str, text: str):
        """Append a message bubble to the chat history (call on GTK main thread)."""
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        row.get_style_context().add_class("msg-row")

        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.get_style_context().add_class("bubble")

        if role == "You":
            bubble.get_style_context().add_class("user-bubble")
            text_class = "user-text"
        else:
            bubble.get_style_context().add_class("assistant-bubble")
            text_class = "assistant-text"

        role_label = Gtk.Label(label=role)
        role_label.get_style_context().add_class("role-label")
        role_label.set_halign(Gtk.Align.START)
        bubble.pack_start(role_label, False, False, 0)

        msg_label = Gtk.Label(label=text)
        msg_label.get_style_context().add_class("msg-text")
        msg_label.get_style_context().add_class(text_class)
        msg_label.set_halign(Gtk.Align.START)
        msg_label.set_line_wrap(True)
        msg_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        msg_label.set_max_width_chars(120)
        msg_label.set_selectable(True)
        bubble.pack_start(msg_label, False, False, 0)

        row.pack_start(bubble, False, False, 0)
        self._chat_box.pack_start(row, False, False, 0)
        self._chat_box.show_all()

        # Auto-scroll to bottom
        GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        adj = self._scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def _set_busy(self, busy: bool):
        """Show/hide the thinking indicator."""
        self._busy = busy
        self._thinking_label.set_visible(busy)
        self._entry.set_sensitive(not busy)

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_key_press(self, widget, event):
        """Handle Escape in the text entry."""
        if event.keyval == Gdk.KEY_Escape:
            self.hide_bar()
            return True
        return False

    def _on_window_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_bar()
            return True
        return False

    def _on_send(self, *_):
        text = self._entry.get_text().strip()
        if not text or self._busy:
            return

        self._entry.set_text("")
        GLib.idle_add(self._add_message, "You", text)
        GLib.idle_add(self._set_busy, True)

        threading.Thread(target=self._process_typed, args=(text,), daemon=True).start()

    def _process_typed(self, text: str):
        """Run LLM inference on a background thread, then update UI + speak."""
        try:
            llm = _get_llm()
            audio = _get_audio()

            if audio.is_system_locked:
                return

            response_text, action_result, new_context = llm.process_intent(text, self._context)
            if audio.is_system_locked:
                return
            self._context = new_context

            display_action, spoken_action = llm.parse_action_result(action_result)

            full_display = ""
            if response_text:
                full_display += response_text
            if display_action:
                full_display += (" " if full_display else "") + display_action

            if not full_display:
                full_display = "(No response)"

            if audio.is_system_locked:
                return
            GLib.idle_add(self._add_message, "Nexovian", full_display)

            # Speak the spoken response
            full_speak = ""
            if response_text:
                full_speak += response_text
            if spoken_action:
                full_speak += (" " if full_speak else "") + spoken_action

            if full_speak:
                if audio.is_system_locked:
                    return
                threading.Thread(target=audio.speak, args=(full_speak,), daemon=True).start()

        except Exception as e:
            if not audio.is_system_locked:
                GLib.idle_add(self._add_message, "Nexovian", f"[Error: {e}]")
        finally:
            GLib.idle_add(self._set_busy, False)

    # ── Public API (thread-safe via GLib.idle_add) ────────────────────────

    def show_bar(self):
        self.show_all()
        self._thinking_label.set_visible(self._busy)
        self.present()
        self._entry.grab_focus()

    def hide_bar(self):
        self.hide()
        try:
            import ui_overlay
            ui_overlay.hide()
        except Exception:
            pass
        try:
            audio = _get_audio()
            audio.set_system_locked(True)
            audio.set_system_locked(False)
        except Exception:
            pass

    def toggle_bar(self):
        if self.get_visible():
            self.hide_bar()
        else:
            self.show_bar()

    def append_spoken_message(self, role: str, text: str):
        """Called externally to surface voice commands/responses in the chat log."""
        if self.get_visible():
            GLib.idle_add(self._add_message, role, text)


# ─── Global instance ──────────────────────────────────────────────────────────
_bar_instance: NexovianBar | None = None


def get_bar() -> NexovianBar:
    global _bar_instance
    if _bar_instance is None:
        _bar_instance = NexovianBar()
    return _bar_instance


def show_bar():
    """Thread-safe: show the bottom bar."""
    GLib.idle_add(lambda: get_bar().show_bar() or False)


def hide_bar():
    """Thread-safe: hide the bottom bar."""
    GLib.idle_add(lambda: get_bar().hide_bar() or False)


def toggle_bar():
    """Thread-safe: toggle the bottom bar visibility."""
    GLib.idle_add(lambda: get_bar().toggle_bar() or False)


def append_spoken(role: str, text: str):
    """Thread-safe: append a voice command or spoken response to the chat log."""
    GLib.idle_add(lambda: get_bar().append_spoken_message(role, text) or False)
