#!/usr/bin/env python3
"""
Todo Wallpaper Module - Dynamic Wallpaper Generator
Creates desktop wallpapers from todo lists with optional AI imagery
"""

import os
import sys
import time
import platform
import subprocess
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    import watchdog.events
    import watchdog.observers
except ImportError:
    print("Required packages not found. Please run: python todo_app.py setup")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class TodoWallpaperGenerator:
    """Dynamic wallpaper generator that monitors todo list changes"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
        self.todo_file = Path("todo.txt")
        self.wallpaper_file = Path("todo_wallpaper.png")
        self.ai_image_file = Path("ai_todo_image.png")
        
        self.resolution = tuple(self.config.get('resolution', [2560, 1440]))
        self.background_color = tuple(self.config.get('background_color', [20, 20, 30]))
        self.text_color = tuple(self.config.get('text_color', [255, 255, 255]))
        self.completed_color = tuple(self.config.get('completed_color', [128, 128, 128]))
        self.title_color = tuple(self.config.get('title_color', [100, 200, 255]))
        
        self.padding = self.config.get('padding', 30)
        self.line_spacing = self.config.get('line_spacing', 8)
        self.font_size = self.config.get('font_size', 18)
        self.title_font_size = self.config.get('title_font_size', 32)
        self.opacity = self.config.get('opacity', 0.85)
        self.todo_width_ratio = self.config.get('todo_width_ratio', 0.33)
        
        self.use_ai_images = self.config.get('use_ai_images', False) and OpenAI is not None
        self.openai_api_key = self.config.get('openai_api_key') or os.environ.get('OPENAI_API_KEY')
        self.ai_prompt_template = self.config.get(
            'ai_image_prompt_template',
            "Create a visually striking image that represents the following tasks: {tasks}."
        )
        self.image_style = self.config.get('image_style', 'modern digital art with vibrant colors')
        self.image_quality = self.config.get('image_quality', 'high')
        self.image_size = self.config.get('image_size', '1024x1024')
        
        self.last_content = None
        self.last_ai_image = None
        self.openai_client = None
        
        if self.use_ai_images and self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                print("AI image generation enabled")
            except Exception as e:
                print(f"Failed to initialize OpenAI: {e}")
                self.use_ai_images = False
    
    def get_font(self, size):
        """Get system font with fallback"""
        font_paths = {
            "Windows": ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf"],
            "Darwin": ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"],
            "Linux": ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        }
        
        for path in font_paths.get(platform.system(), []):
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except:
                    pass
        return ImageFont.load_default()
    
    def parse_todo_file(self):
        """Parse todo file and return list of tasks"""
        tasks = []
        if self.todo_file.exists():
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        if line.startswith('[x]'):
                            tasks.append({'text': line[3:].strip(), 'completed': True})
                        elif line.startswith('[ ]'):
                            tasks.append({'text': line[3:].strip(), 'completed': False})
                        elif line.startswith('x '):
                            tasks.append({'text': line[2:].strip(), 'completed': True})
                        else:
                            tasks.append({'text': line, 'completed': False})
            except Exception as e:
                print(f"Error reading todo file: {e}")
        return tasks
    
    def generate_ai_image(self, tasks):
        """Generate AI image based on tasks using gpt-image-1"""
        if not self.openai_client or not tasks:
            return None
        
        task_desc = "\n".join(
            f"{t['text']} ({'completed' if t['completed'] else 'pending'})"
            for t in tasks[:10]
        )
        
        prompt = self.ai_prompt_template.format(tasks=task_desc)
        if self.image_style:
            prompt += f"\n\nStyle: {self.image_style}"
        
        print(f"Generating AI image...")
        print(f"Prompt: {prompt[:1000]}..." if len(prompt) > 1000 else f"Prompt: {prompt}")
        
        try:
            response = self.openai_client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=self.image_size,
                quality=self.image_quality,
                n=1
            )
            
            image_data = base64.b64decode(response.data[0].b64_json)
            with open(self.ai_image_file, 'wb') as f:
                f.write(image_data)
            
            print("AI image generated successfully")
            return str(self.ai_image_file)
            
        except Exception as e:
            error_msg = str(e)
            errors = {
                "api_key": "Invalid or missing OpenAI API key",
                "quality": f"Invalid quality parameter. Use 'low', 'medium', 'high', or 'auto' for gpt-image-1",
                "size": f"Invalid size. Use '1024x1024', '1536x1024', '1024x1536', or 'auto' for gpt-image-1",
                "content_policy": "Content policy violation. Try modifying your tasks or prompt template.",
                "unknown_parameter": f"Unknown parameter in API call. Details: {error_msg}"
            }
            
            for key, msg in errors.items():
                if key in error_msg.lower():
                    print(f"Error: {msg}")
                    return None
            
            print(f"Error generating AI image: {error_msg}")
            return None
    
    def create_wallpaper(self, tasks):
        """Create wallpaper image"""
        width, height = self.resolution
        todo_width = int(width * self.todo_width_ratio)
        image_width = width - todo_width
        
        img = Image.new('RGB', (width, height), self.background_color)
        
        if self.use_ai_images:
            tasks_content = str(tasks)
            if tasks_content != self.last_content or not self.ai_image_file.exists():
                ai_path = self.generate_ai_image(tasks)
                if ai_path:
                    self.last_ai_image = ai_path
                self.last_content = tasks_content
            
            if self.last_ai_image and Path(self.last_ai_image).exists():
                try:
                    ai_img = Image.open(self.last_ai_image)
                    ai_img.thumbnail((image_width, height), Image.Resampling.LANCZOS)
                    x_offset = (image_width - ai_img.width) // 2
                    y_offset = (height - ai_img.height) // 2
                    img.paste(ai_img, (x_offset, y_offset))
                except Exception as e:
                    print(f"Error loading AI image: {e}")
        
        overlay = Image.new('RGBA', (todo_width, height), (*self.background_color, int(255 * self.opacity)))
        img = img.convert('RGBA')
        todo_img = Image.new('RGBA', (todo_width, height), (0, 0, 0, 0))
        todo_img.paste(overlay, (0, 0))
        
        draw = ImageDraw.Draw(todo_img)
        title_font = self.get_font(self.title_font_size)
        task_font = self.get_font(self.font_size)
        
        y = self.padding
        x_pad = self.padding
        
        draw.text((x_pad, y), "Today's Tasks", fill=self.title_color, font=title_font)
        y += self.title_font_size + 5
        
        draw.text((x_pad, y), datetime.now().strftime("%A, %B %d"), fill=self.completed_color, font=task_font)
        y += self.font_size + self.line_spacing * 2
        
        max_y = height - self.padding * 2
        max_width = todo_width - 2 * x_pad - 40
        
        for task in tasks:
            if y + self.font_size > max_y:
                draw.text((x_pad, max_y - self.font_size), "...", fill=self.completed_color, font=task_font)
                break
            
            prefix = "✓ " if task['completed'] else "○ "
            color = self.completed_color if task['completed'] else self.text_color
            
            prefix_bbox = draw.textbbox((0, 0), prefix, font=task_font)
            prefix_width = prefix_bbox[2] - prefix_bbox[0]
            
            draw.text((x_pad, y), prefix, fill=color, font=task_font)
            
            words = task['text'].split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=task_font)
                if bbox[2] - bbox[0] + prefix_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            for i, line in enumerate(lines):
                if y > max_y:
                    break
                draw.text((x_pad + (prefix_width if i == 0 else 0), y), line, fill=color, font=task_font)
                y += self.font_size + self.line_spacing
            
            y += self.line_spacing
        
        draw.text((x_pad, height - self.padding - self.font_size), 
                 f"Updated: {datetime.now().strftime('%H:%M')}", fill=self.completed_color, font=task_font)
        
        img.paste(todo_img, (width - todo_width, 0), todo_img)
        img.convert('RGB').save(self.wallpaper_file, quality=95)
    
    def set_wallpaper(self):
        """Set the generated image as desktop wallpaper"""
        path = str(self.wallpaper_file.absolute())
        system = platform.system()
        
        try:
            if system == "Windows":
                import ctypes
                ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 0)
            elif system == "Darwin":
                subprocess.run(['osascript', '-e', f'tell application "Finder" to set desktop picture to POSIX file "{path}"'])
            elif system == "Linux":
                desktop = os.environ.get('DESKTOP_SESSION', '').lower()
                if 'gnome' in desktop:
                    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f'file://{path}'])
                elif 'kde' in desktop:
                    script = f'var allDesktops = desktops(); for (i=0;i<allDesktops.length;i++) {{ d = allDesktops[i]; d.wallpaperPlugin = "org.kde.image"; d.currentConfigGroup = Array("Wallpaper", "org.kde.image", "General"); d.writeConfig("Image", "file://{path}") }}'
                    subprocess.run(['qdbus', 'org.kde.plasmashell', '/PlasmaShell', 'org.kde.PlasmaShell.evaluateScript', script])
                else:
                    subprocess.run(['feh', '--bg-scale', path])
        except Exception as e:
            print(f"Error setting wallpaper: {e}\nPlease manually set {path} as your wallpaper")
    
    def update_wallpaper(self):
        """Update wallpaper if todo list has changed"""
        tasks = self.parse_todo_file()
        current_content = str(tasks)
        
        if self.use_ai_images or current_content != self.last_content or not self.wallpaper_file.exists():
            print(f"Updating wallpaper... ({len(tasks)} tasks)")
            self.create_wallpaper(tasks)
            self.set_wallpaper()
            if not self.use_ai_images:
                self.last_content = current_content
            return True
        return False
    
    def run(self):
        """Run the wallpaper generator with file monitoring"""
        print(f"""
Todo Wallpaper Generator
========================
Watching: {self.todo_file}
Output: {self.wallpaper_file}
Resolution: {self.resolution}
AI Images: {'Enabled' if self.use_ai_images else 'Disabled'}

Press Ctrl+C to stop
""")
        
        self.update_wallpaper()
        
        event_handler = TodoFileHandler(self)
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, path='.', recursive=False)
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\nStopping wallpaper generator...")
        
        observer.join()

class TodoFileHandler(watchdog.events.FileSystemEventHandler):
    """File system event handler for todo file changes"""
    
    def __init__(self, generator):
        self.generator = generator
        self.last_modified = 0
    
    def on_modified(self, event):
        if event.src_path.endswith('todo.txt'):
            current_time = time.time()
            if current_time - self.last_modified > 1:
                self.generator.update_wallpaper()
                self.last_modified = current_time

if __name__ == "__main__":
    print("Please run: python todo_app.py wallpaper")