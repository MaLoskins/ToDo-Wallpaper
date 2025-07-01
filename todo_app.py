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

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Core modules will be imported conditionally based on command
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
            # Application settings
            "app": {
                "version": __version__,
                "auto_start": True,
                "start_minimized": True,
                "enable_wallpaper": True
            },
            # Todo editor settings
            "editor": {
                "auto_save": True,
                "font_size": 11,
                "window_size": [600, 700],
                "dark_mode": True
            },
            # Wallpaper settings
            "wallpaper": {
                "resolution": [2560, 1440],
                "update_interval": 1,
                "todo_width_ratio": 0.3,
                "font_size": 16,
                "use_ai_images": True,  # Enable by default
                "openai_api_key": os.environ.get('OPENAI_API_KEY'),  # Load from environment
                "image_quality": "high",  # low, medium, high, or auto for gpt-image-1
                "image_size": "1024x1024",  # 1024x1024, 1536x1024, 1024x1536, or auto for gpt-image-1
                "image_style": "modern digital art with vibrant colors",
                "ai_image_prompt_template": "Create a visually striking, abstract digital art image that represents productivity and the following tasks in a metaphorical way: {tasks}. Use modern, vibrant colors and dynamic compositions. Do not include any text in the image.",
                "background_color": [20, 20, 30],
                "text_color": [255, 255, 255],
                "completed_color": [128, 128, 128]
            },
            # System integration
            "system": {
                "shortcuts": {
                    "desktop": True,
                    "start_menu": True,
                    "startup": True
                }
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                # Deep merge user config into defaults
                return self._deep_merge(default_config, user_config)
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
            # Don't save sensitive data
            save_config = self.config.copy()
            if 'wallpaper' in save_config and 'openai_api_key' in save_config['wallpaper']:
                # Only save if it's not from environment
                if save_config['wallpaper']['openai_api_key'] == os.environ.get('OPENAI_API_KEY'):
                    save_config['wallpaper']['openai_api_key'] = None
            
            with open(self.config_file, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def run_editor(self, minimized=False):
        """Run the todo editor"""
        # Import here to avoid loading heavy modules unnecessarily
        from todo_editor_module import TodoEditor
        
        editor = TodoEditor(
            todo_file=str(self.todo_file),
            config=self.config,
            start_minimized=minimized
        )
        editor.run()
    
    def run_wallpaper(self):
        """Run the wallpaper generator"""
        from todo_wallpaper_module import TodoWallpaperGenerator
        
        generator = TodoWallpaperGenerator(self.config['wallpaper'])
        generator.run()
    
    def setup(self):
        """Run complete setup process"""
        print(f"""
========================================
    {__app_name__} - Complete Setup
========================================
""")
        
        # Install dependencies
        print("[1/5] Installing required packages...")
        self._install_dependencies()
        
        # Check for API key
        print("\n[2/5] Checking AI configuration...")
        self._check_ai_setup()
        
        # Create icon
        print("\n[3/5] Creating application icon...")
        self._create_icon()
        
        # Create shortcuts
        print("\n[4/5] Creating shortcuts...")
        self._create_shortcuts()
        
        # Configure startup
        if self.config['app']['auto_start']:
            print("\n[5/5] Configuring auto-start...")
            self._configure_autostart()
        
        # Save configuration
        self.save_config()
        
        print(f"""
========================================
Setup Complete!

You can now:
- Launch from Desktop: "{__app_name__}" icon
- Pin to taskbar: Search "{__app_name__}" in Start Menu
- It will auto-start with Windows: {'Yes' if self.config['app']['auto_start'] else 'No'}
- AI Image Generation: {'Configured' if self.config['wallpaper'].get('openai_api_key') or os.environ.get('OPENAI_API_KEY') else 'Not configured (optional)'}

Configuration: {self.config_file}
========================================
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
        
        response = input("Would you like to enter an API key now? (y/N): ")
        if response.lower() == 'y':
            api_key = input("Enter your OpenAI API key: ").strip()
            if api_key:
                # Save to .env file
                env_file = self.app_dir / '.env'
                try:
                    with open(env_file, 'w') as f:
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
        packages = [
            'pystray',
            'pillow',
            'watchdog',
            'openai',
            'python-dotenv'
        ]
        
        for package in packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    
    def _create_icon(self):
        """Create application icon"""
        from PIL import Image, ImageDraw
        
        # Create icon at multiple sizes
        icon_size = 256
        img = Image.new('RGBA', (icon_size, icon_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background
        padding = 20
        draw.rounded_rectangle(
            [padding, padding, icon_size-padding, icon_size-padding],
            radius=40,
            fill=(30, 30, 46),
            outline=(0, 122, 204),
            width=4
        )
        
        # Checkbox
        checkbox_size = 60
        checkbox_x = 50
        checkbox_y = icon_size // 2 - checkbox_size // 2
        
        draw.rounded_rectangle(
            [checkbox_x, checkbox_y, checkbox_x + checkbox_size, checkbox_y + checkbox_size],
            radius=8,
            fill=(45, 45, 55),
            outline=(100, 200, 255),
            width=3
        )
        
        # Checkmark
        check_points = [
            (checkbox_x + 15, checkbox_y + 30),
            (checkbox_x + 25, checkbox_y + 40),
            (checkbox_x + 45, checkbox_y + 20)
        ]
        draw.line(check_points[0:2], fill=(100, 255, 100), width=6)
        draw.line(check_points[1:3], fill=(100, 255, 100), width=6)
        
        # Save icon
        icon_path = self.app_dir / f"{__app_name__.replace(' ', '_').lower()}.ico"
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        images = [img.resize(size, Image.Resampling.LANCZOS) for size in icon_sizes]
        images[-1].save(icon_path, format='ICO', sizes=icon_sizes, append_images=images[:-1])
        
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
        
        # Prepare shortcut data
        target = sys.executable
        script_path = str(self.app_dir / "todo_app.py")
        
        shortcuts = []
        if self.config['system']['shortcuts']['desktop']:
            shortcuts.append({
                'path': Path.home() / 'Desktop' / f'{__app_name__}.lnk',
                'args': f'"{script_path}" editor'
            })
        
        if self.config['system']['shortcuts']['start_menu']:
            shortcuts.append({
                'path': Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / f'{__app_name__}.lnk',
                'args': f'"{script_path}" editor'
            })
        
        # Create shortcuts using PowerShell
        for shortcut in shortcuts:
            ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut['path']}")
$Shortcut.TargetPath = "{target}"
$Shortcut.Arguments = '{shortcut['args']}'
$Shortcut.WorkingDirectory = "{self.app_dir}"
$Shortcut.IconLocation = "{icon_path}"
$Shortcut.Save()
'''
            try:
                subprocess.run(
                    ['powershell', '-Command', ps_script],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"Created shortcut: {shortcut['path'].name}")
            except Exception as e:
                print(f"Failed to create shortcut: {e}")
    
    def _configure_autostart(self):
        """Configure application to start with Windows"""
        if platform.system() != "Windows":
            print("Auto-start configuration is currently only supported on Windows")
            return
        
        startup_dir = Path.home() / 'AppData' / 'Roaming' / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
        startup_shortcut = startup_dir / f'{__app_name__}.lnk'
        
        # Create startup shortcut
        ps_script = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{startup_shortcut}")
$Shortcut.TargetPath = "{sys.executable}"
$Shortcut.Arguments = '"{self.app_dir / "todo_app.py"}" editor --minimized'
$Shortcut.WorkingDirectory = "{self.app_dir}"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
'''
        try:
            subprocess.run(
                ['powershell', '-Command', ps_script],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Configured auto-start")
        except Exception as e:
            print(f"Failed to configure auto-start: {e}")
    
    def uninstall(self):
        """Remove shortcuts and configuration"""
        print(f"Uninstalling {__app_name__}...")
        
        # Remove shortcuts
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
    
    parser.add_argument(
        'command',
        nargs='?',
        default='editor',
        choices=['editor', 'wallpaper', 'setup', 'config', 'uninstall'],
        help='Command to run (default: editor)'
    )
    
    parser.add_argument(
        '--minimized',
        action='store_true',
        help='Start minimized to system tray'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'{__app_name__} {__version__}'
    )
    
    args = parser.parse_args()
    
    # Initialize application
    app = TodoApp()
    
    # Override config file if specified
    if args.config:
        app.config_file = Path(args.config)
        app.config = app.load_config()
    
    # Check if this is first run
    if not app.config_file.exists() and args.command == 'editor':
        print(f"Welcome to {__app_name__}!")
        print("This appears to be your first time running the application.")
        if input("Would you like to run the setup? (Y/n): ").lower() != 'n':
            args.command = 'setup'
    
    # Execute command
    if args.command == 'editor':
        app.run_editor(minimized=args.minimized)
    elif args.command == 'wallpaper':
        app.run_wallpaper()
    elif args.command == 'setup':
        app.setup()
    elif args.command == 'config':
        print(json.dumps(app.config, indent=2))
        print(f"\nConfiguration file: {app.config_file}")
    elif args.command == 'uninstall':
        app.uninstall()

if __name__ == "__main__":
    main()