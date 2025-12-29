#!/usr/bin/env python3
"""
Plan Executor
Executes a move plan via Corrade API.

Usage:
    python execute_plan.py <plan_file.json> [--dry-run]
    
The executor will:
1. Read the plan file
2. For each folder in the plan:
   - Create the target folder structure if needed
   - Move all ITEMS from source to target (not the folder itself)
   - Leave empty source folders for manual cleanup
3. Mark the plan as executed
4. NEVER delete anything
"""

import json
import sys
import time
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime

# Corrade configuration - loaded from config
CONFIG = None


def load_config():
    """Load Corrade config from the main config file."""
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)
    
    with open(config_path) as f:
        return json.load(f)


def send_command(**params) -> dict:
    """Send a command to Corrade and return the response."""
    params['group'] = CONFIG['group']
    params['password'] = CONFIG['password']
    
    try:
        response = requests.post(
            CONFIG['corrade_url'],
            data=params,
            timeout=60
        )
        
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
    result = send_command(
        command='inventory',
        action='ls',
        path=path,
        cache='force'
    )
    
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
    """Ensure a folder path exists, creating parent folders as needed."""
    # Remove leading /My Inventory/ if present
    path = path.replace('/My Inventory/', '').lstrip('/')
    parts = path.split('/')
    
    current_path = '/My Inventory'
    
    for part in parts:
        next_path = f"{current_path}/{part}"
        
        # Check if folder exists
        result = send_command(
            command='inventory',
            action='ls',
            path=next_path
        )
        
        if result.get('success', '').lower() != 'true':
            # Create the folder
            print(f"  Creating folder: {next_path}")
            create_result = send_command(
                command='inventory',
                action='mkdir',
                path=current_path,
                name=part
            )
            
            if create_result.get('success', '').lower() != 'true':
                error = create_result.get('error', 'Unknown error')
                if 'already exists' not in error.lower():
                    print(f"  Failed to create {next_path}: {error}")
                    return False
            
            time.sleep(0.5)
        
        current_path = next_path
    
    return True


def move_item(source_uuid: str, target_path: str) -> bool:
    """Move an item by UUID to a target folder path."""
    result = send_command(
        command='inventory',
        action='mv',
        source=source_uuid,
        path=target_path
    )
    
    return result.get('success', '').lower() == 'true'


def execute_folder_move(source_path: str, target_path: str, dry_run: bool = True) -> dict:
    """
    Move contents of a source folder to target folder.
    Returns statistics about the operation.
    """
    stats = {'moved': 0, 'failed': 0, 'skipped': 0}
    
    # Ensure target folder exists
    if not dry_run:
        if not ensure_folder_exists(target_path):
            print(f"  Failed to create target path: {target_path}")
            return stats
    else:
        print(f"  [DRY RUN] Would create: {target_path}")
    
    # List source folder contents
    full_source = source_path if source_path.startswith('/') else f'/My Inventory/{source_path}'
    items = list_folder(full_source)
    
    if not items:
        print(f"  Source folder empty or not found: {full_source}")
        return stats
    
    print(f"  Found {len(items)} items in source folder")
    
    # Move each item
    for item in items:
        if item['type'] == 'Folder':
            # For folders, we need to recursively move contents
            # For now, just note them - don't move folder structures
            print(f"    [SKIP] Subfolder: {item['name']} (needs separate plan)")
            stats['skipped'] += 1
            continue
        
        full_target = target_path if target_path.startswith('/') else f'/My Inventory/{target_path}'
        
        if dry_run:
            print(f"    [DRY RUN] Would move: {item['name']} -> {target_path}")
            stats['moved'] += 1
        else:
            if move_item(item['uuid'], full_target):
                print(f"    [OK] {item['name']}")
                stats['moved'] += 1
            else:
                print(f"    [FAIL] {item['name']}")
                stats['failed'] += 1
            
            time.sleep(0.3)  # Rate limiting
    
    return stats


def execute_plan(plan_file: Path, dry_run: bool = True):
    """Execute a move plan."""
    
    with open(plan_file) as f:
        plan = json.load(f)
    
    target_path = plan['target_path']
    folders = plan['folders']
    
    print(f"\n{'='*60}")
    print(f"Plan: {plan_file.name}")
    print(f"Target: {target_path}")
    print(f"Folders to process: {len(folders)}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")
    
    if plan.get('status') == 'executed':
        print("This plan has already been executed!")
        return
    
    if plan.get('status') == 'needs_review':
        print("This plan needs manual review before execution!")
        print("Update the plan file to set appropriate target paths.")
        return
    
    total_stats = {'moved': 0, 'failed': 0, 'skipped': 0}
    
    for folder_info in folders:
        name = folder_info['name']
        source_path = folder_info['path']
        
        # Target is the plan's target path + the folder name
        folder_target = f"{target_path}/{name}"
        
        print(f"\nProcessing: {name}")
        print(f"  Source: {source_path}")
        print(f"  Target: {folder_target}")
        
        stats = execute_folder_move(source_path, folder_target, dry_run)
        
        for key in total_stats:
            total_stats[key] += stats[key]
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Moved: {total_stats['moved']}")
    print(f"  Failed: {total_stats['failed']}")
    print(f"  Skipped: {total_stats['skipped']}")
    print(f"{'='*60}")
    
    # Mark plan as executed (if not dry run)
    if not dry_run and total_stats['failed'] == 0:
        plan['status'] = 'executed'
        plan['executed_at'] = datetime.now().isoformat()
        
        # Move to executed folder
        executed_dir = plan_file.parent.parent / 'executed'
        executed_dir.mkdir(exist_ok=True)
        
        executed_file = executed_dir / plan_file.name
        with open(executed_file, 'w') as f:
            json.dump(plan, f, indent=2)
        
        plan_file.unlink()
        print(f"\nPlan moved to: {executed_file}")


def main():
    global CONFIG
    
    if len(sys.argv) < 2:
        print("Usage: python execute_plan.py <plan_file.json> [--dry-run]")
        print("\nAvailable plans:")
        plans_dir = Path(__file__).parent / "plans"
        for plan in sorted(plans_dir.glob("*.json")):
            print(f"  - {plan.name}")
        sys.exit(1)
    
    plan_file = Path(sys.argv[1])
    if not plan_file.exists():
        # Try relative to plans directory
        plan_file = Path(__file__).parent / "plans" / sys.argv[1]
    
    if not plan_file.exists():
        print(f"Plan file not found: {sys.argv[1]}")
        sys.exit(1)
    
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    CONFIG = load_config()
    
    # Verify Corrade is running
    print("Checking Corrade connection...")
    result = send_command(command='version')
    if result.get('success', '').lower() != 'true':
        print("Failed to connect to Corrade. Is it running?")
        sys.exit(1)
    
    print(f"Connected to Corrade")
    
    execute_plan(plan_file, dry_run)


if __name__ == '__main__':
    main()

