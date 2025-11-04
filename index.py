import pygame
import os
import pathlib
import importlib
from PIL import Image
import time
import math
import json

pygame.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
# --- CAMERA SYSTEM ---
camera_x = 0
camera_y = 0
show_collision_overlay = False  # Toggle with F6

def clamp_camera_to_map(player_x, player_y, map_width, map_height):
    # Center camera on player, clamp to map edges
    cam_x = int(player_x - SCREEN_WIDTH // 2)
    cam_y = int(player_y - SCREEN_HEIGHT // 2)
    cam_x = max(0, min(cam_x, map_width - SCREEN_WIDTH))
    cam_y = max(0, min(cam_y, map_height - SCREEN_HEIGHT))
    return cam_x, cam_y
show_player_hitbox_overlay = False  # Toggle with F5

# --- TILEMAP SYSTEM ---
TILE_SIZE = 16

# Tiled GID flip flags (see Tiled documentation)
FLIPPED_HORIZONTALLY_FLAG = 0x80000000
FLIPPED_VERTICALLY_FLAG   = 0x40000000
FLIPPED_DIAGONALLY_FLAG   = 0x20000000

def load_tileset(tileset_name):
    """Load a tileset and extract all tiles from it."""
    # Resolve tileset image path robustly
    base_dir = 'Tilesets'
    candidate = os.path.join(base_dir, f'{tileset_name}.png')
    if not os.path.exists(candidate):
        # Try case-insensitive and prefix matches (e.g., 'cave' -> 'cave_1.png')
        try_name = tileset_name.lower()
        matches = []
        for fn in os.listdir(base_dir):
            if not fn.lower().endswith('.png'):
                continue
            name_no_ext = os.path.splitext(fn)[0].lower()
            if name_no_ext == try_name or name_no_ext.startswith(try_name):
                matches.append(os.path.join(base_dir, fn))
        if matches:
            matches.sort()
            candidate = matches[0]
            print(f"[WARN] Tileset '{tileset_name}.png' not found. Using '{os.path.basename(candidate)}' instead.")
        else:
            available = ', '.join(sorted([fn for fn in os.listdir(base_dir) if fn.lower().endswith('.png')]))
            raise FileNotFoundError(f"No file '{os.path.join(base_dir, tileset_name + '.png')}' found. Available tilesets: {available}")
    
    tileset_img = pygame.image.load(candidate).convert_alpha()
    tileset_width, tileset_height = tileset_img.get_size()
    
    tiles = []
    for y in range(0, tileset_height, TILE_SIZE):
        for x in range(0, tileset_width, TILE_SIZE):
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            tile = tileset_img.subsurface(rect).copy()
            tiles.append(tile)
    return tiles


def draw_tilemap_single(surface, tilemap, tiles, camera_x=0, camera_y=0):
    """Draw using a single tileset where tilemap indexes directly reference 'tiles'."""
    # Only draw tiles that are visible on screen
    start_col = max(0, camera_x // TILE_SIZE)
    end_col = min(len(tilemap[0]) if tilemap else 0, (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1)
    start_row = max(0, camera_y // TILE_SIZE)
    end_row = min(len(tilemap), (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1)
    
    for row_idx in range(start_row, end_row):
        row = tilemap[row_idx]
        for col_idx in range(start_col, min(end_col, len(row))):
            tile_idx = row[col_idx]
            if 0 <= tile_idx < len(tiles):
                surface.blit(tiles[tile_idx], (col_idx * TILE_SIZE - camera_x, row_idx * TILE_SIZE - camera_y))

def draw_tilemap_multi(surface, tilemap, tilesets, camera_x=0, camera_y=0):
    """Draw a tilemap whose cells are Tiled GIDs using multiple tilesets.

    tilesets: list of dicts [{'firstgid': int, 'tiles': [surfaces], 'name': str}], sorted by firstgid.
    """
    if not tilesets:
        print("[DEBUG] No tilesets provided to draw_tilemap_multi!")
        return
    
    # Only draw tiles that are visible on screen
    start_col = max(0, camera_x // TILE_SIZE)
    end_col = min(len(tilemap[0]) if tilemap else 0, (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1)
    start_row = max(0, camera_y // TILE_SIZE)
    end_row = min(len(tilemap), (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1)
    
    # Cache for transformed tiles to avoid per-frame rotate/flip costs
    # Keyed by (tiles_id, local_index, rot, flip_h, flip_v)
    if not hasattr(draw_tilemap_multi, "_transform_cache"):
        draw_tilemap_multi._transform_cache = {}
    _transform_cache = draw_tilemap_multi._transform_cache

    for row_idx in range(start_row, end_row):
        row = tilemap[row_idx]
        for col_idx in range(start_col, min(end_col, len(row))):
            gid = row[col_idx]
            if gid <= 0:
                continue  # empty
            # Extract Tiled flip/rotation flags and normalize GID
            flipped_h = bool(gid & FLIPPED_HORIZONTALLY_FLAG)
            flipped_v = bool(gid & FLIPPED_VERTICALLY_FLAG)
            flipped_d = bool(gid & FLIPPED_DIAGONALLY_FLAG)
            base_gid = gid & ~(FLIPPED_HORIZONTALLY_FLAG | FLIPPED_VERTICALLY_FLAG | FLIPPED_DIAGONALLY_FLAG)

            # Find tileset for gid: last tileset with firstgid <= base_gid
            chosen = None
            for ts in tilesets:
                if ts['firstgid'] <= base_gid:
                    chosen = ts
                else:
                    break
            if not chosen:
                continue
            local_index = base_gid - chosen['firstgid']
            if 0 <= local_index < len(chosen['tiles']):
                x_pos = col_idx * TILE_SIZE - camera_x
                y_pos = row_idx * TILE_SIZE - camera_y

                # Build a cached transformed surface based on Tiled flags
                base_tile = chosen['tiles'][local_index]

                # Apply Tiled flip/rotation flags using rotation-based mapping for R-rotations in Tiled:
                # Tiled encodes 90/180/270 rotations as combinations of the diagonal flag with H/V.
                # Common mapping (orthogonal):
                #  - 0°:  d=0, h=0, v=0        -> rot=0,   no flips
                #  - 90°: d=1, h=1, v=0        -> rot=-90 (90° CW), no flips
                #  - 180°:d=0, h=1, v=1        -> rot=180, no flips
                #  - 270°:d=1, h=0, v=1        -> rot=90  (90° CCW), no flips
                #  - d=1 only (transpose): approximate as rot=90 CCW + H flip
                h = flipped_h
                v = flipped_v
                rot = 0  # degrees CCW (pygame positive = CCW)
                if flipped_d:
                    if h and not v:
                        # 90° CW
                        rot = 270  # CCW equivalent of -90
                        h = False
                        v = False
                    elif v and not h:
                        # 270° CW (90° CCW)
                        rot = 90
                        h = False
                        v = False
                    elif h and v:
                        # 180°
                        rot = 180
                        h = False
                        v = False
                    else:
                        # Only diagonal (transpose) -> 90° CCW + H flip
                        rot = 90
                        h = True
                        v = False

                cache_key = (id(chosen['tiles']), local_index, rot, h, v)
                tile_surf = _transform_cache.get(cache_key)
                if tile_surf is None:
                    tile_surf = base_tile
                    if rot:
                        tile_surf = pygame.transform.rotate(tile_surf, rot)
                    if h or v:
                        tile_surf = pygame.transform.flip(tile_surf, h, v)
                    _transform_cache[cache_key] = tile_surf

                surface.blit(tile_surf, (x_pos, y_pos))

# --- SCENE MANAGEMENT SYSTEM ---
class Scene:
    def __init__(self, name, tileset_name, tilemap, objects=None, items=None, tilesets_info=None, min_x=0, min_y=0, layers=None, layer_names=None, layer_props=None):
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
        self.tilesets_info = tilesets_info or []  # [{'name','firstgid'}] for multi-tileset scenes
        self.tilemap = tilemap  # Composite/flattened tilemap (for sizing, fallback draw)
        self.layers = layers or []  # Optional list of per-layer tilemaps
        self.min_x = min_x
        self.min_y = min_y
        self.layer_names = layer_names or []
        self.layer_props = layer_props or []
        if self.tilesets_info:
            # Multi-tileset scene: load all referenced tilesets
            loaded = []
            for tsi in sorted(self.tilesets_info, key=lambda t: t.get('firstgid', 1)):
                name = tsi.get('name')
                if not name:
                    continue
                tiles = load_tileset(name)
                loaded.append({'name': name, 'firstgid': tsi.get('firstgid', 1), 'tiles': tiles})
            self._tilesets_loaded = loaded
            self.tiles = None
        else:
            # Single tileset
            self.tiles = load_tileset(tileset_name)
            self._tilesets_loaded = None
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
        # Build a collision grid from any layers marked for collision
        self._collision_grid = self._build_collision_grid()

    def _build_collision_grid(self):
        if not self.layers or not self.tilemap:
            return None
        height = len(self.tilemap)
        width = len(self.tilemap[0]) if height > 0 else 0
        if width == 0:
            return None
        # Determine which layer indices are collision layers (by name keyword or property 'collision'==True)
        chosen = set()
        for i, name in enumerate(self.layer_names or []):
            lname = (name or '').lower()
            props = self.layer_props[i] if (self.layer_props and i < len(self.layer_props)) else {}
            is_collision = (
                ('collision' in lname) or ('collide' in lname) or ('solid' in lname) or ('wall' in lname)
                or (isinstance(props, dict) and bool(props.get('collision')))
            )
            if is_collision:
                chosen.add(i)
        if not chosen:
            return None
        grid = [[False for _ in range(width)] for _ in range(height)]
        for i in chosen:
            if i >= len(self.layers):
                continue
            layer_map = self.layers[i]
            for r in range(min(height, len(layer_map))):
                row = layer_map[r]
                for c in range(min(width, len(row))):
                    if row[c]:
                        grid[r][c] = True
        return grid

    def is_solid_at_tile(self, tx, ty):
        if not self._collision_grid:
            return False
        if ty < 0 or tx < 0:
            return False
        if ty >= len(self._collision_grid) or tx >= len(self._collision_grid[0]):
            return False
        return self._collision_grid[ty][tx]

    def collides_rect_with_tiles(self, rect):
        if not self._collision_grid:
            return False
        start_tx = max(0, rect.left // TILE_SIZE)
        start_ty = max(0, rect.top // TILE_SIZE)
        end_tx = min(len(self._collision_grid[0]) - 1, (rect.right - 1) // TILE_SIZE)
        end_ty = min(len(self._collision_grid) - 1, (rect.bottom - 1) // TILE_SIZE)
        for ty in range(start_ty, end_ty + 1):
            for tx in range(start_tx, end_tx + 1):
                if self._collision_grid[ty][tx]:
                    return True
        return False
    
    def draw(self, surface, object_defs_by_tileset, camera_x=0, camera_y=0):
        """Draw the scene's tilemap and objects with camera offset."""
        if self._tilesets_loaded:
            if self.layers:
                # Draw each layer in order so decorations appear on top
                for layer_map in self.layers:
                    draw_tilemap_multi(surface, layer_map, self._tilesets_loaded, camera_x, camera_y)
            else:
                draw_tilemap_multi(surface, self.tilemap, self._tilesets_loaded, camera_x, camera_y)
        else:
            if self.layers:
                for layer_map in self.layers:
                    draw_tilemap_single(surface, layer_map, self.tiles, camera_x, camera_y)
            else:
                draw_tilemap_single(surface, self.tilemap, self.tiles, camera_x, camera_y)
        # Select object definitions for this scene's tileset
        obj_defs = object_defs_by_tileset.get(self.tileset_name, {})
        # Use the appropriate tiles for drawing objects
        tiles_for_objects = self._tilesets_loaded[0]['tiles'] if self._tilesets_loaded else self.tiles
        for obj in self.objects:
            if obj.get('visible', True):
                draw_object(
                    surface,
                    obj['name'],
                    obj['x'] - camera_x,
                    obj['y'] - camera_y,
                    tiles_for_objects,
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
            items=scene_info.get('items', []),
            tilesets_info=scene_info.get('tilesets'),
            layers=scene_info.get('layers'),
            layer_names=scene_info.get('layer_names'),
            layer_props=scene_info.get('layer_props')
        )
    return scenes

# Load scenes from JSON
scenes = load_scenes_from_json(os.path.join('Tilesets', 'scenes.json'))
 
# --- OPTIONAL: Load additional scenes directly from Tiled maps in Maps/ ---
def _normalize_tileset_name(name: str) -> str:
    """Map Tiled tileset names to actual PNG filenames in Tilesets/ (without extension)."""
    if not name:
        return 'Overworld'
    n = name.strip()
    # Return name as-is for cave_1, cave_2, etc.
    if n.lower() in ['cave_1', 'cave_2', 'cave1', 'cave2']:
        return n
    if n.lower().startswith('overworld'):
        return 'Overworld'
    if n.lower().startswith('inner'):
        return 'Inner'
    # Fallback: return as-is
    return n

def _load_tiled_maps_into_scenes(maps_dir: str):
    """Scan Maps/ for *.json/*.tmj and add them as scenes using the converter."""
    try:
        # Lazy import to avoid hard dependency if script is moved
        tc = importlib.import_module('tiled_converter')
    except Exception as e:
        print(f"[DEBUG] Skipping Tiled map import (tiled_converter not available): {e}")
        return
    if not os.path.isdir(maps_dir):
        return
    for fname in os.listdir(maps_dir):
        if not (fname.endswith('.json') or fname.endswith('.tmj')):
            continue
        fpath = os.path.join(maps_dir, fname)
        try:
            # Parse tiled data
            tiled_data = tc.parse_json(fpath)
            # Detect tileset name from Tiled (first tileset) and normalize to actual PNG name
            detected = None
            if isinstance(tiled_data, dict):
                ts_list = tiled_data.get('tilesets') or []
                if ts_list:
                    ts0 = ts_list[0]
                    detected = ts0.get('name')
                    if not detected:
                        # Derive from source (e.g., 'cave_2.tsx' -> 'cave_2')
                        src = ts0.get('source', '')
                        if src:
                            detected = os.path.splitext(os.path.basename(src))[0]
            tileset_name = _normalize_tileset_name(detected or 'Overworld')
            # Scene name from file stem
            scene_name = os.path.splitext(fname)[0]
            # Convert to our scene dict
            scene_dict = tc.convert_tiled_to_scene(tiled_data, scene_name, tileset_name)
            # Get min_x and min_y from debug output or scene_dict if available
            min_x = tiled_data.get('min_x', 0)
            min_y = tiled_data.get('min_y', 0)
            # If tilemap is chunked, try to infer min_x/min_y from chunks
            if 'layers' in tiled_data:
                for layer in tiled_data['layers']:
                    if 'chunks' in layer:
                        min_x = min((c['x'] for c in layer['chunks']), default=0)
                        min_y = min((c['y'] for c in layer['chunks']), default=0)
                        break
            scenes[scene_name] = Scene(
                name=scene_name,
                tileset_name=scene_dict.get('tileset', tileset_name),
                tilemap=scene_dict['tilemap'],
                objects=scene_dict.get('objects', []),
                items=scene_dict.get('items', []),
                tilesets_info=scene_dict.get('tilesets'),
                min_x=min_x,
                min_y=min_y,
                layers=scene_dict.get('layers'),
                layer_names=scene_dict.get('layer_names'),
                layer_props=scene_dict.get('layer_props')
            )
            # Debug: Count non-empty tiles
            non_empty = sum(1 for row in scene_dict['tilemap'] for tile in row if tile > 0)
            total = len(scene_dict['tilemap']) * len(scene_dict['tilemap'][0]) if scene_dict['tilemap'] else 0
            print(f"[DEBUG] Loaded Tiled scene '{scene_name}' (tileset='{tileset_name}') from {fname}")
            print(f"[DEBUG] Map size: {len(scene_dict['tilemap'][0]) if scene_dict['tilemap'] else 0}x{len(scene_dict['tilemap'])} tiles, {non_empty}/{total} non-empty")
        except Exception as e:
            print(f"[DEBUG] Failed to import Tiled map {fname}: {e}")

# Attempt to load any Tiled maps from Maps/
_load_tiled_maps_into_scenes('Maps')
print("[DEBUG] Scenes loaded:", ", ".join(scenes.keys()))



# Set the current scene (change here if you want to start in a different one)
current_scene = scenes.get('cave_1', scenes.get('cave'))

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
    frames, durations = load_gif_frames(os.path.join('Characters', 'Archer', filename))
    animation_data[direction] = {
        'frames': frames,
        'durations': durations,
        'current_frame': 0,
        'last_update': time.time() * 1000,  # ms
        'loop': True
    }

# Optional combat animations (non-looping), loaded if present
def _maybe_add_animation(key, filename, loop=False):
    path = os.path.join('Characters', 'Archer', filename)
    if os.path.exists(path):
        frames, durations = load_gif_frames(path)
        animation_data[key] = {
            'frames': frames,
            'durations': durations,
            'current_frame': 0,
            'last_update': time.time() * 1000,
            'loop': loop
        }

# Primary attack (melee/close) and shots (ranged)
_maybe_add_animation('attack1_east', 'Attack_1_east.gif', loop=False)
_maybe_add_animation('attack1_west', 'Attack_1_west.gif', loop=False)
_maybe_add_animation('shot1_east', 'Shot_1_east.gif', loop=False)
_maybe_add_animation('shot1_west', 'Shot_1_west.gif', loop=False)
# Shot 2 files use slightly different naming
_maybe_add_animation('shot2_east', 'Shot_2.gif', loop=False)
_maybe_add_animation('shot2_west', 'Shot_2_west.gif', loop=False)

# Load static facing images (using first frame of Idle animations)
facing_images = {}
# Load east idle
idle_east_frames, _ = load_gif_frames(os.path.join('Characters', 'Archer', 'Idle_east.gif'))
facing_images['east'] = idle_east_frames[0]

# Load west idle
idle_west_frames, _ = load_gif_frames(os.path.join('Characters', 'Archer', 'Idle_west.gif'))
facing_images['west'] = idle_west_frames[0]

# Track the last direction the player was facing
last_facing_direction = 'east'  # Default facing direction (east or west only)
last_horizontal_direction = 'east'  # Track last horizontal direction for north/south movement

# Attack state
is_attacking = False
current_attack = None  # e.g., 'attack1_east', 'shot1_west'

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
COLLISION_MARGIN = 0  # Pixels to shrink the player hitbox for more forgiving collision (higher = closer to walls)

# Start with static animation
current_animation = 'static'
player = animation_data[current_animation]['frames'][0].get_rect()
# Set the initial position (center of screen, will be adjusted for map offset)
player.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

# Create floating point position variables (use rect's topleft after scaling)
player_x = float(player.x)
player_y = float(player.y)
# Offset player spawn by negative chunk origin if present
# This converts from screen-relative position to map-absolute position
if hasattr(current_scene, 'min_x') and hasattr(current_scene, 'min_y'):
    # Calculate map center in pixels
    map_width = len(current_scene.tilemap[0]) * TILE_SIZE if current_scene.tilemap else SCREEN_WIDTH
    map_height = len(current_scene.tilemap) * TILE_SIZE if current_scene.tilemap else SCREEN_HEIGHT
    # Spawn player at the center of the actual map
    player_x = 354
    player_y = 1130
    print(f"[DEBUG] Spawning player at map center: ({player_x}, {player_y})")
else:
    # For non-chunked maps, keep the original spawn position
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
ARROW_SPEED = 7
ARROW_RANGE = 480  # pixels
# Fine-tune spawn alignment so the arrow appears centered on the character/bow
ARROW_SPAWN_OFFSET_X_EAST = 0
ARROW_SPAWN_OFFSET_X_WEST = 0
ARROW_SPAWN_OFFSET_Y = -4

# Load projectile images
arrow_east_img = pygame.image.load(os.path.join('Characters', 'Archer', 'Arrow_east.png')).convert_alpha()
arrow_west_img = pygame.image.load(os.path.join('Characters', 'Archer', 'Arrow_west.png')).convert_alpha()

# Active projectiles
projectiles = []  # each: {x,y,vx,vy,img,dist}

def spawn_arrow(facing: str, origin_rect: pygame.Rect):
    """Spawn an arrow projectile from player's center, in facing direction."""
    if facing not in ('east', 'west'):
        facing = 'east'
    img = arrow_east_img if facing == 'east' else arrow_west_img
    # Center the arrow on the character, with fine-tune offsets
    cx, cy = origin_rect.centerx, origin_rect.centery
    x = cx - img.get_width() // 2 + (ARROW_SPAWN_OFFSET_X_EAST if facing == 'east' else ARROW_SPAWN_OFFSET_X_WEST)
    y = cy - img.get_height() // 2 + ARROW_SPAWN_OFFSET_Y
    speed = ARROW_SPEED if facing == 'east' else -ARROW_SPEED
    projectiles.append({'x': float(x), 'y': float(y), 'vx': float(speed), 'vy': 0.0, 'img': img, 'dist': 0.0})
_COL_TILE_SURF = None  # cached semi-transparent tile for collision overlay

def _get_collision_tile_surface():
    global _COL_TILE_SURF
    if _COL_TILE_SURF is None:
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        surf.fill((255, 0, 0, 90))  # semi-transparent red
        _COL_TILE_SURF = surf
    return _COL_TILE_SURF

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
    # Clear the screen
    screen.fill((24, 24, 24))
    # Calculate map pixel size
    map_width = len(current_scene.tilemap[0]) * TILE_SIZE if current_scene.tilemap else SCREEN_WIDTH
    map_height = len(current_scene.tilemap) * TILE_SIZE if current_scene.tilemap else SCREEN_HEIGHT
    # Update camera position to follow player
    camera_x, camera_y = clamp_camera_to_map(player_x, player_y, map_width, map_height)

    # Draw the current scene (tilemap + objects) with camera
    current_scene.draw(screen, object_defs_by_tileset, camera_x, camera_y)

    # Optional: draw collision overlay on top of map layers (under player)
    if show_collision_overlay and hasattr(current_scene, '_collision_grid') and current_scene._collision_grid:
        grid = current_scene._collision_grid
        grid_h = len(grid)
        grid_w = len(grid[0]) if grid_h else 0
        if grid_w and grid_h:
            start_col = max(0, camera_x // TILE_SIZE)
            end_col = min(grid_w, (camera_x + SCREEN_WIDTH) // TILE_SIZE + 1)
            start_row = max(0, camera_y // TILE_SIZE)
            end_row = min(grid_h, (camera_y + SCREEN_HEIGHT) // TILE_SIZE + 1)
            cell_surf = _get_collision_tile_surface()
            for ry in range(start_row, end_row):
                row = grid[ry]
                y = ry * TILE_SIZE - camera_y
                for rx in range(start_col, end_col):
                    if row[rx]:
                        x = rx * TILE_SIZE - camera_x
                        screen.blit(cell_surf, (x, y))

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

    # Update floating point position (skip while attacking)
    if not is_attacking:
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

    # --- Tile collision resolution (axis-aligned) ---
    dx = player_x - old_player_x
    dy = player_y - old_player_y
    # Base rect at old position
    base_rect = player.copy()
    base_rect.topleft = (round(old_player_x), round(old_player_y))
    hitbox = base_rect.inflate(-COLLISION_MARGIN, -COLLISION_MARGIN)
    # Horizontal
    if abs(dx) > 0:
        test_rect = hitbox.copy()
        test_rect.x += int(round(dx))
        if current_scene and hasattr(current_scene, 'collides_rect_with_tiles') and current_scene.collides_rect_with_tiles(test_rect):
            player_x = old_player_x  # block horizontal move
            dx = 0
        else:
            player_x = old_player_x + dx
    # Vertical (use possibly-updated x)
    if abs(dy) > 0:
        test_rect = hitbox.copy()
        test_rect.x = int(round(player_x))
        test_rect.y += int(round(dy))
        if current_scene and hasattr(current_scene, 'collides_rect_with_tiles') and current_scene.collides_rect_with_tiles(test_rect):
            player_y = old_player_y  # block vertical move
            dy = 0
        else:
            player_y = old_player_y + dy

    # Determine the animation based on movement direction and running state
    animation_prefix = 'run_' if is_running else ''

    if not is_attacking and moving_east:
        current_animation = f'{animation_prefix}east'
        last_facing_direction = 'east'
    elif not is_attacking and moving_west:
        current_animation = f'{animation_prefix}west'
        last_facing_direction = 'west'
    elif not is_attacking and moving_north:
        # Use last horizontal direction for north movement
        current_animation = f'{animation_prefix}north_{last_horizontal_direction}'
        last_facing_direction = last_horizontal_direction
    elif not is_attacking and moving_south:
        # Use last horizontal direction for south movement
        current_animation = f'{animation_prefix}south_{last_horizontal_direction}'
        last_facing_direction = last_horizontal_direction
    elif is_attacking and current_attack:
        current_animation = current_attack

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

        # Create a smaller player hitbox for more forgiving collision (world coordinates)
        player_hitbox = player.inflate(-COLLISION_MARGIN, -COLLISION_MARGIN)
        # Check if player collides with this solid object (use world coordinates for both)
        if player_hitbox.colliderect(obj_rect):
            # Collision detected - revert to old position
            player_x = old_player_x
            player_y = old_player_y
            player.x = round(player_x)
            player.y = round(player_y)
            is_moving = False  # Stop the walking animation
            break  # Stop checking other objects once we hit one

    # Update projectiles (movement + tile collisions) BEFORE handling animations/drawing
    if projectiles:
        remaining = []
        for p in projectiles:
            # Move
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['dist'] += abs(p['vx']) + abs(p['vy'])
            # Build rect in world coords for collision
            img = p['img']
            rect = pygame.Rect(int(p['x']), int(p['y']), img.get_width(), img.get_height())
            # Tile collision
            if hasattr(current_scene, 'collides_rect_with_tiles') and current_scene.collides_rect_with_tiles(rect):
                continue  # discard projectile on impact
            # Range limit
            if p['dist'] >= ARROW_RANGE:
                continue
            remaining.append(p)
        projectiles[:] = remaining

    # Handle animation
    current_time = time.time() * 1000
    anim = animation_data[current_animation]
    if current_time - anim['last_update'] > anim['durations'][anim['current_frame']]:
        next_frame = anim['current_frame'] + 1
        if anim.get('loop', True):
            anim['current_frame'] = next_frame % len(anim['frames'])
        else:
            if next_frame < len(anim['frames']):
                anim['current_frame'] = next_frame
            else:
                # Non-looping animation ended
                ended_attack = current_attack if is_attacking else None
                anim['current_frame'] = len(anim['frames']) - 1
                # Spawn projectile at the end of shot animations
                if ended_attack and ended_attack.startswith('shot'):
                    spawn_arrow(last_facing_direction, player)
                if is_attacking:
                    is_attacking = False
                    current_attack = None
                    # Reset to static; facing image will be used below
                    current_animation = 'static'
                    # Reset for next time we play this attack
                    anim['current_frame'] = 0
        anim['last_update'] = current_time

    # Draw projectiles (map-relative), under the player so player appears above
    if projectiles:
        for p in projectiles:
            screen.blit(p['img'], (int(p['x']) - camera_x, int(p['y']) - camera_y))

    # Draw the current animation frame or facing image
    if is_attacking and current_attack:
        attack_anim = animation_data[current_attack]
        frame = attack_anim['frames'][attack_anim['current_frame']]
        screen.blit(frame, player.move(-camera_x, -camera_y))
    elif is_moving:
        # Show walking/running animation
        current_frame_img = animation_data[current_animation]['frames'][anim['current_frame']]
        screen.blit(current_frame_img, player.move(-camera_x, -camera_y))

    else:
        # Show static facing image based on last direction
        screen.blit(facing_images[last_facing_direction], player.move(-camera_x, -camera_y))

    # Draw player hitbox overlay if enabled (after player is drawn)
    if show_player_hitbox_overlay:
        hitbox = player.copy().inflate(-COLLISION_MARGIN, -COLLISION_MARGIN)
        hitbox_rect = pygame.Rect(hitbox.x - camera_x, hitbox.y - camera_y, hitbox.width, hitbox.height)
        hitbox_surface = pygame.Surface((hitbox.width, hitbox.height), pygame.SRCALPHA)
        hitbox_surface.fill((0, 255, 0, 100))  # semi-transparent green
        screen.blit(hitbox_surface, hitbox_rect)

    # Draw player hitbox overlay if enabled (after player is drawn)
    if show_player_hitbox_overlay:
        hitbox = player.copy().inflate(-COLLISION_MARGIN, -COLLISION_MARGIN)
        hitbox_rect = pygame.Rect(hitbox.x - camera_x, hitbox.y - camera_y, hitbox.width, hitbox.height)
        hitbox_surface = pygame.Surface((hitbox.width, hitbox.height), pygame.SRCALPHA)
        hitbox_surface.fill((0, 255, 0, 100))  # semi-transparent green
        screen.blit(hitbox_surface, hitbox_rect)

    # Draw and handle items for the current scene
    for item in getattr(current_scene, 'items', []):
        if item.get('collected'):
            continue
        item_type = item.get('type')
        img = ITEM_IMAGES.get(item_type)
        if not img:
            continue
        # Position from scene item definition (pixel coordinates)
        item_rect = img.get_rect(topleft=(item.get('x', 0) - camera_x, item.get('y', 0) - camera_y))
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
        if player.move(-camera_x, -camera_y).colliderect(item_rect):
            item['collected'] = True
            # For now add a generic item token (1). Can extend to item ids later.
            inventory.add_item(1)

    # Check if R key is currently pressed (not just when it's first pressed)
    keys = pygame.key.get_pressed()
    inventory.visible = keys[pygame.K_r]

    # Debug overlay (press F5 to toggle)
    if keys[pygame.K_F5]:
        font = pygame.font.Font(None, 24)
        debug_texts = [
            f"Player: ({int(player_x)}, {int(player_y)}) | Tile: ({int(player_x//TILE_SIZE)}, {int(player_y//TILE_SIZE)})",
            f"Camera: ({camera_x}, {camera_y})",
            f"Map size: {map_width}x{map_height}px ({map_width//TILE_SIZE}x{map_height//TILE_SIZE} tiles)",
            f"Collision margin: {COLLISION_MARGIN} px"
        ]
        for i, text in enumerate(debug_texts):
            surf = font.render(text, True, (255, 255, 0))
            screen.blit(surf, (10, SCREEN_HEIGHT - 100 + i * 25))

    # Handle other events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.KEYDOWN:
            # --- DEBUG HOTKEYS ---
            if event.key == pygame.K_F6:
                show_collision_overlay = not show_collision_overlay
                print(f"[DEBUG] Collision overlay: {'ON' if show_collision_overlay else 'OFF'}")
                
            if event.key == pygame.K_F7:
                # Decrease collision margin (down to 0)
                COLLISION_MARGIN = max(0, COLLISION_MARGIN - 1)
                print(f"[DEBUG] Collision margin -> {COLLISION_MARGIN} px")
            if event.key == pygame.K_F8:
                # Increase collision margin (cap at 12)
                COLLISION_MARGIN = min(12, COLLISION_MARGIN + 1)
                print(f"[DEBUG] Collision margin -> {COLLISION_MARGIN} px")

            # --- COMBAT HOTKEYS ---
            if not is_attacking:
                if event.key == pygame.K_j and ('attack1_east' in animation_data or 'attack1_west' in animation_data):
                    # Primary attack
                    face = last_facing_direction
                    key_name = f"attack1_{face}"
                    if key_name in animation_data:
                        current_attack = key_name
                        is_attacking = True
                        animation_data[current_attack]['current_frame'] = 0
                        animation_data[current_attack]['last_update'] = time.time() * 1000
                elif event.key == pygame.K_k and ('shot1_east' in animation_data or 'shot1_west' in animation_data):
                    # Shot 1
                    face = last_facing_direction
                    key_name = f"shot1_{face}"
                    # Fallback to shot2 if shot1 not available on this side
                    if key_name not in animation_data and f"shot2_{face}" in animation_data:
                        key_name = f"shot2_{face}"
                    if key_name in animation_data:
                        current_attack = key_name
                        is_attacking = True
                        animation_data[current_attack]['current_frame'] = 0
                        animation_data[current_attack]['last_update'] = time.time() * 1000
                        # Arrow will be spawned when the shot animation finishes

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
            elif event.key == pygame.K_F5:
                if 'cave_2' in scenes:
                    current_scene = scenes['cave_2']
                    player.center = (265, 425)
                    player_x = float(player.x)
                    player_y = float(player.y)
                    print("[DEBUG] Jumped to cave_2 scene.")
                else:
                    print("[DEBUG] Scene 'cave_2' not found.")
            elif event.key == pygame.K_F4:
                if 'cave_1' in scenes:
                    current_scene = scenes['cave_1']
                    player.center = (265, 425)
                    player_x = float(player.x)
                    player_y = float(player.y)
                    print("[DEBUG] Jumped to cave_1 scene.")
                else:
                    print("[DEBUG] Scene 'cave_1' not found.")
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
            elif event.key == pygame.K_4:
                if 'cave_1' in scenes:
                    current_scene = scenes['cave_1']
                    print("Switched to cave_1")
                else:
                    print("Scene 'cave_1' not found")
            elif event.key == pygame.K_5:
                if 'cave_2' in scenes:
                    current_scene = scenes['cave_2']
                    print("Switched to cave_2")
                else:
                    print("Scene 'cave_2' not found")
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