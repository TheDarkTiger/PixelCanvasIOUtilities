import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from PIL import Image, ImageTk
import io
import time
import math
from typing import Dict, Tuple, List

PIXELCANVAS_TILE_SIZE = 1024

# ============= DATA FETCHER MODULE =============

def fetch_json_data(local: bool = False, save: bool = False) -> Dict:
    """Download and parse the !data.json file from GitHub"""
    url = "https://raw.githubusercontent.com/PixelAtlas/Minimap/master/templates/!data.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = json.loads(response.text)
        if save:
            with open("!data.json", "w") as writeFile :
                json.dump(data, writeFile)
        return data
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch template data: {e}")
        return {"Templates": {}}

def fetch_template_image(template_name: str, local: bool = False, save: bool = False) -> Image.Image:
    """Download a template PNG from GitHub"""
    url = f"https://raw.githubusercontent.com/PixelAtlas/Minimap/master/templates/{template_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        img = Image.open(io.BytesIO(response.content))
        if save:
            img.save(template_name)
        return img
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch template: {e}")
        return None

def fetch_canvas_tile(x: int, y: int, timestamp: int) -> Image.Image:
    """Download a 1024x1024 tile from pixelcanvas.io"""
    url = f"https://pixelcanvas.io/tiles/{x}/{y}/{timestamp}.png"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        if response.content:
            return Image.open(io.BytesIO(response.content)).convert("RGBA")
        else:
            raise Exception("Couldn't download a useable tile image from the canvas")
        
    except Exception as e:
        print(f"Failed to fetch tile at {x},{y}: {e}")
        return None

# ============= IMAGE PROCESSOR MODULE =============
def calculate_required_tiles(x: int, y: int, width: int, height: int) -> List[Tuple[int, int]]:
    """Calculate which 1024x1024 tiles are needed for the given rectangle"""
    # Find the tile coordinates for corners
    left_tile = math.floor(x / PIXELCANVAS_TILE_SIZE) * PIXELCANVAS_TILE_SIZE
    top_tile = math.floor(y / PIXELCANVAS_TILE_SIZE) * PIXELCANVAS_TILE_SIZE
    right_tile = math.floor((x + width - 1) / PIXELCANVAS_TILE_SIZE) * PIXELCANVAS_TILE_SIZE
    bottom_tile = math.floor((y + height - 1) / PIXELCANVAS_TILE_SIZE) * PIXELCANVAS_TILE_SIZE
    
    tiles = []
    for tile_x in range(left_tile, right_tile + 1, PIXELCANVAS_TILE_SIZE):
        for tile_y in range(top_tile, bottom_tile + 1, PIXELCANVAS_TILE_SIZE):
            tiles.append((tile_x, tile_y))
    
    return tiles

def combine_and_crop_tiles(tiles_coords: List[Tuple[int, int]], 
                          template_x: int, template_y: int, 
                          template_width: int, template_height: int,
                          white_bg_enabled: bool) -> Image.Image:
    """Combine tiles and crop to template area"""
    if not tiles_coords:
        return None
    
    # Set the background color
    if white_bg_enabled:
        background_color = (255, 255, 255, 255)
    else:
        background_color = (158, 189, 255, 255)
    
    # Find bounds of all tiles
    min_x = min(coord[0] for coord in tiles_coords)
    min_y = min(coord[1] for coord in tiles_coords)
    max_x = max(coord[0] for coord in tiles_coords) + PIXELCANVAS_TILE_SIZE
    max_y = max(coord[1] for coord in tiles_coords) + PIXELCANVAS_TILE_SIZE
    
    # Create combined image
    combined_width = max_x - min_x
    combined_height = max_y - min_y
    combined = Image.new('RGBA', (combined_width, combined_height), background_color)
    
    try:
        # Download and paste each tile
        timestamp = int(time.time())
        for tile_x, tile_y in tiles_coords:
            tile_img = fetch_canvas_tile(math.floor(tile_x/PIXELCANVAS_TILE_SIZE), math.floor(tile_y/PIXELCANVAS_TILE_SIZE), timestamp)
            
            if tile_img:
                # Calculate where to paste this tile in the combined image
                paste_x = tile_x - min_x
                paste_y = tile_y - min_y
                #combined.paste(tile_img, (paste_x, paste_y))
                combined.alpha_composite(tile_img, dest=(paste_x, paste_y))
        
        # Crop to template area
        crop_left = template_x - min_x
        crop_top = template_y - min_y
        crop_right = crop_left + template_width
        crop_bottom = crop_top + template_height
        
        return combined.crop((crop_left, crop_top, crop_right, crop_bottom))
    except Exception as e:
        print(f"Failed to combine and crop tiles: {e}")
        return None

def compare_images(template: Image.Image, canvas: Image.Image, white_background: bool = True) -> tuple[Image.Image, int, int]:
    """Compare template and canvas, return difference mask, diff count, and total non-transparent pixels"""
    # Convert both to RGBA for comparison
    template = template.convert('RGBA')
    canvas = canvas.convert('RGBA')
    
    # Create difference mask and counters
    width, height = template.size
    diff_mask = Image.new('L', (width, height), 0)
    diff_count = 0
    total_pixels = 0
    
    for x in range(width):
        for y in range(height):
            template_pixel = template.getpixel((x, y))
            canvas_pixel = canvas.getpixel((x, y))
            
            # Skip transparent pixels in template
            if template_pixel[3] == 0:  # Alpha channel is 0 (transparent)
                continue
            
            total_pixels += 1  # Count non-transparent pixels
            
            # Handle transparent canvas pixels
            if (canvas_pixel[3] == 0) or (canvas_pixel[:3]==(158, 189, 255)):  # Canvas pixel is transparent
                if white_background:
                    # Treat transparent canvas pixel as white
                    canvas_pixel = (255, 255, 255, 255)
                else:
                    # Mark as different since template has non-transparent pixel
                    diff_mask.putpixel((x, y), 255)
                    diff_count += 1
                    continue
            
            # Check if pixels match (comparing RGB, ignoring alpha)
            if template_pixel[:3] != canvas_pixel[:3]:
                diff_mask.putpixel((x, y), 255)  # Mark as different
                diff_count += 1  # Count the difference
    
    return diff_mask, diff_count, total_pixels

def create_result_image(canvas: Image.Image, diff_mask: Image.Image) -> Image.Image:
    """Convert canvas to grayscale and apply red highlighting"""
    # Convert to grayscale
    gray = canvas.convert('L')
    # Convert back to RGB to add red
    result = gray.convert('RGB')
    
    width, height = result.size
    for x in range(width):
        for y in range(height):
            if diff_mask.getpixel((x, y)) > 0:
                # Set to bright red
                result.putpixel((x, y), (255, 0, 0))
    
    return result

# ============= GUI MODULE =============

class PixelCanvasChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("PixelCanvas Template Checker")
        self.root.geometry("800x600")
        
        # Maximize the window
        self.root.state('zoomed')  # Works on Windows
        # For Linux/Mac, use: self.root.attributes('-zoomed', True)
        
        self.template_data = {}
        self.current_image = None
        self.original_image = None  # Store original for zooming
        self.zoom_level = 1.0
        self.scroll_timer = None
        self.current_template_info = None  # Store template info for coordinates
        
        # White background checkbox variable
        self.white_background_var = tk.BooleanVar(value=True)  # Default to checked
        
        # Create GUI elements
        self.setup_gui()
        
        # Load template data
        self.load_templates()
    
    def setup_gui(self):
        """Create the GUI layout"""
        # Top frame for controls
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Select Template:").pack(side=tk.LEFT, padx=5)
        
        self.template_var = tk.StringVar()
        self.template_dropdown = ttk.Combobox(control_frame, textvariable=self.template_var, 
                                              state="readonly", width=50)
        self.template_dropdown.pack(side=tk.LEFT, padx=5)
        self.template_dropdown.bind("<<ComboboxSelected>>", self.on_template_selected)
        
        # White background checkbox
        self.white_bg_checkbox = ttk.Checkbutton(control_frame, 
                                                 text="White Background", 
                                                 variable=self.white_background_var)
        self.white_bg_checkbox.pack(side=tk.LEFT, padx=15)
        
        # Zoom level display
        self.zoom_label = ttk.Label(control_frame, text="Zoom: 100%")
        self.zoom_label.pack(side=tk.LEFT, padx=20)
        
        # Copy button on the right
        self.copy_button = ttk.Button(control_frame, text="Copy Image to Clipboard", 
                                      command=self.copy_to_clipboard, state="disabled")
        self.copy_button.pack(side=tk.RIGHT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(self.root, text="Loading templates...")
        self.status_label.pack(pady=7)
        
        # Completeness label
        self.complete_label = tk.Text(self.root, height=1, wrap="none", 
                                     relief="flat", state="normal", 
                                     bg=self.root.cget("bg"),
                                     font=("TkDefaultFont",),  # Match default font
                                     width=30,  # Set specific width
                                     cursor="arrow")  # Normal cursor instead of text cursor
        self.complete_label.tag_configure("center", justify="center")
        self.complete_label.insert("1.0", "0 Errors | 0% Complete", "center")
        self.complete_label.config(state="disabled")
        self.complete_label.pack(pady=5)
        
        # Coordinate display label
        self.coord_label = ttk.Label(self.root, text="Coordinates: (--, --)")
        self.coord_label.pack(pady=2)
        
        # Image display frame with scrollbars
        self.image_frame = ttk.Frame(self.root)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure grid for proper scrollbar placement
        self.image_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)
        
        # Canvas for image display
        self.image_canvas = tk.Canvas(self.image_frame, bg="gray")
        self.image_canvas.grid(row=0, column=0, sticky="nsew")
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(self.image_frame, orient=tk.VERTICAL, 
                                    command=self.image_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self.image_frame, orient=tk.HORIZONTAL, 
                                    command=self.image_canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.image_canvas.configure(yscrollcommand=v_scrollbar.set, 
                                   xscrollcommand=h_scrollbar.set)
        
        # Bind mouse events
        self.image_canvas.bind("<Motion>", self.on_mouse_move)
        self.image_canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.image_canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.image_canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
    
    def load_templates(self):
        """Load template data from GitHub"""
        data = fetch_json_data()
        self.template_data = data.get("Templates", {})
        
        # Populate dropdown
        template_names = []
        for key, value in self.template_data.items():
            display_name = f"{key} ({value['name']})"
            template_names.append(display_name)
        
        self.template_dropdown['values'] = template_names
        
        if template_names:
            self.status_label.config(text="Templates loaded. Select one to begin.")
        else:
            self.status_label.config(text="No templates found.")
    
    def on_template_selected(self, event=None):
        """Handle template selection"""
        if not self.template_var.get():
            return
        
        # Get template key from selection
        selected = self.template_var.get()
        template_key = selected.split(" (")[0]
        
        if template_key not in self.template_data:
            return
        
        template_info = self.template_data[template_key]
        self.status_label.config(text="Processing template...")
        self.root.update()
        
        # Process the template
        self.process_template(template_info)
    
    def process_template(self, template_info):
        """Main processing pipeline"""
        try:
            # Store template info for coordinate calculation
            self.current_template_info = template_info
            self.zoom_level = 1.0  # Reset zoom
            self.zoom_label.config(text="Zoom: 100%")
            
            # Step 1: Download template
            self.status_label.config(text="Downloading template...")
            self.root.update()
            template_img = fetch_template_image(template_info['name'])
            if not template_img:
                return
            
            # Step 2: Calculate required tiles
            x = template_info['x']
            y = template_info['y']
            width = template_info['width']
            height = template_info['height']
            
            tiles_needed = calculate_required_tiles(x, y, width, height)
            white_bg_enabled = self.white_background_var.get()
            
            # Step 3: Download and combine tiles
            self.status_label.config(text=f"Downloading {len(tiles_needed)} tile(s)...")
            self.root.update()
            canvas_img = combine_and_crop_tiles(tiles_needed, x, y, width, height, white_bg_enabled)
            if not canvas_img:
                self.status_label.config(text="Failed to download canvas tiles.")
                return
            
            # Step 4: Compare images with white background setting
            self.status_label.config(text="Comparing images...")
            self.root.update()
            diff_mask, diff_count, total_count = compare_images(template_img, canvas_img, white_bg_enabled)
            
            # Step 5: Create result image
            result_img = create_result_image(canvas_img, diff_mask)
            
            # Store original image for zooming
            self.original_image = result_img
            
            # Step 6: Display result
            self.display_image(result_img)
            self.status_label.config(text="Comparison complete. Red pixels show differences.")
            
            # Step 7: Calculate Completeness
            percent_complete = 100 * (total_count - diff_count)/total_count
            if diff_count > 0 and percent_complete > 99.9:
                percent_complete = 99.9
            self.complete_label.config(state="normal")
            self.complete_label.delete("1.0", "end")
            self.complete_label.insert("1.0", f" {diff_count} Errors | {percent_complete:.1f}% Complete ", "center")
            self.complete_label.config(state="disabled")
            
            
            # Enable copy button
            self.copy_button.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process template: {e}")
            self.status_label.config(text="Error processing template.")
    
    def display_image(self, image):
        """Display the result image in the canvas"""
        # Apply zoom if needed
        if self.zoom_level != 1.0:
            new_width = int(image.width * self.zoom_level)
            new_height = int(image.height * self.zoom_level)
            image = image.resize((new_width, new_height), Image.Resampling.NEAREST)
        
        # Convert to PhotoImage for tkinter
        self.current_image = ImageTk.PhotoImage(image)
        
        # Clear canvas
        self.image_canvas.delete("all")
        
        # Display image and store the canvas item ID
        self.image_item = self.image_canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
        
        # Update scroll region
        self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))
        
        # Add click/drag panning
        self.image_canvas.bind("<Button-1>", self.start_pan)
        self.image_canvas.bind("<B1-Motion>", self.do_pan)

    def start_pan(self, event):
        """Start panning when mouse button is pressed"""
        self.image_canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        """Pan the image as mouse is dragged"""
        self.image_canvas.scan_dragto(event.x, event.y, gain=1)
    
    def on_mouse_move(self, event):
        """Handle mouse movement to show coordinates"""
        if not self.current_template_info or not self.original_image:
            return
        
        # Get canvas coordinates
        canvas_x = self.image_canvas.canvasx(event.x)
        canvas_y = self.image_canvas.canvasy(event.y)
        
        # Convert to image pixel coordinates considering zoom
        pixel_x = int(canvas_x / self.zoom_level)
        pixel_y = int(canvas_y / self.zoom_level)
        
        # Check if within image bounds
        if 0 <= pixel_x < self.original_image.width and 0 <= pixel_y < self.original_image.height:
            # Convert to site coordinates
            site_x = self.current_template_info['x'] + pixel_x
            site_y = self.current_template_info['y'] + pixel_y
            self.coord_label.config(text=f"Coordinates: ({site_x}, {site_y})")
        else:
            self.coord_label.config(text="Coordinates: (--, --)")
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if not self.original_image:
            return
        
        # Determine scroll direction
        if event.num == 4 or event.delta > 0:  # Scroll up
            scale_factor = 1.25
        elif event.num == 5 or event.delta < 0:  # Scroll down
            scale_factor = 0.8
        else:
            return
        
        # Update zoom level (limit between 0.5x and 20x)
        new_zoom = self.zoom_level * scale_factor
        new_zoom = max(0.5, min(20.0, new_zoom))
        
        if new_zoom != self.zoom_level:
            self.zoom_level = new_zoom
            self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")
            
            # Cancel previous timer if it exists
            if self.scroll_timer:
                self.root.after_cancel(self.scroll_timer)
            
            # Set new timer to update image after 100ms of no scrolling
            self.scroll_timer = self.root.after(200, self.update_zoomed_image)

    def update_zoomed_image(self):
        """Update the image display after scrolling stops"""
        if not self.original_image:
            return
            
        # Store scroll position
        x_pos = self.image_canvas.xview()[0]
        y_pos = self.image_canvas.yview()[0]
        
        # Redisplay image with new zoom
        self.display_image(self.original_image)
        
        # Restore scroll position
        self.image_canvas.xview_moveto(x_pos)
        self.image_canvas.yview_moveto(y_pos)
        
        self.scroll_timer = None
    
    def copy_to_clipboard(self):
        """Copy the current image to clipboard as PNG"""
        if not self.original_image:
            return
        
        try:
            # Save image to a temporary file and copy to clipboard
            # This works cross-platform
            import tempfile
            import os
            
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = tmp.name
                self.original_image.save(temp_path, 'PNG')
            
            # Try to use platform-specific clipboard handling
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windows-specific clipboard handling
                try:
                    from PIL import ImageGrab
                    import win32clipboard
                    from io import BytesIO
                    
                    output = BytesIO()
                    self.original_image.save(output, 'BMP')
                    data = output.getvalue()[14:]  # Remove BMP header
                    output.close()
                    
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    win32clipboard.CloseClipboard()
                    
                    self.status_label.config(text="Image copied to clipboard!")
                except ImportError:
                    # Fallback message if win32clipboard not available
                    self.status_label.config(text=f"Image saved to: {temp_path}")
                    messagebox.showinfo("Copy to Clipboard", 
                                      f"Please install 'pywin32' for clipboard support.\nImage saved to: {temp_path}")
            else:
                # For Linux/Mac, just save the file
                self.status_label.config(text=f"Image saved to: {temp_path}")
                messagebox.showinfo("Copy to Clipboard", 
                                  f"Image saved to: {temp_path}\n(Direct clipboard copy requires additional libraries)")
            
            # Clean up temp file after a delay (let clipboard access it first)
            if system == "Windows":
                self.root.after(1000, lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy image: {e}")

# ============= MAIN APPLICATION =============

def main():
    root = tk.Tk()
    icon = tk.PhotoImage(file="PixelAtlas.png")
    root.iconphoto(True, icon) 
    app = PixelCanvasChecker(root)
    root.mainloop()

if __name__ == "__main__":
    main()