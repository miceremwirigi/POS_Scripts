import os
import json
import re

# Define the expected values for KENYATEST1
KENYATEST1_EXPECTED = {
    "itemCd": "KENYATEST1",
    "itemClsCd": "99010000",
    "itemNm": "HARDWARE ITEMS",
    "bcd": ""
}

def is_printable_ascii(s):
    """Checks if a string contains only printable ASCII characters."""
    return all(32 <= ord(char) <= 126 for char in s)

def detect_json_errors(parent_path):
    """
    Walks through the specified parent path, identifies .txt files,
    and categorizes any errors found (encoding, syntax, logical).

    Args:
        parent_path (str): The starting directory to search.

    Returns:
        dict: A dictionary of lists, categorizing problematic files.
    """
    error_summary = {
        "encoding_errors": [],
        "json_syntax_errors": [],
        "truncation_errors": [], # Specifically for unterminated strings at the end
        "logical_data_errors": [], # itemCd='KENYATEST1' but associated fields are wrong
        "garbage_item_code_errors": [], # itemCd contains non-standard chars or looks like garbage
        "other_errors": []
    }
    print(f"Scanning for various JSON errors in: {parent_path}\n")

    for root, _, files in os.walk(parent_path):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                file_content = None
                try:
                    # Attempt to read as UTF-8 first
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                except UnicodeDecodeError as e:
                    error_summary["encoding_errors"].append(f"{file_path} (Error: {e})")
                    # Try reading with a more permissive encoding for further checks, replacing errors
                    try:
                        with open(file_path, 'r', encoding='cp1252', errors='replace') as f_cp1252:
                            file_content = f_cp1252.read()
                            print(f"  Attempted re-read of {file_path} with cp1252 (errors replaced).")
                    except Exception as re_e:
                        error_summary["other_errors"].append(f"{file_path} (Re-read failed after encoding error: {re_e})")
                        continue # Can't read, skip to next file

                if file_content is None:
                    continue # Skip if content couldn't be loaded at all

                try:
                    data = json.loads(file_content)

                    # --- Logical Data Validation ---
                    if "itemList" in data and isinstance(data["itemList"], list):
                        for item in data["itemList"]:
                            item_cd = item.get("itemCd", "")
                            item_cls_cd = item.get("itemClsCd", "")
                            item_nm = item.get("itemNm", "")
                            bcd = item.get("bcd", "")

                            # Check for garbage characters in itemCd (if not KENYATEST1 already)
                            if not is_printable_ascii(item_cd) and item_cd != KENYATEST1_EXPECTED["itemCd"]:
                                error_summary["garbage_item_code_errors"].append(f"{file_path} (Garbage itemCd: '{item_cd}')")
                            # If it's KENYATEST1, check if other fields match
                            elif item_cd == KENYATEST1_EXPECTED["itemCd"]:
                                if not (item_cls_cd == KENYATEST1_EXPECTED["itemClsCd"] and \
                                        # item_nm == KENYATEST1_EXPECTED["itemNm"] and \
                                        bcd == KENYATEST1_EXPECTED["bcd"] or KENYATEST1_EXPECTED["itemCd"]):
                                    error_summary["logical_data_errors"].append(f"{file_path} (KENYATEST1 inconsistency: itemClsCd='{item_cls_cd}', itemNm='{item_nm}', bcd='{bcd}')")

                except json.JSONDecodeError as e:
                    if "Unterminated string" in str(e) and file_content.endswith(('"', "'", ':', ',', '[', '{')):
                        error_summary["truncation_errors"].append(f"{file_path} (Error: {e})")
                    else:
                        error_summary["json_syntax_errors"].append(f"{file_path} (Error: {e})")
                except Exception as e:
                    error_summary["other_errors"].append(f"{file_path} (Unexpected error during processing: {e})")

    return error_summary

if __name__ == "__main__":
    while True:
        parent_directory = input("Please enter the parent path to scan (e.g., C:\\Users\\HP\\Desktop\\Temp\\DEJA012202500292\\JSON): ")
        if os.path.isdir(parent_directory):
            break
        else:
            print("Invalid path. Please enter a valid directory.")

    errors = detect_json_errors(parent_directory)

    print("\n--- Scan Complete ---")
    print("\n--- Error Summary ---")

    if any(errors.values()):
        for error_type, file_list in errors.items():
            if file_list:
                print(f"\n{error_type.replace('_', ' ').title()}:")
                for fpath in file_list:
                    print(f"- {fpath}")
    else:
        print("No errors found in any of the .txt files.")
