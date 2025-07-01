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
        
        # Get editor config
        self.editor_config = self.config.get('editor', {})
        self.wallpaper_config = self.config.get('wallpaper', {})
        self.app_config = self.config.get('app', {})
        
        # Dark mode colors
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'select_bg': '#264f78',
            'button_bg': '#007acc',
            'button_hover': '#1a8ccc',
            'entry_bg': '#2d2d2d',
            'complete': '#808080',
            'incomplete': '#ffffff',
            'border': '#3e3e3e',
            'delete': '#ff4444',
            'delete_hover': '#ff6666'
        }
        
        # Override with light mode if configured
        if not self.editor_config.get('dark_mode', True):
            self.colors = {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'select_bg': '#0078d4',
                'button_bg': '#0078d4',
                'button_hover': '#106ebe',
                'entry_bg': '#ffffff',
                'complete': '#666666',
                'incomplete': '#000000',
                'border': '#cccccc',
                'delete': '#d13438',
                'delete_hover': '#e81123'
            }
    
    def create_tray_icon(self):
        """Create system tray icon"""
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw checkbox
        draw.rectangle([10, 10, 54, 54], outline='white', width=3)
        # Draw checkmark
        draw.line([18, 32, 28, 42], fill='white', width=4)
        draw.line([28, 42, 46, 22], fill='white', width=4)
        
        return img
    
    def manage_wallpaper(self, action='check'):
        """Manage wallpaper subprocess"""
        if not self.app_config.get('enable_wallpaper', True):
            return
        
        if action == 'start':
            if self.wallpaper_process is None or self.wallpaper_process.poll() is not None:
                try:
                    script_path = Path(__file__).parent / 'todo_app.py'
                    self.wallpaper_process = subprocess.Popen(
                        [sys.executable, str(script_path), 'wallpaper'],
                        cwd=Path(__file__).parent
                    )
                    print(f"Started wallpaper updater (PID: {self.wallpaper_process.pid})")
                except Exception as e:
                    print(f"Error starting wallpaper: {e}")
        
        elif action == 'stop':
            if self.wallpaper_process and self.wallpaper_process.poll() is None:
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
        
        elif action == 'toggle':
            if self.wallpaper_process and self.wallpaper_process.poll() is None:
                self.manage_wallpaper('stop')
                return False
            else:
                self.manage_wallpaper('start')
                return True
        
        elif action == 'check':
            return self.wallpaper_process and self.wallpaper_process.poll() is None
    
    def generate_ai_wallpaper(self):
        """Generate AI wallpaper image using current todos"""
        self.set_status("Generating AI image...")
        
        # Disable button during generation
        if hasattr(self, 'ai_wallpaper_btn'):
            self.ai_wallpaper_btn.config(state='disabled', text="🎨 Generating...")
        
        def generate_in_thread():
            try:
                # Import wallpaper module
                from todo_wallpaper_module import TodoWallpaperGenerator
                
                # Create a temporary generator instance with AI enabled
                temp_config = self.wallpaper_config.copy()
                temp_config['use_ai_images'] = True
                
                # Check for API key
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
                
                # Create generator
                generator = TodoWallpaperGenerator(temp_config)
                
                # Parse current todos
                tasks = generator.parse_todo_file()
                
                if not tasks:
                    self.window.after(0, lambda: messagebox.showwarning(
                        "No Tasks",
                        "No tasks found to generate an image from!"
                    ))
                    return
                
                # Generate AI image
                ai_image_path = generator.generate_ai_image(tasks)
                
                if ai_image_path:
                    # Update wallpaper with new AI image
                    generator.last_ai_image = ai_image_path
                    generator.create_wallpaper(tasks)
                    generator.set_wallpaper()
                    
                    self.window.after(0, lambda: self.set_status("AI wallpaper generated!"))
                    self.window.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"AI wallpaper generated and set!\n\nImage saved to:\n{ai_image_path}"
                    ))
                else:
                    self.window.after(0, lambda: self.set_status("Failed to generate AI image"))
                    
            except ImportError as e:
                self.window.after(0, lambda: messagebox.showerror(
                    "Import Error",
                    f"Failed to import required modules:\n{str(e)}"
                ))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror(
                    "Generation Error",
                    f"Failed to generate AI wallpaper:\n{str(e)}"
                ))
            finally:
                # Re-enable button
                if hasattr(self, 'ai_wallpaper_btn'):
                    self.window.after(0, lambda: self.ai_wallpaper_btn.config(
                        state='normal',
                        text="🎨 Generate AI Wallpaper"
                    ))
        
        # Run in separate thread to avoid blocking UI
        thread = threading.Thread(target=generate_in_thread, daemon=True)
        thread.start()
    
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
        
        # Get window size from config
        window_size = self.editor_config.get('window_size', [600, 700])
        self.window.geometry(f"{window_size[0]}x{window_size[1]}")
        self.window.minsize(400, 300)
        
        # Configure theme
        self.window.configure(bg=self.colors['bg'])
        
        # Configure font
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10)
        
        # Build UI
        self._build_ui()
        
        # Load todos
        self.todo_widgets = []
        self.load_todos()
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Center window on screen
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Start minimized if requested
        if self.start_minimized:
            self.window.withdraw()
        else:
            self.window.focus_force()
        
        self.window.mainloop()
    
    def _build_ui(self):
        """Build the user interface"""
        # Main container
        container = tk.Frame(self.window, bg=self.colors['bg'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            container,
            text="Todo List",
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            font=('Segoe UI', 20, 'bold')
        )
        title_label.pack(anchor='w', pady=(0, 5))
        
        # Subtitle
        subtitle_label = tk.Label(
            container,
            text=f"Editing: {self.todo_file.absolute()}",
            bg=self.colors['bg'],
            fg='#888888',
            font=('Segoe UI', 9)
        )
        subtitle_label.pack(anchor='w', pady=(0, 15))
        
        # Todo list container
        list_container = tk.Frame(container, bg=self.colors['border'])
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        inner_frame = tk.Frame(list_container, bg=self.colors['entry_bg'])
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Scrollable canvas
        self.canvas = tk.Canvas(inner_frame, bg=self.colors['entry_bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(inner_frame, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors['entry_bg'])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind events
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Button frame
        self._create_buttons(container)
    
    def _create_buttons(self, parent):
        """Create control buttons"""
        button_frame = tk.Frame(parent, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X)
        
        # Left side buttons
        left_buttons = tk.Frame(button_frame, bg=self.colors['bg'])
        left_buttons.pack(side=tk.LEFT)
        
        # Add task button
        self.add_btn = tk.Button(
            left_buttons,
            text="➕ Add Task",
            bg=self.colors['button_bg'],
            fg=self.colors['fg'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            font=('Segoe UI', 10),
            cursor='hand2',
            activebackground=self.colors['button_hover'],
            activeforeground=self.colors['fg'],
            command=self.add_task
        )
        self.add_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Save button
        self.save_btn = tk.Button(
            left_buttons,
            text="💾 Save",
            bg='#28a745',
            fg=self.colors['fg'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            font=('Segoe UI', 10, 'bold'),
            cursor='hand2',
            activebackground='#34ce57',
            activeforeground=self.colors['fg'],
            command=self.save_todos
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reload button
        self.reload_btn = tk.Button(
            left_buttons,
            text="🔄 Reload",
            bg='#6c757d',
            fg=self.colors['fg'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            font=('Segoe UI', 10),
            cursor='hand2',
            activebackground='#7d868e',
            activeforeground=self.colors['fg'],
            command=self.load_todos
        )
        self.reload_btn.pack(side=tk.LEFT)
        
        # Second row of buttons
        second_row = tk.Frame(parent, bg=self.colors['bg'])
        second_row.pack(fill=tk.X, pady=(10, 0))
        
        left_buttons2 = tk.Frame(second_row, bg=self.colors['bg'])
        left_buttons2.pack(side=tk.LEFT)
        
        # Wallpaper toggle (if enabled)
        if self.app_config.get('enable_wallpaper', True):
            self.wallpaper_btn = tk.Button(
                left_buttons2,
                text="🖼️ Toggle Wallpaper",
                bg='#6c757d',
                fg=self.colors['fg'],
                relief=tk.FLAT,
                padx=15,
                pady=8,
                font=('Segoe UI', 10),
                cursor='hand2',
                activebackground='#7d868e',
                activeforeground=self.colors['fg'],
                command=self.toggle_wallpaper
            )
            self.wallpaper_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # AI Wallpaper button
            self.ai_wallpaper_btn = tk.Button(
                left_buttons2,
                text="🎨 Generate AI Wallpaper",
                bg='#9b59b6',
                fg=self.colors['fg'],
                relief=tk.FLAT,
                padx=15,
                pady=8,
                font=('Segoe UI', 10),
                cursor='hand2',
                activebackground='#a569c6',
                activeforeground=self.colors['fg'],
                command=self.generate_ai_wallpaper
            )
            self.ai_wallpaper_btn.pack(side=tk.LEFT)
        
        # Right side elements
        self.status_label = tk.Label(
            second_row,
            text="Ready",
            bg=self.colors['bg'],
            fg='#888888',
            font=('Segoe UI', 9)
        )
        self.status_label.pack(side=tk.RIGHT)
        
        # Auto-save checkbox
        self.auto_save_var = tk.BooleanVar(value=self.editor_config.get('auto_save', True))
        auto_save_check = tk.Checkbutton(
            second_row,
            text="Auto-save",
            variable=self.auto_save_var,
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            selectcolor=self.colors['entry_bg'],
            activebackground=self.colors['bg'],
            activeforeground=self.colors['fg'],
            font=('Segoe UI', 9)
        )
        auto_save_check.pack(side=tk.RIGHT, padx=(0, 20))
        
        # Wallpaper status (if enabled)
        if self.app_config.get('enable_wallpaper', True):
            self.wallpaper_label = tk.Label(
                second_row,
                text="🖼️ Wallpaper: OFF",
                bg=self.colors['bg'],
                fg='#ff6666',
                font=('Segoe UI', 9)
            )
            self.wallpaper_label.pack(side=tk.RIGHT, padx=(10, 0))
            self.update_wallpaper_status()
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
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
            if self.manage_wallpaper('check'):
                self.wallpaper_label.config(text="🖼️ Wallpaper: ON", fg='#66ff66')
            else:
                self.wallpaper_label.config(text="🖼️ Wallpaper: OFF", fg='#ff6666')
        
        # Check again in 2 seconds
        if self.window and self.window.winfo_exists():
            self.window.after(2000, self.update_wallpaper_status)
    
    def load_todos(self):
        """Load todos from file"""
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.todo_widgets = []
        
        if self.todo_file.exists():
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        for line in lines:
                            line = line.strip()
                            if line:
                                self.create_todo_widget(line)
                    else:
                        self.add_task()
            except Exception as e:
                self.set_status(f"Error loading: {e}")
                return
        else:
            self.add_task()
        
        self.set_status("Loaded successfully")
    
    def create_todo_widget(self, line="[ ] "):
        """Create a todo item widget"""
        # Parse the line
        completed = False
        text = line
        
        if line.startswith('[x]'):
            completed = True
            text = line[3:].strip()
        elif line.startswith('[ ]'):
            text = line[3:].strip()
        elif line.startswith('x '):
            completed = True
            text = line[2:].strip()
        
        # Create frame
        todo_frame = tk.Frame(self.scrollable_frame, bg=self.colors['entry_bg'])
        todo_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Checkbox
        var = tk.BooleanVar(value=completed)
        check = tk.Checkbutton(
            todo_frame,
            variable=var,
            bg=self.colors['entry_bg'],
            fg=self.colors['fg'],
            activebackground=self.colors['entry_bg'],
            activeforeground=self.colors['fg'],
            selectcolor=self.colors['entry_bg'],
            command=lambda: self.on_checkbox_change(entry, var.get())
        )
        check.pack(side=tk.LEFT, padx=(5, 10))
        
        # Text entry
        font_size = self.editor_config.get('font_size', 11)
        entry = tk.Entry(
            todo_frame,
            bg=self.colors['entry_bg'],
            fg=self.colors['complete'] if completed else self.colors['incomplete'],
            insertbackground=self.colors['fg'],
            relief=tk.FLAT,
            font=('Segoe UI', font_size),
            bd=0
        )
        entry.insert(0, text)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Bind events
        entry.bind('<KeyRelease>', self.on_text_change)
        entry.bind('<Return>', lambda e: self.add_task())
        
        # Delete button
        delete_btn = tk.Button(
            todo_frame,
            text="✕",
            bg=self.colors['entry_bg'],
            fg=self.colors['delete'],
            activebackground=self.colors['entry_bg'],
            activeforeground=self.colors['delete_hover'],
            relief=tk.FLAT,
            font=('Segoe UI', 12),
            cursor='hand2',
            bd=0,
            padx=5,
            command=lambda: self.delete_task(todo_frame)
        )
        delete_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Apply strikethrough if completed
        if completed:
            entry.config(font=('Segoe UI', font_size, 'overstrike'))
        
        self.todo_widgets.append((var, entry, todo_frame))
        
        # Focus on new entry if empty
        if not text:
            entry.focus_set()
    
    def on_checkbox_change(self, entry, completed):
        """Handle checkbox state change"""
        font_size = self.editor_config.get('font_size', 11)
        if completed:
            entry.config(
                fg=self.colors['complete'],
                font=('Segoe UI', font_size, 'overstrike')
            )
        else:
            entry.config(
                fg=self.colors['incomplete'],
                font=('Segoe UI', font_size)
            )
        
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
        # Scroll to bottom
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
                        prefix = "[x]" if var.get() else "[ ]"
                        f.write(f"{prefix} {text}\n")
            
            self.set_status(f"Saved at {datetime.now().strftime('%H:%M:%S')}")
            
            # Flash save button
            original_bg = self.save_btn['bg']
            self.save_btn.config(bg='#5cb85c')
            self.window.after(200, lambda: self.save_btn.config(bg=original_bg))
            
        except Exception as e:
            self.set_status(f"Error saving: {e}")
    
    def set_status(self, text):
        """Update status label"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=text)
    
    def run_tray(self):
        """Run system tray icon"""
        menu = pystray.Menu(
            pystray.MenuItem("Open", self.show_window, default=True),
            pystray.MenuItem("Quit", self.quit_app)
        )
        
        self.icon = pystray.Icon(
            "todo_editor",
            self.create_tray_icon(),
            "Todo Editor",
            menu
        )
        
        self.icon.run()
    
    def run(self):
        """Start the application"""
        # Start wallpaper if enabled and not minimized
        if self.app_config.get('enable_wallpaper', True) and not self.start_minimized:
            self.manage_wallpaper('start')
        
        # Start tray icon in separate thread
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()
        
        # Show window
        self.show_window()