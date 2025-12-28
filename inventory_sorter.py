#!/usr/bin/env python3
"""
Corrade Inventory Auto-Sorter
Connects to Corrade's HTTP API to sort inventory items based on rules.

Usage:
    python inventory_sorter.py --dry-run     # Preview what would be moved
    python inventory_sorter.py               # Actually perform the sort
    
Performance Notes:
    - Uses UUIDs wherever possible for speed (name lookups are slow)
    - Caches folder UUIDs to minimize API calls
    - Includes folder name normalization for consistent matching
"""

import requests
import time
import re
import argparse
import logging
import json
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class InventoryItem:
    """Represents an inventory item with UUID for efficient operations."""
    uuid: str
    name: str
    item_type: str
    parent_uuid: str = ""
    
    @property
    def normalized_name(self) -> str:
        """Normalize name for consistent matching."""
        return normalize_folder_name(self.name)


@dataclass
class SortRule:
    """Defines a sorting rule with name, target path, and matcher function."""
    name: str
    target_path: str  # e.g., "Apparel/Hair" or "Gestures/Dances"
    matcher: Callable[[str], bool]
    priority: int = 0


def normalize_folder_name(name: str) -> str:
    """
    Normalize folder/item names for consistent matching.
    
    Handles common SL naming quirks:
    - Leading/trailing whitespace
    - Multiple spaces
    - Unicode spaces and special characters
    - Common brand prefixes/suffixes
    - Version numbers
    """
    if not name:
        return ""
    
    # Strip leading/trailing whitespace (including Unicode spaces)
    result = name.strip()
    
    # Replace various Unicode spaces with regular space
    unicode_spaces = [
        '\u00A0',  # Non-breaking space
        '\u2000',  # En quad
        '\u2001',  # Em quad
        '\u2002',  # En space
        '\u2003',  # Em space
        '\u2004',  # Three-per-em space
        '\u2005',  # Four-per-em space
        '\u2006',  # Six-per-em space
        '\u2007',  # Figure space
        '\u2008',  # Punctuation space
        '\u2009',  # Thin space
        '\u200A',  # Hair space
        '\u200B',  # Zero-width space
        '\u202F',  # Narrow no-break space
        '\u205F',  # Medium mathematical space
        '\u3000',  # Ideographic space
    ]
    for space in unicode_spaces:
        result = result.replace(space, ' ')
    
    # Collapse multiple spaces
    result = re.sub(r'\s+', ' ', result)
    
    # Remove common problematic characters that can break API calls
    result = result.replace('\t', ' ')
    result = result.replace('\n', ' ')
    result = result.replace('\r', '')
    
    return result.strip()


def extract_brand_from_name(name: str) -> Optional[str]:
    """
    Try to extract a brand name from an item name.
    
    Common patterns:
    - "[Brand] Item Name"
    - "Brand - Item Name"
    - "Brand :: Item Name"
    - "Brand: Item Name"
    """
    normalized = normalize_folder_name(name)
    
    # Pattern: [Brand] ...
    bracket_match = re.match(r'^\[([^\]]+)\]', normalized)
    if bracket_match:
        return bracket_match.group(1).strip()
    
    # Pattern: Brand - ...
    dash_match = re.match(r'^([^-]+?)\s*[-–—]\s', normalized)
    if dash_match:
        potential_brand = dash_match.group(1).strip()
        # Avoid matching things like "Demo - " or version numbers
        if len(potential_brand) > 2 and not potential_brand.lower() in ['demo', 'v1', 'v2']:
            return potential_brand
    
    # Pattern: Brand :: ...
    double_colon_match = re.match(r'^([^:]+?)\s*::\s', normalized)
    if double_colon_match:
        return double_colon_match.group(1).strip()
    
    # Pattern: Brand: ... (less reliable, only use for known brands)
    # Skipped to avoid false positives
    
    return None


class CorradeInventorySorter:
    """Sorts inventory via Corrade's HTTP API using UUIDs for performance."""
    
    # Known system folder UUIDs (these are constant for all avatars)
    SYSTEM_FOLDER_NAMES = {
        'Calling Cards', 'Current Outfit', 'Landmarks', 'Lost And Found',
        'Materials', 'My Favorites', 'My Outfits', 'Notecards',
        'Photo Album', 'Trash', 'Inbox', 'Received Items',
        'Animation Overrides', '#RLV', 'Animations', 'Library'
    }
    
    def __init__(
        self,
        corrade_url: str,
        group: str,
        password: str,
        dry_run: bool = True,
        delay_between_moves: float = 1.0,
        batch_size: int = 10,
        batch_delay: float = 5.0,
        force_cache_refresh: bool = False
    ):
        self.corrade_url = corrade_url.rstrip('/')
        self.group = group
        self.password = password
        self.dry_run = dry_run
        self.delay = delay_between_moves
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self.force_cache_refresh = force_cache_refresh
        
        self.rules: list[SortRule] = []
        
        # UUID-based caches for performance
        self.folder_uuid_cache: dict[str, str] = {}  # path -> UUID
        self.folder_path_cache: dict[str, str] = {}  # UUID -> path
        self.uuid_name_cache: dict[str, str] = {}    # UUID -> name
        
        self.moved_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
        self._init_default_rules()
    
    def _init_default_rules(self):
        """Initialize default sorting rules based on user preferences."""
        
        # Helper to create case-insensitive regex matcher
        def regex_matcher(pattern: str) -> Callable[[str], bool]:
            compiled = re.compile(pattern, re.IGNORECASE)
            return lambda name: bool(compiled.search(normalize_folder_name(name)))
        
        # Helper to create keyword matcher
        def keyword_matcher(keywords: list[str]) -> Callable[[str], bool]:
            patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE) for kw in keywords]
            return lambda name: any(p.search(normalize_folder_name(name)) for p in patterns)
        
        # Rules in priority order (highest first)
        self.rules = [
            # Boxed items - highest priority
            SortRule(
                name="Boxed Items",
                target_path="Boxed Items",
                matcher=regex_matcher(r'(Box|Add\s*Me|Rezz\s*Me|Unpack)'),
                priority=100
            ),
            
            # Demos
            SortRule(
                name="Demos",
                target_path="_Demos",
                matcher=regex_matcher(r'\bdemo\b'),
                priority=90
            ),
            
            # Gestures - the PoC category
            SortRule(
                name="Dance Gestures",
                target_path="Gestures/Dances",
                matcher=keyword_matcher(['dance', 'dancing', 'dances']),
                priority=85
            ),
            SortRule(
                name="Expression Gestures",
                target_path="Gestures/Expressions",
                matcher=keyword_matcher(['laugh', 'cry', 'smile', 'wave', 'clap', 'cheer', 'boo', 'shrug']),
                priority=84
            ),
            
            # Hair - using Option A: Apparel/Hair/[Brand]/
            SortRule(
                name="Hair",
                target_path="Apparel/Hair",
                matcher=keyword_matcher([
                    'Hair', 'Hairstyle', 'Magika', 'Stealthic', 'Doux',
                    'Truth', 'Sintiklia', 'Wasabi', 'Tableau Vivant'
                ]),
                priority=80
            ),
            
            # Shoes
            SortRule(
                name="Shoes",
                target_path="Apparel/Shoes",
                matcher=keyword_matcher([
                    'Boots', 'Heels', 'Shoes', 'Sneakers', 'Sandals',
                    'Flats', 'Pumps', 'Loafers', 'Stilettos'
                ]),
                priority=75
            ),
            
            # Clothing
            SortRule(
                name="Clothing",
                target_path="Apparel/Clothing",
                matcher=keyword_matcher([
                    'Dress', 'Gown', 'Skirt', 'Pants', 'Shirt', 'Top',
                    'Sweater', 'Lingerie', 'Bikini', 'Blouse', 'Jacket',
                    'Coat', 'Jeans', 'Shorts', 'Leggings'
                ]),
                priority=70
            ),
            
            # Body Parts
            SortRule(
                name="Body Parts",
                target_path="Avatar/Body Parts",
                matcher=keyword_matcher([
                    'Skin', 'Shape', 'Eyes', 'Head', 'Body', 'Mesh Body',
                    'Bento', 'Maitreya', 'Legacy', 'Belleza', 'Slink',
                    'Catwa', 'Lelutka', 'Genus'
                ]),
                priority=60
            ),
            
            # Furniture & Decor
            SortRule(
                name="Furniture & Decor",
                target_path="Home & Decor",
                matcher=keyword_matcher([
                    'Chair', 'Table', 'Lamp', 'Rug', 'Decor', 'Furniture',
                    'Sofa', 'Bed', 'Couch', 'Desk', 'Shelf', 'Cabinet',
                    'Mirror', 'Plant', 'Vase'
                ]),
                priority=50
            ),
        ]
        
        # Sort by priority descending
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def add_rule(self, rule: SortRule):
        """Add a custom sorting rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def _send_command(self, **params) -> dict:
        """Send a command to Corrade and return the response."""
        params['group'] = self.group
        params['password'] = self.password
        
        try:
            response = requests.post(
                self.corrade_url,
                data=params,
                timeout=60  # Longer timeout for inventory operations
            )
            response.raise_for_status()
            
            # Parse Corrade's response format (URL-encoded key=value pairs)
            result = {}
            for item in response.text.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1)
                    result[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
            
            return result
            
        except requests.Timeout:
            logger.error("Request timed out - Corrade may be busy or inventory is large")
            return {'success': 'False', 'error': 'Timeout'}
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {'success': 'False', 'error': str(e)}
    
    def get_folder_uuid(self, folder_path: str) -> Optional[str]:
        """Get UUID for a folder path, using cache when possible."""
        if folder_path in self.folder_uuid_cache:
            return self.folder_uuid_cache[folder_path]
        
        result = self._send_command(
            command='getinventorypath',
            path=folder_path
        )
        
        if result.get('success', '').lower() == 'true':
            uuid = result.get('data', '')
            if uuid:
                self.folder_uuid_cache[folder_path] = uuid
                self.folder_path_cache[uuid] = folder_path
                return uuid
        
        return None
    
    def get_folder_contents_by_uuid(
        self,
        folder_uuid: str,
        force_refresh: bool = False
    ) -> list[InventoryItem]:
        """Get contents of a folder by UUID for better performance."""
        params = {
            'command': 'inventory',
            'action': 'ls',
            'folder': folder_uuid,  # Use UUID instead of path
        }
        if force_refresh or self.force_cache_refresh:
            params['cache'] = 'force'
        
        result = self._send_command(**params)
        
        if result.get('success', '').lower() != 'true':
            error = result.get('error', 'Unknown error')
            logger.error(f"Failed to list folder UUID {folder_uuid}: {error}")
            return []
        
        # Parse the inventory data
        items = []
        data = result.get('data', '')
        if data:
            # Corrade returns CSV-like format: name,uuid,type
            for line in data.split('\n'):
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        item = InventoryItem(
                            uuid=parts[1].strip(),
                            name=parts[0].strip(),
                            item_type=parts[2].strip(),
                            parent_uuid=folder_uuid
                        )
                        # Cache the name for this UUID
                        self.uuid_name_cache[item.uuid] = item.name
                        items.append(item)
        
        return items
    
    def get_folder_contents(self, folder_path: str, force_refresh: bool = False) -> list[InventoryItem]:
        """Get contents of a folder by path (uses UUID internally when possible)."""
        # Try to get UUID first for better performance
        folder_uuid = self.get_folder_uuid(folder_path)
        
        if folder_uuid:
            return self.get_folder_contents_by_uuid(folder_uuid, force_refresh)
        
        # Fallback to path-based lookup
        params = {
            'command': 'inventory',
            'action': 'ls',
            'path': folder_path,
        }
        if force_refresh or self.force_cache_refresh:
            params['cache'] = 'force'
        
        result = self._send_command(**params)
        
        if result.get('success', '').lower() != 'true':
            logger.error(f"Failed to list folder {folder_path}: {result.get('error', 'Unknown error')}")
            return []
        
        # Parse the inventory data
        items = []
        data = result.get('data', '')
        if data:
            for line in data.split('\n'):
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 3:
                        item = InventoryItem(
                            uuid=parts[1].strip(),
                            name=parts[0].strip(),
                            item_type=parts[2].strip()
                        )
                        self.uuid_name_cache[item.uuid] = item.name
                        items.append(item)
        
        return items
    
    def ensure_folder_exists(self, path: str) -> Optional[str]:
        """Ensure a folder path exists, creating if necessary. Returns UUID."""
        # Check cache first
        if path in self.folder_uuid_cache:
            return self.folder_uuid_cache[path]
        
        # Try to get existing folder
        folder_uuid = self.get_folder_uuid(path)
        if folder_uuid:
            return folder_uuid
        
        # Need to create the folder - do it path segment by path segment
        parts = path.split('/')
        current_path = ""
        parent_uuid = None
        
        for part in parts:
            parent_path = current_path
            current_path = f"{current_path}/{part}" if current_path else part
            
            # Check if this segment exists
            segment_uuid = self.get_folder_uuid(current_path)
            
            if not segment_uuid:
                # Create this folder
                logger.info(f"Creating folder: {current_path}")
                
                if not self.dry_run:
                    create_params = {
                        'command': 'inventory',
                        'action': 'mkdir',
                        'name': part,
                    }
                    
                    # Use parent UUID if we have it, otherwise use path
                    if parent_uuid:
                        create_params['folder'] = parent_uuid
                    elif parent_path:
                        create_params['path'] = parent_path
                    
                    create_result = self._send_command(**create_params)
                    
                    if create_result.get('success', '').lower() != 'true':
                        logger.error(f"Failed to create folder {current_path}: {create_result.get('error', '')}")
                        return None
                    
                    # Get the UUID of newly created folder
                    time.sleep(0.5)  # Brief delay for SL to process
                    segment_uuid = self.get_folder_uuid(current_path)
                else:
                    logger.info(f"[DRY RUN] Would create folder: {current_path}")
                    segment_uuid = f"dry-run-uuid-{current_path}"  # Placeholder
            
            parent_uuid = segment_uuid
        
        if parent_uuid:
            self.folder_uuid_cache[path] = parent_uuid
        
        return parent_uuid
    
    def move_item_by_uuid(self, item_uuid: str, target_folder_uuid: str, item_name: str = "") -> bool:
        """Move an inventory item by UUID for better performance."""
        display_name = item_name or self.uuid_name_cache.get(item_uuid, item_uuid)
        target_path = self.folder_path_cache.get(target_folder_uuid, target_folder_uuid)
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would move '{display_name}' -> {target_path}")
            return True
        
        result = self._send_command(
            command='inventory',
            action='mv',
            item=item_uuid,        # UUID of item to move
            folder=target_folder_uuid  # UUID of target folder
        )
        
        if result.get('success', '').lower() == 'true':
            logger.info(f"Moved '{display_name}' -> {target_path}")
            return True
        else:
            error = result.get('error', 'Unknown')
            logger.error(f"Failed to move '{display_name}': {error}")
            return False
    
    def find_matching_rule(self, item_name: str) -> Optional[SortRule]:
        """Find the first matching rule for an item name."""
        normalized = normalize_folder_name(item_name)
        for rule in self.rules:
            if rule.matcher(normalized):
                return rule
        return None
    
    def is_system_folder(self, folder_name: str) -> bool:
        """Check if a folder is a system/protected folder."""
        normalized = normalize_folder_name(folder_name)
        return normalized in self.SYSTEM_FOLDER_NAMES
    
    def sort_folder(
        self,
        source_path: str,
        recursive: bool = True,
        source_uuid: str = None
    ):
        """Sort items in a folder according to rules."""
        logger.info(f"Processing folder: {source_path}")
        
        # Get folder UUID for better performance
        if not source_uuid:
            source_uuid = self.get_folder_uuid(source_path)
        
        if not source_uuid:
            logger.error(f"Could not find folder: {source_path}")
            return
        
        # Force refresh to get current state
        items = self.get_folder_contents_by_uuid(
            source_uuid,
            force_refresh=True
        )
        
        if not items:
            logger.info(f"No items found in {source_path}")
            return
        
        batch_count = 0
        
        for item in items:
            # Skip system folders if this is a folder
            if item.item_type.lower() == 'folder':
                if self.is_system_folder(item.name):
                    logger.debug(f"Skipping system folder: {item.name}")
                    self.skipped_count += 1
                    continue
                
                # Recursively process subfolder
                if recursive:
                    subfolder_path = f"{source_path}/{item.name}"
                    self.sort_folder(
                        subfolder_path,
                        recursive=True,
                        source_uuid=item.uuid
                    )
                continue
            
            # Find matching rule using normalized name
            rule = self.find_matching_rule(item.name)
            
            if rule:
                # Ensure target folder exists and get its UUID
                target_uuid = self.ensure_folder_exists(rule.target_path)
                
                if target_uuid:
                    if self.move_item_by_uuid(item.uuid, target_uuid, item.name):
                        self.moved_count += 1
                        batch_count += 1
                        
                        # Delay between moves
                        time.sleep(self.delay)
                        
                        # Batch pause
                        if batch_count >= self.batch_size:
                            logger.info(f"Batch complete ({self.batch_size} items), pausing {self.batch_delay}s...")
                            time.sleep(self.batch_delay)
                            batch_count = 0
                    else:
                        self.error_count += 1
    
    def run(self, start_folders: list[str] = None):
        """Run the sorting process."""
        if start_folders is None:
            # Default folders to sort based on user preferences
            start_folders = [
                'Gestures',      # PoC - start simple
                'Body Parts',
                'Clothing',
                'Objects',
                'Scripts',
                'Settings',
                'Sounds',
            ]
        
        mode = "[DRY RUN] " if self.dry_run else ""
        logger.info(f"{mode}Starting inventory sort...")
        logger.info(f"Folders to process: {start_folders}")
        logger.info(f"Rules loaded: {len(self.rules)}")
        
        start_time = time.time()
        
        for folder in start_folders:
            try:
                self.sort_folder(folder)
            except KeyboardInterrupt:
                logger.warning("Sort interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error processing {folder}: {e}")
                self.error_count += 1
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n{'='*50}")
        logger.info(f"{mode}Sort complete!")
        logger.info(f"Time elapsed: {elapsed:.1f}s")
        logger.info(f"Items moved: {self.moved_count}")
        logger.info(f"Items skipped: {self.skipped_count}")
        logger.info(f"Errors: {self.error_count}")


def load_rules_from_file(filepath: Path) -> list[SortRule]:
    """Load custom sorting rules from a JSON file."""
    rules = []
    
    with open(filepath) as f:
        data = json.load(f)
    
    for rule_def in data.get('rules', []):
        # Build matcher from definition
        if 'regex' in rule_def:
            pattern = re.compile(rule_def['regex'], re.IGNORECASE)
            matcher = lambda name, p=pattern: bool(p.search(normalize_folder_name(name)))
        elif 'keywords' in rule_def:
            patterns = [
                re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE)
                for kw in rule_def['keywords']
            ]
            matcher = lambda name, ps=patterns: any(p.search(normalize_folder_name(name)) for p in ps)
        else:
            continue
        
        rules.append(SortRule(
            name=rule_def.get('name', 'Custom Rule'),
            target_path=rule_def['target_path'],
            matcher=matcher,
            priority=rule_def.get('priority', 0)
        ))
    
    return rules


def main():
    parser = argparse.ArgumentParser(
        description='Sort Second Life inventory via Corrade HTTP API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run --folders Gestures
      Preview sorting of just the Gestures folder
  
  %(prog)s --config config.json --dry-run
      Preview full sort using config file settings
  
  %(prog)s --config config.json
      Actually perform the sort

Performance Tips:
  - Uses UUIDs internally for speed (name lookups are slow)
  - Adjust --delay and --batch-delay based on your connection
  - Start with --dry-run to preview changes
  - Use --force-refresh if inventory seems stale
        """
    )
    parser.add_argument('--config', type=Path,
                        help='Path to JSON config file')
    parser.add_argument('--rules', type=Path,
                        help='Path to custom rules JSON file')
    parser.add_argument('--url', default='http://localhost:8080',
                        help='Corrade HTTP server URL (default: localhost:8080)')
    parser.add_argument('--group',
                        help='Corrade group name')
    parser.add_argument('--password',
                        help='Corrade group password')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without moving anything')
    parser.add_argument('--folders', nargs='+',
                        help='Specific folders to sort (default: standard set)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between moves in seconds (default: 1.0)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of moves before batch pause (default: 10)')
    parser.add_argument('--batch-delay', type=float, default=5.0,
                        help='Pause duration between batches (default: 5.0)')
    parser.add_argument('--force-refresh', action='store_true',
                        help='Force refresh inventory cache from SL servers')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose/debug logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config from file if provided
    config = {}
    if args.config and args.config.exists():
        with open(args.config) as f:
            config = json.load(f)
        logger.info(f"Loaded config from {args.config}")
    
    # CLI args override config file
    url = args.url if args.url != 'http://localhost:8080' else config.get('corrade_url', args.url)
    group = args.group or config.get('group')
    password = args.password or config.get('password')
    folders = args.folders or config.get('folders_to_sort')
    
    if not group or not password:
        parser.error("--group and --password are required (or provide via --config)")
    
    sorter = CorradeInventorySorter(
        corrade_url=url,
        group=group,
        password=password,
        dry_run=args.dry_run,
        delay_between_moves=args.delay if args.delay != 1.0 else config.get('delay_between_moves', 1.0),
        batch_size=args.batch_size if args.batch_size != 10 else config.get('batch_size', 10),
        batch_delay=args.batch_delay if args.batch_delay != 5.0 else config.get('batch_delay', 5.0),
        force_cache_refresh=args.force_refresh or config.get('force_cache_refresh', False)
    )
    
    # Load custom rules if provided
    if args.rules and args.rules.exists():
        custom_rules = load_rules_from_file(args.rules)
        for rule in custom_rules:
            sorter.add_rule(rule)
        logger.info(f"Loaded {len(custom_rules)} custom rules from {args.rules}")
    
    sorter.run(folders)


if __name__ == '__main__':
    main()
