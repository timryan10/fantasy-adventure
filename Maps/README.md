# Maps Directory

This folder contains your Tiled map files (.tmx, .json, .tmj).

## Structure

- **\*.tmx** - Tiled native map format (XML-based)
- **\*.json / \*.tmj** - Tiled JSON export format
- **\*.tsx** - Tileset files (referenced by maps)

## Workflow

1. Create/edit maps in Tiled Map Editor
2. Save as `.tmx` (for editing) and export as `.json` (for conversion)
3. Run converter: `python tiled_converter.py Maps/yourmap.json scene_name`
4. The converter updates `Tilesets/scenes.json` automatically
5. Test in-game with debug keys (F1/F2/F3)

## Tips

- Keep `.tmx` files for future editing
- Export to `.json` for the converter
- Name your maps clearly (e.g., `overworld.tmx`, `cave_level1.tmx`)
- Back up your maps before major changes
