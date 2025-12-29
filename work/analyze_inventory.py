#!/usr/bin/env python3
"""
Inventory Cache Analyzer
Parses the Alchemy/Firestorm inventory cache and generates move plans.

Usage:
    python analyze_inventory.py <cache_file>
    
Outputs:
    - analysis/structure.md - Current inventory structure
    - analysis/root_items.md - Items at root that need sorting
    - plans/*.json - Move plans for each category
"""

import re
import json
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

@dataclass
class InventoryFolder:
    uuid: str
    name: str
    parent_uuid: str
    preferred_type: str = "-1"
    children: list = field(default_factory=list)
    items: list = field(default_factory=list)

@dataclass
class InventoryItem:
    uuid: str
    name: str
    parent_uuid: str
    item_type: str
    inv_type: str = ""

@dataclass
class MoveOperation:
    source_path: str
    source_uuid: str
    target_path: str
    item_name: str
    item_type: str
    reason: str

# System folder types (green folders)
SYSTEM_FOLDER_TYPES = {
    'animatn': 'Animations',
    'bodypart': 'Body Parts', 
    'callcard': 'Calling Cards',
    'clothing': 'Clothing',
    'current': 'Current Outfit',
    'favorite': 'Favorites',
    'gesture': 'Gestures',
    'landmark': 'Landmarks',
    'lstndfnd': 'Lost And Found',
    'material': 'Materials',
    'my_otfts': 'My Outfits',
    'notecard': 'Notecards',
    'object': 'Objects',
    'snapshot': 'Photo Album',
    'inbox': 'Received Items',
    'lsltext': 'Scripts',
    'settings': 'Settings',
    'sound': 'Sounds',
    'texture': 'Textures',
    'trash': 'Trash',
    'root_inv': 'My Inventory',
}

# Mapping of content types to target system folders
CONTENT_TO_SYSTEM_FOLDER = {
    # Hair
    'hair': 'Body Parts/Hair',
    'hairstyle': 'Body Parts/Hair',
    
    # Heads
    'head': 'Body Parts/Heads',
    'lelutka': 'Body Parts/Heads',
    'genus': 'Body Parts/Heads',
    'catwa': 'Body Parts/Heads',
    
    # Bodies
    'body': 'Body Parts/Bodies',
    'lara': 'Body Parts/Bodies',
    'reborn': 'Body Parts/Bodies',
    'maitreya': 'Body Parts/Bodies',
    'legacy': 'Body Parts/Bodies',
    
    # Skins
    'skin': 'Body Parts/Skins',
    'velour': 'Body Parts/Skins',
    'pepe skins': 'Body Parts/Skins',
    
    # Shapes
    'shape': 'Body Parts/Shapes',
    
    # Deformers
    'deformer': 'Body Parts/Bodies',
    'fixer': 'Body Parts/Bodies',
    'kuromori': 'Body Parts/Bodies',
    
    # Clothing
    'dress': 'Clothing',
    'pants': 'Clothing',
    'shirt': 'Clothing',
    'top': 'Clothing',
    'skirt': 'Clothing',
    'outfit': 'Clothing',
    'thong': 'Clothing',
    'panties': 'Clothing',
    'corset': 'Clothing/Corsets',
    
    # Hosiery
    'pantyhose': 'Clothing/Hosiery',
    'stockings': 'Clothing/Hosiery',
    'tights': 'Clothing/Hosiery',
    'facs': 'Clothing/Hosiery',
    
    # Shoes
    'shoes': 'Clothing/Shoes',
    'boots': 'Clothing/Shoes',
    'heels': 'Clothing/Shoes',
    
    # BDSM Equipment
    'hood': 'BDSM/Equipment',
    'armbinder': 'BDSM/Equipment',
    'gag': 'BDSM/Equipment',
    'muzzle': 'BDSM/Equipment',
    'blindfold': 'BDSM/Equipment',
    'straitjacket': 'BDSM/Equipment',
    'chastity': 'BDSM/Equipment',
    
    # BDSM Restraints
    'collar': 'BDSM/Restraints',
    'cuff': 'BDSM/Restraints',
    'cuffs': 'BDSM/Restraints',
    'leash': 'BDSM/Restraints',
    
    # BDSM Brands
    'kdc': 'BDSM',
    'ngw': 'BDSM',
    'biodoll': 'BDSM',
    
    # Animations
    'ao': 'Animations',
    'animation': 'Animations',
    'bento ao': 'Animations',
    'bodylanguage': 'Animations',
    
    # Materials
    'latex': 'Materials',
    'metal': 'Materials',
    
    # Utilities
    'teleporter': 'Objects/Utilities',
    'updater': 'Objects/Updaters',
    'update folder': 'Objects/Updaters',
}


def parse_cache_file(filepath: str) -> tuple[dict, dict]:
    """Parse the inventory cache file and return folders and items."""
    folders = {}  # uuid -> InventoryFolder
    items = []    # list of InventoryItem
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Parse folder (category)
            if "'type':'category'" in line:
                uuid_match = re.search(r"'cat_id':u([a-f0-9-]+)", line)
                name_match = re.search(r"'name':'([^']*)'", line)
                parent_match = re.search(r"'parent_id':u([a-f0-9-]+)", line)
                pref_match = re.search(r"'preferred_type':'([^']*)'", line)
                
                if uuid_match and name_match and parent_match:
                    folder = InventoryFolder(
                        uuid=uuid_match.group(1),
                        name=name_match.group(1),
                        parent_uuid=parent_match.group(1),
                        preferred_type=pref_match.group(1) if pref_match else '-1'
                    )
                    folders[folder.uuid] = folder
            
            # Parse item
            elif "'inv_type':" in line and "'type':'" in line:
                uuid_match = re.search(r"'item_id':u([a-f0-9-]+)", line)
                name_match = re.search(r"'name':'([^']*)'", line)
                parent_match = re.search(r"'parent_id':u([a-f0-9-]+)", line)
                type_match = re.search(r"'type':'([^']*)'", line)
                inv_type_match = re.search(r"'inv_type':'([^']*)'", line)
                
                if uuid_match and name_match and parent_match and type_match:
                    item = InventoryItem(
                        uuid=uuid_match.group(1),
                        name=name_match.group(1),
                        parent_uuid=parent_match.group(1),
                        item_type=type_match.group(1),
                        inv_type=inv_type_match.group(1) if inv_type_match else ''
                    )
                    items.append(item)
    
    # Build parent-child relationships
    for folder in folders.values():
        if folder.parent_uuid in folders:
            folders[folder.parent_uuid].children.append(folder.uuid)
    
    for item in items:
        if item.parent_uuid in folders:
            folders[item.parent_uuid].items.append(item)
    
    return folders, items


def get_folder_path(folders: dict, folder_uuid: str, max_depth: int = 10) -> str:
    """Get the full path of a folder."""
    parts = []
    current = folder_uuid
    depth = 0
    
    while current in folders and depth < max_depth:
        folder = folders[current]
        parts.insert(0, folder.name)
        if folder.parent_uuid == '00000000-0000-0000-0000-000000000000':
            break
        current = folder.parent_uuid
        depth += 1
    
    return '/'.join(parts)


def find_root_uuid(folders: dict) -> str:
    """Find the root 'My Inventory' folder UUID."""
    for uuid, folder in folders.items():
        if folder.preferred_type == 'root_inv':
            return uuid
    return None


def classify_folder(name: str) -> Optional[str]:
    """Determine where a folder should be sorted based on its name."""
    name_lower = name.lower()
    
    for keyword, target in CONTENT_TO_SYSTEM_FOLDER.items():
        if keyword in name_lower:
            return target
    
    return None


def generate_structure_report(folders: dict, root_uuid: str, output_path: Path):
    """Generate a markdown report of the inventory structure."""
    
    def print_tree(folder_uuid: str, indent: int = 0) -> list[str]:
        lines = []
        if folder_uuid not in folders:
            return lines
        
        folder = folders[folder_uuid]
        prefix = "  " * indent
        
        # Mark system folders
        is_system = folder.preferred_type != '-1'
        marker = "📗" if is_system else "📁"
        
        item_count = len(folder.items)
        child_count = len(folder.children)
        
        lines.append(f"{prefix}{marker} **{folder.name}** ({item_count} items, {child_count} subfolders)")
        
        # Only expand first 2 levels for root children
        if indent < 2:
            for child_uuid in sorted(folder.children, key=lambda u: folders[u].name if u in folders else ''):
                lines.extend(print_tree(child_uuid, indent + 1))
        
        return lines
    
    lines = ["# Inventory Structure\n"]
    lines.append("📗 = System folder (green)\n")
    lines.append("📁 = Custom folder\n\n")
    
    lines.extend(print_tree(root_uuid))
    
    output_path.write_text('\n'.join(lines))
    print(f"Structure report written to {output_path}")


def generate_root_items_report(folders: dict, root_uuid: str, output_path: Path):
    """Generate a report of items/folders at root that need sorting."""
    
    if root_uuid not in folders:
        print("Could not find root folder")
        return
    
    root = folders[root_uuid]
    
    lines = ["# Root Level Items Needing Organization\n"]
    lines.append("These folders are at the root level and should be sorted into system folders.\n\n")
    
    system_folders = []
    custom_folders = []
    
    for child_uuid in root.children:
        if child_uuid not in folders:
            continue
        child = folders[child_uuid]
        
        if child.preferred_type != '-1':
            system_folders.append(child)
        else:
            custom_folders.append(child)
    
    lines.append("## System Folders (Keep at root)\n")
    for folder in sorted(system_folders, key=lambda f: f.name):
        lines.append(f"- 📗 {folder.name}")
    
    lines.append("\n## Custom Folders (Need sorting)\n")
    lines.append("| Folder | Suggested Target | Reason |")
    lines.append("|--------|-----------------|--------|")
    
    for folder in sorted(custom_folders, key=lambda f: f.name):
        target = classify_folder(folder.name)
        if target:
            lines.append(f"| {folder.name} | {target} | Keyword match |")
        else:
            lines.append(f"| {folder.name} | *Manual review* | No match |")
    
    output_path.write_text('\n'.join(lines))
    print(f"Root items report written to {output_path}")


def generate_move_plans(folders: dict, root_uuid: str, output_dir: Path):
    """Generate move plan JSON files for each category."""
    
    if root_uuid not in folders:
        return
    
    root = folders[root_uuid]
    
    # Group folders by target
    by_target = defaultdict(list)
    manual_review = []
    
    for child_uuid in root.children:
        if child_uuid not in folders:
            continue
        child = folders[child_uuid]
        
        # Skip system folders
        if child.preferred_type != '-1':
            continue
        
        # Skip special folders that should stay at root
        if child.name in ['#Firestorm', '#RLV', 'BDSM', '_Demos', 'Boxed Items', 'Animation Overrides']:
            continue
        
        target = classify_folder(child.name)
        if target:
            by_target[target].append({
                'name': child.name,
                'uuid': child.uuid,
                'path': get_folder_path(folders, child.uuid),
                'item_count': len(child.items),
                'child_count': len(child.children)
            })
        else:
            manual_review.append({
                'name': child.name,
                'uuid': child.uuid,
                'path': get_folder_path(folders, child.uuid),
                'item_count': len(child.items),
                'child_count': len(child.children)
            })
    
    # Write a plan for each target category
    for target, folders_list in by_target.items():
        safe_name = target.replace('/', '_').replace(' ', '_')
        plan_file = output_dir / f"plan_{safe_name}.json"
        
        plan = {
            'target_path': target,
            'description': f"Move folders to {target}",
            'folders': folders_list,
            'status': 'pending'
        }
        
        plan_file.write_text(json.dumps(plan, indent=2))
        print(f"Plan written: {plan_file.name} ({len(folders_list)} folders)")
    
    # Write manual review list
    if manual_review:
        review_file = output_dir / "plan_MANUAL_REVIEW.json"
        plan = {
            'target_path': 'Objects/Pending Review',
            'description': 'Folders that need manual categorization',
            'folders': manual_review,
            'status': 'needs_review'
        }
        review_file.write_text(json.dumps(plan, indent=2))
        print(f"Manual review list written: {review_file.name} ({len(manual_review)} folders)")


def main():
    if len(sys.argv) < 2:
        # Default to the dump file
        cache_file = Path(__file__).parent.parent / "dump" / "a5fc0c7e-aef1-48b4-a395-94e74d818aa0.inv.llsd"
    else:
        cache_file = Path(sys.argv[1])
    
    if not cache_file.exists():
        print(f"Cache file not found: {cache_file}")
        sys.exit(1)
    
    print(f"Parsing cache file: {cache_file}")
    folders, items = parse_cache_file(str(cache_file))
    print(f"Found {len(folders)} folders and {len(items)} items")
    
    root_uuid = find_root_uuid(folders)
    if not root_uuid:
        print("Could not find root inventory folder")
        sys.exit(1)
    
    # Create output directories
    work_dir = Path(__file__).parent
    analysis_dir = work_dir / "analysis"
    plans_dir = work_dir / "plans"
    
    analysis_dir.mkdir(exist_ok=True)
    plans_dir.mkdir(exist_ok=True)
    
    # Generate reports
    generate_structure_report(folders, root_uuid, analysis_dir / "structure.md")
    generate_root_items_report(folders, root_uuid, analysis_dir / "root_items.md")
    generate_move_plans(folders, root_uuid, plans_dir)
    
    print("\nDone! Review the analysis and plans before executing.")


if __name__ == '__main__':
    main()

