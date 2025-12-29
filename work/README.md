# Inventory Sorter - Work Directory

This directory contains tools for analyzing inventory and generating/executing move plans.

## Structure

```
work/
├── analysis/           # Generated analysis reports
│   ├── structure.md    # Full inventory tree
│   └── root_items.md   # Items at root needing sorting
├── plans/              # Pending move plans (JSON)
├── executed/           # Completed move plans
├── analyze_inventory.py    # Parses cache and generates plans
└── execute_plan.py         # Executes a plan via Corrade API
```

## Workflow

### 1. Analyze Inventory
```bash
python analyze_inventory.py
```
This parses the inventory cache from `dump/` and generates:
- Analysis reports in `analysis/`
- Move plans in `plans/`

### 2. Review Plans
Check each plan file in `plans/`. Plans have a status:
- `pending` - Ready to execute
- `needs_review` - Needs manual categorization
- `needs_special_handling` - Requires merge operations (not simple moves)
- `executed` - Already completed

### 3. Execute a Plan
```bash
# Dry run first (shows what would happen)
python execute_plan.py plan_Body_Parts_Heads.json --dry-run

# Execute for real
python execute_plan.py plan_Body_Parts_Heads.json
```

**Important:** Corrade must be running and logged in before executing plans.

## Safety Features

- **No deletions** - The executor only moves items, never deletes
- **Dry run mode** - Test before executing
- **Plan tracking** - Executed plans are moved to `executed/`
- **Rate limiting** - Delays between API calls to avoid issues
- **Source folders preserved** - Empty folders left for manual cleanup in-viewer

## Special Cases

### Merge Operations
Some folders need their *contents* merged into existing folders rather than moved as-is.
These are marked with `needs_special_handling` status and require manual intervention
or a dedicated merge script.

Example: `Apparel/Hair/*` should merge into `Body Parts/Hair/*`

### Pending Deletion
Instead of deleting anything, items that should be removed go to:
`Objects/Pending Deletion`

You can review and delete manually in-viewer.

