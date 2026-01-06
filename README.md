# EVE Online SDE to CSV Converter

Converts EVE Online's new JSON Lines Static Data Export (SDE) to CSV files compatible with the legacy Fuzzwork dump format.

## CLI Usage

```bash
# Download and extract the latest SDE
curl -LO "https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip"
unzip eve-online-static-data-latest-jsonl.zip -d sde

# Convert to CSV
python3 convert.py sde/ csv/

# Convert specific files only
python3 convert.py sde/ csv/ --only invTypes invGroups

# Quiet mode
python3 convert.py sde/ csv/ -q
```

## Library Usage

```python
from convert import convert, convert_all, CONVERTERS

# Convert all files
convert_all("sde/", "csv/")

# Convert specific files
convert("sde/", "csv/", only=["invTypes", "invGroups"])

# Quiet mode (no output)
convert_all("sde/", "csv/", quiet=True)

# List available converters
print(list(CONVERTERS.keys()))
```

## Generated Files

| CSV File | Source | Description |
|----------|--------|-------------|
| invTypes.csv | types.jsonl | Item types |
| invGroups.csv | groups.jsonl | Item groups |
| invMetaGroups.csv | metaGroups.jsonl | Meta groups (Tech I/II/etc) |
| invMetaTypes.csv | types.jsonl | Type to meta group mappings |
| industryActivity.csv | blueprints.jsonl | Blueprint activity times |
| industryActivityMaterials.csv | blueprints.jsonl | Blueprint input materials |
| industryActivityProducts.csv | blueprints.jsonl | Blueprint outputs |
| ramActivities.csv | static | Activity type definitions |
| invFlags.csv | static | Inventory location flags |
| invUniqueNames.csv | npcCharacters.jsonl | NPC character names |
| invNames.csv | multiple | Entity names (systems, planets, moons, etc) |
| invItems.csv | multiple | Entity locations and types |

## Not Available

- `aggregatecsv.csv` - market data (use [Fuzzwork Market API](https://market.fuzzwork.co.uk/))

## Requirements

Python 3.10+
