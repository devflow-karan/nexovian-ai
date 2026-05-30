import math
import time
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo

class NexovianUI(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        
        self.set_title("Nexovian Overlay")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        
        # Make transparent
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)
        
        # Center of screen
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(300, 300)
        
        # Drawing area
        self.darea = Gtk.DrawingArea()
        self.darea.connect("draw", self.on_draw)
        self.add(self.darea)
        
        # Animation state
        self.active = False
        self.start_time = 0
        self.state = "standby" # 'listening', 'speaking', 'standby'
        self.anim_source_id = None
        
    def on_draw(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Clear background (transparent)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        
        if not self.active:
            return False
            
        center_x = width / 2.0
        center_y = height / 2.0
        
        elapsed = time.time() - self.start_time
        
        if self.state == "listening":
            # Fast pulse, cyan
            scale = 1.0 + 0.3 * math.sin(elapsed * 5.0)
            color = (0.0, 0.8, 1.0, 0.6) # R, G, B, A
        elif self.state == "speaking":
            # Slower pulse, purple/magenta
            scale = 1.0 + 0.2 * math.sin(elapsed * 3.0)
            color = (0.8, 0.2, 1.0, 0.8)
        else:
            scale = 1.0
            color = (0.5, 0.5, 0.5, 0.5)
            
        base_radius = 50.0
        radius = base_radius * scale
        
        # Draw outer glow
        cr.arc(center_x, center_y, radius * 1.2, 0, 2 * math.pi)
        cr.set_source_rgba(color[0], color[1], color[2], color[3] * 0.3)
        cr.fill()
        
        # Draw inner circle
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.set_source_rgba(color[0], color[1], color[2], color[3])
        cr.fill()
        
        return False

    def trigger_redraw(self):
        if self.active:
            self.darea.queue_draw()
            return True
        return False

    def show_ui(self, state="listening"):
        self.state = state
        self.start_time = time.time()
        
        if not self.active:
            self.active = True
            self.show_all()
            if self.anim_source_id is None:
                # 60fps = ~16ms
                self.anim_source_id = GLib.timeout_add(16, self.trigger_redraw)
                
    def hide_ui(self):
        self.active = False
        self.hide()
        if self.anim_source_id is not None:
            GLib.source_remove(self.anim_source_id)
            self.anim_source_id = None

# Global instance
_ui_instance = None

def get_ui():
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = NexovianUI()
    return _ui_instance

def show_state(state):
    """Thread-safe way to update UI state"""
    GLib.idle_add(lambda: get_ui().show_ui(state) or False)

def hide():
    """Thread-safe way to hide UI"""
    GLib.idle_add(lambda: get_ui().hide_ui() or False)
