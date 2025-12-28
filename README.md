# Corrade Inventory Sorter

A Python tool for automatically sorting Second Life inventory using [Corrade's](https://grimore.org/secondlife/scripted_agents/corrade) HTTP API.

## Features

- **UUID-based operations** for faster performance (name lookups are slow)
- **Folder name normalization** handles Unicode spaces, special characters, and SL naming quirks
- **Dry-run mode** to preview changes before actually moving anything
- **Configurable delays** to avoid overwhelming SL's inventory system
- **Batch processing** with automatic pauses to prevent timeouts
- **Custom rules** via JSON configuration files
- **Brand extraction** from common naming patterns (`[Brand] Item`, `Brand - Item`, etc.)

## Requirements

- Python 3.8+
- [Corrade](https://grimore.org/secondlife/scripted_agents/corrade) bot configured with HTTP API enabled
- The bot must have inventory permissions in the configured group

## Installation

```bash
git clone https://github.com/yourusername/corrade-inventory-sorter.git
cd corrade-inventory-sorter
pip install -r requirements.txt
cp config.example.json config.json
# Edit config.json with your Corrade credentials
```

## Usage

### Preview changes (dry run)

```bash
python inventory_sorter.py --config config.json --dry-run
```

### Sort specific folders

```bash
python inventory_sorter.py --config config.json --dry-run --folders Gestures
```

### Actually perform the sort

```bash
python inventory_sorter.py --config config.json
```

### With verbose logging

```bash
python inventory_sorter.py --config config.json --dry-run -v
```

## Configuration

### config.json

```json
{
    "corrade_url": "http://localhost:8080",
    "group": "Your Group Name",
    "password": "your-group-password",
    "delay_between_moves": 1.0,
    "batch_size": 10,
    "batch_delay": 5.0,
    "force_cache_refresh": false,
    "folders_to_sort": [
        "Gestures",
        "Clothing",
        "Objects"
    ]
}
```

### Custom Rules (rules.json)

You can define custom sorting rules:

```json
{
    "rules": [
        {
            "name": "My Custom Rule",
            "target_path": "Sorted/Custom",
            "keywords": ["keyword1", "keyword2"],
            "priority": 50
        },
        {
            "name": "Regex Rule",
            "target_path": "Sorted/Regex",
            "regex": "\\bpattern\\b",
            "priority": 40
        }
    ]
}
```

Use with:
```bash
python inventory_sorter.py --config config.json --rules rules.json --dry-run
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--config FILE` | Path to JSON config file |
| `--rules FILE` | Path to custom rules JSON file |
| `--url URL` | Corrade HTTP server URL |
| `--group NAME` | Corrade group name |
| `--password PASS` | Corrade group password |
| `--dry-run` | Preview changes without moving anything |
| `--folders FOLDER [...]` | Specific folders to sort |
| `--delay SECONDS` | Delay between moves (default: 1.0) |
| `--batch-size N` | Moves before batch pause (default: 10) |
| `--batch-delay SECONDS` | Pause between batches (default: 5.0) |
| `--force-refresh` | Force refresh inventory cache |
| `-v, --verbose` | Enable debug logging |

## Default Sorting Rules

The tool includes sensible defaults:

| Priority | Rule | Target Path |
|----------|------|-------------|
| 100 | Boxed Items | `Boxed Items/` |
| 90 | Demos | `_Demos/` |
| 85 | Dance Gestures | `Gestures/Dances/` |
| 84 | Expression Gestures | `Gestures/Expressions/` |
| 80 | Hair | `Apparel/Hair/` |
| 75 | Shoes | `Apparel/Shoes/` |
| 70 | Clothing | `Apparel/Clothing/` |
| 60 | Body Parts | `Avatar/Body Parts/` |
| 50 | Furniture & Decor | `Home & Decor/` |

Rules are evaluated in priority order (highest first). The first matching rule wins.

## Performance Tips

- **Start with dry-run** to verify the rules work as expected
- **Use UUIDs** - the tool does this automatically, but avoid unnecessary path lookups
- **Adjust delays** based on your connection and inventory size
- **Process one folder at a time** for large inventories
- **Use `--force-refresh`** if inventory seems stale after recent changes in-world

## Troubleshooting

### "Request timed out"
- Corrade may be busy or inventory is very large
- Try increasing the delay between operations
- Process smaller folders

### Items not moving
- Check that Corrade has proper permissions
- Use `--force-refresh` to clear stale cache
- Verify the target folder path is correct

### Folder name issues
- The tool normalizes Unicode spaces and special characters
- Check logs for the normalized name being matched

## License

MIT License - see LICENSE file for details.

## Related Projects

- [Corrade](https://grimore.org/secondlife/scripted_agents/corrade) - The scripted agent this tool interfaces with
- [Alchemy Viewer](https://alchemyviewer.org/) - A viewer with planned native inventory sorting

