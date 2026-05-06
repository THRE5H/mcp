import json
from pathlib import Path

kb_path = Path(__file__).parent / "knowledge_base.json"

with open(kb_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Root type: {type(data)}")

if isinstance(data, list):
    print(f"Number of items: {len(data)}")
    for i, item in enumerate(data[:3]):
        print(f"\nItem {i} type: {type(item)}")
        if isinstance(item, dict):
            print(f"  Keys: {list(item.keys())}")
            print(f"  id value: {repr(item.get('id'))}")
        else:
            print(f"  Value preview: {repr(str(item)[:100])}")
elif isinstance(data, dict):
    print(f"Root keys: {list(data.keys())}")
    # Maybe the list is nested under a key
    for k, v in data.items():
        print(f"  '{k}': {type(v)} — length {len(v) if hasattr(v, '__len__') else 'N/A'}")