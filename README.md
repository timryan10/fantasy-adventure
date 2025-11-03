# Pygame RPG Adventure

A 2D tile-based RPG built with Pygame. It features a camera-following archer, multi-layer Tiled maps (including infinite/chunked), proper tile flips/rotations, tile/object collisions, inventory, portals, and combat with bow shots and melee.

## Highlights

- Multi-layer Tiled map support (JSON/.tmj): base + decorations drawn in order
- Multi-tileset rendering with correct firstgid and Tiled flip/rotation flags
- Camera follows the player with viewport culling (fast rendering on large maps)
- Tile-based collisions from a dedicated layer (by name or property)
- Archer animations: walk/run/idle + attacks with non-looping attack/shot animations
- Ranged projectiles (arrows) collide with walls and despawn at range
- Inventory and interactive objects (doors/portals)
- Handy debug overlays and hotkeys

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd pygame1
```

2. Create a virtual environment (recommended):
```bash
python -m venv .venv
```

3. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Game

```bash
python index.py
```

## Controls

| Key | Action |
|-----|--------|
| W | Move North |
| A | Move West |
| S | Move South |
| D | Move East |
| SPACE (hold) | Run |
| E | Interact / Toggle nearby doors |
| R (hold) | Show inventory |
| J | Attack 1 (non-looping) |
| K | Shoot (spawns arrow at the end of the shot animation) |
| 1 / 2 / 3 / 4 | Switch to overworld / cave / house / cave_1 |
| F1 / F2 / F3 / F4 | Teleport to overworld / cave / house / cave_1 |
| F5 (hold) | Debug text overlay (coords, map size, margin) |
| F6 | Toggle collision grid overlay |
| F7 / F8 | Decrease / increase collision margin |

## Game Mechanics

### Movement
- **Walking**: Use WASD keys to move
- **Running**: Hold SPACE to run
- **Facing**: When moving north/south the last horizontal direction (east/west) is preserved

### Collision System
- Tile collisions come from any tile layer whose name contains "collision", "solid", or "wall" (case-insensitive) or has a layer property `collision=true` in Tiled
- Only tiles in those marked layers are solid; decoration layers are visual only
- Movement resolves per-axis against the tile grid for smooth sliding
- Solid objects (from object layers) can also block movement; invisible/open doors do not

### Inventory
- Walk over items to collect them automatically
- Items appear in your inventory slots
- Hold R to view your current inventory

### Scene Transitions & Portals
- Interact with doors using E to toggle visibility (open/close)
- Portals are defined as objects with a `portal` JSON property, e.g. `{ "targetScene": "overworld", "spawnX": 260, "spawnY": 500 }`
- By default, a portal only triggers when the related door/object is invisible (treated as "open"). You can set `visible=false` to make a portal always-on.

### Combat
- Press J for Attack 1 (plays once, no movement during the attack)
- Press K for a Shot; the arrow spawns when the shot animation finishes
- Arrows collide with solid tiles and despawn after a fixed range

## Project Structure

```
pygame1/
├── index.py              # Main game file
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── Archer/              # Archer character animations
│   ├── Idle_east.gif
│   ├── Idle_west.gif
│   ├── archer_walk.gif
│   ├── archer_walk_west.gif
│   ├── Run_east.gif
│   ├── Run_west.gif
│   └── ...
├── Items/               # Collectible item sprites
│   └── sword.png
├── Tilesets/            # Tilesets and scene data
│   ├── Overworld.png
│   ├── cave_1.png / cave_2.png / Inner.png ...
│   ├── objects.json     # Object definitions by tileset
│   └── scenes.json      # Scene configurations
├── Maps/                # Tiled source maps (.json/.tmj)
│   └── cave_1.json
└── tiled_converter.py   # Tiled → scene converter (used by the game at runtime)
```

## Configuration

### Adjusting Game Settings

Edit these constants in `index.py` to customize gameplay:

```python
PLAYER_SPEED = 2           # Walking speed
PLAYER_RUN_SPEED = 4       # Running speed
PLAYER_SCALE = 0.6         # Character size (0.0-1.0)
COLLISION_MARGIN = 6       # Hitbox shrink (higher = closer to walls). F7/F8 adjust at runtime.
ARROW_SPEED = 7            # Arrow speed (px/frame)
ARROW_RANGE = 480          # Max travel distance (px)
ARROW_SPAWN_OFFSET_Y = -4  # Fine alignment of arrow spawn relative to player center
```

### Authoring Maps in Tiled

- Use as many tile layers as you like; they render in order (topmost draws last)
- Create a Collision layer by naming it “Collision” (or include “solid”/“wall”) or add a boolean property `collision=true`
- Use object layers for doors, portals, and interactables
  - For portals, add a `portal` property with JSON: `{ "targetScene": "house", "spawnX": 260, "spawnY": 500 }`
- Place your exported `.json/.tmj` maps in the `Maps/` folder — the game will auto-load them on start

## Credits

- Built with [Pygame](https://www.pygame.org/)
- Character sprites: Archer animations
- Tileset assets: Custom tilesets

## License

This project is for educational purposes.

## Future Enhancements

- [ ] Enemies with health and hit reactions
- [ ] Projectile-enemy collisions + damage numbers
- [ ] NPC dialogue and quests
- [ ] Save/load game functionality
- [ ] Sound effects and music