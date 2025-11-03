#!/usr/bin/env python3
"""
Tiled Map Converter
Converts Tiled JSON/TMX exports to the game's scenes.json format.

Usage:
    python tiled_converter.py <tiled_map_file> <scene_name> [tileset_name]

Example:
    python tiled_converter.py Maps/overworld.json overworld Overworld
"""

import json
import sys
import os
import xml.etree.ElementTree as ET
import base64
import zlib
import struct


def parse_tmx(tmx_file):
    """Parse TMX (XML) format from Tiled."""
    tree = ET.parse(tmx_file)
    root = tree.getroot()
    
    map_data = {
        'width': int(root.get('width')),
        'height': int(root.get('height')),
        'tilewidth': int(root.get('tilewidth')),
        'tileheight': int(root.get('tileheight')),
        'layers': [],
        'tilesets': []
    }
    
    # Parse tilesets
    for tileset in root.findall('tileset'):
        ts_data = {
            'firstgid': int(tileset.get('firstgid')),
            'name': tileset.get('name'),
            'source': tileset.get('source', '')
        }
        map_data['tilesets'].append(ts_data)
    
    # Parse layers
    for layer in root.findall('layer'):
        layer_data = {
            'name': layer.get('name'),
            'width': int(layer.get('width')),
            'height': int(layer.get('height')),
            'type': 'tilelayer',
            'data': []
        }
        
        # Parse tile data
        data_elem = layer.find('data')
        encoding = data_elem.get('encoding', 'csv')
        
        if encoding == 'csv':
            csv_data = data_elem.text.strip()
            layer_data['data'] = [int(x) for x in csv_data.split(',')]
        elif encoding == 'base64':
            compression = data_elem.get('compression')
            decoded = base64.b64decode(data_elem.text.strip())
            if compression == 'zlib':
                decoded = zlib.decompress(decoded)
            # Unpack as unsigned integers (4 bytes each)
            layer_data['data'] = list(struct.unpack('<%dI' % (len(decoded) // 4), decoded))
        
        map_data['layers'].append(layer_data)
    
    # Parse object groups
    for objectgroup in root.findall('objectgroup'):
        og_data = {
            'name': objectgroup.get('name'),
            'type': 'objectgroup',
            'objects': []
        }
        
        for obj in objectgroup.findall('object'):
            obj_data = {
                'id': int(obj.get('id')),
                'name': obj.get('name', ''),
                'x': float(obj.get('x')),
                'y': float(obj.get('y')),
                'width': float(obj.get('width', 0)),
                'height': float(obj.get('height', 0)),
                'properties': {}
            }
            
            # Parse custom properties
            properties = obj.find('properties')
            if properties is not None:
                for prop in properties.findall('property'):
                    prop_name = prop.get('name')
                    prop_type = prop.get('type', 'string')
                    prop_value = prop.get('value')
                    
                    # Convert types
                    if prop_type == 'bool':
                        obj_data['properties'][prop_name] = prop_value.lower() == 'true'
                    elif prop_type == 'int':
                        obj_data['properties'][prop_name] = int(prop_value)
                    elif prop_type == 'float':
                        obj_data['properties'][prop_name] = float(prop_value)
                    else:
                        obj_data['properties'][prop_name] = prop_value
            
            og_data['objects'].append(obj_data)
        
        map_data['layers'].append(og_data)
    
    return map_data


def parse_json(json_file):
    """Parse JSON format from Tiled."""
    with open(json_file, 'r') as f:
        return json.load(f)


def convert_tiled_to_scene(tiled_data, scene_name, tileset_name=None):
    """Convert Tiled map data to game's scene format."""
    
    # Auto-detect tileset name from Tiled data if not provided
    if tileset_name is None and 'tilesets' in tiled_data and len(tiled_data['tilesets']) > 0:
        tileset_name = tiled_data['tilesets'][0].get('name', 'Overworld')
    elif tileset_name is None:
        tileset_name = 'Overworld'  # Default
    
    scene = {
        'tileset': tileset_name,
        'tilemap': [],   # Composite/flattened view for compatibility (top layers overwrite lower ones)
        'layers': [],    # List of per-layer tilemaps (2D arrays of GIDs)
        'objects': [],
        'items': []
    }

    # Capture all tilesets with their firstgid so runtime can render multi-tileset maps
    ts_info = []
    for ts in tiled_data.get('tilesets', []) or []:
        name = ts.get('name')
        if not name:
            src = ts.get('source', '')
            if src:
                name = os.path.splitext(os.path.basename(src))[0]
        if not name:
            continue
        ts_info.append({'name': name, 'firstgid': ts.get('firstgid', 1)})
    # Sort by firstgid ascending
    ts_info.sort(key=lambda t: t['firstgid'])
    if ts_info:
        scene['tilesets'] = ts_info
    
    # Collect all visible tile layers in order
    tile_layers = [
        layer for layer in tiled_data.get('layers', [])
        if layer.get('type') == 'tilelayer' and layer.get('visible', True)
    ]

    if tile_layers:
        # Determine if any layer uses chunks (infinite map)
        uses_chunks = any('chunks' in layer for layer in tile_layers)
        composed_layers = []
        width = 0
        height = 0
        if uses_chunks:
            # Compute global extents across all tilelayers' chunks
            all_chunks = []
            for layer in tile_layers:
                all_chunks.extend(layer.get('chunks', []))
            if not all_chunks:
                scene['layers'] = []
                scene['tilemap'] = []
                return scene
            min_x = min(c['x'] for c in all_chunks)
            min_y = min(c['y'] for c in all_chunks)
            max_x = max(c['x'] + c['width'] for c in all_chunks)
            max_y = max(c['y'] + c['height'] for c in all_chunks)
            width = max_x - min_x
            height = max_y - min_y
            print(f"[DEBUG] Assembled (multi-layer) tilemap size: {width}x{height} (min_x={min_x}, min_y={min_y})")
            # Build per-layer maps aligned to the same extents
            for layer in tile_layers:
                layer_map = [[0 for _ in range(width)] for _ in range(height)]
                for c in layer.get('chunks', []) or []:
                    cw, ch = c['width'], c['height']
                    cx, cy = c['x'] - min_x, c['y'] - min_y
                    data = c.get('data', [])
                    for r in range(ch):
                        for col in range(cw):
                            idx = r * cw + col
                            gid = data[idx] if idx < len(data) else 0
                            rr = cy + r
                            cc = cx + col
                            if 0 <= rr < height and 0 <= cc < width:
                                layer_map[rr][cc] = int(gid)
                composed_layers.append(layer_map)
        else:
            # Finite map: use the overall map width/height
            width = tiled_data.get('width', tile_layers[0].get('width'))
            height = tiled_data.get('height', tile_layers[0].get('height'))
            for layer in tile_layers:
                data = layer.get('data', [])
                layer_map = []
                for row in range(height):
                    row_data = []
                    for col in range(width):
                        idx = row * width + col
                        gid = data[idx] if idx < len(data) else 0
                        row_data.append(int(gid))
                    layer_map.append(row_data)
                composed_layers.append(layer_map)

        # Save per-layer maps
        scene['layers'] = composed_layers
        # Also capture layer names and properties (flattened)
        layer_names = [layer.get('name', '') for layer in tile_layers]
        layer_props = []
        for layer in tile_layers:
            props_dict = {}
            props = layer.get('properties') or []
            # Tiled JSON stores properties as list of {name,type,value}
            if isinstance(props, list):
                for p in props:
                    if isinstance(p, dict) and 'name' in p:
                        props_dict[p['name']] = p.get('value')
            elif isinstance(props, dict):
                props_dict = props
            layer_props.append(props_dict)
        scene['layer_names'] = layer_names
        scene['layer_props'] = layer_props
        # Also create a flattened composite for compatibility and sizing
        composite = [[0 for _ in range(width)] for _ in range(height)]
        for layer_map in composed_layers:
            for r in range(height):
                row_l = layer_map[r]
                row_c = composite[r]
                for c in range(width):
                    gid = row_l[c]
                    if gid:
                        row_c[c] = gid
        scene['tilemap'] = composite
    
    # Process object layers
    for layer in tiled_data.get('layers', []):
        if layer.get('type') == 'objectgroup':
            for obj in layer.get('objects', []):
                props = obj.get('properties', {})
                
                # Check if this is an item (has 'item_type' property)
                if 'item_type' in props:
                    item = {
                        'type': props.get('item_type'),
                        'x': int(obj.get('x', 0)),
                        'y': int(obj.get('y', 0))
                    }
                    scene['items'].append(item)
                else:
                    # Regular object
                    game_obj = {
                        'name': obj.get('name', 'unnamed'),
                        'x': int(obj.get('x', 0)),
                        'y': int(obj.get('y', 0))
                    }
                    
                    # Add optional properties
                    if 'scale' in props:
                        game_obj['scale'] = props['scale']
                    if 'solid' in props:
                        game_obj['solid'] = props['solid']
                    if 'visible' in props:
                        game_obj['visible'] = props['visible']
                    if 'interactive' in props:
                        game_obj['interactive'] = props['interactive']
                    if 'toggleKey' in props:
                        game_obj['toggleKey'] = props['toggleKey']
                    if 'portal' in props:
                        # Portal should be a JSON string
                        try:
                            game_obj['portal'] = json.loads(props['portal'])
                        except:
                            game_obj['portal'] = props['portal']
                    
                    scene['objects'].append(game_obj)
    
    return scene


def update_scenes_json(scene_name, scene_data, scenes_file='Tilesets/scenes.json'):
    """Update or add a scene to scenes.json."""
    
    # Load existing scenes
    if os.path.exists(scenes_file):
        with open(scenes_file, 'r') as f:
            scenes = json.load(f)
    else:
        scenes = {}
    
    # Update with new scene
    scenes[scene_name] = scene_data
    
    # Save back to file
    with open(scenes_file, 'w') as f:
        json.dump(scenes, f, indent=2)
    
    print(f"✓ Updated '{scene_name}' in {scenes_file}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python tiled_converter.py <tiled_map_file> <scene_name> [tileset_name]")
        print("\nExample:")
        print("  python tiled_converter.py Maps/overworld.json overworld Overworld")
        print("  python tiled_converter.py Maps/cave.tmx cave cave")
        sys.exit(1)
    
    tiled_file = sys.argv[1]
    scene_name = sys.argv[2]
    tileset_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(tiled_file):
        print(f"Error: File '{tiled_file}' not found!")
        sys.exit(1)
    
    print(f"Converting '{tiled_file}' to scene '{scene_name}'...")
    
    # Determine file type and parse
    if tiled_file.endswith('.tmx'):
        tiled_data = parse_tmx(tiled_file)
    elif tiled_file.endswith('.json') or tiled_file.endswith('.tmj'):
        tiled_data = parse_json(tiled_file)
    else:
        print("Error: Unsupported file format. Use .tmx, .json, or .tmj files.")
        sys.exit(1)
    
    # Convert to game format
    scene_data = convert_tiled_to_scene(tiled_data, scene_name, tileset_name)
    
    # Show summary
    print(f"\nScene Summary:")
    print(f"  Tileset: {scene_data['tileset']}")
    print(f"  Map size: {len(scene_data['tilemap'][0])}x{len(scene_data['tilemap'])} tiles")
    print(f"  Objects: {len(scene_data['objects'])}")
    print(f"  Items: {len(scene_data['items'])}")
    
    # Update scenes.json
    update_scenes_json(scene_name, scene_data)
    
    print(f"\n✓ Conversion complete! Your scene is ready to use in the game.")
    print(f"  Test it by pressing F1/F2/F3 or changing the initial scene in index.py")


if __name__ == '__main__':
    main()
