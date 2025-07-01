#!/usr/bin/env python3
"""
Todo Editor Module - GUI Component
Lightweight desktop todo editor with system tray integration
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, font, messagebox
import threading
import subprocess
import json
from pathlib import Path
from datetime import datetime
# Utility to create application icon
from create_icon import create_app_icon

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    print("Required packages not found. Please run: python todo_app.py setup")
    sys.exit(1)

class TodoEditor:
    """Main todo editor window and system tray integration"""
    
    def __init__(self, todo_file="todo.txt", config=None, start_minimized=False):
        self.todo_file = Path(todo_file)
        self.config = config or {}
        self.start_minimized = start_minimized
        self.window = None
        self.icon = None
        self.running = True
        self.wallpaper_process = None
        
        self.editor_config = self.config.get('editor', {})
        self.wallpaper_config = self.config.get('wallpaper', {})
        self.app_config = self.config.get('app', {})
        
        dark = self.editor_config.get('dark_mode', True)
        self.colors = {
            'bg': '#1e1e1e' if dark else '#f0f0f0',
            'fg': '#ffffff' if dark else '#000000',
            'select_bg': '#264f78' if dark else '#0078d4',
            'button_bg': '#007acc' if dark else '#0078d4',
            'button_hover': '#1a8ccc' if dark else '#106ebe',
            'entry_bg': '#2d2d2d' if dark else '#ffffff',
            'complete': '#808080' if dark else '#666666',
            'incomplete': '#ffffff' if dark else '#000000',
            'border': '#3e3e3e' if dark else '#cccccc',
            'delete': '#ff4444' if dark else '#d13438',
            'delete_hover': '#ff6666' if dark else '#e81123'
        }
    
    def manage_wallpaper(self, action='check'):
        """Manage wallpaper subprocess"""
        if not self.app_config.get('enable_wallpaper', True):
            return
        
        actions = {
            'start': lambda: self._start_wallpaper(),
            'stop': lambda: self._stop_wallpaper(),
            'toggle': lambda: self._stop_wallpaper() if self._is_running() else self._start_wallpaper(),
            'check': lambda: self._is_running()
        }
        return actions.get(action, lambda: None)()
    
    def _start_wallpaper(self):
        if not self._is_running():
            try:
                script_path = Path(__file__).parent / 'todo_app.py'
                self.wallpaper_process = subprocess.Popen(
                    [sys.executable, str(script_path), 'wallpaper'],
                    cwd=Path(__file__).parent
                )
                print(f"Started wallpaper updater (PID: {self.wallpaper_process.pid})")
                return True
            except Exception as e:
                print(f"Error starting wallpaper: {e}")
        return False
    
    def _stop_wallpaper(self):
        if self._is_running():
            try:
                self.wallpaper_process.terminate()
                try:
                    self.wallpaper_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.wallpaper_process.kill()
                print("Stopped wallpaper updater")
            except Exception as e:
                print(f"Error stopping wallpaper: {e}")
            finally:
                self.wallpaper_process = None
        return False
    
    def _is_running(self):
        return self.wallpaper_process and self.wallpaper_process.poll() is None
    
    def generate_ai_wallpaper(self):
        """Generate AI wallpaper image using current todos"""
        self.set_status("Generating AI image...")
        if hasattr(self, 'ai_wallpaper_btn'):
            self.ai_wallpaper_btn.config(state='disabled', text="🎨 Generating...")
        
        def generate():
            try:
                from todo_wallpaper_module import TodoWallpaperGenerator
                temp_config = self.wallpaper_config.copy()
                temp_config['use_ai_images'] = True
                
                api_key = temp_config.get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
                if not api_key:
                    self.window.after(0, lambda: messagebox.showerror(
                        "API Key Missing",
                        "OpenAI API key not found!\n\n"
                        "Please set your API key in:\n"
                        "1. The .env file (OPENAI_API_KEY=your-key)\n"
                        "2. Or in config.json (wallpaper.openai_api_key)"
                    ))
                    return
                
                temp_config['openai_api_key'] = api_key
                generator = TodoWallpaperGenerator(temp_config)
                tasks = generator.parse_todo_file()
                
                if not tasks:
                    self.window.after(0, lambda: messagebox.showwarning(
                        "No Tasks", "No tasks found to generate an image from!"
                    ))
                    return
                
                ai_image_path = generator.generate_ai_image(tasks)
                if ai_image_path:
                    generator.last_ai_image = ai_image_path
                    generator.create_wallpaper(tasks)
                    generator.set_wallpaper()
                    self.window.after(0, lambda: self.set_status("AI wallpaper generated!"))
                    self.window.after(0, lambda: messagebox.showinfo(
                        "Success", f"AI wallpaper generated and set!\n\nImage saved to:\n{ai_image_path}"
                    ))
                else:
                    self.window.after(0, lambda: self.set_status("Failed to generate AI image"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror(
                    "Generation Error", f"Failed to generate AI wallpaper:\n{str(e)}"
                ))
            finally:
                if hasattr(self, 'ai_wallpaper_btn'):
                    self.window.after(0, lambda: self.ai_wallpaper_btn.config(
                        state='normal', text="🎨 Generate AI Wallpaper"
                    ))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def show_window(self, icon=None, item=None):
        """Show or create the editor window"""
        if self.app_config.get('enable_wallpaper', True):
            self.manage_wallpaper('start')
        
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        else:
            self.create_window()
    
    def hide_window(self):
        """Hide window to system tray"""
        if self.auto_save_var.get():
            self.save_todos()
        if self.window:
            self.window.withdraw()
    
    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        self.running = False
        self.manage_wallpaper('stop')
        if self.icon:
            self.icon.stop()
        if self.window and self.window.winfo_exists():
            self.window.quit()
            self.window.destroy()
    
    def create_window(self):
        """Create the main editor window"""
        self.window = tk.Tk()
        self.window.title("Todo List Editor")
        
        window_size = self.editor_config.get('window_size', [600, 700])
        self.window.geometry(f"{window_size[0]}x{window_size[1]}")
        self.window.minsize(400, 300)
        self.window.configure(bg=self.colors['bg'])
        
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        
        self._build_ui()
        self.todo_widgets = []
        self.load_todos()
        
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        if self.start_minimized:
            self.window.withdraw()
        else:
            self.window.focus_force()
        
        self.window.mainloop()
    
    def _build_ui(self):
        """Build the user interface"""
        container = tk.Frame(self.window, bg=self.colors['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(container, text="Todo List", bg=self.colors['bg'], 
                fg=self.colors['fg'], font=('Segoe UI', 20, 'bold')).pack(anchor='w', pady=(0, 5))
        
        tk.Label(container, text=f"Editing: {self.todo_file.absolute()}", 
                bg=self.colors['bg'], fg='#888888', font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 15))
        
        list_container = tk.Frame(container, bg=self.colors['border'])
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        inner_frame = tk.Frame(list_container, bg=self.colors['entry_bg'])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        self.canvas = tk.Canvas(inner_frame, bg=self.colors['entry_bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(inner_frame, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['entry_bg'])
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        self._create_buttons(container)
    
    def _create_button(self, parent, text, bg, command, hover=None):
        """Helper to create styled button"""
        btn = tk.Button(parent, text=text, bg=bg, fg=self.colors['fg'], relief=tk.FLAT,
                       padx=15, pady=8, font=('Segoe UI', 10), cursor='hand2',
                       activebackground=hover or bg, activeforeground=self.colors['fg'],
                       command=command)
        btn.pack(side=tk.LEFT, padx=(0, 10))
        return btn
    
    def _create_buttons(self, parent):
        """Create control buttons"""
        button_frame = tk.Frame(parent, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X)
        
        left_buttons = tk.Frame(button_frame, bg=self.colors['bg'])
        left_buttons.pack(side=tk.LEFT)
        
        self.add_btn = self._create_button(left_buttons, "➕ Add Task", self.colors['button_bg'], 
                                          self.add_task, self.colors['button_hover'])
        self.save_btn = self._create_button(left_buttons, "💾 Save", '#28a745', self.save_todos, '#34ce57')
        self.save_btn.configure(font=('Segoe UI', 10, 'bold'))
        self.reload_btn = self._create_button(left_buttons, "🔄 Reload", '#6c757d', self.load_todos, '#7d868e')
        self.reload_btn.pack(side=tk.LEFT, padx=0)
        
        second_row = tk.Frame(parent, bg=self.colors['bg'])
        second_row.pack(fill=tk.X, pady=(10, 0))
        
        left_buttons2 = tk.Frame(second_row, bg=self.colors['bg'])
        left_buttons2.pack(side=tk.LEFT)
        
        if self.app_config.get('enable_wallpaper', True):
            self.wallpaper_btn = self._create_button(left_buttons2, "🖼️ Toggle Wallpaper", '#6c757d',
                                                    self.toggle_wallpaper, '#7d868e')
            self.ai_wallpaper_btn = self._create_button(left_buttons2, "🎨 Generate AI Wallpaper", '#9b59b6',
                                                       self.generate_ai_wallpaper, '#a569c6')
            self.ai_wallpaper_btn.pack(side=tk.LEFT, padx=0)
        
        self.status_label = tk.Label(second_row, text="Ready", bg=self.colors['bg'], 
                                    fg='#888888', font=('Segoe UI', 9))
        self.status_label.pack(side=tk.RIGHT)
        
        self.auto_save_var = tk.BooleanVar(value=self.editor_config.get('auto_save', True))
        tk.Checkbutton(second_row, text="Auto-save", variable=self.auto_save_var,
                      bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['entry_bg'],
                      activebackground=self.colors['bg'], activeforeground=self.colors['fg'],
                      font=('Segoe UI', 9)).pack(side=tk.RIGHT, padx=(0, 20))
        
        if self.app_config.get('enable_wallpaper', True):
            self.wallpaper_label = tk.Label(second_row, text="🖼️ Wallpaper: OFF",
                                          bg=self.colors['bg'], fg='#ff6666', font=('Segoe UI', 9))
            self.wallpaper_label.pack(side=tk.RIGHT, padx=(10, 0))
            self.update_wallpaper_status()
    
    def toggle_wallpaper(self):
        """Toggle wallpaper on/off"""
        if self.manage_wallpaper('toggle'):
            self.set_status("Wallpaper updater started")
        else:
            self.set_status("Wallpaper updater stopped")
        self.update_wallpaper_status()
    
    def update_wallpaper_status(self):
        """Update wallpaper status indicator"""
        if hasattr(self, 'wallpaper_label'):
            is_on = self.manage_wallpaper('check')
            self.wallpaper_label.config(text=f"🖼️ Wallpaper: {'ON' if is_on else 'OFF'}", 
                                      fg='#66ff66' if is_on else '#ff6666')
        if self.window and self.window.winfo_exists():
            self.window.after(2000, self.update_wallpaper_status)
    
    def load_todos(self):
        """Load todos from file"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.todo_widgets = []
        
        if self.todo_file.exists():
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    for line in lines:
                        self.create_todo_widget(line)
                    if not lines:
                        self.add_task()
            except Exception as e:
                self.set_status(f"Error loading: {e}")
                return
        else:
            self.add_task()
        
        self.set_status("Loaded successfully")
    
    def create_todo_widget(self, line="[ ] "):
        """Create a todo item widget"""
        completed = line.startswith('[x]') or line.startswith('x ')
        if line.startswith('[x]') or line.startswith('[ ]'):
            text = line[3:].strip()
        elif line.startswith('x '):
            text = line[2:].strip()
        else:
            text = line
        
        todo_frame = tk.Frame(self.scrollable_frame, bg=self.colors['entry_bg'])
        todo_frame.pack(fill=tk.X, padx=10, pady=5)
        
        var = tk.BooleanVar(value=completed)
        check = tk.Checkbutton(todo_frame, variable=var, bg=self.colors['entry_bg'],
                              fg=self.colors['fg'], activebackground=self.colors['entry_bg'],
                              activeforeground=self.colors['fg'], selectcolor=self.colors['entry_bg'],
                              command=lambda: self.on_checkbox_change(entry, var.get()))
        check.pack(side=tk.LEFT, padx=(5, 10))
        
        font_size = self.editor_config.get('font_size', 11)
        entry = tk.Entry(todo_frame, bg=self.colors['entry_bg'],
                        fg=self.colors['complete'] if completed else self.colors['incomplete'],
                        insertbackground=self.colors['fg'], relief=tk.FLAT,
                        font=('Segoe UI', font_size, 'overstrike' if completed else 'normal'), bd=0)
        entry.insert(0, text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        entry.bind('<KeyRelease>', self.on_text_change)
        entry.bind('<Return>', lambda e: self.add_task())
        
        delete_btn = tk.Button(todo_frame, text="✕", bg=self.colors['entry_bg'],
                              fg=self.colors['delete'], activebackground=self.colors['entry_bg'],
                              activeforeground=self.colors['delete_hover'], relief=tk.FLAT,
                              font=('Segoe UI', 12), cursor='hand2', bd=0, padx=5,
                              command=lambda: self.delete_task(todo_frame))
        delete_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        self.todo_widgets.append((var, entry, todo_frame))
        
        if not text:
            entry.focus_set()
    
    def on_checkbox_change(self, entry, completed):
        """Handle checkbox state change"""
        font_size = self.editor_config.get('font_size', 11)
        entry.config(fg=self.colors['complete' if completed else 'incomplete'],
                    font=('Segoe UI', font_size, 'overstrike' if completed else 'normal'))
        if self.auto_save_var.get():
            self.window.after(500, self.save_todos)
    
    def on_text_change(self, event=None):
        """Handle text change for auto-save"""
        if self.auto_save_var.get():
            if hasattr(self, '_save_timer'):
                self.window.after_cancel(self._save_timer)
            self._save_timer = self.window.after(1000, self.save_todos)
    
    def add_task(self):
        """Add a new task"""
        self.create_todo_widget("[ ] ")
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)
        self.set_status("Task added")
    
    def delete_task(self, frame):
        """Delete a task"""
        self.todo_widgets = [(v, e, f) for v, e, f in self.todo_widgets if f != frame]
        frame.destroy()
        
        if not self.todo_widgets:
            self.add_task()
        
        if self.auto_save_var.get():
            self.window.after(100, self.save_todos)
        else:
            self.set_status("Task deleted (unsaved)")
    
    def save_todos(self):
        """Save todos to file"""
        try:
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                for var, entry, _ in self.todo_widgets:
                    text = entry.get().strip()
                    if text:
                        f.write(f"[{'x' if var.get() else ' '}] {text}\n")
            
            self.set_status(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
            
            original_bg = self.save_btn['bg']
            self.save_btn.config(bg='#5cb85c')
            self.window.after(200, lambda: self.save_btn.config(bg=original_bg))
        except Exception as e:
            self.set_status(f"Error saving: {e}")
    
    def set_status(self, text):
        """Update status label"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=text)
    
    def run(self):
        """Start the application"""
        if self.app_config.get('enable_wallpaper', True) and not self.start_minimized:
            self.manage_wallpaper('start')
        
        threading.Thread(target=self._run_tray, daemon=True).start()
        self.show_window()
    
    def _run_tray(self):
        """Run system tray icon"""
        menu = pystray.Menu(
            pystray.MenuItem("Open", self.show_window, default=True),
            pystray.MenuItem("Quit", self.quit_app)
        )
        self.icon = pystray.Icon("todo_editor", create_app_icon(64), "Todo Editor", menu)
        self.icon.run()