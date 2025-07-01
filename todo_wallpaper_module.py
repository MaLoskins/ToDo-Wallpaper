#!/usr/bin/env python3
"""
Todo Wallpaper Module - Dynamic Wallpaper Generator
Creates desktop wallpapers from todo lists with optional AI imagery
Enhanced with unified design system
"""

import os
import sys
import time
import platform
import subprocess
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
    """Dynamic wallpaper generator with unified design system"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
        self.todo_file = Path("todo.txt")
        self.wallpaper_file = Path("todo_wallpaper.png")
        self.ai_image_file = Path("ai_todo_image.png")
        
        self.resolution = tuple(self.config.get('resolution', [2560, 1440]))
        
        # Load design system from config if available
        self.design_config = self.config.get('design_system', {})
        
        # Design System Configuration
        self.setup_design_system()
        
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
    
    def setup_design_system(self):
        """Initialize unified design system"""
        # Grid system
        self.grid_unit = self.design_config.get('grid_unit', 8)  # Base unit for spacing
        self.column_count = self.design_config.get('column_count', 12)
        self.column_width = self.resolution[0] // self.column_count
        self.gutter = self.grid_unit * 3  # 24px gutters
        
        # Typography hierarchy (3 scales)
        typography_config = self.design_config.get('typography', {})
        base_size = typography_config.get('base_size', 16)
        
        self.typography = {
            'title': {
                'size': int(base_size * typography_config.get('title_scale', 2.5)),
                'weight': 'bold',
                'line_height': 1.2
            },
            'headline': {
                'size': int(base_size * typography_config.get('headline_scale', 1.25)),
                'weight': 'medium',
                'line_height': 1.4
            },
            'body': {
                'size': base_size,
                'weight': 'regular',
                'line_height': 1.6
            }
        }
        
        # Color system with accent
        accent = self.design_config.get('accent_color', [100, 200, 255])
        surface = self.design_config.get('surface_color', [28, 30, 42])
        overlay = self.design_config.get('overlay_color', [35, 38, 54])
        
        self.colors = {
            'background': tuple(self.config.get('background_color', [20, 20, 30])),
            'surface': tuple(surface),
            'overlay': tuple(overlay),
            'overlay_alpha': self.design_config.get('overlay_alpha', 0.92),
            'text_primary': tuple(self.config.get('text_color', [255, 255, 255])),
            'text_secondary': (180, 185, 195),
            'text_disabled': tuple(self.config.get('completed_color', [110, 115, 125])),
            'accent': tuple(accent),
            'accent_secondary': (accent[0]-20, accent[1]-40, accent[2]-45),
            'success': (100, 255, 150),
            'border': (50, 54, 70),
            'shadow': (0, 0, 0, 80)
        }
        
        # Module dimensions (uniform sizing)
        modules_config = self.design_config.get('modules', {})
        self.modules = {
            'card': {
                'width': self.column_width * 4 - self.gutter,
                'min_height': modules_config.get('card_min_height', self.grid_unit * 20),
                'padding': modules_config.get('card_padding', self.grid_unit * 3),
                'border_radius': modules_config.get('border_radius', self.grid_unit * 2)
            },
            'image': {
                'aspect_ratio': modules_config.get('image_aspect_ratio', 1.0),  # Default to square for AI images
                'border_radius': modules_config.get('border_radius', self.grid_unit * 2)
            }
        }
        
        # Container specs
        self.container_padding = self.design_config.get('container_padding', self.grid_unit * 4)
        self.vertical_padding_ratio = self.design_config.get('vertical_padding_ratio', 0.1)
        self.section_spacing = self.design_config.get('section_spacing', self.grid_unit * 6)
        self.max_visible_tasks = self.design_config.get('max_visible_tasks', 5)
        self.enable_shadows = self.design_config.get('enable_shadows', True)
        self.enable_gradient_bg = self.design_config.get('enable_gradient_bg', True)
    
    def get_font(self, style='body'):
        """Get system font with fallback based on typography system"""
        size = self.typography[style]['size']
        
        font_paths = {
            "Windows": ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
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
    
    def draw_rounded_rectangle(self, draw, coords, radius, fill=None, outline=None, width=1):
        """Draw a rounded rectangle"""
        x1, y1, x2, y2 = coords
        diameter = radius * 2
        
        # Create mask for rounded corners
        if fill:
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
            draw.pieslice([x1, y1, x1 + diameter, y1 + diameter], 180, 270, fill=fill)
            draw.pieslice([x2 - diameter, y1, x2, y1 + diameter], 270, 360, fill=fill)
            draw.pieslice([x1, y2 - diameter, x1 + diameter, y2], 90, 180, fill=fill)
            draw.pieslice([x2 - diameter, y2 - diameter, x2, y2], 0, 90, fill=fill)
        
        if outline:
            draw.arc([x1, y1, x1 + diameter, y1 + diameter], 180, 270, fill=outline, width=width)
            draw.arc([x2 - diameter, y1, x2, y1 + diameter], 270, 360, fill=outline, width=width)
            draw.arc([x1, y2 - diameter, x1 + diameter, y2], 90, 180, fill=outline, width=width)
            draw.arc([x2 - diameter, y2 - diameter, x2, y2], 0, 90, fill=outline, width=width)
            draw.line([x1 + radius, y1, x2 - radius, y1], fill=outline, width=width)
            draw.line([x1 + radius, y2, x2 - radius, y2], fill=outline, width=width)
            draw.line([x1, y1 + radius, x1, y2 - radius], fill=outline, width=width)
            draw.line([x2, y1 + radius, x2, y2 - radius], fill=outline, width=width)
    
    def create_soft_gradient(self, size, start_color, end_color, direction='vertical'):
        """Create a soft gradient background"""
        width, height = size
        gradient = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(gradient)
        
        for i in range(height if direction == 'vertical' else width):
            ratio = i / (height if direction == 'vertical' else width)
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            
            if direction == 'vertical':
                draw.line([(0, i), (width, i)], fill=(r, g, b))
            else:
                draw.line([(i, 0), (i, height)], fill=(r, g, b))
        
        return gradient
    
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
            print(f"Error generating AI image: {e}")
            return None
    
    def create_task_module(self, draw, task, x, y, width, completed_count, total_count):
        """Create a single task module with unified design"""
        module_height = self.modules['card']['min_height']
        padding = self.modules['card']['padding']
        radius = self.modules['card']['border_radius']
        
        # Draw module background with subtle shadow (if enabled)
        if self.enable_shadows:
            shadow_offset = 4
            for i in range(shadow_offset):
                alpha = int(40 * (1 - i/shadow_offset))
                shadow_color = (*self.colors['shadow'][:3], alpha)
                self.draw_rounded_rectangle(
                    draw, 
                    (x + i, y + i, x + width + i, y + module_height + i), 
                    radius, 
                    fill=shadow_color
                )
        
        # Draw main container
        self.draw_rounded_rectangle(
            draw, 
            (x, y, x + width, y + module_height), 
            radius, 
            fill=self.colors['overlay']
        )
        
        # Task status indicator with accent color
        indicator_size = self.grid_unit * 2
        indicator_x = x + padding
        indicator_y = y + padding + (self.typography['headline']['size'] - indicator_size) // 2
        
        if task['completed']:
            draw.ellipse(
                [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                fill=self.colors['success']
            )
            # Checkmark
            draw.line(
                [(indicator_x + 5, indicator_y + 8), (indicator_x + 8, indicator_y + 11), 
                 (indicator_x + 13, indicator_y + 6)],
                fill=self.colors['overlay'], width=2
            )
        else:
            draw.ellipse(
                [indicator_x, indicator_y, indicator_x + indicator_size, indicator_y + indicator_size],
                outline=self.colors['accent'], width=2
            )
        
        # Task text with typography hierarchy
        text_x = indicator_x + indicator_size + self.grid_unit * 2
        text_width = width - padding * 2 - indicator_size - self.grid_unit * 2
        
        # Task headline
        headline_font = self.get_font('headline')
        task_color = self.colors['text_disabled'] if task['completed'] else self.colors['text_primary']
        
        # Word wrap text
        words = task['text'].split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=headline_font)
            if bbox[2] - bbox[0] <= text_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw task text (max 2 lines)
        text_y = y + padding
        for i, line in enumerate(lines[:2]):
            if i == 1 and len(lines) > 2:
                line = line + "..."
            draw.text((text_x, text_y), line, fill=task_color, font=headline_font)
            text_y += int(self.typography['headline']['size'] * self.typography['headline']['line_height'])
        
        # Progress indicator at bottom
        progress_y = y + module_height - padding - self.grid_unit
        progress_width = width - padding * 2
        progress_height = self.grid_unit // 2
        
        # Background bar
        draw.rectangle(
            [x + padding, progress_y, x + padding + progress_width, progress_y + progress_height],
            fill=self.colors['border']
        )
        
        # Progress fill
        if total_count > 0:
            progress = completed_count / total_count
            draw.rectangle(
                [x + padding, progress_y, 
                 x + padding + int(progress_width * progress), progress_y + progress_height],
                fill=self.colors['accent']
            )
        
        return module_height + self.grid_unit * 2
    
    def create_wallpaper(self, tasks):
        """Create wallpaper with unified design system"""
        width, height = self.resolution
        
        # Create background (gradient or solid based on config)
        if self.enable_gradient_bg:
            img = self.create_soft_gradient(
                (width, height),
                self.colors['background'],
                (self.colors['background'][0] + 10, self.colors['background'][1] + 10, self.colors['background'][2] + 20)
            )
        else:
            img = Image.new('RGB', (width, height), self.colors['background'])
        
        # Calculate layout based on grid system
        content_width = width - self.container_padding * 2
        
        # Left section for AI image (if enabled)
        if self.use_ai_images:
            image_section_width = self.column_width * 7
            todo_section_width = self.column_width * 5 - self.gutter
        else:
            image_section_width = 0
            todo_section_width = content_width
        
        # Generate AI image if needed
        if self.use_ai_images:
            tasks_content = str(tasks)
            if tasks_content != self.last_content or not self.ai_image_file.exists():
                ai_path = self.generate_ai_image(tasks)
                if ai_path:
                    self.last_ai_image = ai_path
                self.last_content = tasks_content
            
            if self.last_ai_image and Path(self.last_ai_image).exists():
                try:
                    # Create image container with overlay
                    ai_img = Image.open(self.last_ai_image)
                    
                    # AI images from OpenAI are always square (1024x1024), maintain 1:1 aspect ratio
                    # Do not use the config aspect ratio for AI images
                    max_dimension = min(image_section_width - self.gutter, height - self.container_padding * 2)
                    
                    # Keep it square
                    target_size = min(max_dimension, ai_img.width)  # Don't upscale beyond original
                    
                    # Resize maintaining square aspect ratio
                    ai_img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                    actual_width = ai_img.width
                    actual_height = ai_img.height
                    
                    # Create overlay for image
                    overlay = Image.new('RGBA', (actual_width, actual_height), (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    
                    # Add rounded corners to image
                    mask = Image.new('L', (actual_width, actual_height), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    self.draw_rounded_rectangle(
                        mask_draw,
                        (0, 0, actual_width, actual_height),
                        self.modules['image']['border_radius'],
                        fill=255
                    )
                    
                    # Apply mask
                    output = Image.new('RGBA', (actual_width, actual_height), (0, 0, 0, 0))
                    output.paste(ai_img, (0, 0))
                    output.putalpha(mask)
                    
                    # Center image in its section
                    image_x = self.container_padding + (image_section_width - self.gutter - actual_width) // 2
                    image_y = (height - actual_height) // 2
                    
                    img.paste(output, (image_x, image_y), output)
                    
                except Exception as e:
                    print(f"Error loading AI image: {e}")
        
        # Create main drawing surface
        draw = ImageDraw.Draw(img)
        
        # Todo section positioning with vertical centering
        todo_x = self.container_padding + (image_section_width if self.use_ai_images else 0)
        
        # Reduce container height and center vertically using config ratio
        vertical_padding = int(height * self.vertical_padding_ratio)
        todo_y = vertical_padding
        container_height = height - (vertical_padding * 2)
        
        # Draw main container for todos with soft overlay
        self.draw_rounded_rectangle(
            draw,
            (todo_x, todo_y, todo_x + todo_section_width, todo_y + container_height),
            self.modules['card']['border_radius'],
            fill=(*self.colors['surface'], int(255 * self.colors['overlay_alpha']))
        )
        
        # Title section
        title_font = self.get_font('title')
        title_padding = self.modules['card']['padding']
        
        # Main title with accent color
        draw.text(
            (todo_x + title_padding, todo_y + title_padding),
            "Today's Focus",
            fill=self.colors['accent'],
            font=title_font
        )
        
        # Date subtitle
        date_y = todo_y + title_padding + int(self.typography['title']['size'] * self.typography['title']['line_height'])
        body_font = self.get_font('body')
        draw.text(
            (todo_x + title_padding, date_y),
            datetime.now().strftime("%A, %B %d, %Y"),
            fill=self.colors['text_secondary'],
            font=body_font
        )
        
        # Stats section
        completed_count = sum(1 for t in tasks if t['completed'])
        total_count = len(tasks)
        
        stats_y = date_y + int(self.typography['body']['size'] * self.typography['body']['line_height']) + self.grid_unit * 2
        
        # Progress summary with accent
        headline_font = self.get_font('headline')
        draw.text(
            (todo_x + title_padding, stats_y),
            f"{completed_count} of {total_count} completed",
            fill=self.colors['accent'],
            font=headline_font
        )
        
        # Task modules
        module_y = stats_y + int(self.typography['headline']['size'] * self.typography['headline']['line_height']) + self.section_spacing
        module_width = todo_section_width - title_padding * 2
        
        # Create task modules with uniform sizing
        visible_tasks = 0
        max_modules = self.max_visible_tasks  # Use configurable limit
        
        # Calculate available space for modules
        available_height = todo_y + container_height - module_y - title_padding - int(self.typography['body']['size'] * 3)
        max_possible_modules = available_height // (self.modules['card']['min_height'] + self.grid_unit * 2)
        actual_max_modules = min(max_modules, int(max_possible_modules))
        
        for i, task in enumerate(tasks[:actual_max_modules]):
            if module_y + self.modules['card']['min_height'] > todo_y + container_height - title_padding:
                break
            
            module_height = self.create_task_module(
                draw, task,
                todo_x + title_padding,
                module_y,
                module_width,
                completed_count,
                total_count
            )
            
            module_y += module_height
            visible_tasks += 1
        
        # Show remaining count if any
        if len(tasks) > visible_tasks:
            remaining_y = todo_y + container_height - title_padding - int(self.typography['body']['size'] * 2)
            draw.text(
                (todo_x + title_padding, remaining_y),
                f"+{len(tasks) - visible_tasks} more tasks",
                fill=self.colors['text_secondary'],
                font=body_font
            )
        
        # Footer with timestamp
        footer_y = todo_y + container_height - title_padding - self.typography['body']['size']
        draw.text(
            (todo_x + todo_section_width - title_padding - 100, footer_y),
            f"Updated {datetime.now().strftime('%H:%M')}",
            fill=self.colors['text_disabled'],
            font=body_font
        )
        
        # Save with high quality
        img.save(self.wallpaper_file, quality=95, optimize=True)
    
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
Todo Wallpaper Generator - Enhanced Design
==========================================
Watching: {self.todo_file}
Output: {self.wallpaper_file}
Resolution: {self.resolution}
AI Images: {'Enabled' if self.use_ai_images else 'Disabled'}
Design: Unified grid system with consistent spacing

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