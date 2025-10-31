import pygame
import os
from PIL import Image
import time
import math
import json

pygame.init()

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# --- TILEMAP SYSTEM ---
TILE_SIZE = 16

def load_tileset(tileset_name):
    """Load a tileset and extract all tiles from it."""
    tileset_img = pygame.image.load(os.path.join('Tilesets', f'{tileset_name}.png')).convert_alpha()
    tileset_width, tileset_height = tileset_img.get_size()
    tiles = []
    for y in range(0, tileset_height, TILE_SIZE):
        for x in range(0, tileset_width, TILE_SIZE):
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            tile = tileset_img.subsurface(rect).copy()
            tiles.append(tile)
    return tiles

def draw_tilemap(surface, tilemap, tiles):
    for row_idx, row in enumerate(tilemap):
        for col_idx, tile_idx in enumerate(row):
            if 0 <= tile_idx < len(tiles):
                surface.blit(tiles[tile_idx], (col_idx * TILE_SIZE, row_idx * TILE_SIZE))

# --- SCENE MANAGEMENT SYSTEM ---
class Scene:
    def __init__(self, name, tileset_name, tilemap, objects=None, items=None):
        """
        Create a scene with its own tileset, tilemap, and objects.
        
        Args:
            name: Scene identifier (e.g., "overworld", "cave", "house")
            tileset_name: Name of the tileset PNG file (without extension)
            tilemap: 2D array of tile indices
            objects: List of dicts with 'name', 'x', 'y' for objects to draw
            items: List of dicts with 'type', 'x', 'y' for item pickups
        """
        self.name = name
        self.tileset_name = tileset_name
        self.tiles = load_tileset(tileset_name)
        self.tilemap = tilemap
        # Initialize objects with runtime state (e.g., visibility)
        self.objects = []
        for obj in (objects or []):
            o = dict(obj)
            o.setdefault('visible', True)
            # normalize toggle key to lowercase string if provided
            if 'toggleKey' in o and isinstance(o['toggleKey'], str):
                o['toggleKey'] = o['toggleKey'].lower()
            self.objects.append(o)
        # Track per-scene items and their collected state
        self.items = []
        for it in (items or []):
            # Make a shallow copy and attach runtime state
            item = dict(it)
            item.setdefault('collected', False)
            self.items.append(item)
    
    def draw(self, surface, object_defs_by_tileset):
        """Draw the scene's tilemap and objects."""
        draw_tilemap(surface, self.tilemap, self.tiles)
        # Select object definitions for this scene's tileset
        obj_defs = object_defs_by_tileset.get(self.tileset_name, {})
        for obj in self.objects:
            if obj.get('visible', True):
                draw_object(
                    surface,
                    obj['name'],
                    obj['x'],
                    obj['y'],
                    self.tiles,
                    obj_defs,
                    scale=max(1, int(obj.get('scale', 1)))
                )

def load_scenes_from_json(filepath):
    """Load all scenes from a JSON file."""
    with open(filepath, 'r') as f:
        scenes_data = json.load(f)
    
    scenes = {}
    for scene_name, scene_info in scenes_data.items():
        scenes[scene_name] = Scene(
            name=scene_name,
            tileset_name=scene_info['tileset'],
            tilemap=scene_info['tilemap'],
            objects=scene_info.get('objects', []),
            items=scene_info.get('items', [])
        )
    return scenes

# Load scenes from JSON
scenes = load_scenes_from_json(os.path.join('Tilesets', 'scenes.json'))

# Set the current scene
current_scene = scenes['cave']

# Create a simple inventory system
class Inventory:
    def __init__(self):
        self.items = []
        self.visible = False  # Track if inventory is visible
        self.slot_size = 40
        self.slot_margin = 4
        self.slot_color = (64, 64, 64)  # Dark gray
        self.slot_border = (128, 128, 128)  # Light gray
        self.background = pygame.Surface((self.slot_size, self.slot_size))
        self.background.fill(self.slot_color)
        # Draw border
        pygame.draw.rect(self.background, self.slot_border, 
                        (0, 0, self.slot_size, self.slot_size), 2)

    def add_item(self, item):
        self.items.append(item)
        print(f"Picked up: {item}")  # Simple notification when item is picked up

    def draw(self, screen, item_image):
        # Draw inventory slots in top-left corner
        for i in range(max(3, len(self.items))):  # Always show at least 3 slots
            slot_x = 10 + (self.slot_size + self.slot_margin) * i
            slot_y = 10
            # Draw slot background
            screen.blit(self.background, (slot_x, slot_y))
            # If this slot has an item, draw the item
            if i < len(self.items):
                # Scale the item image to fit in the slot
                scaled_item = pygame.transform.scale(item_image, 
                    (self.slot_size - 8, self.slot_size - 8))
                # Center the item in the slot
                item_x = slot_x + 4
                item_y = slot_y + 4
                screen.blit(scaled_item, (item_x, item_y))

def load_gif_frames(file_path):
    frames = []
    durations = []
    with Image.open(file_path) as gif:
        for frame in range(gif.n_frames):
            gif.seek(frame)
            # Convert to RGBA to handle transparency
            frame_surface = pygame.image.fromstring(
                gif.convert("RGBA").tobytes(), gif.size, "RGBA"
            )
            frames.append(frame_surface)
            durations.append(gif.info['duration'] if 'duration' in gif.info else 100)
    return frames, durations

# Load all archer animations
PLAYER_SCALE = 0.6  # Set between 0.6 and 1.0 to make the player smaller
animation_data = {}

# Map archer GIF files to animation directions
archer_animation_map = {
    'static': 'Idle_east.gif',  # Default idle animation
    'north_east': 'archer_walk.gif',  # Walking up while facing east
    'north_west': 'archer_walk_west.gif',  # Walking up while facing west
    'south_east': 'archer_walk.gif',  # Walking down while facing east
    'south_west': 'archer_walk_west.gif',  # Walking down while facing west
    'east': 'archer_walk.gif',  # Walking right (reusing walk animation)
    'west': 'archer_walk_west.gif',   # Walking left
    'run_north_east': 'Run_east.gif',  # Running up while facing east
    'run_north_west': 'Run_west.gif',  # Running up while facing west
    'run_south_east': 'Run_east.gif',  # Running down while facing east
    'run_south_west': 'Run_west.gif',  # Running down while facing west
    'run_east': 'Run_east.gif',  # Running right
    'run_west': 'Run_west.gif'   # Running left
}

for direction, filename in archer_animation_map.items():
    frames, durations = load_gif_frames(os.path.join('Archer', filename))
    animation_data[direction] = {
        'frames': frames,
        'durations': durations,
        'current_frame': 0,
        'last_update': time.time() * 1000  # Convert to milliseconds
    }

# Load static facing images (using first frame of Idle animations)
facing_images = {}
# Load east idle
idle_east_frames, _ = load_gif_frames(os.path.join('Archer', 'Idle_east.gif'))
facing_images['east'] = idle_east_frames[0]

# Load west idle
idle_west_frames, _ = load_gif_frames(os.path.join('Archer', 'Idle_west.gif'))
facing_images['west'] = idle_west_frames[0]

# Track the last direction the player was facing
last_facing_direction = 'east'  # Default facing direction (east or west only)
last_horizontal_direction = 'east'  # Track last horizontal direction for north/south movement

# Scale animation frames if needed (before creating the player's rect)
def _scale_frames(frames, scale):
    if abs(scale - 1.0) < 1e-6:
        return frames
    scaled = []
    for f in frames:
        w, h = f.get_width(), f.get_height()
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        scaled.append(pygame.transform.scale(f, new_size))
    return scaled

if PLAYER_SCALE and abs(PLAYER_SCALE - 1.0) > 1e-6:
    for direction, data in animation_data.items():
        data['frames'] = _scale_frames(data['frames'], PLAYER_SCALE)
    # Also scale the facing images
    for direction in facing_images:
        img = facing_images[direction]
        w, h = img.get_width(), img.get_height()
        new_size = (max(1, int(w * PLAYER_SCALE)), max(1, int(h * PLAYER_SCALE)))
        facing_images[direction] = pygame.transform.scale(img, new_size)

# Movement speed (reduce this number to move slower)
PLAYER_SPEED = 2
PLAYER_RUN_SPEED = 4  # Running is faster than walking

# Collision settings
COLLISION_MARGIN = 4  # Pixels to shrink the player hitbox for more forgiving collision

# Start with static animation
current_animation = 'static'
player = animation_data[current_animation]['frames'][0].get_rect()
# Set the initial position (center of screen)
player.center = (265, 425)
# Create floating point position variables (use rect's topleft after scaling)
player_x = float(player.x)
player_y = float(player.y)

# Animation speed control
FRAME_RATE = 60

# Arrow animation settings (used for item indicators)
ARROW_AMPLITUDE = 10  # How many pixels up and down
ARROW_SPEED = 0.005  # Speed of bounce
arrow_base_y = 30  # Distance above the item

# Load item images (extendable for more item types)
sword_image = pygame.image.load(os.path.join('Items', 'sword.png'))
# Optional scaling example:
# sword_image = pygame.transform.scale(sword_image, (32, 32))
ITEM_IMAGES = {
    'sword': sword_image
}

# Create inventory
inventory = Inventory()

# Load object definitions grouped by tileset from JSON
with open(os.path.join('Tilesets', 'objects.json'), 'r') as f:
    object_defs_by_tileset = json.load(f)

# Cache for scaled tiles to avoid re-scaling every frame
_SCALED_TILES_CACHE = {}

def _get_scaled_tiles(tiles, scale):
    if scale == 1:
        return tiles
    key = (id(tiles), scale)
    cached = _SCALED_TILES_CACHE.get(key)
    if cached is not None:
        return cached
    scaled = [
        pygame.transform.scale(t, (TILE_SIZE * scale, TILE_SIZE * scale))
        for t in tiles
    ]
    _SCALED_TILES_CACHE[key] = scaled
    return scaled

def draw_object(surface, object_name, x, y, tiles, object_defs, scale=1):
    """
    Draws an object (multi-tile) at pixel position (x, y) using its definition from the JSON.
    Optionally scales the object by an integer factor (scale >= 1) to make it bigger.
    """
    obj = object_defs.get(object_name)
    if not obj:
        return
    scale = max(1, int(scale))
    chosen_tiles = _get_scaled_tiles(tiles, scale)
    step = TILE_SIZE * scale
    for row_idx, row in enumerate(obj):
        for col_idx, tile_idx in enumerate(row):
            if 0 <= tile_idx < len(chosen_tiles):
                surface.blit(chosen_tiles[tile_idx], (x + col_idx * step, y + row_idx * step))

def get_object_rect(object_name, x, y, object_defs, scale=1):
    """Compute the object's bounding rect based on its definition and scale."""
    obj = object_defs.get(object_name)
    if not obj:
        return pygame.Rect(x, y, 0, 0)
    scale = max(1, int(scale))
    height_tiles = len(obj)
    width_tiles = max((len(row) for row in obj), default=0)
    w = width_tiles * TILE_SIZE * scale
    h = height_tiles * TILE_SIZE * scale
    return pygame.Rect(x, y, w, h)

run = True
while run:
    # Draw the current scene (tilemap + objects)
    current_scene.draw(screen, object_defs_by_tileset)
    
    #screen.fill((0, 0, 0))  # Clear the screen with black color

    # Handle movement and animation
    key = pygame.key.get_pressed()
    current_animation = 'static'  # Default to static
    is_moving = False  # Track if player is actually moving
    is_running = key[pygame.K_SPACE]  # Check if spacebar is held for running
    
    # Store the old position in case we need to revert due to collision
    old_player_x = player_x
    old_player_y = player_y
    
    # Track which directions are being pressed
    moving_north = False
    moving_south = False
    moving_east = False
    moving_west = False
    
    # Determine movement speed based on running state
    current_speed = PLAYER_RUN_SPEED if is_running else PLAYER_SPEED
    
    # Update floating point position
    if key[pygame.K_a]:
        player_x -= current_speed
        moving_west = True
        last_horizontal_direction = 'west'
        is_moving = True
    if key[pygame.K_d]:
        player_x += current_speed
        moving_east = True
        last_horizontal_direction = 'east'
        is_moving = True
    if key[pygame.K_w]:
        player_y -= current_speed
        moving_north = True
        is_moving = True
    if key[pygame.K_s]:
        player_y += current_speed
        moving_south = True
        is_moving = True
    
    # Determine the animation based on movement direction and running state
    animation_prefix = 'run_' if is_running else ''
    
    if moving_east:
        current_animation = f'{animation_prefix}east'
        last_facing_direction = 'east'
    elif moving_west:
        current_animation = f'{animation_prefix}west'
        last_facing_direction = 'west'
    elif moving_north:
        # Use last horizontal direction for north movement
        current_animation = f'{animation_prefix}north_{last_horizontal_direction}'
        last_facing_direction = last_horizontal_direction
    elif moving_south:
        # Use last horizontal direction for south movement
        current_animation = f'{animation_prefix}south_{last_horizontal_direction}'
        last_facing_direction = last_horizontal_direction
    
    # Update the rect position from floating point position
    player.x = round(player_x)
    player.y = round(player_y)
    
    # Check collision with solid objects
    obj_defs = object_defs_by_tileset.get(current_scene.tileset_name, {})
    for obj in current_scene.objects:
        # Skip non-solid objects or invisible objects
        if not obj.get('solid', False):
            continue
        if not obj.get('visible', True):
            continue
        
        scale = max(1, int(obj.get('scale', 1)))
        obj_rect = get_object_rect(obj['name'], obj['x'], obj['y'], obj_defs, scale)
        
        # Create a smaller player hitbox for more forgiving collision
        player_hitbox = player.inflate(-COLLISION_MARGIN, -COLLISION_MARGIN)
        
        # Check if player collides with this solid object
        if player_hitbox.colliderect(obj_rect):
            # Collision detected - revert to old position
            player_x = old_player_x
            player_y = old_player_y
            player.x = round(player_x)
            player.y = round(player_y)
            is_moving = False  # Stop the walking animation
            break  # Stop checking other objects once we hit one

    # Handle animation
    current_time = time.time() * 1000
    anim = animation_data[current_animation]
    if current_time - anim['last_update'] > anim['durations'][anim['current_frame']]:
        anim['current_frame'] = (anim['current_frame'] + 1) % len(anim['frames'])
        anim['last_update'] = current_time

    # Draw the current animation frame or facing image
    if is_moving:
        # Show walking animation
        current_frame = animation_data[current_animation]['frames'][anim['current_frame']]
        screen.blit(current_frame, player)
    else:
        # Show static facing image based on last direction
        screen.blit(facing_images[last_facing_direction], player)

    # Draw and handle items for the current scene
    for item in getattr(current_scene, 'items', []):
        if item.get('collected'):
            continue
        item_type = item.get('type')
        img = ITEM_IMAGES.get(item_type)
        if not img:
            continue
        # Position from scene item definition (pixel coordinates)
        item_rect = img.get_rect(topleft=(item.get('x', 0), item.get('y', 0)))
        screen.blit(img, item_rect)

        # Bouncing arrow indicator
        arrow_offset = math.sin(time.time() * ARROW_SPEED * 1000) * ARROW_AMPLITUDE
        arrow_x = item_rect.centerx
        arrow_y = item_rect.top - arrow_base_y + arrow_offset
        arrow_points = [
            (arrow_x, arrow_y + 15),
            (arrow_x - 10, arrow_y),
            (arrow_x + 10, arrow_y)
        ]
        pygame.draw.polygon(screen, (255, 255, 0), arrow_points)

        # Pickup detection
        if player.colliderect(item_rect):
            item['collected'] = True
            # For now add a generic item token (1). Can extend to item ids later.
            inventory.add_item(1)

    # Check if R key is currently pressed (not just when it's first pressed)
    keys = pygame.key.get_pressed()
    inventory.visible = keys[pygame.K_r]

    # Handle other events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.KEYDOWN:
            # --- DEBUG HOTKEYS ---
            if event.key == pygame.K_F1:
                current_scene = scenes['overworld']
                player.center = (265, 425)
                player_x = float(player.x)
                player_y = float(player.y)
                print("[DEBUG] Jumped to overworld scene.")
            elif event.key == pygame.K_F2:
                current_scene = scenes['cave']
                player.center = (265, 425)
                player_x = float(player.x)
                player_y = float(player.y)
                print("[DEBUG] Jumped to cave scene.")
            elif event.key == pygame.K_F3:
                current_scene = scenes['house']
                player.center = (265, 425)
                player_x = float(player.x)
                player_y = float(player.y)
                print("[DEBUG] Jumped to house scene.")
            # Scene switching with number keys
            if event.key == pygame.K_1:
                current_scene = scenes['overworld']
                print("Switched to overworld")
            elif event.key == pygame.K_2:
                current_scene = scenes['cave']
                print("Switched to cave")
            elif event.key == pygame.K_3:
                current_scene = scenes['house']
                print("Switched to house")
            elif event.key == pygame.K_e:
                # Toggle nearest interactive object's visibility if within radius
                px, py = player.centerx, player.centery
                # find objects that are interactive (toggleable)
                for obj in current_scene.objects:
                    # If toggleKey specified, require it to be 'e' (default accepts any if missing)
                    toggle_key = obj.get('toggleKey')
                    if toggle_key is not None and toggle_key != 'e':
                        continue
                    if not obj.get('interactive', False):
                        continue
                    scale = max(1, int(obj.get('scale', 1)))
                    rect = get_object_rect(
                        obj['name'], obj['x'], obj['y'],
                        object_defs_by_tileset.get(current_scene.tileset_name, {}),
                        scale
                    )
                    cx, cy = rect.centerx, rect.centery
                    dx = px - cx
                    dy = py - cy
                    dist = math.hypot(dx, dy)
                    radius = obj.get('radius', 60)
                    if dist <= radius:
                        obj['visible'] = not obj.get('visible', True)
                        state = 'shown' if obj['visible'] else 'hidden'
                        print(f"Toggled {obj['name']} -> {state}")
                        break

    # After handling input, check for portal transitions on open doors
    for obj in getattr(current_scene, 'objects', []):
        portal = obj.get('portal')
        if not portal:
            continue
        # Require door to be open (invisible) to enter
        if obj.get('visible', True):
            continue
        scale = max(1, int(obj.get('scale', 1)))
        rect = get_object_rect(
            obj['name'], obj['x'], obj['y'],
            object_defs_by_tileset.get(current_scene.tileset_name, {}),
            scale
        )
        if player.colliderect(rect):
            target = portal.get('targetScene')
            if target and target in scenes:
                current_scene = scenes[target]
                # Move player to spawn position
                sx = int(portal.get('spawnX', player.centerx))
                sy = int(portal.get('spawnY', player.centery))
                player.center = (sx, sy)
                player_x = float(player.x)
                player_y = float(player.y)
                print(f"Entered scene '{target}' at ({sx}, {sy})")
            break

    # Only draw inventory while R is held down
    if inventory.visible:
        # Add a semi-transparent background when inventory is open
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)  # 128 for 50% transparency
        screen.blit(overlay, (0, 0))
        # Draw inventory with item images
        inventory.draw(screen, sword_image)

    pygame.display.update()
    clock.tick(FRAME_RATE)

pygame.quit()