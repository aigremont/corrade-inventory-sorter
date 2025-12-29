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
    - "*Brand* Item Name" (asterisks)
    - ".::Brand::. Item Name" (decorative)
    - "~Brand~ Item Name" (tildes)
    - "::Brand:: Item Name"
    """
    normalized = normalize_folder_name(name)
    
    # Pattern: [Brand] ...
    bracket_match = re.match(r'^\[([^\]]+)\]', normalized)
    if bracket_match:
        return bracket_match.group(1).strip()
    
    # Pattern: *Brand* ... (asterisks around brand)
    asterisk_match = re.match(r'^\*([^*]+)\*', normalized)
    if asterisk_match:
        return asterisk_match.group(1).strip()
    
    # Pattern: .::Brand::. ... (decorative punctuation)
    decorative_match = re.match(r'^[.\s]*::([^:]+)::[.\s]*', normalized)
    if decorative_match:
        return decorative_match.group(1).strip()
    
    # Pattern: ~Brand~ ... (tildes)
    tilde_match = re.match(r'^~([^~]+)~', normalized)
    if tilde_match:
        return tilde_match.group(1).strip()
    
    # Pattern: ::Brand:: ... (just double colons)
    double_colon_match = re.match(r'^::([^:]+)::', normalized)
    if double_colon_match:
        return double_colon_match.group(1).strip()
    
    # Pattern: Brand :: ... (space before double colon)
    spaced_double_colon_match = re.match(r'^([^:]+?)\s*::\s', normalized)
    if spaced_double_colon_match:
        return spaced_double_colon_match.group(1).strip()
    
    # Pattern: Brand - ... (dash separator)
    dash_match = re.match(r'^([^-]+?)\s*[-–—]\s', normalized)
    if dash_match:
        potential_brand = dash_match.group(1).strip()
        # Avoid matching things like "Demo - " or version numbers
        if len(potential_brand) > 2 and not potential_brand.lower() in ['demo', 'v1', 'v2']:
            return potential_brand
    
    return None


def extract_product_name(folder_name: str, brand: str = None) -> Optional[str]:
    """
    Extract product name from a folder name.
    E.g., "Magika - Sadie Hair" -> "Sadie"
    """
    normalized = normalize_folder_name(folder_name)
    
    # Remove brand prefix if known
    if brand:
        # Pattern: "Brand - Product ..." or "Brand :: Product ..."
        pattern = rf'^{re.escape(brand)}\s*[-–—:]+\s*'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove common suffixes like "Hair", "Skin", "(BOX)", etc.
    normalized = re.sub(r'\s*(Hair|Skin|Head|Body|Eyes|Shape|\(BOX\)|\(boxed\)|boxed|box)\s*$', '', normalized, flags=re.IGNORECASE)
    
    # Remove version numbers
    normalized = re.sub(r'\s*v?\d+\.?\d*\s*$', '', normalized, flags=re.IGNORECASE)
    
    # Clean up any remaining artifacts
    normalized = re.sub(r'\s*[-–—:]+\s*$', '', normalized)
    
    return normalized.strip() if normalized.strip() else None


def detect_item_subfolder(item_name: str) -> str:
    """
    Detect what subfolder an item should go into based on its name.
    For CTS Wardrobe compatibility.
    
    Returns subfolder name like 'Hair', 'HUDs', 'Skin', etc.
    """
    name_lower = item_name.lower()
    
    # HUDs
    if 'hud' in name_lower:
        return 'HUDs'
    
    # Hair (including bangs, pigtails, etc.)
    if any(x in name_lower for x in ['hair', 'bangs', 'pigtail', 'ponytail', 'braid', 'wig']) and 'chair' not in name_lower:
        return 'Hair'
    
    # Skin
    if 'skin' in name_lower:
        return 'Skin'
    
    # Shape
    if 'shape' in name_lower:
        return 'Shape'
    
    # Eyes
    if 'eye' in name_lower and 'eyeshadow' not in name_lower:
        return 'Eyes'
    
    # Head
    if 'head' in name_lower:
        return 'Head'
    
    # Body
    if 'body' in name_lower:
        return 'Body'
    
    # Animations/AO
    if 'animation' in name_lower or ' ao ' in name_lower or name_lower.endswith(' ao'):
        return 'Animations'
    
    # Tattoo/Applier
    if 'tattoo' in name_lower or 'applier' in name_lower:
        return 'Appliers'
    
    # Makeup
    if any(x in name_lower for x in ['makeup', 'lipstick', 'eyeshadow', 'blush', 'liner']):
        return 'Makeup'
    
    # Clothing items
    if any(x in name_lower for x in ['dress', 'top', 'pants', 'skirt', 'shirt', 'jacket', 'coat']):
        return 'Clothing'
    
    # Shoes
    if any(x in name_lower for x in ['shoe', 'boot', 'heel', 'sandal', 'sneaker']):
        return 'Shoes'
    
    # Accessories
    if any(x in name_lower for x in ['ring', 'necklace', 'earring', 'bracelet', 'collar', 'cuff']):
        return 'Accessories'
    
    # Scripts/Utilities
    if 'script' in name_lower or 'updater' in name_lower:
        return 'Scripts'
    
    # Landmarks
    if 'landmark' in name_lower or name_lower.endswith('.lm'):
        return 'Landmarks'
    
    # Documentation (ReadMe, Instructions, etc.)
    if 'notecard' in name_lower or 'read me' in name_lower or 'readme' in name_lower or 'instructions' in name_lower:
        return 'Docs'
    
    # Posters/Ads
    if 'poster' in name_lower or 'ad ' in name_lower or ' ad' in name_lower:
        return 'Extras'
    
    # Default - put in main folder
    return ''


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
            
            # BDSM/Kink items - high priority to catch before generic clothing
            # Equipment = physical restraints (hoods, armbinders, cuffs, etc.)
            SortRule(
                name="BDSM Equipment",
                target_path="BDSM/Equipment",
                matcher=keyword_matcher([
                    'hood', 'armbinder', 'gag', 'muzzle', 'blindfold',
                    'cuff', 'cuffs', 'spreader', 'straitjacket', 'chastity',
                    'restraint', 'bondage', 'padlock'
                ]),
                priority=89
            ),
            # KDC makes BDSM equipment specifically
            SortRule(
                name="KDC Equipment",
                target_path="BDSM/Equipment",
                matcher=regex_matcher(r'\bKDC\b'),
                priority=89
            ),
            # CC/T&T makes chastity belts
            SortRule(
                name="CC Chastity",
                target_path="BDSM/Equipment",
                matcher=regex_matcher(r'CC[\/\\]T&T|Chastity Belt'),
                priority=89
            ),
            # BDSM Restraints (collars, leashes, harnesses)
            SortRule(
                name="BDSM Restraints",
                target_path="BDSM",
                matcher=keyword_matcher([
                    'collar', 'leash', 'harness',
                    'prisoner', 'prison', 'slave', 'submissa'
                ]),
                priority=88
            ),
            # NGW makes equipment (hoods, armbinders) - higher priority to route to Equipment
            SortRule(
                name="NGW Equipment",
                target_path="BDSM/Equipment",
                matcher=regex_matcher(r'\bNGW\b'),
                priority=89
            ),
            SortRule(
                name="BDSM Brands",
                target_path="BDSM",
                # Note: \* escapes literal asterisks for *HDM* pattern
                matcher=regex_matcher(r'(\*HDM\*|\bHDM\b|Vixen|~?Silenced~?|RR&Co|Bad Bunny|OpenCollar|Realrestraint|Decima|Aphasia|SNUGGLIES|CryBunBun|LnB|BioDoll|Size:KaS|KaS\b)'),
                priority=87
            ),
            # BDSM Animations
            SortRule(
                name="BDSM Animations",
                target_path="Animations/BDSM",
                matcher=keyword_matcher(['BDSM animations', 'BDSM anim', 'bondage animations']),
                priority=87
            ),
            # Corsets go to BDSM/Clothing/Corsets (match on product type, not brand)
            SortRule(
                name="Corsets",
                target_path="BDSM/Clothing/Corsets",
                matcher=keyword_matcher(['corset', 'corsets']),
                priority=87
            ),
            SortRule(
                name="BDSM Latex",
                target_path="BDSM",
                matcher=keyword_matcher([
                    'latex catsuit', 'rubber doll', 'latex doll', 'kink add-on',
                    'open body', 'polyform latex'
                ]),
                priority=86
            ),
            
            # Whips/Crops to Accessories (not BDSM restraints)
            SortRule(
                name="Whips",
                target_path="Clothing/Accessories",
                matcher=keyword_matcher(['whip', 'crop', 'riding crop']),
                priority=85
            ),
            
            # Animation Overrides - goes to system folder
            SortRule(
                name="Animation Overrides",
                target_path="Animation Overrides",
                matcher=regex_matcher(r'(\bAO\b|Animation Override|BENTO AO|BodyLanguage.*AO|AO.*Pack)'),
                priority=86
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
            
            # Hair - organized by brand/product for CTS Wardrobe compatibility
            SortRule(
                name="Hair",
                target_path="Body Parts/Hair",  # Base path - brand/product added dynamically
                matcher=keyword_matcher([
                    'Hair', 'Hairstyle', 'Magika', 'Stealthic', 'Doux',
                    'Truth', 'Sintiklia', 'Wasabi', 'Tableau Vivant', 'KUNI'
                ]),
                priority=78  # Lower than heads since some head brands also make hair
            ),
            
            # Shoes
            SortRule(
                name="Shoes",
                target_path="Clothing/Shoes",
                matcher=keyword_matcher([
                    'Boots', 'Heels', 'Shoes', 'Sneakers', 'Sandals',
                    'Flats', 'Pumps', 'Loafers', 'Stilettos', 'Cuban heel'
                ]),
                priority=75
            ),
            # Shoe brands (erratic, etc.)
            SortRule(
                name="Shoe Brands",
                target_path="Clothing/Shoes",
                matcher=regex_matcher(r'\berratic\b'),
                priority=74
            ),
            
            # Clothing
            SortRule(
                name="Clothing",
                target_path="Clothing",
                matcher=keyword_matcher([
                    'Dress', 'Gown', 'Skirt', 'Pants', 'Shirt', 'Top',
                    'Sweater', 'Lingerie', 'Bikini', 'Blouse', 'Jacket',
                    'Coat', 'Jeans', 'Shorts', 'Leggings', 'Thong', 'Panties',
                    'Bra', 'Underwear', 'Pantyhose', 'Stockings', 'Bodysuit',
                    'Catsuit', 'Suit'
                ]),
                priority=70
            ),
            
            # Hosiery - specific subcategory (by product keywords, not brand)
            SortRule(
                name="Hosiery",
                target_path="Clothing/Hosiery",
                matcher=keyword_matcher(['Pantyhose', 'Stockings', 'Tights', 'Hosiery', 'Nylons']),
                priority=71
            ),
            
            # Mesh Heads - require brand + "Head" to avoid matching clothing
            # "Dress for LeLUTKA" won't match, but "LeLUTKA Avalon Head" will
            # "GENUS Project - BOM MAKEUP" won't match (no "Head"), but "GENUS Head" will
            SortRule(
                name="Mesh Heads",
                target_path="Body Parts/Heads",
                matcher=regex_matcher(r'((LeLUTKA|GENUS|Catwa|LAQ|Akeruka|Logo).*Head|Mesh Head)'),
                priority=82  # Higher than hair to catch head products first
            ),
            
            # Mesh Bodies - match on specific PRODUCT names, not just brand names
            # "Maitreya Dress" should NOT match, but "Maitreya Lara Body" should
            SortRule(
                name="Mesh Bodies",
                target_path="Body Parts/Bodies",
                matcher=regex_matcher(r'(Lara\b|LaraX|Mesh Body|Reborn\b|Kupra|Perky|Freya|Isis|Venus|Hourglass|Physique|Legacy.*Body|eBody.*Reborn)'),
                priority=64
            ),
            
            # Body Deformers/Fixers
            SortRule(
                name="Body Deformers",
                target_path="Body Parts/Bodies",
                matcher=keyword_matcher([
                    'deformer', 'fixer', 'butt fixer', 'flat ass', 'morph',
                    'kuromori', 'Influence'
                ]),
                priority=63
            ),
            
            # Skins - by product type keywords, not brand names
            # Brands can make multiple products, so match on what the item IS
            SortRule(
                name="Skins",
                target_path="Body Parts/Skins",
                matcher=keyword_matcher(['Skin', 'Skins', 'Body Skin', 'Head Skin', 'BOM Skin']),
                priority=62
            ),
            # Specific skin brands (these primarily make skins)
            SortRule(
                name="Skin Brands",
                target_path="Body Parts/Skins",
                matcher=regex_matcher(r'(VELOUR|Pepe Skins|Ipanema Body)'),
                priority=62
            ),
            
            # Body Parts - generic (lower priority)
            SortRule(
                name="Body Parts",
                target_path="Body Parts",
                matcher=keyword_matcher([
                    'Skin', 'Shape', 'Eyes', 'Bento', 'BOM', 'Applier'
                ]),
                priority=60
            ),
            
            # Body Accessories (piercings, nipple rings, etc.)
            SortRule(
                name="Body Accessories",
                target_path="Body Parts/Accessories",
                matcher=keyword_matcher(['nipple rings', 'nipple piercing', 'piercing', 'body jewelry', 'belly ring']),
                priority=61
            ),
            
            # Tattoos
            SortRule(
                name="Tattoos",
                target_path="Body Parts/Tattoos",
                matcher=keyword_matcher(['tattoo', 'tattoos', 'tat', 'barcode']),
                priority=59
            ),
            
            # Utility HUDs (teleporters, pose adjusters, etc.)
            SortRule(
                name="Utility HUDs",
                target_path="Objects/Utilities",
                matcher=keyword_matcher([
                    'Teleporter', 'Auto Teleporter', 'Pose Adjuster', 'Resizer',
                    'Animator', 'Face Light', 'AO HUD'
                ]),
                priority=55
            ),
            # Update folders (RealRestraint, etc.)
            SortRule(
                name="Updaters",
                target_path="Objects/Updaters",
                matcher=regex_matcher(r'(Update folder|Updater|RR Update)'),
                priority=54
            ),
            
            # OMY is generally animations
            SortRule(
                name="OMY Animations",
                target_path="Animations",
                matcher=regex_matcher(r'\bOMY\b'),
                priority=54
            ),
            
            # Furniture - goes to Objects/Furniture/Vendor/Item
            SortRule(
                name="Furniture",
                target_path="Objects/Furniture",
                matcher=keyword_matcher([
                    'Chair', 'Table', 'Lamp', 'Rug', 'Furniture',
                    'Sofa', 'Bed', 'Couch', 'Desk', 'Shelf', 'Cabinet',
                    'Cage', 'Cross', 'Rack', 'Stocks', 'Pillory', 'Frame',
                    'Dungeon', 'Throne'
                ]),
                priority=50
            ),
            
            # Uncertain boxed items that need manual review
            SortRule(
                name="Check Items",
                target_path="Objects/Check",
                matcher=regex_matcher(r'(Unpacker|unpack|rez to unpack|wear.*unpack)'),
                priority=40
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
        
        # Corrade uses path= with inventory command to access folders
        # We'll extract UUID from a successful listing
        full_path = folder_path if folder_path.startswith('/') else f'/My Inventory/{folder_path}'
        
        result = self._send_command(
            command='inventory',
            action='ls',
            path=full_path
        )
        
        if result.get('success', '').lower() == 'true':
            # If listing succeeded, the folder exists - use path as identifier
            self.folder_uuid_cache[folder_path] = full_path
            self.folder_path_cache[full_path] = folder_path
            return full_path
        
        return None
    
    def _parse_inventory_data(self, data: str, parent_path: str = "") -> list[InventoryItem]:
        """
        Parse Corrade's inventory CSV format.
        Format: name,<value>,item,<uuid>,type,<type>,permissions,<perms>,time,<time>,...
        """
        items = []
        if not data:
            return items
        
        # Split by comma and parse field-value pairs
        parts = [p.strip() for p in data.split(',')]
        
        i = 0
        current_item = {}
        while i < len(parts) - 1:
            field = parts[i].lower()
            value = parts[i + 1]
            
            # Remove quotes from value if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith('"'):
                # Handle multi-part quoted values
                value = value[1:]
                i += 2
                while i < len(parts) and not parts[i-1].endswith('"'):
                    value += ',' + parts[i]
                    i += 1
                if value.endswith('"'):
                    value = value[:-1]
                continue
            
            if field == 'name':
                # Start of new item - save previous if exists
                if current_item.get('name') and current_item.get('uuid'):
                    items.append(InventoryItem(
                        uuid=current_item['uuid'],
                        name=urllib.parse.unquote_plus(current_item['name']),
                        item_type=current_item.get('type', 'Unknown'),
                        parent_uuid=parent_path
                    ))
                current_item = {'name': value}
            elif field == 'item':
                current_item['uuid'] = value
            elif field == 'type':
                current_item['type'] = value
            
            i += 2
        
        # Don't forget the last item
        if current_item.get('name') and current_item.get('uuid'):
            items.append(InventoryItem(
                uuid=current_item['uuid'],
                name=urllib.parse.unquote_plus(current_item['name']),
                item_type=current_item.get('type', 'Unknown'),
                parent_uuid=parent_path
            ))
        
        # Cache names
        for item in items:
            self.uuid_name_cache[item.uuid] = item.name
        
        return items
    
    def get_folder_contents_by_path(
        self,
        folder_path: str,
        force_refresh: bool = False
    ) -> list[InventoryItem]:
        """Get contents of a folder by path."""
        full_path = folder_path if folder_path.startswith('/') else f'/My Inventory/{folder_path}'
        
        params = {
            'command': 'inventory',
            'action': 'ls',
            'path': full_path,
        }
        
        result = self._send_command(**params)
        
        if result.get('success', '').lower() != 'true':
            error = result.get('error', 'Unknown error')
            logger.error(f"Failed to list folder {folder_path}: {error}")
            return []
        
        return self._parse_inventory_data(result.get('data', ''), full_path)
    
    def get_folder_contents(self, folder_path: str, force_refresh: bool = False) -> list[InventoryItem]:
        """Get contents of a folder by path."""
        return self.get_folder_contents_by_path(folder_path, force_refresh)
    
    def ensure_folder_exists(self, path: str) -> Optional[str]:
        """Ensure a folder path exists, creating if necessary. Returns full path."""
        # Build full path
        full_path = path if path.startswith('/') else f'/My Inventory/{path}'
        
        # Check cache first
        if full_path in self.folder_uuid_cache:
            return full_path
        
        # Try to list the folder to see if it exists
        result = self._send_command(
            command='inventory',
            action='ls',
            path=full_path
        )
        
        if result.get('success', '').lower() == 'true':
            # Folder exists
            self.folder_uuid_cache[full_path] = full_path
            return full_path
        
        # Need to create the folder - do it path segment by path segment
        # Remove leading /My Inventory/ for processing
        rel_path = path.replace('/My Inventory/', '').lstrip('/')
        parts = [p for p in rel_path.split('/') if p]
        
        current_path = "/My Inventory"
        
        for part in parts:
            next_path = f"{current_path}/{part}"
            
            # Check if this segment exists via direct path
            check_result = self._send_command(
                command='inventory',
                action='ls',
                path=next_path
            )
            
            if check_result.get('success', '').lower() != 'true':
                # Path doesn't exist - but check if folder with same name exists at parent
                # This prevents creating duplicate folders
                parent_contents = self.get_folder_contents_by_path(current_path)
                existing_folder = None
                part_lower = part.lower()
                
                for item in parent_contents:
                    if item.item_type.lower() == 'folder' and item.name.lower() == part_lower:
                        existing_folder = item
                        logger.debug(f"Found existing folder '{item.name}' at {current_path}")
                        break
                
                if existing_folder:
                    # Use the existing folder (with its actual name/casing)
                    next_path = f"{current_path}/{existing_folder.name}"
                else:
                    # Create this folder
                    logger.info(f"Creating folder: {next_path}")
                    
                    if not self.dry_run:
                        create_result = self._send_command(
                            command='inventory',
                            action='mkdir',
                            name=part,
                            path=current_path
                        )
                        
                        if create_result.get('success', '').lower() != 'true':
                            logger.error(f"Failed to create folder {next_path}: {create_result.get('error', '')}")
                            return None
                        
                        time.sleep(0.5)  # Brief delay for SL to process
                    else:
                        logger.info(f"[DRY RUN] Would create folder: {next_path}")
            
            current_path = next_path
        
        self.folder_uuid_cache[full_path] = full_path
        return full_path
    
    def move_item(self, source_path: str, target_folder_path: str, item_name: str = "") -> bool:
        """
        Move an inventory item using source and target paths.
        Per Corrade API: action=mv, source=<path>, target=<folder path>
        """
        display_name = item_name or source_path.split('/')[-1]
        
        # Ensure target path is absolute
        if not target_folder_path.startswith('/'):
            target_folder_path = f'/My Inventory/{target_folder_path}'
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would move '{display_name}' -> {target_folder_path}")
            return True
        
        result = self._send_command(
            command='inventory',
            action='mv',
            source=source_path,
            target=target_folder_path
        )
        
        if result.get('success', '').lower() == 'true':
            logger.info(f"Moved '{display_name}' -> {target_folder_path}")
            return True
        else:
            error = result.get('error', 'Unknown')
            logger.error(f"Failed to move '{display_name}': {error}")
            return False
    
    def move_folder_contents(self, source_folder_path: str, target_path: str, folder_name: str, keep_folder_name: bool = False) -> bool:
        """
        Move a folder by recreating structure and moving its contents.
        SL doesn't allow moving folders directly - must move contents.
        
        Items are sorted into type-specific subfolders (Hair/, HUDs/, etc.)
        for CTS Wardrobe compatibility.
        
        Args:
            source_folder_path: Full path to source folder
            target_path: Target folder path (already includes brand/product hierarchy)
            folder_name: Name of the original folder (for logging)
            keep_folder_name: If True, create subfolder with original name
        """
        # Ensure paths are absolute
        if not source_folder_path.startswith('/'):
            source_folder_path = f'/My Inventory/{source_folder_path}'
        if not target_path.startswith('/'):
            target_path = f'/My Inventory/{target_path}'
        
        # If keeping folder name, append it to target
        if keep_folder_name:
            target_path = f"{target_path}/{folder_name}"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would move folder '{folder_name}' -> {target_path}")
            return True
        
        # Step 1: Get contents of source folder
        items = self.get_folder_contents_by_path(source_folder_path)
        
        if not items:
            logger.warning(f"Source folder '{source_folder_path}' is empty or not found")
            return False
        
        # Step 2: Move each item from source to target, organizing into subfolders
        moved_count = 0
        subfolder_cache = set()  # Track which subfolders we've created
        
        for item in items:
            item_source = f"{source_folder_path}/{item.name}"
            
            # Detect what subfolder this item should go in (Hair/, HUDs/, etc.)
            subfolder = detect_item_subfolder(item.name)
            
            if subfolder:
                item_target = f"{target_path}/{subfolder}"
                
                # Create subfolder path if we haven't already
                if subfolder not in subfolder_cache:
                    # Ensure full path exists
                    self.ensure_folder_exists(item_target.replace('/My Inventory/', ''))
                    subfolder_cache.add(subfolder)
                    time.sleep(0.3)
            else:
                # No specific subfolder - ensure target exists
                self.ensure_folder_exists(target_path.replace('/My Inventory/', ''))
                item_target = target_path
            
            result = self._send_command(
                command='inventory',
                action='mv',
                source=item_source,
                target=item_target
            )
            
            if result.get('success', '').lower() == 'true':
                if subfolder:
                    logger.debug(f"  Moved: {item.name} -> {subfolder}/")
                else:
                    logger.debug(f"  Moved: {item.name}")
                moved_count += 1
            else:
                logger.error(f"  Failed to move {item.name}: {result.get('error', 'Unknown')}")
            
            time.sleep(0.3)  # Brief delay between items
        
        logger.info(f"Moved {moved_count}/{len(items)} items from '{folder_name}' -> {target_path}")
        if subfolder_cache:
            logger.info(f"  Organized into subfolders: {', '.join(sorted(subfolder_cache))}")
        
        # Step 3: Delete empty source folder
        if moved_count == len(items) and moved_count > 0:
            logger.debug(f"Removing empty source folder: {source_folder_path}")
            self._send_command(
                command='inventory',
                action='rm',
                path=source_folder_path
            )
        
        return moved_count > 0
    
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
        recursive: bool = False,
        sort_folders: bool = True
    ):
        """
        Sort items in a folder according to rules.
        
        Args:
            source_path: Path to folder to sort
            recursive: Whether to recurse into subfolders
            sort_folders: Whether to sort folders themselves (not just items inside)
        """
        logger.info(f"Processing folder: {source_path}")
        
        # Normalize path
        full_path = source_path if source_path.startswith('/') else f'/My Inventory/{source_path}'
        
        # Get folder contents
        items = self.get_folder_contents_by_path(full_path)
        
        if not items:
            logger.info(f"No items found in {source_path}")
            return
        
        batch_count = 0
        
        for item in items:
            # Skip system folders
            if self.is_system_folder(item.name):
                logger.debug(f"Skipping system folder: {item.name}")
                self.skipped_count += 1
                continue
            
            # For folders: check if they match any rules (product folders)
            if item.item_type.lower() == 'folder':
                if sort_folders:
                    # Try to match folder name against rules
                    rule = self.find_matching_rule(item.name)
                    
                    if rule:
                        # Build dynamic path with brand/product hierarchy
                        brand = extract_brand_from_name(item.name)
                        product = extract_product_name(item.name, brand) if brand else None
                        
                        # Build target path: BaseCategory/Brand/Product/
                        dynamic_path = rule.target_path
                        if brand:
                            dynamic_path = f"{dynamic_path}/{brand}"
                            if product:
                                dynamic_path = f"{dynamic_path}/{product}"
                        
                        target_path = self.ensure_folder_exists(dynamic_path)
                        
                        if target_path:
                            item_source_path = f"{full_path}/{item.name}"
                            
                            # Use move_folder_contents for folders (SL can't move folders directly)
                            # Pass dynamic_path directly - items go into Brand/Product/Type structure
                            if self.move_folder_contents(item_source_path, dynamic_path, item.name):
                                self.moved_count += 1
                                batch_count += 1
                                logger.info(f"  Matched rule: {rule.name} -> {dynamic_path}")
                                
                                time.sleep(self.delay)
                                
                                if batch_count >= self.batch_size:
                                    logger.info(f"Batch complete ({self.batch_size} items), pausing {self.batch_delay}s...")
                                    time.sleep(self.batch_delay)
                                    batch_count = 0
                            else:
                                self.error_count += 1
                        continue
                
                # Recursively process if enabled and didn't match/move
                if recursive:
                    subfolder_path = f"{full_path}/{item.name}"
                    self.sort_folder(subfolder_path, recursive=True, sort_folders=sort_folders)
                continue
            
            # For non-folder items: match and move
            rule = self.find_matching_rule(item.name)
            
            if rule:
                target_path = self.ensure_folder_exists(rule.target_path)
                
                if target_path:
                    item_source_path = f"{full_path}/{item.name}"
                    
                    if self.move_item(item_source_path, target_path, item.name):
                        self.moved_count += 1
                        batch_count += 1
                        logger.info(f"  Matched rule: {rule.name}")
                        
                        time.sleep(self.delay)
                        
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
