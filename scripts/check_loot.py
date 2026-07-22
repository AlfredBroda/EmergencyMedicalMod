import json
import re
import glob

from typing import List, Union
from utilities import reporting_summary, load_json_files, load_json_with_comments

def _load_patterns_to_set(patterns: Union[str, List[str]], key_field: str) -> set[str]:
    """Helper to load one or multiple file patterns into a single combined set."""
    if isinstance(patterns, str):
        patterns = [patterns]
        
    combined_set = set()
    for pattern in patterns:
        combined_set |= load_json_files(pattern, key_field)
    return combined_set


def validate_loot(
    co_patterns: Union[str, List[str]], 
    loot_patterns: Union[str, List[str]]
) -> int:
    
    # 1. Load reference sets from all provided patterns
    existing_names: set[str] = _load_patterns_to_set(co_patterns, "strName")

    # 2. Expand loot patterns into a list of file paths
    if isinstance(loot_patterns, str):
        loot_patterns = [loot_patterns]

    loot_file_paths = []
    for pattern in loot_patterns:
        loot_file_paths.extend(glob.glob(pattern))

    if not loot_file_paths:
        print(f"⚠️ Warning: No files matched loot patterns: {loot_patterns}")
        return False

    loot_names: set[str] = _load_patterns_to_set(loot_patterns, "strName")

    got_errors = 0

    # 2. Loop through every matching loot file
    for filepath in loot_file_paths:
        print(f"\n--- Processing file: {filepath} ---")
        local_errors = 0
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                item_structures = load_json_with_comments(f)
        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
            got_errors += 1
            continue

        num_loots = 0
        # 3. Iterate through structures and check for existence
        for item in item_structures:
            type = item.get("strType", "Unknown")
            if type == "item":
                num_loots += 1
                cos_list = item.get("aCOs", [])
                loots_list = item.get("aLoots", [])
                
                for co_entry in cos_list:
                    for clean_co_name in parse_co_entry(co_entry):
                        # O(1) set lookup
                        if clean_co_name not in existing_names:
                            local_errors += 1
                            print(f"  ✗ Missing CO: '{clean_co_name}' was NOT found.")

                for loot in loots_list:
                    if "--" in loot:
                        continue
                    for clean_loot_name in parse_co_entry(loot):
                        # O(1) set lookup
                        if clean_loot_name not in loot_names:
                            local_errors += 1
                            print(f"  ✗ Missing Loot: '{clean_loot_name}' was NOT found.")

        print (f"Checked {num_loots} loot items with {local_errors} errors.")
        got_errors += local_errors

    return got_errors

def parse_co_entry(co_entry: str) -> list[str]:
    """
    Splits a pipe-delimited co_entry and strips quantity modifiers (e.g., '=1.0x1').
    
    Example:
        "ItemA=0.03x1|ItemB=0.03x1" -> ["ItemA", "ItemB"]
    """
    modifier_pattern = re.compile(r"=.*$")
    cleaned_items = []
    
    for sub_entry in co_entry.split("|"):
        clean_name = modifier_pattern.sub("", sub_entry.strip())
        if clean_name:
            cleaned_items.append(clean_name)
            
    return cleaned_items

if __name__ == "__main__":
    got_errors = 0

    got_errors += validate_loot([
        "data/condowners/*.json",
        "data/cooverlays/*.json"
    ], [
        "data/loot/*.json"
    ])

    if got_errors > 0:
        print(f"❌ {got_errors} validation checks failed. Please review the errors above.")

    reporting_summary(got_errors > 0)