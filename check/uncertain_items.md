# Uncertain Items - Post-Sort Analysis (Dec 29, 2025)

## Summary
After multiple sort passes, 101+ items were successfully moved. The following items remain at inventory root and need review.

---

## Empty Folders (items already moved, container remains)
These folders matched rules but show 0 items - the contents were moved in previous runs. The empty folders should be cleaned up manually or by a cleanup pass:

- `LeLUTKA Noel Head 3.1` → was targeting Body Parts/Heads
- `LeLUTKA Raven Head 3.1` → was targeting Body Parts/Heads  
- `LeLUTKA Avalon Head 3.1` → was targeting Body Parts/Heads
- `GENUS Project - Genus Head - Strong Face W003 - v2.0` → was targeting Body Parts/Heads
- `GENUS Project - BOM 4K - MAKEUP\/SKIN` → was targeting Body Parts/Skins
- `~Silenced~ Whim HUD v1.6056` → was targeting BDSM
- `RemVision BOXED` → was targeting Boxed Items
- `BodyLanguage SLC BENTO AO Cecilia` → was targeting Animation Overrides

---

## Items Needing Rule Updates

### 1. HDM Products (BDSM)
**Folders:**
- `*HDM* Nilea - open body v2.6.0b for Maitreya (unpacked)`
- `*HDM* Nilea - the kink add-on v2.6.0c for Maitreya (unpacked)`

**Issue:** The `*` characters in the name may be causing regex matching issues.
**Suggested fix:** Escape asterisks in brand name matching or add specific keyword pattern.
**Destination:** BDSM/HDM/

---

### 2. NGW Products (BDSM Restraints)
**Folders:**
- `NGW helene hood box V2`
- `NGW compact armbinder 1.3 rlv + (mait...`

**Issue:** These are boxed items but also BDSM restraints. Need to decide priority.
**Question:** Should boxed BDSM items go to Boxed Items or BDSM?
**Current behavior:** Tried Boxed Items but items not found

---

### 3. Skins/Body Products
**Folders:**
- `VELOUR: The "Ipanema Body" for Maitreya (BLUSH)` - This is a body SKIN (applier)
- `Pepe Skins - Lelu X \/ Peach V2 \/ Moonbeam` - Skin product
- `2faces - "UNA" - full pack` - Skin product
- `OMY Megan Fatpack` - Skin product

**Issue:** These should go to Body Parts/Skins but didn't match. The path separators (`\/`) and quotes may cause issues.
**Destination:** Body Parts/Skins/[Brand]/

---

### 4. Body Deformers
**Folder:**
- `++ kuromori ++ ebody reborn butt fixer deformer`

**Issue:** Has "deformer" and "fixer" keywords but didn't match.
**Destination:** Body Parts/Bodies/ (with body fixer products)

---

### 5. Clothing Items
**Folder:**
- `erratic \/ ciri - cuban heel \/ FATPACK (maitreya) (unpacked)` - Shoes

**Issue:** Path separators in name (`\/`). This is clearly shoes.
**Destination:** Clothing/Shoes/erratic/

---

### 6. Animation Overrides
**Folder:**
- `BodyLanguage SLC BENTO AO Cecilia`

**Issue:** Has "AO" and "BENTO AO" but items showed not found (empty folder).
**Destination:** Animation Overrides/ (already attempted)

---

### 7. Jewelry/Accessories
**Folder:**
- `[BB] Belzebubble - Nipple Rings`

**Issue:** Nipple rings - is this jewelry/accessories or BDSM?
**Question for user:** Where should nipple jewelry go?

---

### 8. HUDs/Unpacker Items
**Folders:**
- `CryBunBun - [Submissa Harness] [FATPACK] Unpacker HUD (reborn)` - Unpacker for BDSM item
- `[chouette] Auto Teleporter HUD (wear\/rez to unpack) (v1.02)` - Utility HUD
- `KUNI - Sharon (Color HUD Pack) (v3)` - Color HUD

**Question:** Should these stay in Boxed Items or go with their respective categories?

---

### 9. Misc/Unknown
**Folders:**
- `Aleph\null Welcome Package` - Welcome/freebie pack
- `Size:KaS, bundle (box)` - Unknown product
- `Loose` - Unknown (possibly unpacked items?)
- `Latex` - Materials folder (should stay in Materials)
- `GIFT LOCATION` - Landmark/location info
- `RR Update folder` - RealRestraint updates (BDSM)
- `BDSM animations` - Should go to BDSM/Animations

---

## Recommended Actions

1. **Clean up empty folders** - Delete the LeLUTKA/GENUS/Silenced empty containers
2. **Fix HDM regex** - Escape or handle `*` characters properly
3. **Add skin brands** - VELOUR, 2faces, OMY, Pepe Skins
4. **Add path sanitization** - Handle `\/` in folder names
5. **Clarify BDSM vs Boxed** - For boxed BDSM items

---

## Questions for User

1. **Nipple rings** (`[BB] Belzebubble`) - Accessories or BDSM?
2. **Boxed BDSM items** - Keep in Boxed Items or move to BDSM?
3. **Utility HUDs** (teleporter, color packs) - Where should these go?
4. **BDSM animations folder** - Move to BDSM/ or keep at root?
