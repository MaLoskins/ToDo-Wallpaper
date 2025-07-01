#!/usr/bin/env python3
"""
Todo Editor Application - Unified Entry Point
Combines todo editor, wallpaper generator, and setup utilities
"""

import os
import sys
import json
import argparse
import platform
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
# Utility to create application icon
from create_icon import create_app_icon

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

__version__ = "2.0.0"
__app_name__ = "Todo Editor"

class TodoApp:
    """Main application controller"""
    
    def __init__(self):
        self.app_dir = Path(__file__).parent
        self.config_file = self.app_dir / "config.json"
        self.todo_file = self.app_dir / "todo.txt"
        self.config = self.load_config()
        

    def load_config(self):
        """Load or create configuration"""
        default_config = {
            "app": {"version": __version__, "auto_start": True, "start_minimized": True, "enable_wallpaper": True},
            "editor": {"auto_save": True, "font_size": 11, "window_size": [600, 700], "dark_mode": True},
            "wallpaper": {
                "resolution": [2560, 1440], "update_interval": 1, "todo_width_ratio": 0.3, "font_size": 16,
                "use_ai_images": True, "openai_api_key": os.environ.get('OPENAI_API_KEY'),
                "image_quality": "high", "image_size": "1024x1024",
                "image_style": "modern digital art with vibrant colors",
                "ai_image_prompt_template": "Create a visually striking image that represents the following tasks: {tasks}.",
                "background_color": [20, 20, 30], "text_color": [255, 255, 255], "completed_color": [128, 128, 128],
                "design_system": {
                    "grid_unit": 8,
                    "column_count": 12,
                    "accent_color": [100, 200, 255],
                    "surface_color": [28, 30, 42],
                    "overlay_color": [35, 38, 54],
                    "overlay_alpha": 0.92,
                    "typography": {
                        "base_size": 16,
                        "title_scale": 2.5,
                        "headline_scale": 1.25,
                        "body_scale": 1.0
                    },
                    "modules": {
                        "card_min_height": 160,
                        "card_padding": 24,
                        "border_radius": 16,
                        "image_aspect_ratio": 1.0
                    },
                    "container_padding": 32,
                    "vertical_padding_ratio": 0.1,
                    "section_spacing": 48,
                    "max_visible_tasks": 5,
                    "enable_shadows": True,
                    "enable_gradient_bg": True
                }
            },
            "system": {"shortcuts": {"desktop": True, "start_menu": True, "startup": True}}
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return self._deep_merge(default_config, json.load(f))
            except Exception as e:
                print(f"Error loading config: {e}")
        
        return default_config
    
    def _deep_merge(self, base, update):
        """Deep merge dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def save_config(self):
        """Save configuration"""
        try:
            save_config = self.config.copy()
            if 'wallpaper' in save_config and save_config['wallpaper'].get('openai_api_key') == os.environ.get('OPENAI_API_KEY'):
                save_config['wallpaper']['openai_api_key'] = None
            
            with open(self.config_file, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def run_editor(self, minimized=False):
        """Run the todo editor"""
        from todo_editor_module import TodoEditor
        editor = TodoEditor(str(self.todo_file), self.config, minimized)
        editor.run()
    
    def run_wallpaper(self):
        """Run the wallpaper generator"""
        from todo_wallpaper_module import TodoWallpaperGenerator
        TodoWallpaperGenerator(self.config['wallpaper']).run()
    
    def setup(self):
        """Run complete setup process"""
        print(f"\n{'='*40}\n    {__app_name__} - Complete Setup\n{'='*40}\n")
        
        steps = [
            ("Installing required packages", self._install_dependencies),
            ("Checking AI configuration", self._check_ai_setup),
            ("Creating application icon", self._create_icon),
            ("Creating shortcuts", self._create_shortcuts),
            ("Configuring auto-start", lambda: self._configure_autostart() if self.config['app']['auto_start'] else None)
        ]
        
        for i, (desc, func) in enumerate(steps, 1):
            print(f"\n[{i}/{len(steps)}] {desc}...")
            func()
        
        self.save_config()
        
        print(f"""
{'='*40}
Setup Complete!

You can now:
- Launch from Desktop: "{__app_name__}" icon
- Pin to taskbar: Search "{__app_name__}" in Start Menu
- It will auto-start with Windows: {'Yes' if self.config['app']['auto_start'] else 'No'}
- AI Image Generation: {'Configured' if self.config['wallpaper'].get('openai_api_key') or os.environ.get('OPENAI_API_KEY') else 'Not configured (optional)'}

Configuration: {self.config_file}
{'='*40}
""")
        
        if input("\nStart application now? (Y/n): ").lower() != 'n':
            self.run_editor()
    
    def _check_ai_setup(self):
        """Check and configure AI image generation"""
        api_key = self.config['wallpaper'].get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
        
        if api_key:
            print("✓ OpenAI API key found")
            return
        
        print("""
AI Image Generation (Optional)
------------------------------
AI image generation can create dynamic wallpapers based on your tasks.
You'll need an OpenAI API key to use this feature.

You can:
1. Add it to the .env file: OPENAI_API_KEY=your-key-here
2. Set it as an environment variable
3. Skip for now (you can add it later)
""")
        
        if input("Would you like to enter an API key now? (y/N): ").lower() == 'y':
            api_key = input("Enter your OpenAI API key: ").strip()
            if api_key:
                try:
                    with open(self.app_dir / '.env', 'w') as f:
                        f.write(f"OPENAI_API_KEY={api_key}\n")
                    os.environ['OPENAI_API_KEY'] = api_key
                    print("✓ API key saved to .env file")
                except Exception as e:
                    print(f"Warning: Could not save to .env file: {e}")
                    self.config['wallpaper']['openai_api_key'] = api_key
        else:
            print("Skipping AI configuration (you can add it later)")
    
    def _install_dependencies(self):
        """Install required Python packages"""
        packages = ['pystray', 'pillow', 'watchdog', 'openai', 'python-dotenv']
        
        for package in packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    def _create_icon(self):
        """Create application icon file"""
        icon_path = self.app_dir / f"{__app_name__.replace(' ', '_').lower()}.ico"
        icon_sizes = [16, 32, 48, 64, 128, 256]
        images = [create_app_icon(size) for size in icon_sizes]
        images[-1].save(icon_path, format='ICO', sizes=[(s, s) for s in icon_sizes], append_images=images[:-1])
        print(f"Created icon: {icon_path}")
        return icon_path
    
    def _create_shortcuts(self):
        """Create system shortcuts"""
        if platform.system() != "Windows":
            print("Shortcut creation is currently only supported on Windows")
            return
        
        icon_path = self.app_dir / f"{__app_name__.replace(' ', '_').lower()}.ico"
        if not icon_path.exists():
            icon_path = self._create_icon()
        
        shortcuts = []
        if self.config['system']['shortcuts']['desktop']:
            shortcuts.append((Path.home() / 'Desktop' / f'{__app_name__}.lnk', f'"{self.app_dir / "todo_app.py"}" editor'))
        if self.config['system']['shortcuts']['start_menu']:
            shortcuts.append((Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / f'{__app_name__}.lnk', f'"{self.app_dir / "todo_app.py"}" editor'))
        
        for path, args in shortcuts:
            self._create_shortcut(path, sys.executable, args, str(self.app_dir), str(icon_path))
    
    def _configure_autostart(self):
        """Configure application to start with Windows"""
        if platform.system() != "Windows":
            print("Auto-start configuration is currently only supported on Windows")
            return
        
        startup_path = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup' / f'{__app_name__}.lnk'
        self._create_shortcut(startup_path, sys.executable, f'"{self.app_dir / "todo_app.py"}" editor --minimized', 
                            str(self.app_dir), window_style=7)
        print("Configured auto-start")
    
    def _create_shortcut(self, path, target, args, working_dir, icon_location=None, window_style=None):
        """Create Windows shortcut using PowerShell"""
        ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = '{args}'
$Shortcut.WorkingDirectory = "{working_dir}"
'''
        if icon_location:
            ps_script += f'$Shortcut.IconLocation = "{icon_location}"\n'
        if window_style:
            ps_script += f'$Shortcut.WindowStyle = {window_style}\n'
        ps_script += '$Shortcut.Save()'
        
        try:
            subprocess.run(['powershell', '-Command', ps_script], check=True, capture_output=True, text=True)
            print(f"Created shortcut: {path.name}")
        except Exception as e:
            print(f"Failed to create shortcut: {e}")
    
    def uninstall(self):
        """Remove shortcuts and configuration"""
        print(f"Uninstalling {__app_name__}...")
        
        shortcuts = [
            Path.home() / 'Desktop' / f'{__app_name__}.lnk',
            Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / f'{__app_name__}.lnk',
            Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup' / f'{__app_name__}.lnk'
        ]
        
        for shortcut in shortcuts:
            if shortcut.exists():
                shortcut.unlink()
                print(f"Removed: {shortcut.name}")
        
        print("Uninstall complete!")

def main():
    """Main entry point with command line interface"""
    parser = argparse.ArgumentParser(
        description=f'{__app_name__} - Lightweight todo list manager with desktop integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run setup if first time, otherwise start editor
  %(prog)s editor             # Start todo editor
  %(prog)s editor --minimized # Start minimized to system tray
  %(prog)s wallpaper          # Start wallpaper generator
  %(prog)s setup              # Run complete setup
  %(prog)s config             # Show configuration
  %(prog)s uninstall          # Remove shortcuts
"""
    )
    
    parser.add_argument('command', nargs='?', default='editor',
                       choices=['editor', 'wallpaper', 'setup', 'config', 'uninstall'],
                       help='Command to run (default: editor)')
    parser.add_argument('--minimized', action='store_true', help='Start minimized to system tray')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--version', action='version', version=f'{__app_name__} {__version__}')
    
    args = parser.parse_args()
    
    app = TodoApp()
    
    if args.config:
        app.config_file = Path(args.config)
        app.config = app.load_config()
    
    if not app.config_file.exists() and args.command == 'editor':
        print(f"Welcome to {__app_name__}!")
        print("This appears to be your first time running the application.")
        if input("Would you like to run the setup? (Y/n): ").lower() != 'n':
            args.command = 'setup'
    
    commands = {
        'editor': lambda: app.run_editor(args.minimized),
        'wallpaper': app.run_wallpaper,
        'setup': app.setup,
        'config': lambda: print(f"{json.dumps(app.config, indent=2)}\n\nConfiguration file: {app.config_file}"),
        'uninstall': app.uninstall
    }
    
    commands[args.command]()

if __name__ == "__main__":
    main()