import json
import glob
import re
import subprocess
import sys
from typing import Dict, Set
from pathlib import Path

def git_version():
    """Fetches git tag or falls back to short commit SHA."""
    try:
        tag = run_command(
            "git describe --tags 2>/dev/null", "Git check failed"
        )
        if tag:
            return tag
    except SystemExit:
        pass

    sha = run_command("git rev-parse --short HEAD", "Could not get git commit SHA")
    return f"dev-{sha}"

def run_command(command, error_msg):
    """Helper to safely run shell commands."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {error_msg}")
        print(result.stderr)
        sys.exit(1)
    result.stdout.strip()

def read_version(file_path, field) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        # Ensure the root is a list of items
        if not isinstance(data, list):
            print("Error: Expected a JSON array/list at the root.")
            return "dev"
        
        if len(data) == 1 and field in data[0]:
            return data[0][field]
        else:
            print(F"Error: Expected {field} not found.")

    return "dev"


def safely_write_json(output, entries, preserve_old):
    # Handle reading and appending to the existing overlays JSON file safely
    existing_data = []
    output_path = Path(output)

    if preserve_old:
        if output_path.exists() and output_path.stat().st_size > 0:
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    # Ensure the existing data is a list
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except json.JSONDecodeError:
                print(
                    f"Warning: {output} was corrupted or not valid JSON. Starting fresh."
                )
                existing_data = []

    # Combine old and new data
    existing_data.extend(entries)

    # Write back to the file with clean formatting
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)

    print(
        f"Successfully added {len(entries)} items to '{output_path.resolve()}'"
    )

def load_json_files(file_pattern: str, key_field: str) -> Set[str]:
    """
    Loads all JSON files matching the pattern and extracts the unique values
    of the specified key_field to act as a validation lookup.
    """
    valid_keys = set()
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"Warning: No files found matching pattern: {file_pattern}")
        return valid_keys

    for file_path in files:
        # print(f"Loading: {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = load_json_with_comments(f)
                
                # Handle both a single JSON object or a list of objects per file
                if isinstance(data, dict):
                    items = [data]
                elif isinstance(data, list):
                    items = data
                else:
                    continue
                
                for item in items:
                    if isinstance(item, dict) and key_field in item:
                        valid_keys.add(item[key_field])
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading file {file_path}: {e}")
            return set()
            
    return valid_keys

def filter_list_formatted(names_list, pattern) -> list[str]:
    return [("{"+name).replace(",","},") for name in names_list.splitlines() if pattern in name]

def get_base_pattern(text: str) -> str:
    """
    Strips a suffix like 'SmallA', 'LargeB', etc., from the end of a string.
    Returns the base string.
    """
    # Pattern: Capitalized word + single Capital letter at the end
    pattern = r'[A-Z][a-z]+[A-Z]$'
    
    # re.sub replaces the matched suffix with an empty string
    base = re.sub(pattern, '', text)
    return base

def list_broad_matches(target_value: str, pool_of_options: set) -> list:
    """
    Takes a specific string, finds its base, and returns all 
    items in the option pool that start with that same base.
    """
    base = get_base_pattern(target_value)
    # print(f"Original: {target_value} -> Isolated Base: {base}")
    
    # Find everything in your JSON pools that starts with the same prefix
    matches = [item for item in pool_of_options if item.startswith(base)]
    return matches

def reporting_summary(errors_found: bool):
    # Final reporting
    print("--- Validation Summary ---")
    if errors_found:
        print("❌ Validation failed with errors.\n")
    else:
        print("✅ All integrity checks passed successfully!\n")


def filter_list(names_list, pattern):
    return [name for name in names_list if pattern in name]

def strip_comments(match):
    item = match.group(1)
    if item.startswith("/") or item.startswith("#"):
        return ""  # It's a comment, delete it
    return item  # It's a string literal, keep it

def load_json_with_comments(file):
    content = file.read()

    # Regex to match syntax like /* comments */ and // comments
    pattern = r"((?:\"(?:\\.|[^\"])*\"|' (?:\\.|[^'])*')|(?:\/\*(?:[^*]|\*(?!\/))*\*\/|\/\/.*))"


    clean_content = re.sub(pattern, strip_comments, content)
    return json.loads(clean_content)
