# Second Life Inventory Auto-Sorter - Project Summary

**Last Updated:** December 29, 2025  
**Repository:** https://github.com/aigremont/corrade-inventory-sorter

---

## Project Goal

Create an automated system to organize Second Life inventory using the Corrade scripted agent's HTTP API. The inventory should be sorted into a hierarchical structure compatible with CTS Wardrobe (`Category/Brand/Product/Type/`), with items organized into Second Life's system folders (Clothing, Body Parts, Animations, etc.).

---

## What We Built

### 1. Main Inventory Sorter (`inventory_sorter.py`)
A Python script that connects to Corrade's HTTP API to sort inventory based on configurable rules.

**Features:**
- ✅ UUID-based operations for performance
- ✅ Folder name normalization (handles Unicode spaces, special characters)
- ✅ Brand/product extraction from item names
- ✅ Hierarchical sorting (Category/Brand/Product/Type)
- ✅ CTS Wardrobe compatible subfolder detection (Hair/, HUDs/, Docs/, etc.)
- ✅ Dry-run mode
- ✅ Configurable via JSON
- ✅ 80+ default sorting rules for:
  - Hair, Heads, Bodies, Skins
  - BDSM equipment and clothing
  - Clothing, Shoes, Hosiery
  - Animations, Gestures
  - Objects, Materials

**Known Issues:**
- ❌ Created custom root folders (Apparel/, Avatar/) instead of using system folders
- ❌ Too aggressive with deletions - accidentally deleted folders with contents
- ⚠️ Rules match on keywords but need refinement for edge cases

### 2. Plan-Based Workflow (`work/` directory)

After issues with the direct sorter, we built a safer, plan-based approach:

#### `analyze_inventory.py`
- Parses Alchemy/Firestorm inventory cache files
- Generates analysis reports showing current structure
- Creates reviewable JSON move plans for each category
- Identifies items needing manual review

#### `execute_plan.py`
- Executes move plans via Corrade API
- Supports dry-run mode (test before executing)
- Moves items one plan at a time
- **Never deletes anything** - only moves items
- Tracks executed plans
- Rate-limited to avoid overwhelming Second Life servers

#### `merge_folders.py`
- Designed to merge contents of custom folders into system folders
- Recursively handles nested folder structures
- **Issue:** Had path duplication bug (created `/My Inventory/My Inventory/`)

---

## What Worked Successfully

### ✅ Successfully Executed Plans (106 items moved)

| Category | Items | Status |
|----------|-------|--------|
| **Materials** | 5 items (Latex, Metal) | ✅ Moved to `Materials/` |
| **Body Parts/Heads** | 21 items (3 LeLUTKA heads) | ✅ Organized by head model |
| **Body Parts/Bodies** | 21 items (VELOUR skin, kuromori deformer) | ✅ Sorted correctly |
| **Body Parts/Hair** | 2 items (KUNI Sharon) | ✅ Moved to Hair folder |
| **BDSM Equipment** | 9 items (NGW hood, armbinder) | ✅ Organized into Equipment |
| **BDSM** | 15 items (KaS Catsuit) | ✅ BDSM folder |
| **Clothing** | 24 items (2faces UNA outfit) | ✅ Moved to Clothing |
| **Objects/Updaters** | 8 items (RR Update folder) | ✅ New folder created |
| **Objects/Utilities** | 1 item (chouette teleporter) | ✅ New folder created |

### ✅ Other Successes

- **BDSM Folder Organization**: Sorted 47 loose BDSM items into organized subfolders:
  - `Equipment/KDC/` - hoods, blindfolds, muzzles, cuffs, padlocks
  - `Equipment/NGW/` - XETAL NGW hoods
  - `Equipment/CC-TT/` - chastity belts
  - Moved changelogs to `Docs/`
  - Cleaned up 4 empty folders

- **Marketplace Lookup Module** (`marketplace_lookup.py`):
  - Scrapes Second Life Marketplace for category information
  - Handles OpenID login for adult content
  - Caches results
  - Maps marketplace categories to sort paths

---

## Current Issues & Challenges

### 🔴 Critical Issues

1. **Accidental Deletions**
   - The initial BDSM folder cleanup deleted the `Accessories` folder which contained:
     - Vixen Leather collar parts (full set)
     - ENVY cuffs and collars
     - Multiple KDC items
     - FACS pantyhose
     - And many more items
   - **Root Cause**: Script was deleting folders it thought were empty, but they weren't
   - **Items are in Trash** - user recovered them to root

2. **Path Duplication Bug**
   - Merge script created `/My Inventory/My Inventory/` nested structure
   - This happened because paths weren't being normalized consistently
   - **Fixed in code**, but the bad folder structure exists in inventory
   - **Manual cleanup needed**: Delete the duplicate `/My Inventory/My Inventory/` folder

3. **Wrong Folder Hierarchy**
   - Early sorter created `Apparel/`, `Avatar/` at root instead of using system folders
   - These should have merged into:
     - `Apparel/Hair/` → `Body Parts/Hair/`
     - `Apparel/Clothing/` → `Clothing/`
     - `Apparel/Shoes/` → `Clothing/Shoes/`
     - `Avatar/Body Parts/` → `Body Parts/`

### ⚠️ Issues Needing Attention

4. **Special Character Handling**
   - Folder names with `\/`, `""`, `++`, `:` characters break API paths
   - Examples:
     - `VELOUR: The ""Ipanema Body""`
     - `Pepe Skins - Lelu X \/ Peach V2`
     - `erratic \/ ciri`
   - These need sanitization before API calls

5. **HDM Regex Pattern**
   - Items like `*HDM* Nilea` weren't matching despite `\*HDM\*` regex
   - Needs investigation into Corrade's regex engine behavior

6. **Empty Folder Cleanup**
   - After moving items, source folders are left empty
   - These need manual cleanup in-viewer
   - No safe automated way to delete (risk of deleting non-empty folders)

7. **Merge Operations Incomplete**
   - The `Apparel/` and `Avatar/` folders still need their contents merged
   - Current state is uncertain due to the path bug
   - Needs manual verification in-viewer

---

## Key Learnings

### What NOT to Do

1. **Never delete folders via API** - Too risky, even with "empty" checks
2. **Always use system folders** - Don't create new root-level organizational folders
3. **Test path handling thoroughly** - Path normalization bugs cause nested folder issues
4. **Verify operations in-viewer** - API success doesn't always mean what you think

### What Works Well

1. **Plan-based workflow** - Review JSON files before executing
2. **Dry-run first** - Always test before real operations
3. **One category at a time** - Easier to verify and rollback
4. **UUID-based operations** - Faster than name-based lookups
5. **Rate limiting** - Essential to avoid overwhelming SL servers

---

## Architecture Decisions

### Why Corrade Over Alchemy Viewer Integration?

**Original Plan:** Integrate directly into Alchemy Viewer (C++)
- ❌ Extremely long compile times (45+ minutes)
- ❌ Complex build dependencies
- ❌ Proprietary packages (FMod) blocking fork builds
- ❌ Requires viewer restart to test changes

**Current Approach:** External Python tool via Corrade
- ✅ Fast iteration (no compilation)
- ✅ Can run on servers/scheduled
- ✅ Language-agnostic (any language that can HTTP)
- ✅ Easier to share and modify
- ✅ Works with any SL viewer

### API Strategy

**Corrade's Inventory API:**
- Format: HTTP POST with URL-encoded params
- Response: CSV-like format `name,<value>,item,<uuid>,type,<type>,...`
- Commands used:
  - `ls` - List folder contents
  - `mkdir` - Create folders (needs `path` + `name` params)
  - `mv` - Move items (needs `source` UUID + `path` OR `source` path + `target` path)
  - `rm` - Delete (we avoid using this!)

**Challenges:**
- Inconsistent parameter formats (`item=` vs `path=` vs `source=`)
- Path handling varies by command
- No way to move folders directly - must move contents
- Cache invalidation timing issues

---

## Project Structure

```
corrade-inventory-sorter/
├── inventory_sorter.py          # Main sorter (direct approach)
├── marketplace_lookup.py        # Marketplace scraping module
├── work/
│   ├── analyze_inventory.py    # Parse cache → generate plans
│   ├── execute_plan.py          # Execute plans via Corrade
│   ├── merge_folders.py         # Merge custom folders into system folders
│   ├── analysis/                # Generated reports
│   │   ├── structure.md         # Inventory tree view
│   │   └── root_items.md        # Items needing sorting
│   ├── plans/                   # Reviewable move plans (JSON)
│   ├── executed/                # Completed plans
│   └── README.md                # Workflow documentation
├── dump/                        # Inventory cache files
├── check/                       # Manual review items
│   ├── TODO.md                  # Tracking list
│   └── uncertain_items.md       # Items needing clarification
├── config.example.json          # Template config
├── rules.example.json           # Template rules
└── README.md                    # Project documentation
```

---

## Next Steps & Recommendations

### Immediate Actions

1. **Manual Cleanup in Viewer:**
   - [ ] Delete `/My Inventory/My Inventory/` folder (created by bug)
   - [ ] Verify items in `Body Parts/`, `Clothing/`, `Materials/` are correct
   - [ ] Delete empty source folders (Metal, Latex, etc. at root)
   - [ ] Check if Vixen Leather items are recovered from Trash

2. **Verify Merge Status:**
   - [ ] Check what's still in `Apparel/` folder
   - [ ] Check what's still in `Avatar/` folder
   - [ ] Manually merge remaining items if needed

3. **Code Fixes (if continuing automated sorting):**
   - [ ] Add path sanitization for special characters
   - [ ] Add more defensive checks before any deletions
   - [ ] Improve empty folder detection (check recursively)
   - [ ] Add inventory verification step after moves

### Future Enhancements

1. **Rule Improvements:**
   - More specific head/body detection (avoid catching clothing)
   - Better brand extraction for various naming patterns
   - Handle furniture properly (`Objects/Furniture/Vendor/Item`)
   - Expand BDSM categories (Restraints, Equipment, Furniture, Toys)

2. **Marketplace Integration:**
   - Use marketplace data to auto-categorize uncertain items
   - Build a database of known products → categories
   - Handle items without marketplace listings

3. **Safety Features:**
   - Pre-move inventory snapshot/backup
   - Rollback capability
   - Verification reports after moves
   - Conflict detection (duplicate folder names)
   - Never delete - only move to "Pending Deletion" folder

4. **Performance:**
   - Batch API calls where possible
   - Better caching strategy
   - Parallel processing for independent operations

---

## Known Limitations

1. **Second Life API Constraints:**
   - No native folder move operation (must move contents)
   - Cache invalidation delays
   - Rate limiting needed
   - No atomic operations (moves can partially fail)

2. **Corrade Specifics:**
   - Requires Corrade to be logged in and running
   - Only works with one account at a time
   - Some inventory operations require cache refresh
   - Path format inconsistencies between commands

3. **Sorting Complexity:**
   - Many items don't follow naming conventions
   - Brands make multiple product types
   - Regional/cultural naming differences
   - User-created items have arbitrary names

---

## Contact & Resources

- **Repository:** https://github.com/aigremont/corrade-inventory-sorter
- **Corrade Documentation:** https://grimore.org/secondlife/scripted_agents/corrade
- **CTS Wardrobe:** https://carlyletheassolutions.com/wardrobe.php

---

## Conclusion

The project successfully demonstrated automated inventory sorting via Corrade, with 106+ items organized correctly. However, aggressive folder deletion and path handling bugs caused significant issues that require manual cleanup.

**The plan-based workflow is production-ready** for future use, with proper safeguards:
- ✅ No deletions
- ✅ Dry-run testing
- ✅ Reviewable plans
- ✅ One category at a time

**Recommendation:** Continue with the plan-based approach for any future sorting, with manual verification after each plan execution.

