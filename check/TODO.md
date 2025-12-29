# Inventory Sorter - TODO List

*Generated: Dec 29, 2025*

## Summary
- **Completed sorts**: 150+ items moved across multiple passes
- **Empty folders cleaned**: 8 deleted by sorter + 5 deleted manually
- **Remaining at root**: ~10 folders (user working through list)

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

### 3. ~~Boxed BDSM Items~~ NGW Items → BDSM
These aren't boxed - they're actual BDSM equipment:

- [ ] `NGW helene hood box V2` → BDSM (alpha for helene hood)
- [ ] `NGW compact armbinder` → BDSM/Equipment
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
- [ ] `Size:KaS, bundle (box)` - Unknown product
- [ ] `Loose` - Loose items folder?
- [x] `2faces - ""UNA"" - full pack` ✓ renamed (outfit)
- [ ] `KUNI - Sharon (Color HUD Pack) (v3)` - Color HUD for what product?
- [ ] `GIFT LOCATION` - Landmark/location info?
- [ ] `RR Update folder` - RealRestraint updates → BDSM?
- [ ] `Latex` - Materials folder (should stay in Materials if contains textures)

---

## Priority Order

1. **Fix path encoding** - This unblocks most of the remaining items
2. **Debug HDM matching** - BDSM products waiting
3. **Add Objects/Check rule** - For uncertain boxed items
4. **Manual review** - Unknown items list above

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

