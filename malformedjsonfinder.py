import os
import json
import re

# This dictionary will now be dynamically populated
KNOWN_ITEM_DATA = {} 

def is_printable_ascii(s):
    """Checks if a string contains only printable ASCII characters."""
    # Also allows for simple Unicode characters that are common in data, but
    # avoids the non-printable garbage. A more permissive approach is
    # needed for some valid data.
    if isinstance(s, (str, bytes)):
        return all(char.isprintable() or char.isspace() for char in s)
    return False

def _learn_item_data(file_path):
    """
    Reads a JSON file, and if it's clean and valid, extracts and stores the
    item metadata (itemCd, itemClsCd, itemNm, bcd) for future correction.
    """
    global KNOWN_ITEM_DATA
    try:
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()
            content = raw_bytes.decode('utf-8', errors='ignore')

        data = json.loads(content)
        
        if "itemList" not in data:
            return False

        for item in data["itemList"]:
            item_cd = item.get("itemCd")
            item_cls_cd = item.get("itemClsCd")
            item_nm = item.get("itemNm")
            bcd = item.get("bcd")
            
            # Simple validation for a valid item
            if isinstance(item_cd, str) and item_cd and \
               isinstance(item_cls_cd, str) and item_cls_cd and \
               isinstance(item_nm, str) and item_nm:
                
                # Exclude items with obviously corrupted characters
                if not is_printable_ascii(item_cd) or not is_printable_ascii(item_cls_cd):
                    continue

                if item_cd not in KNOWN_ITEM_DATA or KNOWN_ITEM_DATA[item_cd]["itemClsCd"] != item_cls_cd:
                    KNOWN_ITEM_DATA[item_cd] = {
                        "itemCd": item_cd,
                        "itemClsCd": item_cls_cd,
                        "itemNm": item_nm,
                        "bcd": bcd if isinstance(bcd, str) else "" 
                    }
        return True

    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
        return False
    
def detect_json_errors(parent_path):
    """
    Walks through the specified parent path, identifies .txt files,
    and categorizes any errors found (encoding, syntax, logical).
    """
    error_summary = {
        "encoding_errors": [],
        "json_syntax_errors": [],
        "truncation_errors": [],
        "logical_data_errors": [],
        "garbage_item_code_errors": [],
        "other_errors": []
    }
    
    print(f"Scanning for various JSON errors in: {parent_path}\n")

    for root, _, files in os.walk(parent_path):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                file_content = None
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                except UnicodeDecodeError as e:
                    error_summary["encoding_errors"].append(f"{file_path} (Error: {e})")
                    try:
                        with open(file_path, 'r', encoding='cp1252', errors='replace') as f_cp1252:
                            file_content = f_cp1252.read()
                            print(f"  Attempted re-read of {file_path} with cp1252 (errors replaced).")
                    except Exception as re_e:
                        error_summary["other_errors"].append(f"{file_path} (Re-read failed after encoding error: {re_e})")
                        continue

                if file_content is None:
                    continue

                try:
                    data = json.loads(file_content)

                    # Logical Data Validation
                    if "itemList" in data and isinstance(data["itemList"], list):
                        for item in data["itemList"]:
                            item_cd = item.get("itemCd", "")
                            
                            # Check for garbage characters in itemCd
                            if not is_printable_ascii(item_cd) and item_cd not in KNOWN_ITEM_DATA:
                                error_summary["garbage_item_code_errors"].append(f"{file_path} (Garbage itemCd: '{item_cd}')")

                            # If a known item, check for logical inconsistencies
                            elif item_cd in KNOWN_ITEM_DATA:
                                expected_data = KNOWN_ITEM_DATA[item_cd]
                                
                                # Check against the learned values
                                item_cls_cd = item.get("itemClsCd", "")
                                item_nm = item.get("itemNm", "")
                                bcd = item.get("bcd", "")

                                if not (item_cls_cd == expected_data["itemClsCd"] and
                                        item_nm == expected_data["itemNm"] and
                                        # The bcd field can be empty or match the expected
                                        (bcd == expected_data["bcd"] or bcd == "")):
                                    
                                    inconsistency_details = []
                                    if item_cls_cd != expected_data["itemClsCd"]:
                                        inconsistency_details.append(f"itemClsCd='{item_cls_cd}' vs expected '{expected_data['itemClsCd']}'")
                                    if item_nm != expected_data["itemNm"]:
                                        inconsistency_details.append(f"itemNm='{item_nm}' vs expected '{expected_data['itemNm']}'")
                                    if bcd != expected_data["bcd"] and bcd != "":
                                         inconsistency_details.append(f"bcd='{bcd}' vs expected '{expected_data['bcd']}'")

                                    error_summary["logical_data_errors"].append(
                                        f"{file_path} (Data inconsistency for '{item_cd}': {', '.join(inconsistency_details)})"
                                    )

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
            
    # First, run a learning pass on all files
    print("--- Starting Learning Phase (Pass 1) ---")
    learned_from_count = 0
    total_files = 0
    for root, _, files in os.walk(parent_directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                total_files += 1
                if _learn_item_data(file_path):
                    learned_from_count += 1
    
    print(f"\nLearning Phase Complete. Learned from {learned_from_count} of {total_files} files.")
    print("-------------------------------------------\n")

    # Now, run the detection pass using the learned data
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