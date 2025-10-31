# Pygame RPG Adventure

A 2D tile-based RPG game built with Pygame featuring an archer character, multiple scenes, inventory system, and interactive objects.

## Features

- **Multiple Scenes**: Explore different areas including overworld, caves, and interior locations
- **Archer Character**: Animated character with walking and running animations
- **Movement System**: 
  - Walk with WASD keys
  - Hold SPACE to run (faster movement)
  - Character maintains directional facing when moving north/south
- **Interactive Objects**: 
  - Open/close doors with E key
  - Portal system to travel between scenes
  - Collision detection with solid objects
- **Inventory System**: 
  - Collect items throughout the world
  - View inventory by holding R key
- **Debug Tools**: 
  - F1: Teleport to overworld
  - F2: Teleport to cave
  - F3: Teleport to house

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
| E | Interact/Toggle doors |
| R (hold) | Show inventory |
| F1 | Debug: Teleport to overworld |
| F2 | Debug: Teleport to cave |
| F3 | Debug: Teleport to house |

## Game Mechanics

### Movement
- **Walking**: Use WASD keys to move in four directions at normal speed
- **Running**: Hold SPACEBAR while moving to run at double speed
- **Directional Facing**: Character maintains left/right orientation when moving up and down

### Collision System
- Solid objects (walls, houses) block player movement
- Collision detection uses a smaller hitbox for more forgiving gameplay
- Invisible objects (like open doors) don't block movement

### Inventory
- Walk over items to collect them automatically
- Items appear in your inventory slots
- Hold R to view your current inventory

### Scene Transitions
- Interact with doors using E key to open them
- Walk through open doors to travel to connected scenes
- Each scene has unique tilesets and objects

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
└── Tilesets/            # Game tilesets and scene data
    ├── Overworld.png
    ├── cave.png
    ├── Inner.png
    ├── objects.json     # Object definitions by tileset
    └── scenes.json      # Scene configurations
```

## Configuration

### Adjusting Game Settings

Edit these constants in `index.py` to customize gameplay:

```python
PLAYER_SPEED = 2          # Walking speed
PLAYER_RUN_SPEED = 4      # Running speed
COLLISION_MARGIN = 8      # Collision hitbox padding
PLAYER_SCALE = 0.6        # Character size (0.0-1.0)
```

### Adding New Scenes

1. Add tileset image to `Tilesets/` folder
2. Define scene in `Tilesets/scenes.json`
3. Add object definitions in `Tilesets/objects.json`

## Credits

- Built with [Pygame](https://www.pygame.org/)
- Character sprites: Archer animations
- Tileset assets: Custom tilesets

## License

This project is for educational purposes.

## Future Enhancements

- [ ] Combat system using attack animations
- [ ] NPC dialogue system
- [ ] Quest system
- [ ] More items and inventory management
- [ ] Save/load game functionality
- [ ] Sound effects and music