#!/usr/bin/env python3
"""
Merge Folders Script
Merges contents of custom folders INTO existing system folders.

This handles cases like:
- Apparel/Hair/* -> Body Parts/Hair/*
- Apparel/Clothing/* -> Clothing/*
- Avatar/Body Parts/* -> Body Parts/*

Usage:
    python merge_folders.py [--dry-run]
"""

import json
import sys
import time
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime

# Merge operations to perform
MERGE_OPERATIONS = [
    {
        'source': 'My Inventory/Apparel/Hair',
        'target': 'My Inventory/Body Parts/Hair',
        'description': 'Merge Apparel/Hair into Body Parts/Hair'
    },
    {
        'source': 'My Inventory/Apparel/Clothing',
        'target': 'My Inventory/Clothing',
        'description': 'Merge Apparel/Clothing into Clothing'
    },
    {
        'source': 'My Inventory/Apparel/Shoes',
        'target': 'My Inventory/Clothing/Shoes',
        'description': 'Merge Apparel/Shoes into Clothing/Shoes'
    },
    {
        'source': 'My Inventory/Avatar/Body Parts',
        'target': 'My Inventory/Body Parts',
        'description': 'Merge Avatar/Body Parts into Body Parts'
    },
]

CONFIG = None


def load_config():
    """Load Corrade config."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


def send_command(**params) -> dict:
    """Send a command to Corrade."""
    params['group'] = CONFIG['group']
    params['password'] = CONFIG['password']
    
    try:
        response = requests.post(CONFIG['corrade_url'], data=params, timeout=60)
        result = {}
        for item in response.text.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                result[urllib.parse.unquote_plus(key)] = urllib.parse.unquote_plus(value)
        return result
    except requests.RequestException as e:
        return {'success': 'False', 'error': str(e)}


def list_folder(path: str) -> list:
    """List contents of a folder."""
    result = send_command(command='inventory', action='ls', path=path, cache='force')
    
    if result.get('success', '').lower() != 'true':
        return []
    
    data = result.get('data', '')
    if not data:
        return []
    
    items = []
    parts = data.split(',')
    i = 0
    while i < len(parts) - 1:
        if parts[i] == 'name' and i + 3 < len(parts):
            name = parts[i + 1].strip('"')
            uuid = parts[i + 3] if parts[i + 2] == 'item' else ''
            itype = parts[i + 5] if i + 5 < len(parts) and parts[i + 4] == 'type' else ''
            items.append({'name': name, 'uuid': uuid, 'type': itype})
        i += 1
    
    return items


def ensure_folder_exists(path: str) -> bool:
    """Ensure a folder exists."""
    # Handle various path formats - strip any My Inventory prefix
    if path.startswith('/My Inventory/'):
        path = path[14:]  # Remove '/My Inventory/'
    elif path.startswith('My Inventory/'):
        path = path[13:]  # Remove 'My Inventory/'
    path = path.lstrip('/')
    parts = path.split('/')
    
    current_path = '/My Inventory'
    
    for part in parts:
        next_path = f"{current_path}/{part}"
        
        result = send_command(command='inventory', action='ls', path=next_path)
        
        if result.get('success', '').lower() != 'true':
            print(f"    Creating: {next_path}")
            create_result = send_command(
                command='inventory',
                action='mkdir',
                path=current_path,
                name=part
            )
            if create_result.get('success', '').lower() != 'true':
                error = create_result.get('error', '')
                if 'already exists' not in error.lower():
                    print(f"    Failed to create {next_path}: {error}")
                    return False
            time.sleep(0.5)
        
        current_path = next_path
    
    return True


def move_item(source_uuid: str, target_path: str) -> bool:
    """Move an item by UUID."""
    result = send_command(command='inventory', action='mv', source=source_uuid, path=target_path)
    return result.get('success', '').lower() == 'true'


def merge_folder_contents(source_path: str, target_path: str, dry_run: bool = True, depth: int = 0) -> dict:
    """
    Recursively merge contents from source into target.
    For folders: create matching folder in target and recurse
    For items: move to target
    """
    stats = {'moved': 0, 'failed': 0, 'folders_processed': 0}
    indent = "  " * depth
    
    # List source contents
    items = list_folder(source_path)
    
    if not items:
        print(f"{indent}  (empty or not found)")
        return stats
    
    print(f"{indent}  Found {len(items)} items")
    
    for item in items:
        name = item['name']
        uuid = item['uuid']
        itype = item['type']
        
        if itype == 'Folder':
            # For folders, create matching folder in target and recurse
            new_source = f"{source_path}/{name}"
            new_target = f"{target_path}/{name}"
            
            print(f"{indent}  📁 {name}/")
            
            if not dry_run:
                ensure_folder_exists(new_target)
                time.sleep(0.3)
            else:
                print(f"{indent}    [DRY RUN] Would create: {new_target}")
            
            # Recurse into subfolder
            sub_stats = merge_folder_contents(new_source, new_target, dry_run, depth + 1)
            
            for key in stats:
                stats[key] += sub_stats[key]
            
            stats['folders_processed'] += 1
            
        else:
            # For items, move to target folder
            if dry_run:
                print(f"{indent}    [DRY RUN] Would move: {name}")
                stats['moved'] += 1
            else:
                if move_item(uuid, target_path):
                    print(f"{indent}    [OK] {name}")
                    stats['moved'] += 1
                else:
                    print(f"{indent}    [FAIL] {name}")
                    stats['failed'] += 1
                time.sleep(0.3)
    
    return stats


def run_merge_operations(dry_run: bool = True):
    """Run all merge operations."""
    
    print(f"\n{'='*60}")
    print(f"MERGE OPERATIONS")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")
    
    total_stats = {'moved': 0, 'failed': 0, 'folders_processed': 0}
    
    for op in MERGE_OPERATIONS:
        source = op['source']
        target = op['target']
        desc = op['description']
        
        print(f"\n--- {desc} ---")
        print(f"Source: {source}")
        print(f"Target: {target}")
        
        # Check if source exists
        items = list_folder(source)
        if not items:
            print("  Source folder is empty or doesn't exist, skipping")
            continue
        
        # Ensure target exists
        if not dry_run:
            if not ensure_folder_exists(target):
                print("  Failed to ensure target exists")
                continue
        
        # Merge contents
        stats = merge_folder_contents(source, target, dry_run)
        
        print(f"\n  Results: {stats['moved']} moved, {stats['failed']} failed, {stats['folders_processed']} subfolders")
        
        for key in total_stats:
            total_stats[key] += stats[key]
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {total_stats['moved']} items moved, {total_stats['failed']} failed")
    print(f"{'='*60}")
    
    return total_stats


def main():
    global CONFIG
    
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    CONFIG = load_config()
    
    # Verify Corrade connection
    print("Checking Corrade connection...")
    result = send_command(command='version')
    if result.get('success', '').lower() != 'true':
        print("Failed to connect to Corrade. Is it running?")
        sys.exit(1)
    print("Connected to Corrade")
    
    run_merge_operations(dry_run)
    
    if not dry_run:
        print("\nMerge complete!")
        print("Empty source folders remain - clean them up manually in-viewer.")


if __name__ == '__main__':
    main()

