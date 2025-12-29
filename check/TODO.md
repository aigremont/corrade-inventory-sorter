# Inventory Sorter - TODO List

*Generated: Dec 29, 2025*

## Summary
- **Completed sorts**: 150+ items moved across multiple passes
- **Empty folders cleaned**: 8 deleted
- **Remaining at root**: 18 folders

---

## Code Fixes Needed

### 1. Path Encoding Issues (HIGH PRIORITY)
The sorter fails on folder names containing special characters that break API paths.

**Affected folders:**
- `Pepe Skins - Lelu X \/ Peach V2 \/ Moonbeam` (forward slashes)
- `erratic \/ ciri - cuban heel \/ FATPACK` (forward slashes)
- `2faces - ""UNA"" - full pack` (double quotes)
- `VELOUR: The ""Ipanema Body""` (colon and double quotes)
- `[chouette] Auto Teleporter HUD (wear\/rez to unpack)` (escaped slashes)
- `++ kuromori ++` (plus signs)
- `Aleph\null Welcome Package` (backslash/null)

**Fix needed:** Sanitize folder names before API calls, escape or URL-encode special characters.

---

### 2. HDM Regex Not Matching
**Affected folders:**
- `*HDM* Nilea - open body v2.6.0b for Maitreya (unpacked)`
- `*HDM* Nilea - the kink add-on v2.6.0c for Maitreya (unpacked)`

**Issue:** Despite regex `\*HDM\*`, these aren't matching. May need to check normalization or matching logic.

**Destination:** BDSM/HDM/

---

## Manual Categorization Needed

### 3. Boxed BDSM Items → Objects/Check
Per user: boxed items that look like unpackers go to Objects/Check for manual review.

- [ ] `NGW helene hood box V2`
- [ ] `NGW compact armbinder 1.3 rlv + (mait...` (truncated name)
- [ ] `CryBunBun - [Submissa Harness] [FATPACK] Unpacker HUD (reborn)`

---

### 4. Skins → Body Parts/Skins
Once path encoding is fixed:

- [ ] `Pepe Skins - Lelu X \/ Peach V2 \/ Moonbeam`
- [ ] `VELOUR: The ""Ipanema Body"" for Maitreya (BLUSH)`

---

### 5. Shoes → Clothing/Shoes
Once path encoding is fixed:

- [ ] `erratic \/ ciri - cuban heel \/ FATPACK (maitreya) (unpacked)`

---

### 6. Body Deformers → Body Parts/Bodies
- [ ] `++ kuromori ++ ebody reborn butt fixer deformer`

---

### 7. Utility HUD → Objects/Utilities or Check
- [ ] `[chouette] Auto Teleporter HUD (wear\/rez to unpack) (v1.02)`

---

### 8. Unknown/Needs Investigation
These need manual inspection to determine category:

- [ ] `Aleph\null Welcome Package` - Freebie/welcome pack?
- [ ] `Size:KaS, bundle (box)` - Unknown product
- [ ] `Loose` - Loose items folder?
- [ ] `2faces - ""UNA"" - full pack` - User said 2faces makes clothing, could be outfit
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

