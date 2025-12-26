"""
Multi-Client Viewer - Baby Tank - Multi-Client Picture-in-Picture
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from PIL import Image, ImageGrab, ImageTk, ImageDraw
import win32gui
import win32con
import win32ui
import win32process
from ctypes import windll
import time
import threading
import logging
import sys
from logging.handlers import RotatingFileHandler
import requests
import json
import os
import subprocess
import tempfile
import queue
import psutil
import webbrowser
import io
import re

# Store version and logs in memory instead of files
IN_MEMORY_VERSION = None
IN_MEMORY_LOGS = []
MAX_LOG_ENTRIES = 1000

def get_version_from_filename():
    """Extract version from the executable filename"""
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            filename = os.path.basename(exe_path)
            
            # Match patterns like: MultiClientViewer-v1.0.35.exe
            match = re.search(r'v?(\d+\.\d+\.\d+)', filename)
            if match:
                version = 'v' + match.group(1)
                logging.info(f"Detected version {version} from filename: {filename}")
                return version
        
        return None
    except Exception as e:
        logging.error(f"Error reading version from filename: {e}")
        return None

# Store version and logs in memory instead of files
IN_MEMORY_VERSION = None
IN_MEMORY_LOGS = []
MAX_LOG_ENTRIES = 1000

# Settings storage
IN_MEMORY_SETTINGS = {
    "theme": "dark",
    "accent_color": "#007AFF",
    "grid_columns": 5,
    "thumbnail_size": "medium",
    "window_positions": {},
    "last_monitor": 0
}

class MemoryLogHandler(logging.Handler):
    """Custom log handler that stores logs in memory"""
    def emit(self, record):
        global IN_MEMORY_LOGS
        log_entry = self.format(record)
        IN_MEMORY_LOGS.append(log_entry)
        if len(IN_MEMORY_LOGS) > MAX_LOG_ENTRIES:
            IN_MEMORY_LOGS.pop(0)

GITHUB_REPO = "BabyTank-Projects/MultiClientViewer"

def get_current_version():
    """Get current version from memory or filename"""
    global IN_MEMORY_VERSION
    
    if IN_MEMORY_VERSION is None:
        # Try to get version from filename as fallback
        IN_MEMORY_VERSION = get_version_from_filename()
    
    return IN_MEMORY_VERSION

def save_current_version(version):
    """Save version to memory"""
    global IN_MEMORY_VERSION
    IN_MEMORY_VERSION = version

def get_setting(key, default=None):
    """Get setting from memory"""
    global IN_MEMORY_SETTINGS
    return IN_MEMORY_SETTINGS.get(key, default)

def save_setting(key, value):
    """Save setting to memory"""
    global IN_MEMORY_SETTINGS
    IN_MEMORY_SETTINGS[key] = value

def compare_versions(current, latest):
    """Compare version strings (e.g., '1.0.6' vs '1.0.7')"""
    try:
        current = current.lstrip('v') if current else "0.0.0"
        latest = latest.lstrip('v') if latest else "0.0.0"
        
        current_parts = [int(x) for x in current.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]
        
        return latest_parts > current_parts
    except:
        return True

def get_latest_release():
    """Fetch the latest release info from GitHub"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error checking for updates: {e}")
        return None

def check_for_updates(show_no_update_message=False):
    """Check for updates and show link to GitHub release"""
    release_info = get_latest_release()
    
    if not release_info:
        if show_no_update_message:
            messagebox.showinfo("Update Check", "Unable to check for updates. Please try again later.")
        return
    
    latest_version = release_info.get('tag_name', '').lstrip('v')
    release_url = release_info.get('html_url', f"https://github.com/{GITHUB_REPO}/releases/latest")
    
    if not latest_version:
        if show_no_update_message:
            messagebox.showinfo("Update Check", "No version information available.")
        return
    
    current_version = get_current_version()
    
    if current_version and not compare_versions(current_version, latest_version):
        if show_no_update_message:
            messagebox.showinfo("No Update", f"You're already on the latest version ({current_version})!")
        return
    
    # Show update available dialog
    result = messagebox.askyesno(
        "Update Available",
        f"A new version ({latest_version}) is available!\n\n"
        f"Current version: {current_version if current_version else 'Unknown'}\n\n"
        "Click YES to download the update.\n"
        "Click NO if you've already updated (to mark as current version).",
        icon='info'
    )

    if result:
        # User wants to download
        webbrowser.open(release_url)
    else:
        # User clicked No - ask if they already updated
        user_response = messagebox.askyesno(
            "Version Update",
            f"Have you already updated to version {latest_version}?",
            icon='question'
        )
        if user_response:
            save_current_version(latest_version)

def check_updates_on_startup():
    """Check for updates in background thread on startup"""
    def bg_check():
        # Don't auto-save version on startup - let user decide
        check_for_updates(show_no_update_message=False)
    
    thread = threading.Thread(target=bg_check, daemon=True)
    thread.start()

def setup_logging():
    """Setup logging to memory instead of file"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    
    memory_handler = MemoryLogHandler()
    memory_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    memory_handler.setFormatter(formatter)
    logger.addHandler(memory_handler)
    
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger

setup_logging()

def get_process_cpu_usage(hwnd):
    """Get CPU usage for a specific window"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = psutil.Process(pid)
        cpu = process.cpu_percent(interval=None)
        return cpu if cpu > 0 else 0.0
    except:
        return 0.0

# Thumbnail size presets (width, height)
THUMBNAIL_SIZES = {
    "small": (240, 180),
    "medium": (320, 240),
    "large": (480, 360)
}

class ModernButton(tk.Canvas):
    """Custom modern button with hover effects"""
    def __init__(self, parent, text, command, bg="#007AFF", fg="white", hover_bg="#0051D5", width=120, **kwargs):
        if width == 120:
            text_width = len(text) * 8 + 30
            width = max(120, text_width)
        
        super().__init__(parent, height=36, width=width, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.bg = bg
        self.fg = fg
        self.hover_bg = hover_bg
        self.is_hovered = False
        self.button_width = width
        
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Configure>", lambda e: self.draw())
        
        self.after(10, self.draw)
    
    def draw(self):
        self.delete("all")
        color = self.hover_bg if self.is_hovered else self.bg
        try:
            parent_bg = self.master.cget('bg')
            self.configure(bg=parent_bg)
        except:
            pass
        
        width = self.button_width
        height = 36
        
        radius = 8
        self.create_rounded_rect(2, 2, width-2, height-2, radius, fill=color, outline="")
        self.create_text(width//2, height//2, text=self.text, fill=self.fg, font=("Segoe UI", 10, "bold"))
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, e):
        self.is_hovered = True
        self.draw()
    
    def on_leave(self, e):
        self.is_hovered = False
        self.draw()

class ModernToggle(tk.Frame):
    """Custom modern toggle switch"""
    def __init__(self, parent, text, variable, command=None, text_color=None, **kwargs):
        # Get parent background safely
        try:
            parent_bg = parent.cget('bg')
        except:
            parent_bg = "#1a1a1a"
        
        super().__init__(parent, bg=parent_bg, **kwargs)
        self.variable = variable
        self.command = command
        self.text = text
        self.bg_color = parent_bg
        self.text_color = text_color if text_color else "white"
        
        container = tk.Frame(self, bg=self.bg_color)
        container.pack(padx=10, pady=5)
        
        self.label = tk.Label(
            container,
            text=text,
            font=("Segoe UI", 10),
            fg=self.text_color,
            bg=self.bg_color
        )
        self.label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.toggle_canvas = tk.Canvas(
            container,
            width=50,
            height=26,
            bg=self.bg_color,
            highlightthickness=0,
            cursor="hand2"
        )
        self.toggle_canvas.pack(side=tk.LEFT)
        
        self.toggle_canvas.bind("<Button-1>", self.toggle)
        self.label.bind("<Button-1>", self.toggle)
        
        self.draw_toggle()
        
        self.variable.trace_add("write", lambda *args: self.draw_toggle())
    
    def draw_toggle(self):
        self.toggle_canvas.delete("all")
        is_on = self.variable.get()
        
        bg_color = get_setting("accent_color", "#007AFF") if is_on else "#3a3a3a"
        self._create_rounded_rect(
            self.toggle_canvas,
            2, 2, 48, 24, 12,
            fill=bg_color,
            outline=""
        )
        
        circle_x = 35 if is_on else 15
        self.toggle_canvas.create_oval(
            circle_x - 8, 5,
            circle_x + 8, 21,
            fill="white",
            outline=""
        )
    
    def toggle(self, event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
    
    def _create_rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

class PiPBoard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Multi-Client Viewer")
        # Don't set initial geometry - let restore_window_position handle it
        # self.root.geometry("2000x1080")
        
        # Load theme settings FIRST before using them
        self.current_theme = get_setting("theme", "dark")
        self.accent_color = get_setting("accent_color", "#007AFF")
        self.grid_columns = get_setting("grid_columns", 5)
        
        # Theme colors - DEFINE BEFORE ANY UI SETUP
        self.themes = {
            "dark": {
                "bg": "#1a1a1a",
                "card_bg": "#2a2a2a",
                "text": "white",
                "text_secondary": "#aaaaaa",
                "button_bg": "#666666",
                "button_hover": "#555555",
                "button_text": "white",
                "toggle_text": "white"
            },
            "light": {
                "bg": "#f5f5f5",
                "card_bg": "#ffffff",
                "text": "#1a1a1a",
                "text_secondary": "#666666",
                "button_bg": "#d0d0d0",
                "button_hover": "#b0b0b0",
                "button_text": "#1a1a1a",
                "toggle_text": "#1a1a1a"
            }
        }
        
        # Set theme colors
        self.bg_color = self.themes[self.current_theme]["bg"]
        self.card_bg = self.themes[self.current_theme]["card_bg"]
        self.text_color = self.themes[self.current_theme]["text"]
        self.text_secondary = self.themes[self.current_theme]["text_secondary"]
        self.button_bg = self.themes[self.current_theme]["button_bg"]
        self.button_hover = self.themes[self.current_theme]["button_hover"]
        self.button_text = self.themes[self.current_theme]["button_text"]
        self.toggle_text = self.themes[self.current_theme]["toggle_text"]
        
        self.fps = 20
        self.movie_mode = False
        self.paused = False
        self.capture_scale = 0.5
        
        self.clients = {}
        self.running = True
        self.paused_clients = set()
        self.expanded_windows = set()
        
        self.client_lock = threading.Lock()
        self.expanded_lock = threading.Lock()
        
        self.ui_queue = queue.Queue()
        
        self.debug_panel_visible = False
        self.debug_panel = None
        
        # Calculate initial thumbnail size
        self.calculate_thumbnail_size()
        
        # Setup UI
        self.setup_modern_ui()
        
        self.process_ui_queue()
        
        # Restore position after UI is fully loaded
        self.root.after(200, self.restore_window_position)
        
        # Start threads
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.monitor_thread = threading.Thread(target=self.monitor_expanded_windows, daemon=True)
        self.monitor_thread.start()
        
        self.status_monitor_thread = threading.Thread(target=self.monitor_window_states, daemon=True)
        self.status_monitor_thread.start()
        
        self.cpu_monitor_thread = threading.Thread(target=self.monitor_cpu_usage, daemon=True)
        self.cpu_monitor_thread.start()
        
        check_updates_on_startup()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def calculate_thumbnail_size(self):
        """Calculate optimal thumbnail size based on grid columns and screen size"""
        try:
            # Get screen width
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            
            # Calculate available width (accounting for window borders, padding, scrollbar)
            window_padding = 60  # Total horizontal padding in window
            scrollbar_width = 20  # Scrollbar width
            card_margin = 24  # Total margin per card (12px each side)
            card_internal_padding = 30  # Padding inside card
            
            # Available width for all columns
            available_width = screen_width - window_padding - scrollbar_width
            
            # Calculate width per column
            width_per_column = available_width / self.grid_columns
            
            # Calculate actual thumbnail width
            thumbnail_width = int(width_per_column - card_margin - card_internal_padding)
            
            # Ensure reasonable size constraints
            thumbnail_width = max(180, min(thumbnail_width, 600))
            
            # Calculate height (4:3 aspect ratio)
            thumbnail_height = int(thumbnail_width * 0.75)
            
            # Store as tuple
            self.current_thumbnail_size = (thumbnail_width, thumbnail_height)
            
            logging.info(f"Calculated thumbnail size: {self.current_thumbnail_size} for {self.grid_columns} columns (screen: {screen_width}px)")
            
        except Exception as e:
            logging.error(f"Error calculating thumbnail size: {e}")
            # Fallback to medium size
            self.current_thumbnail_size = (320, 240)
    
    def on_window_configure(self, event):
        """Save window position when moved"""
        if event.widget == self.root:
            # Use after_idle to debounce and ensure we capture final position
            if hasattr(self, '_save_position_job'):
                self.root.after_cancel(self._save_position_job)
            self._save_position_job = self.root.after(500, self._save_window_position)
    
    def _save_window_position(self):
        """Actually save the window position"""
        try:
            positions = get_setting("window_positions", {})
            # Check if window is maximized
            is_maximized = (self.root.state() == 'zoomed')
            
            # Force update to get accurate position
            self.root.update_idletasks()
            
            positions["main"] = {
                "x": self.root.winfo_x(),
                "y": self.root.winfo_y(),
                "width": self.root.winfo_width(),
                "height": self.root.winfo_height(),
                "maximized": is_maximized
            }
            save_setting("window_positions", positions)
            logging.debug(f"Saved window position: x={positions['main']['x']}, y={positions['main']['y']}")
        except Exception as e:
            logging.error(f"Error saving window position: {e}")
    
    def restore_window_position(self):
        """Restore window position from saved settings"""
        try:
            positions = get_setting("window_positions", {})
            if "main" in positions:
                pos = positions["main"]
                
                # Check if position is valid (not off-screen)
                x = pos.get('x', 100)
                y = pos.get('y', 100)
                width = pos.get('width', 2000)
                height = pos.get('height', 1080)
                is_maximized = pos.get("maximized", False)
                
                logging.debug(f"Attempting to restore: x={x}, y={y}, w={width}, h={height}, maximized={is_maximized}")
                
                # Temporarily unbind configure to avoid triggering saves during restore
                self.root.unbind("<Configure>")
                
                if is_maximized:
                    # If it was maximized, just set the position and then maximize
                    self.root.geometry(f"+{x}+{y}")
                    self.root.update_idletasks()
                    self.root.after(200, lambda: self.root.state('zoomed'))
                else:
                    # Normal window - restore size and position
                    self.root.geometry(f"{width}x{height}+{x}+{y}")
                    self.root.update_idletasks()
                
                # Re-bind configure after restoration is complete
                self.root.after(1000, lambda: self.root.bind("<Configure>", self.on_window_configure))
                
                logging.debug(f"Window restored successfully")
            else:
                logging.debug("No saved window position found, using default")
                # Re-bind configure immediately if no saved position
                self.root.bind("<Configure>", self.on_window_configure)
        except Exception as e:
            logging.error(f"Error restoring window position: {e}")
            # Make sure we re-bind even if there's an error
            self.root.after(1000, lambda: self.root.bind("<Configure>", self.on_window_configure))
    
    def process_ui_queue(self):
        """Process UI updates from background threads safely"""
        try:
            while not self.ui_queue.empty():
                try:
                    func, args, kwargs = self.ui_queue.get_nowait()
                    func(*args, **kwargs)
                except queue.Empty:
                    break
                except Exception as e:
                    logging.error(f"Error processing UI queue item: {e}")
        except Exception as e:
            logging.error(f"Error in process_ui_queue: {e}")
        finally:
            if self.running:
                self.root.after(50, self.process_ui_queue)
    
    def queue_ui_update(self, func, *args, **kwargs):
        """Queue a UI update to be executed on the main thread"""
        try:
            self.ui_queue.put((func, args, kwargs))
        except Exception as e:
            logging.error(f"Error queuing UI update: {e}")
    
    def apply_theme(self):
        """Apply current theme to all UI elements"""
        # Update theme colors
        self.bg_color = self.themes[self.current_theme]["bg"]
        self.card_bg = self.themes[self.current_theme]["card_bg"]
        self.text_color = self.themes[self.current_theme]["text"]
        self.text_secondary = self.themes[self.current_theme]["text_secondary"]
        self.button_bg = self.themes[self.current_theme]["button_bg"]
        self.button_hover = self.themes[self.current_theme]["button_hover"]
        self.button_text = self.themes[self.current_theme]["button_text"]
        self.toggle_text = self.themes[self.current_theme]["toggle_text"]
        
        self.root.configure(bg=self.bg_color)
        
        # Recalculate thumbnail size
        self.calculate_thumbnail_size()
        
        # Store current clients data before destroying widgets
        with self.client_lock:
            clients_copy = list(self.clients.items())
        
        # Destroy all widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Recreate UI
        self.setup_modern_ui()
        
        # Recreate all client cards
        for hwnd, client_data in clients_copy:
            self.recreate_client_card(hwnd, client_data)
    
    def recreate_client_card(self, hwnd, old_data):
        """Recreate a client card with current theme"""
        position = old_data["position"]
        title = old_data["title"]
        
        row = position // self.grid_columns
        col = position % self.grid_columns
        
        card, img_label, controls, title_label, status_indicator, cpu_label = self.create_modern_card(
            self.scrollable_frame,
            title,
            position + 1
        )
        
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        
        self.scrollable_frame.grid_columnconfigure(col, weight=1, minsize=self.current_thumbnail_size[0] + 30)
        
        img_label.bind('<Button-1>', lambda e: self.expand_pip(hwnd))
        
        btn_frame = tk.Frame(controls, bg=self.card_bg)
        btn_frame.pack(side=tk.LEFT)
        
        up_btn = tk.Label(btn_frame, text="↑", fg=self.text_color, bg=self.card_bg, cursor="hand2", font=("Segoe UI", 12), padx=10)
        up_btn.pack(side=tk.LEFT, padx=2)
        up_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, -1))
        
        down_btn = tk.Label(btn_frame, text="↓", fg=self.text_color, bg=self.card_bg, cursor="hand2", font=("Segoe UI", 12), padx=10)
        down_btn.pack(side=tk.LEFT, padx=2)
        down_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, 1))
        
        remove_btn = tk.Label(controls, text="✕ Remove", fg="#ff4444", bg=self.card_bg, cursor="hand2", font=("Segoe UI", 9))
        remove_btn.pack(side=tk.RIGHT)
        remove_btn.bind("<Button-1>", lambda e: self.remove_client(hwnd))
        
        with self.client_lock:
            self.clients[hwnd].update({
                "frame": card,
                "label": img_label,
                "title_label": title_label,
                "status_indicator": status_indicator,
                "cpu_label": cpu_label,
                "row": row,
                "col": col
            })
    
    def setup_modern_ui(self):
        self.root.configure(bg=self.bg_color)
        
        header = tk.Frame(self.root, bg=self.bg_color, height=80)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header, 
            text="Multi-Client Viewer", 
            font=("Segoe UI", 24, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        title_label.pack(side=tk.LEFT, padx=30, pady=20)
        
        controls = tk.Frame(header, bg=self.bg_color)
        controls.pack(side=tk.RIGHT, padx=30, pady=20)
        
        add_btn = ModernButton(controls, "＋ Add Window", self.add_window, bg=self.accent_color, width=150)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        self.movie_mode_var = tk.BooleanVar(value=False)
        self.movie_toggle = self.create_toggle_button(controls, "🎬 Movie Mode", self.movie_mode_var, self.toggle_movie_mode)
        self.movie_toggle.pack(side=tk.LEFT, padx=8)
        
        self.auto_minimize_var = tk.BooleanVar(value=True)
        self.auto_toggle = self.create_toggle_button(controls, "⚡ Auto-Minimize", self.auto_minimize_var, None)
        self.auto_toggle.pack(side=tk.LEFT, padx=8)
        
        utility_frame = tk.Frame(controls, bg=self.bg_color)
        utility_frame.pack(side=tk.LEFT, padx=15)
        
        settings_btn = ModernButton(utility_frame, "⚙️ Settings", self.show_settings_dialog, 
                                     bg=self.button_bg, hover_bg=self.button_hover, 
                                     fg=self.button_text, width=120)
        settings_btn.pack(side=tk.LEFT, padx=3)
        
        updates_btn = ModernButton(utility_frame, "🔄 Updates", lambda: check_for_updates(show_no_update_message=True), 
                                   bg=self.button_bg, hover_bg=self.button_hover, 
                                   fg=self.button_text, width=120)
        updates_btn.pack(side=tk.LEFT, padx=3)
        
        help_btn = ModernButton(utility_frame, "❓ Help", self.show_help_dialog, 
                                bg=self.button_bg, hover_bg=self.button_hover, 
                                fg=self.button_text, width=100)
        help_btn.pack(side=tk.LEFT, padx=3)
        
        chatgpt_btn = ModernButton(utility_frame, "💬 ChatGPT", self.open_chatgpt, 
                                   bg="#10a37f", hover_bg="#0d8c6d", 
                                   fg="white", width=120)
        chatgpt_btn.pack(side=tk.LEFT, padx=3)
        
        debug_btn = ModernButton(utility_frame, "🐛 Debug", self.toggle_debug_panel, 
                                 bg="#444444", hover_bg="#333333", width=110)
        debug_btn.pack(side=tk.LEFT, padx=3)
        
        status_frame = tk.Frame(controls, bg=self.bg_color)
        status_frame.pack(side=tk.LEFT, padx=15)
        
        self.status_dot = tk.Canvas(status_frame, width=12, height=12, bg=self.bg_color, highlightthickness=0)
        self.status_dot.create_oval(2, 2, 10, 10, fill="#00ff00", outline="")
        self.status_dot.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Active",
            fg="#00ff00",
            bg=self.bg_color,
            font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(side=tk.LEFT)
        
        content = tk.Frame(self.root, bg=self.bg_color)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.canvas = tk.Canvas(content, bg=self.bg_color, highlightthickness=0)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create scroll button container on the right
        scroll_buttons = tk.Frame(content, bg=self.bg_color, width=50)
        scroll_buttons.pack(side=tk.RIGHT, fill=tk.Y)

        # Add vertical spacer to center the buttons
        tk.Frame(scroll_buttons, bg=self.bg_color).pack(side=tk.TOP, expand=True)

        # Up arrow button
        up_arrow = tk.Label(
            scroll_buttons,
            text="▲",
            font=("Segoe UI", 20),
            fg=self.accent_color,
            bg=self.bg_color,
            cursor="hand2",
            padx=10,
            pady=5
        )
        up_arrow.pack(side=tk.TOP, pady=5)

        def scroll_up(event=None):
            self.canvas.yview_scroll(-3, "units")

        up_arrow.bind("<Button-1>", scroll_up)

        # Down arrow button
        down_arrow = tk.Label(
            scroll_buttons,
            text="▼",
            font=("Segoe UI", 20),
            fg=self.accent_color,
            bg=self.bg_color,
            cursor="hand2",
            padx=10,
            pady=5
        )
        down_arrow.pack(side=tk.TOP, pady=5)

        def scroll_down(event=None):
            self.canvas.yview_scroll(3, "units")

        down_arrow.bind("<Button-1>", scroll_down)

        # Add vertical spacer to center the buttons
        tk.Frame(scroll_buttons, bg=self.bg_color).pack(side=tk.TOP, expand=True)

        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        self.debug_panel = None
        self.debug_panel_visible = False
    
    def create_toggle_button(self, parent, text, variable, command):
        return ModernToggle(parent, text, variable, command, text_color=self.toggle_text)
    
    def create_modern_card(self, parent, title, position):
        card = tk.Frame(parent, bg=self.card_bg, relief="flat", bd=0)
        
        # Header with title and CPU
        header = tk.Frame(card, bg=self.card_bg, height=40)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text=f"#{position} {title}",
            font=("Segoe UI", 11, "bold"),
            fg=self.text_color,
            bg=self.card_bg,
            anchor="w"
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        cpu_label = tk.Label(
            header,
            text="0%",
            font=("Segoe UI", 9),
            fg=self.text_secondary,
            bg=self.card_bg
        )
        cpu_label.pack(side=tk.RIGHT, padx=(10, 5))
        
        # Image frame
        img_frame = tk.Frame(card, bg="#000000", relief="flat")
        img_frame.pack(padx=15, pady=5)
        
        thumb_width, thumb_height = self.current_thumbnail_size
        img_container = tk.Frame(img_frame, width=thumb_width, height=thumb_height, bg="#000000")
        img_container.pack()
        img_container.pack_propagate(False)
        
        img_label = tk.Label(img_container, bg="#000000", cursor="hand2")
        img_label.pack(fill=tk.BOTH, expand=True)
        
        # Status indicator below image
        status_frame = tk.Frame(card, bg=self.card_bg)
        status_frame.pack(fill=tk.X, padx=15, pady=(5, 5))
        
        status_indicator = tk.Canvas(status_frame, width=10, height=10, bg=self.card_bg, highlightthickness=0)
        status_indicator.create_oval(2, 2, 8, 8, fill="#00ff00", outline="")
        status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        status_text = tk.Label(
            status_frame,
            text="Minimized",
            font=("Segoe UI", 9),
            fg=self.text_secondary,
            bg=self.card_bg
        )
        status_text.pack(side=tk.LEFT)
        
        # Controls at bottom
        controls = tk.Frame(card, bg=self.card_bg)
        controls.pack(fill=tk.X, padx=15, pady=(5, 15))
        
        return card, img_label, controls, title_label, status_indicator, cpu_label
    
    def get_window_list(self):
        windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and title not in ["", "Multi-Client Viewer"]:
                    windows.append((hwnd, title))
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows
    
    def add_window(self):
        def get_windows_async():
            windows = self.get_window_list()
            
            with self.client_lock:
                available_windows = [(hwnd, title) for hwnd, title in windows if hwnd not in self.clients]
            
            self.queue_ui_update(self._show_window_dialog, available_windows)
        
        thread = threading.Thread(target=get_windows_async, daemon=True)
        thread.start()
    
    def _show_window_dialog(self, available_windows):
        """Show window selection dialog (called on UI thread)"""
        if not available_windows:
            messagebox.showinfo("No Windows", "No new capturable windows found!")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Window")
        dialog.geometry("500x400")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        dialog.grab_set()
        
        header = tk.Label(
            dialog,
            text="Select a window to monitor",
            font=("Segoe UI", 16, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        header.pack(pady=(20, 10), padx=20)
        
        list_container = tk.Frame(dialog, bg=self.card_bg)
        list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(list_container)
        listbox = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            bg=self.card_bg,
            fg=self.text_color,
            font=("Segoe UI", 10),
            selectbackground=self.accent_color,
            selectforeground="white",
            relief="flat",
            highlightthickness=0
        )
        scrollbar.config(command=listbox.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for hwnd, title in available_windows:
            listbox.insert(tk.END, title)
        
        button_frame = tk.Frame(dialog, bg=self.bg_color)
        button_frame.pack(pady=20)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                hwnd, title = available_windows[selection[0]]
                self.add_client(hwnd, title)
                dialog.destroy()
        
        ModernButton(button_frame, "Add", on_select, width=120).pack(side=tk.LEFT, padx=5)
        ModernButton(button_frame, "Cancel", dialog.destroy, bg=self.button_bg, hover_bg=self.button_hover, width=120).pack(side=tk.LEFT, padx=5)
        
        listbox.bind('<Double-Button-1>', lambda e: on_select())
    
    def add_client(self, hwnd, title):
        with self.client_lock:
            if hwnd in self.clients:
                messagebox.showinfo("Already Added", f"Window '{title}' is already being monitored!")
                return
            client_count = len(self.clients)
        
        row = client_count // self.grid_columns
        col = client_count % self.grid_columns
        
        card, img_label, controls, title_label, status_indicator, cpu_label = self.create_modern_card(
            self.scrollable_frame,
            title,
            client_count + 1
        )
        
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        
        thumb_width = self.current_thumbnail_size[0]
        self.scrollable_frame.grid_columnconfigure(col, weight=1, minsize=thumb_width + 30)
        self.scrollable_frame.grid_rowconfigure(row, weight=1)
        
        img_label.bind('<Button-1>', lambda e: self.expand_pip(hwnd))
        
        btn_frame = tk.Frame(controls, bg=self.card_bg)
        btn_frame.pack(side=tk.LEFT)
        
        up_btn = tk.Label(btn_frame, text="↑", fg=self.text_color, bg=self.card_bg, cursor="hand2", font=("Segoe UI", 12), padx=10)
        up_btn.pack(side=tk.LEFT, padx=2)
        up_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, -1))
        
        down_btn = tk.Label(btn_frame, text="↓", fg=self.text_color, bg=self.card_bg, cursor="hand2", font=("Segoe UI", 12), padx=10)
        down_btn.pack(side=tk.LEFT, padx=2)
        down_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, 1))
        
        remove_btn = tk.Label(controls, text="✕ Remove", fg="#ff4444", bg=self.card_bg, cursor="hand2", font=("Segoe UI", 9))
        remove_btn.pack(side=tk.RIGHT)
        remove_btn.bind("<Button-1>", lambda e: self.remove_client(hwnd))
        
        with self.client_lock:
            self.clients[hwnd] = {
                "title": title,
                "frame": card,
                "label": img_label,
                "title_label": title_label,
                "status_indicator": status_indicator,
                "cpu_label": cpu_label,
                "photo": None,
                "row": row,
                "col": col,
                "last_update": 0,
                "position": client_count,
                "is_minimized": False,
                "cpu_usage": 0.0
            }
        
        logging.info(f"Added client: {title} (hwnd: {hwnd})")

        # Scroll to top when adding new window
        self.canvas.yview_moveto(0)
    
    def monitor_cpu_usage(self):
        """Monitor CPU usage for each window"""
        process_cache = {}
        
        while self.running:
            try:
                with self.client_lock:
                    clients_copy = list(self.clients.keys())
                
                for hwnd in list(process_cache.keys()):
                    if hwnd not in clients_copy:
                        del process_cache[hwnd]
                
                for hwnd in clients_copy:
                    if not win32gui.IsWindow(hwnd):
                        if hwnd in process_cache:
                            del process_cache[hwnd]
                        continue
                    
                    try:
                        if hwnd not in process_cache:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            proc.cpu_percent(interval=None)
                            process_cache[hwnd] = proc
                        
                        cpu_usage = process_cache[hwnd].cpu_percent(interval=None)
                        
                        with self.client_lock:
                            if hwnd in self.clients:
                                self.clients[hwnd]["cpu_usage"] = cpu_usage
                                self.queue_ui_update(self.update_cpu_display, hwnd, cpu_usage)
                                
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        if hwnd in process_cache:
                            del process_cache[hwnd]
                    except Exception as e:
                        logging.error(f"Error getting CPU usage for {hwnd}: {e}")
                        if hwnd in process_cache:
                            del process_cache[hwnd]
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error in CPU monitor thread: {e}")
                time.sleep(2)
    
    def update_cpu_display(self, hwnd, cpu_usage):
        """Update CPU usage display"""
        try:
            with self.client_lock:
                if hwnd not in self.clients:
                    return
                cpu_label = self.clients[hwnd]["cpu_label"]
            
            cpu_label.configure(text=f"{cpu_usage:.1f}%")
        except Exception as e:
            logging.error(f"Error updating CPU display for {hwnd}: {e}")
    
    def monitor_window_states(self):
        """Monitor window states to update status indicators"""
        while self.running:
            try:
                with self.client_lock:
                    clients_copy = list(self.clients.keys())
                
                for hwnd in clients_copy:
                    if not win32gui.IsWindow(hwnd):
                        continue
                    
                    try:
                        is_minimized = win32gui.IsIconic(hwnd)
                        
                        with self.client_lock:
                            if hwnd in self.clients:
                                old_state = self.clients[hwnd].get("is_minimized", False)
                                if old_state != is_minimized:
                                    self.clients[hwnd]["is_minimized"] = is_minimized
                                    self.queue_ui_update(self.update_client_status, hwnd, is_minimized)
                    except Exception as e:
                        logging.error(f"Error checking window state for {hwnd}: {e}")
                
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error in status monitor thread: {e}")
                time.sleep(1)
    
    def update_client_status(self, hwnd, is_minimized):
        """Update client status indicator"""
        try:
            with self.client_lock:
                if hwnd not in self.clients:
                    return
                status_ind = self.clients[hwnd]["status_indicator"]
            
            color = "#00ff00" if is_minimized else "#ff4444"
            status_ind.delete("all")
            status_ind.create_oval(2, 2, 8, 8, fill=color, outline="")
        except Exception as e:
            logging.error(f"Error updating status for {hwnd}: {e}")
    
    def move_client(self, hwnd, direction):
        with self.client_lock:
            if hwnd not in self.clients:
                return
            
            current_pos = self.clients[hwnd]["position"]
            new_pos = current_pos + direction
            
            if new_pos < 0 or new_pos >= len(self.clients):
                return
            
            target_hwnd = None
            for check_hwnd, client_data in self.clients.items():
                if client_data["position"] == new_pos:
                    target_hwnd = check_hwnd
                    break
            
            if target_hwnd:
                self.clients[hwnd]["position"] = new_pos
                self.clients[target_hwnd]["position"] = current_pos
        
        self.reorganize_grid()
    
    def remove_client(self, hwnd):
        with self.client_lock:
            if hwnd in self.clients:
                self.clients[hwnd]["frame"].destroy()
                del self.clients[hwnd]
                
                for idx, (client_hwnd, client_data) in enumerate(sorted(self.clients.items(), key=lambda x: x[1]["position"])):
                    client_data["position"] = idx
        
        with self.expanded_lock:
            self.expanded_windows.discard(hwnd)
            self.paused_clients.discard(hwnd)
        
        self.reorganize_grid()
        logging.info(f"Removed client hwnd: {hwnd}")
    
    def expand_pip(self, hwnd):
        def expand_async():
            if not win32gui.IsWindow(hwnd):
                self.queue_ui_update(messagebox.showerror, "Error", "Window no longer exists!")
                return
            
            try:
                with self.client_lock:
                    if hwnd not in self.clients:
                        return
                    window_title = self.clients[hwnd]["title"]
                
                is_dreambot = "DreamBot" in window_title
                
                with self.expanded_lock:
                    self.expanded_windows.add(hwnd)
                    if is_dreambot:
                        self.paused_clients.add(hwnd)
                
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.3)
                
                for attempt in range(3):
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                        win32gui.BringWindowToTop(hwnd)
                        win32gui.SetForegroundWindow(hwnd)
                        
                        time.sleep(0.15)
                        if win32gui.GetForegroundWindow() == hwnd:
                            break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        time.sleep(0.2)
                
            except Exception as e:
                logging.error(f"Error bringing window to front: {e}")
                with self.expanded_lock:
                    self.paused_clients.discard(hwnd)
                    self.expanded_windows.discard(hwnd)
        
        thread = threading.Thread(target=expand_async, daemon=True)
        thread.start()
    
    def monitor_expanded_windows(self):
        last_foreground = None
        
        while self.running:
            try:
                if not self.auto_minimize_var.get():
                    time.sleep(0.5)
                    continue
                
                with self.expanded_lock:
                    expanded_copy = self.expanded_windows.copy()
                
                if expanded_copy:
                    try:
                        current_foreground = win32gui.GetForegroundWindow()
                    except:
                        current_foreground = None
                    
                    if current_foreground != last_foreground:
                        for hwnd in expanded_copy:
                            if hwnd == current_foreground:
                                continue
                            
                            if not win32gui.IsWindow(hwnd):
                                with self.expanded_lock:
                                    self.expanded_windows.discard(hwnd)
                                    self.paused_clients.discard(hwnd)
                                continue
                            
                            try:
                                if not win32gui.IsIconic(hwnd):
                                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                                
                                with self.expanded_lock:
                                    self.expanded_windows.discard(hwnd)
                                    self.paused_clients.discard(hwnd)
                                    
                            except Exception as e:
                                with self.expanded_lock:
                                    self.expanded_windows.discard(hwnd)
                                    self.paused_clients.discard(hwnd)
                        
                        last_foreground = current_foreground
                
                time.sleep(0.3)
                
            except Exception as e:
                logging.error(f"Error in monitor thread: {e}")
                time.sleep(0.5)
    
    def reorganize_grid(self):
        with self.client_lock:
            sorted_clients = sorted(self.clients.items(), key=lambda x: x[1]["position"])
            
            for index, (hwnd, client_data) in enumerate(sorted_clients):
                row = index // self.grid_columns
                col = index % self.grid_columns
                
                client_data["frame"].grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
                client_data["title_label"].configure(text=f"#{index + 1} {client_data['title']}")
                client_data["row"] = row
                client_data["col"] = col
                client_data["position"] = index
                
                # Update column configuration
                self.scrollable_frame.grid_columnconfigure(col, weight=1, minsize=self.current_thumbnail_size[0] + 30)
    
    def capture_window(self, hwnd):
        try:
            window_rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = window_rect
            window_width = right - left
            window_height = bottom - top
            
            if window_width <= 0 or window_height <= 0:
                return None
            
            try:
                client_rect = win32gui.GetClientRect(hwnd)
                client_width = client_rect[2]
                client_height = client_rect[3]
                
                client_to_screen = win32gui.ClientToScreen(hwnd, (0, 0))
                offset_x = client_to_screen[0] - left
                offset_y = client_to_screen[1] - top
                
                if client_width < window_width - 10 or client_height < window_height - 10:
                    capture_width = client_width
                    capture_height = client_height
                    use_offset = True
                else:
                    capture_width = window_width
                    capture_height = window_height
                    use_offset = False
                    offset_x = 0
                    offset_y = 0
            except:
                capture_width = window_width
                capture_height = window_height
                use_offset = False
                offset_x = 0
                offset_y = 0
            
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, window_width, window_height)
            saveDC.SelectObject(saveBitMap)
            
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
            
            img = None
            
            if result == 1:
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                
                if use_offset and offset_x > 0 and offset_y > 0:
                    try:
                        img = img.crop((offset_x, offset_y, offset_x + capture_width, offset_y + capture_height))
                    except:
                        pass
                
                thumb_size = self.current_thumbnail_size
                img = img.resize(thumb_size, Image.LANCZOS)
            
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return img
            
        except Exception as e:
            logging.error(f"Error capturing window {hwnd}: {e}")
            return None
    
    def capture_loop(self):
        while self.running:
            if not self.paused:
                with self.client_lock:
                    has_clients = len(self.clients) > 0
                
                if has_clients:
                    start_time = time.time()
                    
                    try:
                        foreground_hwnd = win32gui.GetForegroundWindow()
                        with self.expanded_lock:
                            paused_copy = self.paused_clients.copy()
                        
                        for hwnd in paused_copy:
                            if hwnd != foreground_hwnd:
                                with self.expanded_lock:
                                    self.paused_clients.discard(hwnd)
                    except Exception as e:
                        logging.error(f"Error checking foreground: {e}")
                    
                    with self.client_lock:
                        clients_copy = list(self.clients.keys())
                    
                    for hwnd in clients_copy:
                        with self.expanded_lock:
                            if hwnd in self.paused_clients:
                                continue
                        
                        if not win32gui.IsWindow(hwnd):
                            self.queue_ui_update(self.remove_client, hwnd)
                            continue
                        
                        with self.client_lock:
                            if hwnd not in self.clients:
                                continue
                            current_time = time.time()
                            last_update = self.clients[hwnd].get("last_update", 0)
                        
                        time_since_update = current_time - last_update
                        should_capture = time_since_update > 0.5
                        
                        if should_capture:
                            img = self.capture_window(hwnd)
                            
                            if img:
                                try:
                                    photo = ImageTk.PhotoImage(img)
                                    with self.client_lock:
                                        if hwnd in self.clients:
                                            self.clients[hwnd]["photo"] = photo
                                            self.clients[hwnd]["last_update"] = current_time
                                    self.queue_ui_update(self.update_client_image, hwnd, photo)
                                except Exception as e:
                                    logging.error(f"Error creating PhotoImage: {e}")
                    
                    elapsed = time.time() - start_time
                    target_delay = 1.0 / self.fps
                    sleep_time = max(0, target_delay - elapsed)
                    time.sleep(sleep_time)
                else:
                    time.sleep(0.1)
            else:
                time.sleep(0.1)
    
    def update_client_image(self, hwnd, photo):
        try:
            with self.client_lock:
                if hwnd not in self.clients:
                    return
                label = self.clients[hwnd]["label"]
            
            label.configure(image=photo)
            label.image = photo
        except Exception as e:
            logging.error(f"Error updating image for {hwnd}: {e}")
    
    def toggle_movie_mode(self):
        self.movie_mode = self.movie_mode_var.get()
        if self.movie_mode:
            self.fps = 5
            self.status_label.configure(text="Movie Mode", fg="#FFA500")
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 10, 10, fill="#FFA500", outline="")
        else:
            self.fps = 20
            self.status_label.configure(text="Active", fg="#00ff00")
            self.status_dot.delete("all")
            self.status_dot.create_oval(2, 2, 10, 10, fill="#00ff00", outline="")
    
    def show_settings_dialog(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("600x650")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        
        header = tk.Label(
            dialog,
            text="⚙️ Settings",
            font=("Segoe UI", 20, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        header.pack(pady=(20, 10), padx=20)
        
        content = tk.Frame(dialog, bg=self.card_bg)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Theme Selection
        theme_frame = tk.Frame(content, bg=self.card_bg)
        theme_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            theme_frame,
            text="Theme",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        ).pack(anchor="w", pady=(0, 10))
        
        theme_buttons = tk.Frame(theme_frame, bg=self.card_bg)
        theme_buttons.pack(anchor="w")
        
        selected_theme = {"current": self.current_theme}
        
        def set_theme(theme):
            selected_theme["current"] = theme
            save_setting("theme", theme)
            # Update button colors
            if theme == "dark":
                dark_btn.bg = self.accent_color
                dark_btn.hover_bg = self.accent_color
                light_btn.bg = self.button_bg
                light_btn.hover_bg = self.button_hover
            else:
                light_btn.bg = self.accent_color
                light_btn.hover_bg = self.accent_color
                dark_btn.bg = self.button_bg
                dark_btn.hover_bg = self.button_hover
            dark_btn.draw()
            light_btn.draw()
        
        dark_btn_bg = self.accent_color if selected_theme["current"] == "dark" else self.button_bg
        light_btn_bg = self.accent_color if selected_theme["current"] == "light" else self.button_bg
        dark_btn_fg = "white"
        light_btn_fg = self.button_text
        
        dark_btn = ModernButton(theme_buttons, "🌙 Dark", lambda: set_theme("dark"),
                    bg=dark_btn_bg,
                    fg=dark_btn_fg,
                    hover_bg=self.button_hover,
                    width=100)
        dark_btn.pack(side=tk.LEFT, padx=5)
        
        light_btn = ModernButton(theme_buttons, "☀️ Light", lambda: set_theme("light"),
                    bg=light_btn_bg,
                    fg=light_btn_fg,
                    hover_bg=self.button_hover,
                    width=100)
        light_btn.pack(side=tk.LEFT, padx=5)
        
        # Accent Color
        accent_frame = tk.Frame(content, bg=self.card_bg)
        accent_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            accent_frame,
            text="Accent Color",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        ).pack(anchor="w", pady=(0, 10))
        
        color_preview = tk.Frame(accent_frame, bg=self.accent_color, width=30, height=30)
        color_preview.pack(anchor="w", pady=(0, 10))
        
        def choose_accent_color():
            color = colorchooser.askcolor(title="Choose Accent Color", initialcolor=self.accent_color)
            if color[1]:
                self.accent_color = color[1]
                save_setting("accent_color", self.accent_color)
                color_preview.configure(bg=self.accent_color)
        
        ModernButton(accent_frame, "🎨 Choose Color", choose_accent_color, bg=self.accent_color, width=150).pack(anchor="w")
        
        # Grid Columns (max 5)
        grid_frame = tk.Frame(content, bg=self.card_bg)
        grid_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(
            grid_frame,
            text="Grid Columns",
            font=("Segoe UI", 12, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        ).pack(anchor="w", pady=(0, 10))
        
        grid_desc = tk.Label(
            grid_frame,
            text="Thumbnail size automatically adjusts to fit the selected grid layout",
            font=("Segoe UI", 9),
            fg=self.text_secondary,
            bg=self.card_bg,
            wraplength=500,
            justify=tk.LEFT
        )
        grid_desc.pack(anchor="w", pady=(0, 10))
        
        grid_value_label = tk.Label(
            grid_frame,
            text=f"{self.grid_columns} columns",
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        )
        grid_value_label.pack(anchor="w", pady=(0, 5))
        
        def on_grid_change(val):
            self.grid_columns = int(float(val))
            grid_value_label.configure(text=f"{self.grid_columns} columns")
            save_setting("grid_columns", self.grid_columns)
        
        grid_slider = tk.Scale(
            grid_frame,
            from_=3,
            to=5,  # Changed from 6 to 5
            orient=tk.HORIZONTAL,
            command=on_grid_change,
            bg=self.card_bg,
            fg=self.text_color,
            highlightthickness=0,
            length=300,
            troughcolor=self.text_secondary
        )
        grid_slider.set(self.grid_columns)
        grid_slider.pack(anchor="w")
        
        # Apply and Close buttons
        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=20)
        
        def apply_and_close():
            # Save the selected theme from the dialog
            self.current_theme = selected_theme["current"]
            save_setting("theme", self.current_theme)
            
            dialog.destroy()  # Close dialog first
            self.calculate_thumbnail_size()
            self.reorganize_grid()
            self.apply_theme()  # Apply theme which recreates all cards
        
        ModernButton(btn_frame, "Apply & Close", apply_and_close, bg=self.accent_color, width=150).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, "Close", dialog.destroy, bg=self.button_bg, hover_bg=self.button_hover, fg=self.button_text, width=100).pack(side=tk.LEFT, padx=5)
    
    def open_chatgpt(self):
        """Open ChatGPT in the default web browser"""
        webbrowser.open("https://chatgpt.com")
        
    def show_help_dialog(self):
        """Show help dialog with features and tips"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Help & Features")
        dialog.geometry("700x600")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.root)
        
        header = tk.Label(
            dialog,
            text="❓ Help & Features",
            font=("Segoe UI", 20, "bold"),
            fg=self.text_color,
            bg=self.bg_color
        )
        header.pack(pady=(20, 10), padx=20)
        
        help_frame = tk.Frame(dialog, bg=self.card_bg)
        help_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        help_canvas = tk.Canvas(help_frame, bg=self.card_bg, highlightthickness=0)
        help_scrollbar = tk.Scrollbar(help_frame, orient="vertical", command=help_canvas.yview)
        help_scrollable = tk.Frame(help_canvas, bg=self.card_bg)
        
        help_scrollable.bind(
            "<Configure>",
            lambda e: help_canvas.configure(scrollregion=help_canvas.bbox("all"))
        )
        
        help_canvas.create_window((0, 0), window=help_scrollable, anchor="nw")
        help_canvas.configure(yscrollcommand=help_scrollbar.set)
        
        def _on_mousewheel(event):
            help_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        help_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        dialog.bind("<Destroy>", lambda e: help_canvas.unbind_all("<MouseWheel>"))
        
        help_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=15, pady=15)
        help_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=15, padx=(0, 15))
        
        help_sections = [
            ("🪟 Adding Windows", 
             "Click '＋ Add Window' to select any open window to monitor. The window will appear as a live thumbnail that updates automatically."),
            ("👆 Click to Expand", 
             "Click on any thumbnail to bring that window to the front and restore it if minimized."),
            ("🔴🟢 Status Indicators", 
             "Each window has a colored dot below the thumbnail:\n• Green = Window is minimized (low resource usage)\n• Red = Window is active/not minimized (high resource usage)"),
            ("📊 CPU Usage", 
             "Each thumbnail shows real-time CPU usage percentage in the top-right corner."),
            ("⚙️ Settings", 
             "Customize themes (Dark/Light), accent colors, and grid layout (3-5 columns). Thumbnail size automatically adjusts to fit your screen!"),
            ("🖥️ Auto-Sizing", 
             "The app automatically calculates the perfect thumbnail size for your screen resolution and grid layout."),
            ("⚡ Auto-Minimize", 
             "When enabled, windows you click to expand will automatically minimize when you click away from them."),
            ("🎬 Movie Mode", 
             "Reduces the capture frame rate to 5 FPS (from 20 FPS) to save CPU resources."),
        ]
        
        for i, (section_title, description) in enumerate(help_sections):
            section_frame = tk.Frame(help_scrollable, bg=self.card_bg)
            section_frame.pack(fill=tk.X, pady=8, padx=15)
            
            title_label = tk.Label(
                section_frame,
                text=section_title,
                font=("Segoe UI", 11, "bold"),
                fg=self.text_color,
                bg=self.card_bg,
                anchor="w",
                justify=tk.LEFT
            )
            title_label.pack(fill=tk.X, pady=(0, 5))
            
            desc_label = tk.Label(
                section_frame,
                text=description,
                font=("Segoe UI", 10),
                fg=self.text_secondary,
                bg=self.card_bg,
                anchor="w",
                justify=tk.LEFT,
                wraplength=600
            )
            desc_label.pack(fill=tk.X, padx=(15, 0))
            
            if i < len(help_sections) - 1:
                separator_color = "#444444" if self.current_theme == "dark" else "#dddddd"
                separator = tk.Frame(help_scrollable, bg=separator_color, height=1)
                separator.pack(fill=tk.X, pady=10, padx=15)
        
        btn_frame = tk.Frame(dialog, bg=self.bg_color)
        btn_frame.pack(pady=(0, 20))
        ModernButton(btn_frame, "Close", dialog.destroy, bg=self.accent_color, width=120).pack()
    
    def toggle_debug_panel(self):
        """Toggle the debug panel visibility"""
        if self.debug_panel_visible:
            if self.debug_panel:
                self.debug_panel.destroy()
                self.debug_panel = None
            self.debug_panel_visible = False
        else:
            self.show_debug_panel()
            self.debug_panel_visible = True
    
    def show_debug_panel(self):
        """Show the debug panel overlay"""
        self.debug_panel = tk.Toplevel(self.root)
        self.debug_panel.title("Debug Panel")
        self.debug_panel.geometry("600x400")
        self.debug_panel.configure(bg=self.bg_color)
        
        self.debug_panel.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - 620
        y = screen_height - 450
        self.debug_panel.geometry(f"600x400+{x}+{y}")
        
        self.debug_panel.attributes('-topmost', True)
        
        def on_close():
            self.debug_panel_visible = False
            self.debug_panel.destroy()
            self.debug_panel = None
        
        self.debug_panel.protocol("WM_DELETE_WINDOW", on_close)
        
        header = tk.Frame(self.debug_panel, bg=self.card_bg, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="🐛 Debug Panel",
            font=("Segoe UI", 14, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        close_btn = tk.Label(
            header,
            text="✕",
            font=("Segoe UI", 16),
            fg="#ff4444",
            bg=self.card_bg,
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT, padx=20)
        close_btn.bind("<Button-1>", lambda e: on_close())
        
        tab_frame = tk.Frame(self.debug_panel, bg=self.bg_color)
        tab_frame.pack(fill=tk.X)
        
        content_frame = tk.Frame(self.debug_panel, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        logs_content = tk.Frame(content_frame, bg=self.bg_color)
        version_content = tk.Frame(content_frame, bg=self.bg_color)
        
        current_tab = {"name": "logs"}
        
        def show_tab(tab_name):
            logs_content.pack_forget()
            version_content.pack_forget()
            
            if tab_name == "logs":
                logs_content.pack(fill=tk.BOTH, expand=True)
                logs_btn.configure(bg=self.accent_color)
                version_btn.configure(bg=self.card_bg)
            else:
                version_content.pack(fill=tk.BOTH, expand=True)
                version_btn.configure(bg=self.accent_color)
                logs_btn.configure(bg=self.card_bg)
            
            current_tab["name"] = tab_name
        
        logs_btn = tk.Label(
            tab_frame,
            text="📋 Logs",
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.accent_color,
            cursor="hand2",
            padx=20,
            pady=10
        )
        logs_btn.pack(side=tk.LEFT)
        logs_btn.bind("<Button-1>", lambda e: show_tab("logs"))
        
        version_btn = tk.Label(
            tab_frame,
            text="ℹ️ Version",
            font=("Segoe UI", 10, "bold"),
            fg=self.text_color,
            bg=self.card_bg,
            cursor="hand2",
            padx=20,
            pady=10
        )
        version_btn.pack(side=tk.LEFT)
        version_btn.bind("<Button-1>", lambda e: show_tab("version"))
        
        logs_scroll_frame = tk.Frame(logs_content, bg=self.card_bg)
        logs_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        log_text_color = "#cccccc" if self.current_theme == "dark" else "#333333"
        
        logs_text = tk.Text(
            logs_scroll_frame,
            bg=self.card_bg,
            fg=log_text_color,
            font=("Consolas", 9),
            wrap=tk.WORD,
            relief="flat",
            padx=10,
            pady=10
        )
        logs_scrollbar = tk.Scrollbar(logs_scroll_frame, command=logs_text.yview)
        logs_text.configure(yscrollcommand=logs_scrollbar.set)
        
        logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        global IN_MEMORY_LOGS
        for log_entry in IN_MEMORY_LOGS:
            logs_text.insert(tk.END, log_entry + "\n")
        
        logs_text.configure(state=tk.DISABLED)
        logs_text.see(tk.END)
        
        version_info_frame = tk.Frame(version_content, bg=self.card_bg)
        version_info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        current_ver = get_current_version()
        version_text = current_ver if current_ver else "Unknown"
        
        version_label = tk.Label(
            version_info_frame,
            text=f"Current Version: {version_text}",
            font=("Segoe UI", 14, "bold"),
            fg=self.text_color,
            bg=self.card_bg
        )
        version_label.pack(pady=(20, 10))
        
        repo_label = tk.Label(
            version_info_frame,
            text=f"Repository: {GITHUB_REPO}",
            font=("Segoe UI", 10),
            fg=self.text_secondary,
            bg=self.card_bg
        )
        repo_label.pack(pady=5)
        
        update_btn_frame = tk.Frame(version_info_frame, bg=self.card_bg)
        update_btn_frame.pack(pady=20)
        
        ModernButton(
            update_btn_frame,
            "Check for Updates",
            lambda: check_for_updates(show_no_update_message=True),
            bg=self.accent_color,
            width=200
        ).pack()
        
        show_tab("logs")
        
        def refresh_logs():
            if self.debug_panel and self.debug_panel.winfo_exists() and current_tab["name"] == "logs":
                try:
                    logs_text.configure(state=tk.NORMAL)
                    logs_text.delete("1.0", tk.END)
                    for log_entry in IN_MEMORY_LOGS:
                        logs_text.insert(tk.END, log_entry + "\n")
                    logs_text.configure(state=tk.DISABLED)
                    logs_text.see(tk.END)
                    self.debug_panel.after(2000, refresh_logs)
                except:
                    pass
        
        self.debug_panel.after(2000, refresh_logs)
    
    def on_closing(self):
        logging.info("Shutting down Multi-Client Viewer")
        # Save position one final time before closing
        self._save_window_position()
        self.running = False
        time.sleep(0.5)
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        logging.info("Starting Multi-Client Viewer")
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = PiPBoard()
        app.run()
    except Exception as e:
        logging.critical(f"Critical error: {e}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
