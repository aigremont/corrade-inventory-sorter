# Inventory Analysis - Post First Sort

Based on cache from allonde Resident's inventory.

## Current State

| Metric | Count |
|--------|-------|
| Folders in root | 90 |
| Duplicate "Hair" folders | 9 |
| Duplicate "Shoes" folders | 11 |
| Duplicate "HUDs" folders | 28 |
| Duplicate "Apparel" folders | 2 |

## Issues Identified

### 1. Duplicate Top-Level Folders
The sorter created a SECOND "Apparel" folder instead of using the existing one:
- `u0862e6dd-41a3-4f5e-89a6-e086224d29bc` (line 81 - used)
- `ue19768ec-b8d4-4db2-b187-dfea7c07b226` (line 194 - duplicate!)

**Fix needed**: Detect existing folders by name before creating new ones.

### 2. Unsorted Products Still in Root

These need rules or better pattern matching:

| Folder Name | Should Go To |
|-------------|--------------|
| `LeLUTKA Avalon Head 3.1` | Body Parts/Heads/LeLUTKA |
| `GENUS Project - Genus Head...` | Body Parts/Heads/GENUS |
| `LeLUTKA Raven Head 3.1` | Body Parts/Heads/LeLUTKA |
| `LeLUTKA Noel Head 3.1` | Body Parts/Heads/LeLUTKA |
| `KDC Avara Hood v8` | BDSM/Hoods/KDC |
| `KDC Classic leather relaxation pack v1` | BDSM/Restraints/KDC |
| `KDC classic leather ankle cuffs v11` | BDSM/Cuffs/KDC |
| `KDC Warden Straitjacket v6` | BDSM/Straitjackets/KDC |
| `KDC Spare Muzzle Plugs` | BDSM/Gags/KDC |
| `*HDM* Nilea...` | BDSM/Body/HDM |
| `CC/T&T Mesh Chastity Belt` | BDSM/Chastity/CC-T&T |
| `Vixen Leather - collar part` | BDSM/Collars/Vixen |
| `NGW helene hood box V2` | BDSM/Hoods/NGW |
| `AVEC TOI - Selene Thong...` | Apparel/Clothing/AVEC TOI |
| `BodyLanguage SLC BENTO AO Cecilia` | Animation Overrides |
| `RemVision BOXED` | Boxed Items |
| `Ava's Lewd: Frame corset` | Apparel/Clothing or BDSM |
| `[BB] Belzebubble - Nipple Rings` | BDSM/Piercings or Accessories |
| `.::Scuttlebutt::. Slut & Tramp Barcode Tattoos` | Body Parts/Tattoos |
| `[ The Nothing Aphasia Collection ]` | ? (need to inspect) |
| `[chouette] Auto Teleporter HUD` | HUDs/Utility |
| `~Silenced~ Whim HUD` | BDSM/HUDs |
| `Kristy's PBR Fixer Scripts` | Scripts |

### 3. Fragmented Subfolders

28 separate "HUDs" folders scattered throughout instead of consolidated per-brand.

**Current**: `Apparel/Shoes/HUDs` (multiple)
**Should be**: Items should stay with their product, not grouped by type at category level.

This is actually correct for CTS Wardrobe! The structure Brand/Product/HUDs is right.

## Recommended Improvements

### Priority 1: Fix Duplicate Folder Creation
- Before `mkdir`, check if folder already exists at that path
- Use existing folder's UUID instead of creating new one

### Priority 2: Add BDSM Category Rules
```json
{
  "name": "BDSM Restraints",
  "keywords": ["KDC", "collar", "cuff", "hood", "gag", "chastity", "straitjacket", "restraint"],
  "target_path": "BDSM"
}
```

### Priority 3: Add Body Parts Rules
```json
{
  "name": "Mesh Heads",
  "keywords": ["LeLUTKA", "GENUS", "Catwa", "LAQ", "Akeruka", "Head"],
  "target_path": "Body Parts/Heads"
}
```

### Priority 4: Merge Duplicate Folders
Add a "merge mode" that:
1. Finds folders with identical names
2. Moves contents to the first/primary one
3. Deletes the empty duplicates

## Brand Detection Improvements

Current patterns miss these brand formats:
- `*HDM*` - asterisks
- `[BB]` - brackets
- `.::Brand::.` - decorative punctuation
- `~Brand~` - tildes
- `[chouette]` - lowercase brackets

