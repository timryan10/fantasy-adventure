# Pygame RPG Adventure

A 2D tile-based RPG built with Pygame. Features a sword-wielding character with Aseprite sprite sheet animations, enemy combat system, multi-layer Tiled maps, tile collisions, inventory, and portals.

## Highlights

- **Character System**: Lvl_1 sword character with directional animations (idle, walk, run, attack, walk_attack, run_attack)
- **Enemy AI**: Rat enemies with health, animations, and distance-based attack detection
- **Health System**: Visual health bars with gradient colors for both player and enemies
- **Combat Mechanics**: Melee attacks with single-target damage, attack cooldowns, and hit detection
- **Sprite Sheets**: Aseprite JSON Array format support for efficient animation loading
- Multi-layer Tiled map support (JSON/.tmj): base + decorations drawn in order
- Multi-tileset rendering with correct firstgid and Tiled flip/rotation flags
- Camera follows the player with viewport culling (fast rendering on large maps)
- Tile-based collisions from a dedicated layer (by name or property)
- Inventory and interactive objects (doors/portals)
- Debug overlays and hotkeys for testing

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
| J | Attack (melee sword attack) |
| H | Debug: Take 10 damage |
| G | Debug: Heal 15 HP |
| 1 / 2 / 3 / 4 / 5 | Switch to overworld / cave / house / cave_1 / cave_2 |
| F1 / F2 / F3 / F4 / F5 | Teleport to overworld / cave / house / cave_1 / cave_2 |
| F5 (hold, when not switching) | Debug text overlay (coords, map size, margin) |
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
- Press J for a melee sword attack (can attack while walking/running)
- Attack range: 40 pixels (distance-based collision detection)
- Each enemy can only be hit once per attack swing
- Enemies attack when within 30 pixels of the player
- Both player and enemies have health bars with gradient colors (green → yellow → red)

## Project Structure

```
pygame1/
├── index.py              # Main game file
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── tiled_converter.py    # Tiled → scene converter (used by the game at runtime)
├── TILED_SETUP.md        # Tiled map editor setup guide
├── Characters/           # Character sprites and animations
│   └── Lvl_1/           # Lvl_1 sword character animations
│       ├── Sword_Idle/  # Idle animations (4 directions)
│       ├── Sword_Walk/  # Walk animations (4 directions)
│       ├── Sword_Run/   # Run animations (4 directions)
│       ├── Attack/      # Attack animations (4 directions)
│       ├── Sword_Walk_Attack/  # Walk while attacking
│       ├── Sword_Run_Attack/   # Run while attacking
│       └── ...          # Each folder contains .json + .png sprite sheets
├── Enemies/             # Enemy sprites and animations
│   └── Rat1/           # Rat enemy animations
│       ├── Idle/       # Idle animations (4 directions)
│       ├── Walk/       # Walk animations (4 directions)
│       ├── Attack/     # Attack animations (4 directions)
│       ├── Hurt/       # Hurt animations (4 directions)
│       └── Death/      # Death animations (4 directions)
├── Items/               # Collectible item sprites
│   └── sword.png
├── Tilesets/            # Tilesets and scene data
│   ├── objects.json     # Object definitions by tileset
│   └── scenes.json      # Scene configurations
└── Maps/                # Tiled source maps (.json/.tmj)
    ├── cave_1.json
    └── cave_2.json
```

## Configuration

### Adjusting Game Settings

Edit these constants in `index.py` to customize gameplay:

```python
PLAYER_SPEED = 2           # Walking speed
PLAYER_RUN_SPEED = 4       # Running speed
PLAYER_SCALE = 0.6         # Character size (0.0-1.0)
COLLISION_MARGIN = 6       # Hitbox shrink (higher = closer to walls). F7/F8 adjust at runtime.

# Health & Combat
player_max_hp = 100        # Maximum player health
enemy_attack_range = 30    # Distance (px) enemies can attack from
player_attack_range = 40   # Distance (px) player can attack from
attack_damage = 10         # Damage dealt per hit
```

### Authoring Maps in Tiled

- Use as many tile layers as you like; they render in order (topmost draws last)
- Create a Collision layer by naming it “Collision” (or include “solid”/“wall”) or add a boolean property `collision=true`
- Use object layers for doors, portals, and interactables
  - For portals, add a `portal` property with JSON: `{ "targetScene": "house", "spawnX": 260, "spawnY": 500 }`
- Place your exported `.json/.tmj` maps in the `Maps/` folder — the game will auto-load them on start
  - Scene names are derived from filenames (e.g., `cave_2.json` becomes scene `cave_2`)
  - Use keys 1–5 or F1–F5 to switch/teleport to scenes that exist

### Troubleshooting

- Black window or extra window appears first: ensure you are running a single instance from one terminal. If you previously saw two windows, this has been fixed in the code by removing an accidental early loop.
- If a scene key (e.g., cave_2) doesn’t work: check the console log for "Scene 'cave_2' not found" and verify the file is in `Maps/` and named correctly.

## Technical Details

### Animation System
- Sprite sheets exported from Aseprite in JSON Array format
- Each animation has 4 directional variants (North, South, East, West)
- Supports looping and non-looping animations with frame durations
- Dynamic frame loading from JSON metadata

### Collision Detection
- Tile-based collision using Tiled map layers
- Distance-based combat collision (center-to-center calculation)
- Per-enemy hit flags prevent multi-hit per attack swing

## Credits

- Built with [Pygame](https://www.pygame.org/)
- Character sprites: Lvl_1 sword character (Aseprite sprite sheets)
- Enemy sprites: Rat1 enemy (Aseprite sprite sheets)
- Tileset assets: Custom tilesets

## License

This project is for educational purposes.

## Future Enhancements

- [ ] Enemy AI movement and pathfinding
- [ ] More enemy types and bosses
- [ ] Damage numbers popup on hit
- [ ] NPC dialogue and quests
- [ ] Save/load game functionality
- [ ] Sound effects and music
- [ ] Particle effects for attacks