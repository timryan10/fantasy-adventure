# Tiled Map Editor Setup Guide

This guide will help you set up Tiled Map Editor to visually design your game maps.

## Step 1: Install Tiled

1. Download Tiled from: **https://www.mapeditor.org/**
2. Choose your installer:
   - **Windows**: Download the `.msi` installer
   - **macOS**: Download the `.dmg` file
   - **Linux**: Use your package manager or download AppImage
3. Run the installer and follow the installation prompts

## Step 2: Create a New Tiled Project

1. Open Tiled Map Editor
2. Go to **File → New → New Project**
3. Save it as `pygame1.tiled-project` in your game folder
4. This keeps all your map settings organized

## Step 3: Import Your Tilesets

### For Overworld Tileset:
1. Go to **File → New → New Tileset**
2. Click **Browse** next to "Source"
3. Navigate to `Tilesets/Overworld.png` and select it
4. Set **Name**: `Overworld`
5. Set **Tile width**: `16`
6. Set **Tile height**: `16`
7. Click **Save As** and save it as `Tilesets/Overworld.tsx`

### Repeat for other tilesets:
- `Tilesets/cave.png` → Save as `cave.tsx`
- `Tilesets/Inner.png` → Save as `Inner.tsx`

## Step 4: Create Your First Map

1. Go to **File → New → New Map**
2. Configure the map:
   - **Orientation**: Orthogonal
   - **Tile layer format**: CSV or Base64 (uncompressed)
   - **Tile render order**: Right Down
   - **Map size**: 
     - Width: `37` tiles (for overworld)
     - Height: `41` tiles
   - **Tile size**: 
     - Width: `16` pixels
     - Height: `16` pixels
3. Click **Save As** and save as `Maps/overworld.tmx`

## Step 5: Design Your Map

### Adding the Tileset to Your Map:
1. In the **Tilesets** panel (bottom-right), click the tileset icon
2. Select **Add Tileset** → Choose `Overworld.tsx`

### Drawing Tiles:
1. Select the **Stamp Brush** tool (B key)
2. In the Tilesets panel, click a tile to select it
3. Click on the map canvas to place tiles
4. Use **Bucket Fill** tool (F key) for large areas
5. Use **Eraser** tool (E key) to remove tiles

### Layers (recommended):
1. **Ground Layer**: Base terrain (grass, dirt, floor)
2. **Objects Layer**: Trees, buildings, walls (mark as object layer)
3. **Collision Layer**: Mark solid areas (we'll use this for collision)

## Step 6: Add Objects (Houses, Trees, etc.)

### Creating an Object Layer:
1. **Layer → New → Object Layer**
2. Name it "Objects"
3. Right-click the layer → **Show/Hide Other Layers** to see ground below

### Placing Objects:
1. Select the **Insert Tile** tool (T key)
2. From Tilesets panel, select multiple tiles (click and drag)
3. Click on map to place the object
4. In the **Properties** panel, add custom properties:
   - `name` (string): "house", "tree", etc.
   - `scale` (int): `2` for 2x size
   - `solid` (bool): `true` for collision
   - `interactive` (bool): `true` for doors
   - `portal` (string): Portal JSON like `{"targetScene": "cave", "spawnX": 300, "spawnY": 300}`

## Step 7: Export Your Map

### Option 1: JSON Export (Recommended)
1. **File → Export As**
2. Choose format: **JSON map files (*.tmj *.json)**
3. Save to `Maps/overworld.json`

### Option 2: Keep as TMX
- Tiled's native `.tmx` format
- The converter script will handle both formats

## Step 8: Convert to Game Format

After creating your map in Tiled, use the converter script:

```bash
python tiled_converter.py Maps/overworld.json overworld
```

This will update your `Tilesets/scenes.json` with the new map data.

## Quick Tips

### Keyboard Shortcuts:
- **B**: Stamp Brush (draw tiles)
- **F**: Bucket Fill
- **E**: Eraser
- **R**: Select tool
- **T**: Insert Tile (for objects)
- **G**: Toggle grid
- **H**: Toggle tile layer visibility
- **Ctrl+Z**: Undo
- **Ctrl+Shift+Z**: Redo

### Best Practices:
1. **Use layers** to organize your map (ground, decorations, objects)
2. **Name your objects** clearly in the properties panel
3. **Save often** (Ctrl+S)
4. **Test in-game frequently** to see how it looks
5. **Use object templates** for repeated objects (houses, trees)

### Collision Setup:
1. Create a layer named "Collision"
2. Mark solid tiles
3. The converter will automatically add `"solid": true` to those objects

## Map Dimensions Reference

Your current maps:
- **Overworld**: 37 tiles wide × 41 tiles tall
- **Cave**: 37 tiles wide × 37 tiles tall  
- **House**: 37 tiles wide × 37 tiles tall

Each tile is **16×16 pixels**, so:
- Overworld screen: 592×656 pixels
- Cave/House screen: 592×592 pixels

## Troubleshooting

**Problem**: Tiles not showing up
- **Solution**: Make sure tile size is 16×16 in both map and tileset

**Problem**: Objects not appearing in game
- **Solution**: Verify object names match your `objects.json` definitions

**Problem**: Map looks different in game
- **Solution**: Check that layer order matches (bottom layer = background)

**Problem**: Converter script errors
- **Solution**: Ensure you exported as JSON format, not XML

## Next Steps

Once you're comfortable with Tiled:
1. Redesign your existing maps (overworld, cave, house)
2. Create new areas and scenes
3. Add more object types with custom properties
4. Experiment with multiple layers for depth

Happy mapping! 🗺️
