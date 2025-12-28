# Sorting Patterns Reference

Extracted from initial development work. Use these to expand rules.

## Folder Detection Patterns

### Boxed Items (Priority 100)
Regex: `(Box|Add\s*Me|Rezz\s*Me|Unpack|boxed|\(boxed\))`

### Demos (Priority 90)
Regex: `demo` (case insensitive)

### Hair Brands
Keywords: Magika, Stealthic, Doux, Truth, Sintiklia, Wasabi, Tableau Vivant

### Shoe Keywords
Boots, Heels, Shoes, Sneakers, Sandals, Flats, Pumps, Loafers, Ballet

### Clothing Keywords
Dress, Gown, Skirt, Pants, Shirt, Top, Sweater, Lingerie, Bikini, 
Blouse, Jacket, Coat, Jeans, Shorts, Tank, Corset

### Body Part Brands
Maitreya, Legacy, Belleza, Slink, Catwa, Lelutka, Genus, LAQ, Akeruka

### Body Part Keywords
Skin, Shape, Eyes, Head, Body, Mesh Body, Bento, BOM, Applier

### Furniture/Decor
Chair, Table, Lamp, Rug, Decor, Furniture, Sofa, Bed, Couch, 
Desk, Shelf, Cabinet, Mirror, Plant, Vase

### Accessory Keywords
Ring, Necklace, Earring, Bracelet, Collar, Cuff, Choker, Piercing

## Item Subfolder Detection

Used for CTS Wardrobe compatible sorting within product folders:

| Pattern | Subfolder |
|---------|-----------|
| hud | HUDs/ |
| hair, bangs, pigtail, ponytail, braid, wig | Hair/ |
| skin | Skin/ |
| shape | Shape/ |
| eye (not eyeshadow) | Eyes/ |
| head | Head/ |
| body | Body/ |
| landmark | Landmarks/ |
| read me, readme, instructions, notecard | Docs/ |
| poster, ad | Extras/ |
| dress, top, pants, skirt, shirt, jacket, coat | Clothing/ |
| shoe, boot, heel, sandal, sneaker | Shoes/ |
| ring, necklace, earring, bracelet, collar | Accessories/ |
| animation, ao | Animations/ |
| tattoo, applier | Appliers/ |
| makeup, lipstick, eyeshadow, blush | Makeup/ |

## Brand Extraction Patterns

1. `[Brand] Item Name` - bracket prefix
2. `Brand - Item Name` - dash separator
3. `Brand :: Item Name` - double colon
4. `Brand: Item Name` - colon (less reliable)

## System Folders to Ignore

- Animation Overrides
- Calling Cards
- Current Outfit
- Favorites / My Favorites
- Landmarks
- Lost And Found
- My Outfits
- Photo Album
- Trash
- #RLV (special handling later)
- Received Items (special handling later)

