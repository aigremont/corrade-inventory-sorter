# Inventory Sorter - TODO List

*Generated: Dec 29, 2025*

## Summary
- **Completed sorts**: 200+ items moved across multiple passes
- **BDSM folder organized**: 47 items sorted into Equipment subfolders
- **Empty folders cleaned**: 12 deleted by sorter + 5 deleted manually
- **Remaining cleanup**: Merge duplicate Docs and KDC folders in-viewer

---

## Code Fixes Needed

### 1. Path Encoding Issues (HIGH PRIORITY)
The sorter fails on folder names containing special characters that break API paths.

**Affected folders:**
- ~~`Pepe Skins - Lelu X \/ Peach V2 \/ Moonbeam`~~ ✓ moved manually
- ~~`erratic \/ ciri - cuban heel \/ FATPACK`~~ ✓ deleted (were stockings)
- ~~`2faces - ""UNA"" - full pack`~~ ✓ renamed (outfit)
- `VELOUR: The ""Ipanema Body""` (colon and double quotes)
- ~~`[chouette] Auto Teleporter HUD (wear\/rez to unpack)`~~ ✓ renamed
- ~~`++ kuromori ++`~~ ✓ renamed
- ~~`Aleph\null Welcome Package`~~ ✓ deleted

**Fix needed:** Sanitize folder names before API calls, escape or URL-encode special characters.

---

### 2. ~~HDM Regex Not Matching~~ ✓ RESOLVED
**Affected folders:**
- ~~`*HDM* Nilea - open body v2.6.0b for Maitreya (unpacked)`~~ ✓ deleted
- ~~`*HDM* Nilea - the kink add-on v2.6.0c for Maitreya (unpacked)`~~ ✓ deleted

~~**Issue:** Despite regex `\*HDM\*`, these aren't matching.~~

User deleted manually.

---

## Manual Categorization Needed

### 3. ~~Boxed BDSM Items~~ NGW Items → BDSM ✓ DONE
These were moved to BDSM/Equipment/NGW:

- [x] `XETAL NGW Ohnus hood` variants → BDSM/Equipment/NGW
- [x] `ngw binder` textures → BDSM/Textures (then deleted - empty)
- [x] `CryBunBun - [Submissa Harness]` ✓ deleted

---

### 4. Skins → Body Parts/Skins
Once path encoding is fixed:

- [x] `Pepe Skins - Lelu X \/ Peach V2 \/ Moonbeam` ✓ moved manually
- [ ] `VELOUR: The ""Ipanema Body"" for Maitreya (BLUSH)`

---

### 5. Shoes → Clothing/Shoes
~~Once path encoding is fixed:~~

- [x] `erratic \/ ciri - cuban heel` ✓ deleted (were stockings, not shoes)

---

### 6. Body Deformers → Body Parts/Bodies
- [x] `++ kuromori ++` ✓ renamed manually

---

### 7. Utility HUD → Objects/Utilities or Check
- [x] `[chouette] Auto Teleporter HUD` ✓ renamed manually

---

### 8. Unknown/Needs Investigation
These need manual inspection to determine category:

- [x] `Aleph\null Welcome Package` ✓ deleted
- [x] `Size:KaS` ✓ renamed (BDSM gear)
- [x] `Loose` ✓ renamed to "metal" (Materials)
- [x] `2faces - ""UNA"" - full pack` ✓ renamed (outfit)
- [x] `KUNI - Sharon` ✓ is hair → Body Parts/Hair
- [x] `GIFT LOCATION` ✓ deleted
- [x] `RR Update folder` → Objects/Updaters
- [x] `Latex` ✓ Materials (stays)

---

## Priority Order

1. ~~**Fix path encoding**~~ - Most handled manually
2. ~~**Debug HDM matching**~~ - Deleted manually
3. **Structure BDSM folder** - Organize items at BDSM root into subfolders
4. **Add Objects/Check rule** - For uncertain boxed items

---

## BDSM Folder Structure ✓ (DONE)

BDSM folder is now organized. All 47 loose items moved to subfolders:
- `BDSM/Equipment/KDC/` - KDC hoods, blindfolds, muzzles, cuffs, padlocks, chastity belts
- `BDSM/Equipment/NGW/` - NGW hoods (including XETAL NGW items)
- `BDSM/Equipment/CC-TT/` - CC/T&T chastity belts
- `BDSM/Docs/` - Changelogs and readme files
- `BDSM/Landmarks/` - Store landmarks (now empty - deleted)
- `BDSM/Clothing/Corsets/` - Corsets
- `BDSM/HUDs/` - KDC HUDs and activators

**Cleanup needed in-viewer:**
- [ ] Merge duplicate `BDSM/Docs/` folders (2 exist)
- [ ] Merge duplicate `BDSM/Equipment/KDC/` folders (2 exist)

---

## Completed ✓

- [x] Nipple rings → Body Parts/Accessories
- [x] BDSM animations → Animations/BDSM
- [x] OMY → Animations
- [x] Corsets → BDSM/Clothing/Corsets
- [x] Pantyhose → Clothing/Hosiery
- [x] Aphasia/Ideeen BDSM → BDSM/
- [x] Empty folder cleanup (8 folders deleted)
- [x] Pepe Skins → moved manually
- [x] erratic ciri → deleted (stockings)
- [x] 2faces UNA → renamed (outfit)
- [x] chouette teleporter → renamed
- [x] kuromori → renamed
- [x] Aleph\null → deleted
- [x] HDM Nilea items → deleted
- [x] CryBunBun Submissa Harness → deleted
- [x] Size:KaS → renamed (BDSM gear)
- [x] KUNI Sharon → Hair (rule added)
- [x] GIFT LOCATION → deleted
- [x] RR Update → Objects/Updaters (rule added)
- [x] Latex → Materials
- [x] Loose → renamed to "metal" (Materials)
- [x] BDSM folder organized - 47 items sorted into Equipment/KDC, Equipment/NGW, Equipment/CC-TT, Docs, Landmarks
- [x] Empty BDSM subfolders deleted - Accessories, Eyes, Textures, Landmarks

