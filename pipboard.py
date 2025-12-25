"""
Multi-Client Viewer - Modern Multi-Client Picture-in-Picture Viewer
Features:
- Modern UI with rounded corners and smooth animations
- Dark mode with gradient backgrounds
- Drag and drop to rearrange clients
- Click to expand, filter added windows, visible dialog buttons
- AUTO-MINIMIZE: Automatically minimizes expanded clients when you click away
- Client status indicators (Green=Minimized/Low CPU, Red=Active/High CPU)
- Thread-safe with proper locking mechanisms
- No admin rights required
- Auto-update functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageGrab, ImageTk, ImageDraw
import win32gui
import win32con
import win32ui
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

import webbrowser

GITHUB_REPO = "BabyTank-Projects/MultiClientViewer"

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
    """Check for updates and download if available"""
    release_info = get_latest_release()
    
    if not release_info:
        if show_no_update_message:
            messagebox.showinfo("Update Check", "Unable to check for updates. Please try again later.")
        return
    
    latest_version = release_info.get('tag_name', '').lstrip('v')
    
    if not latest_version:
        if show_no_update_message:
            messagebox.showinfo("Update Check", "No version information available.")
        return
    
    # Get download URL for the .exe file
    download_url = None
    for asset in release_info.get('assets', []):
        if asset['name'].endswith('.exe'):
            download_url = asset['browser_download_url']
            break
    
    if not download_url:
        if show_no_update_message:
            messagebox.showinfo("Update Check", "No executable found in the latest release.")
        return
    
    # Always show update available (since we removed version comparison)
    result = messagebox.askyesno(
        "Update Available",
        f"A new version ({latest_version}) is available!\n\n"
        "Would you like to download and install it now?\n\n"
        "The application will close and restart automatically.",
        icon='info'
    )
    
    if result:
        download_and_install_update(download_url)

def download_and_install_update(download_url):
    """Download and install the update"""
    try:
        # Show progress dialog
        progress_window = tk.Toplevel()
        progress_window.title("Downloading Update")
        progress_window.geometry("400x150")
        progress_window.transient()
        progress_window.grab_set()
        
        tk.Label(
            progress_window,
            text="Downloading update...",
            font=("Segoe UI", 12)
        ).pack(pady=20)
        
        progress_bar = ttk.Progressbar(
            progress_window,
            length=350,
            mode='indeterminate'
        )
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        status_label = tk.Label(progress_window, text="Please wait...")
        status_label.pack(pady=10)
        
        def download():
            try:
                # Download the new version
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()
                
                # Get current executable path
                current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
                exe_dir = os.path.dirname(os.path.abspath(current_exe))
                exe_name = os.path.basename(current_exe)
                
                # Save to temp file first
                temp_exe = os.path.join(tempfile.gettempdir(), 'multiclientviewer_update.exe')
                
                with open(temp_exe, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                progress_window.destroy()
                
                # Create a batch script to replace the old exe and restart
                batch_script = f'''@echo off
timeout /t 2 /nobreak > nul
del /f /q "{current_exe}.old" 2>nul
move /y "{current_exe}" "{current_exe}.old"
move /y "{temp_exe}" "{current_exe}"
del /f /q "{current_exe}.old" 2>nul
start "" "{current_exe}"
del "%~f0"
'''
                
                batch_file = os.path.join(tempfile.gettempdir(), 'update_multiclientviewer.bat')
                with open(batch_file, 'w') as f:
                    f.write(batch_script)
                
                # Start the batch script and exit
                subprocess.Popen(batch_file, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                # Close the application
                os._exit(0)
                
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Update Failed", f"Failed to install update: {str(e)}")
        
        # Run download in separate thread
        thread = threading.Thread(target=download, daemon=True)
        thread.start()
        
    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to download update: {str(e)}")

def check_updates_on_startup():
    """Check for updates in background thread on startup"""
    def bg_check():
        check_for_updates(show_no_update_message=False)
    
    thread = threading.Thread(target=bg_check, daemon=True)
    thread.start()

def setup_logging():
    """Setup logging with fallback if file is locked"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    
    try:
        handler = RotatingFileHandler(
            'pipboard.log',
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except PermissionError:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
    
    return logger

setup_logging()

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
        self.configure(bg=self.master['bg'])
        
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
    def __init__(self, parent, text, variable, command=None, **kwargs):
        super().__init__(parent, bg=parent['bg'], **kwargs)
        self.variable = variable
        self.command = command
        self.text = text
        self.bg_color = parent['bg']
        
        container = tk.Frame(self, bg=self.bg_color)
        container.pack(padx=10, pady=5)
        
        self.label = tk.Label(
            container,
            text=text,
            font=("Segoe UI", 10),
            fg="white",
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
        
        bg_color = "#007AFF" if is_on else "#3a3a3a"
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
        self.root.geometry("2000x1080")
        
        self.dark_mode = True
        self.bg_dark = "#1a1a1a"
        self.bg_light = "#f5f5f5"
        self.card_bg_dark = "#2a2a2a"
        self.card_bg_light = "#ffffff"
        self.accent_color = "#007AFF"
        
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
        
        self.setup_modern_ui()
        
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.monitor_thread = threading.Thread(target=self.monitor_expanded_windows, daemon=True)
        self.monitor_thread.start()
        
        self.status_monitor_thread = threading.Thread(target=self.monitor_window_states, daemon=True)
        self.status_monitor_thread.start()
        
        # Check for updates on startup
        check_updates_on_startup()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_modern_ui(self):
        self.root.configure(bg=self.bg_dark)
        
        header = tk.Frame(self.root, bg=self.bg_dark, height=80)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header, 
            text="Multi-Client Viewer", 
            font=("Segoe UI", 24, "bold"),
            fg="white",
            bg=self.bg_dark
        )
        title_label.pack(side=tk.LEFT, padx=30, pady=20)
        
        controls = tk.Frame(header, bg=self.bg_dark)
        controls.pack(side=tk.RIGHT, padx=30, pady=20)
        
        add_btn = ModernButton(controls, "＋ Add Window", self.add_window, width=150)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Update button
        update_btn = ModernButton(controls, "🔄 Check Updates", lambda: check_for_updates(show_no_update_message=True), bg="#666666", hover_bg="#555555", width=150)
        update_btn.pack(side=tk.LEFT, padx=5)
        
        # Help button
        help_btn = ModernButton(controls, "❓ Help", self.show_help, bg="#666666", hover_bg="#555555", width=100)
        help_btn.pack(side=tk.LEFT, padx=5)
        
        # Movie Mode toggle
        self.movie_mode_var = tk.BooleanVar(value=False)
        self.movie_toggle = self.create_toggle_button(controls, "🎬 Movie Mode", self.movie_mode_var, self.toggle_movie_mode)
        self.movie_toggle.pack(side=tk.LEFT, padx=8)
        
        # Auto-minimize toggle
        self.auto_minimize_var = tk.BooleanVar(value=True)
        self.auto_toggle = self.create_toggle_button(controls, "⚡ Auto-Minimize", self.auto_minimize_var, None)
        self.auto_toggle.pack(side=tk.LEFT, padx=8)
        
        status_frame = tk.Frame(controls, bg=self.bg_dark)
        status_frame.pack(side=tk.LEFT, padx=15)
        
        self.status_dot = tk.Canvas(status_frame, width=12, height=12, bg=self.bg_dark, highlightthickness=0)
        self.status_dot.create_oval(2, 2, 10, 10, fill="#00ff00", outline="")
        self.status_dot.pack(side=tk.LEFT, padx=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Active",
            fg="#00ff00",
            bg=self.bg_dark,
            font=("Segoe UI", 10, "bold")
        )
        self.status_label.pack(side=tk.LEFT)
        
        content = tk.Frame(self.root, bg=self.bg_dark)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.canvas = tk.Canvas(content, bg=self.bg_dark, highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_dark)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_toggle_button(self, parent, text, variable, command):
        return ModernToggle(parent, text, variable, command)
        
    def create_modern_card(self, parent, title, position):
        card = tk.Frame(parent, bg=self.card_bg_dark, relief="flat", bd=0)
        
        header = tk.Frame(card, bg=self.card_bg_dark, height=40)
        header.pack(fill=tk.X, padx=15, pady=(15, 5))
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text=f"#{position} {title}",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg=self.card_bg_dark,
            anchor="w"
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        status_indicator = tk.Canvas(header, width=10, height=10, bg=self.card_bg_dark, highlightthickness=0)
        status_indicator.create_oval(2, 2, 8, 8, fill="#00ff00", outline="")
        status_indicator.pack(side=tk.RIGHT, padx=5)
        
        img_frame = tk.Frame(card, bg="#000000", relief="flat")
        img_frame.pack(padx=15, pady=5)
        
        img_container = tk.Frame(img_frame, width=320, height=240, bg="#000000")
        img_container.pack()
        img_container.pack_propagate(False)
        
        img_label = tk.Label(img_container, bg="#000000", cursor="hand2")
        img_label.pack(fill=tk.BOTH, expand=True)
        
        controls = tk.Frame(card, bg=self.card_bg_dark)
        controls.pack(fill=tk.X, padx=15, pady=(5, 15))
        
        return card, img_label, controls, title_label, status_indicator
        
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
        windows = self.get_window_list()
        
        with self.client_lock:
            available_windows = [(hwnd, title) for hwnd, title in windows if hwnd not in self.clients]
        
        if not available_windows:
            messagebox.showinfo("No Windows", "No new capturable windows found!")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Window")
        dialog.geometry("500x400")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        header = tk.Label(
            dialog,
            text="Select a window to monitor",
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg=self.bg_dark
        )
        header.pack(pady=(20, 10), padx=20)
        
        list_container = tk.Frame(dialog, bg=self.card_bg_dark)
        list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = ttk.Scrollbar(list_container)
        listbox = tk.Listbox(
            list_container,
            yscrollcommand=scrollbar.set,
            bg=self.card_bg_dark,
            fg="white",
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
        
        button_frame = tk.Frame(dialog, bg=self.bg_dark)
        button_frame.pack(pady=20)
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                hwnd, title = available_windows[selection[0]]
                self.add_client(hwnd, title)
                dialog.destroy()
        
        ModernButton(button_frame, "Add", on_select, width=120).pack(side=tk.LEFT, padx=5)
        ModernButton(button_frame, "Cancel", dialog.destroy, bg="#666666", hover_bg="#555555", width=120).pack(side=tk.LEFT, padx=5)
        
        listbox.bind('<Double-Button-1>', lambda e: on_select())
    
    def show_help(self):
        """Show help dialog explaining all features"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Multi-Client Viewer - Help")
        dialog.geometry("700x600")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = tk.Label(
            dialog,
            text="Multi-Client Viewer - Feature Guide",
            font=("Segoe UI", 20, "bold"),
            fg="white",
            bg=self.bg_dark
        )
        header.pack(pady=(20, 10), padx=20)
        
        # Scrollable content
        content_frame = tk.Frame(dialog, bg=self.bg_dark)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(content_frame, bg=self.card_bg_dark, highlightthickness=0)
        scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.card_bg_dark)
        
        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Help content
        help_sections = [
            ("🪟 Adding Windows", 
             "Click '＋ Add Window' to select any open window to monitor. The window will appear as a live thumbnail that updates automatically."),
            
            ("👆 Click to Expand", 
             "Click on any thumbnail to bring that window to the front and restore it if minimized."),
            
            ("🔴🟢 Status Indicators", 
             "Each window has a colored dot in the top-right:\n• Green = Window is minimized (low CPU usage)\n• Red = Window is active/not minimized (high CPU usage)"),
            
            ("⚡ Auto-Minimize", 
             "When enabled, windows you click to expand will automatically minimize when you click away from them. Perfect for quickly checking windows without cluttering your screen."),
            
            ("🎬 Movie Mode", 
             "Reduces the capture frame rate to 5 FPS (from 20 FPS) to save CPU resources when you don't need real-time updates."),
            
            ("↑↓ Rearrange Windows", 
             "Use the up/down arrows on each card to reorder your windows in the grid."),
            
            ("✕ Remove", 
             "Click the 'Remove' button to stop monitoring a window and remove it from the grid."),
            
            ("🔄 Auto-Update", 
             "The app automatically checks for updates on startup. Click '🔄 Check Updates' to manually check for new versions."),
            
            ("💡 Tips", 
             "• Minimize windows when not actively using them to reduce CPU usage\n• Use Movie Mode when monitoring many windows\n• The app works best with 5 windows per row\n• No admin rights required!")
        ]
        
        for i, (title, description) in enumerate(help_sections):
            section_frame = tk.Frame(scrollable, bg=self.card_bg_dark)
            section_frame.pack(fill=tk.X, padx=20, pady=10)
            
            title_label = tk.Label(
                section_frame,
                text=title,
                font=("Segoe UI", 12, "bold"),
                fg="white",
                bg=self.card_bg_dark,
                anchor="w",
                justify=tk.LEFT
            )
            title_label.pack(fill=tk.X, pady=(5, 5))
            
            desc_label = tk.Label(
                section_frame,
                text=description,
                font=("Segoe UI", 10),
                fg="#cccccc",
                bg=self.card_bg_dark,
                anchor="w",
                justify=tk.LEFT,
                wraplength=600
            )
            desc_label.pack(fill=tk.X, padx=(10, 0))
            
            if i < len(help_sections) - 1:
                separator = tk.Frame(scrollable, bg="#444444", height=1)
                separator.pack(fill=tk.X, padx=30, pady=5)
        
        # Close button
        button_frame = tk.Frame(dialog, bg=self.bg_dark)
        button_frame.pack(pady=20)
        
        ModernButton(button_frame, "Got it!", dialog.destroy, width=150).pack()
        
        
    def add_client(self, hwnd, title):
        with self.client_lock:
            if hwnd in self.clients:
                messagebox.showinfo("Already Added", f"Window '{title}' is already being monitored!")
                return
            client_count = len(self.clients)
        
        row = client_count // 5
        col = client_count % 5
        
        card, img_label, controls, title_label, status_indicator = self.create_modern_card(
            self.scrollable_frame,
            title,
            client_count + 1
        )
        
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        
        self.scrollable_frame.grid_columnconfigure(col, weight=1, minsize=360)
        self.scrollable_frame.grid_rowconfigure(row, weight=1)
        
        img_label.bind('<Button-1>', lambda e: self.expand_pip(hwnd))
        
        btn_frame = tk.Frame(controls, bg=self.card_bg_dark)
        btn_frame.pack(side=tk.LEFT)
        
        up_btn = tk.Label(btn_frame, text="↑", fg="white", bg=self.card_bg_dark, cursor="hand2", font=("Segoe UI", 12), padx=10)
        up_btn.pack(side=tk.LEFT, padx=2)
        up_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, -1))
        
        down_btn = tk.Label(btn_frame, text="↓", fg="white", bg=self.card_bg_dark, cursor="hand2", font=("Segoe UI", 12), padx=10)
        down_btn.pack(side=tk.LEFT, padx=2)
        down_btn.bind("<Button-1>", lambda e: self.move_client(hwnd, 1))
        
        remove_btn = tk.Label(controls, text="✕ Remove", fg="#ff4444", bg=self.card_bg_dark, cursor="hand2", font=("Segoe UI", 9))
        remove_btn.pack(side=tk.RIGHT)
        remove_btn.bind("<Button-1>", lambda e: self.remove_client(hwnd))
        
        with self.client_lock:
            self.clients[hwnd] = {
                "title": title,
                "frame": card,
                "label": img_label,
                "title_label": title_label,
                "status_indicator": status_indicator,
                "photo": None,
                "row": row,
                "col": col,
                "last_update": 0,
                "position": client_count,
                "is_minimized": False
            }
        
        logging.info(f"Added client: {title} (hwnd: {hwnd})")
    
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
                                    self.root.after(0, self.update_client_status, hwnd, is_minimized)
                    except Exception as e:
                        logging.error(f"Error checking window state for {hwnd}: {e}")
                
                time.sleep(0.5)
                
            except Exception as e:
                logging.error(f"Error in status monitor thread: {e}")
                time.sleep(1)
    
    def update_client_status(self, hwnd, is_minimized):
        """Update client status indicator - Green when minimized (low CPU), Red when active (high CPU)"""
        with self.client_lock:
            if hwnd in self.clients:
                status_ind = self.clients[hwnd]["status_indicator"]
        
        # Green when minimized (low CPU usage), Red when active (high CPU usage)
        color = "#00ff00" if is_minimized else "#ff4444"
        try:
            status_ind.delete("all")
            status_ind.create_oval(2, 2, 8, 8, fill=color, outline="")
        except:
            pass
    
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
        if not win32gui.IsWindow(hwnd):
            messagebox.showerror("Error", "Window no longer exists!")
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
                row = index // 5
                col = index % 5
                
                client_data["frame"].grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
                client_data["title_label"].configure(text=f"#{index + 1} {client_data['title']}")
                client_data["row"] = row
                client_data["col"] = col
                client_data["position"] = index
    
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
                
                img = img.resize((320, 240), Image.LANCZOS)
            
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
                            self.root.after(0, self.remove_client, hwnd)
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
                                    self.root.after(0, self.update_client_image, hwnd, photo)
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
        with self.client_lock:
            if hwnd in self.clients:
                try:
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
    
    def on_closing(self):
        logging.info("Shutting down Multi-Client Viewer")
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
