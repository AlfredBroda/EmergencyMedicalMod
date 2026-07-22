
import json
import glob
import sys

from utilities import reporting_summary, load_json_files, list_broad_matches

def validate_interactions(interactions_pattern: str = "data/interactions/interactions*.json",
                          condtrigs_pattern: str = "data/condtrigs/condtrigs*.json",
                          loot_pattern: str = "data/loot/loot*.json") -> bool:
    """
    Walks all interaction files and validates that:
    - values in `CTTestUs` and `CTTestThem` exist as `strName` in condtrigs files
    - values in `LootCTsThem` exist as `strName` in loot files
    Returns True if any errors were found.
    """
    print("Loading reference data for interactions...")
    condtrigs = load_json_files(condtrigs_pattern, "strName")
    loots = load_json_files(loot_pattern, "strName")

    errors_found = False

    interaction_files = glob.glob(interactions_pattern)
    if not interaction_files:
        print(f"Warning: No interaction files found matching '{interactions_pattern}'")
        return False

    print(f"Starting validation of interaction files matching '{interactions_pattern}'...")
    for file_path in interaction_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                interactions = data if isinstance(data, list) else [data]

            for index, interaction in enumerate(interactions):
                if not isinstance(interaction, dict):
                    continue

                name = interaction.get("strName", f"Index {index} in {file_path}")

                # Check CTTestUs and CTTestThem
                for ct_field in ("CTTestUs", "CTTestThem"):
                    ct_val = interaction.get(ct_field)
                    if ct_val:
                        if ct_val in ["TIsHumanAwake", "TIsDead", "TIsValidSocialTarget"]:
                            # Known globals
                            continue
                        if ct_val not in condtrigs:
                            print(f"[{name}]: '{ct_field}' value '{ct_val}' not found in condtrigs files.")
                            alt = list_broad_matches(ct_val, condtrigs)
                            if alt:
                                print(f"  Possible alternatives in condtrigs: {', '.join(alt)}")
                            else:
                                print("  No close matches found in condtrigs.")
                            errors_found = True

                # Check LootCTsThem
                loot_field = "LootCTsThem"
                loot_val = interaction.get(loot_field)
                if loot_val:
                    if loot_val not in loots:
                        print(f"[{name}]: '{loot_field}' value '{loot_val}' not found in loot files.")
                        alt = list_broad_matches(loot_val, loots)
                        if alt:
                            print(f"  Possible alternatives in loot files: {', '.join(alt)}")
                        else:
                            print("  No close matches found in loot files.")
                        errors_found = True

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error parsing interaction file {file_path}: {e}")
            errors_found = True

    reporting_summary(errors_found)
    return errors_found


if __name__ == "__main__":
    got_errors = False


    got_errors |= validate_interactions()

    if got_errors:
        print("❌ One or more validation checks failed. Please review the errors above.")
        sys.exit(1)
