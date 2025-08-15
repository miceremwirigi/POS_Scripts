import os
import json
import re

# Define the expected values for KENYATEST1
KENYATEST1_CORRECTION = {
    "itemCd": "KENYATEST1",
    "itemClsCd": "99010000",
    "itemNm": "HARDWARE ITEMS",
    "bcd": ""
}

def is_printable_ascii(s):
    """Checks if a string contains only printable ASCII characters."""
    return all(32 <= ord(char) <= 126 for char in s)

def fix_json_file(file_path):
    """
    Attempts to fix common JSON errors in a single file:
    1. Encoding issues by re-reading with cp1252 and replacing errors.
    2. Aggressive cleanup of invalid control characters, non-ASCII characters, and invalid escape sequences.
    3. Robust fix for JSON truncation (missing closing brackets/braces/string quotes) and other syntax errors,
       attempting to preserve partial numeric values.
    4. Logical data inconsistencies in itemCd/bcd fields, ONLY if a character/encoding issue was found.
    5. Reconstructs missing totAmt, taxblAmt, taxAmt based on prc and taxTyCd 'B'.
    """
    original_content = None
    file_modified = False
    had_char_corruption_issue = False 
    
    # --- Step 1: Robustly read file content and perform initial character cleanup ---
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except UnicodeDecodeError:
        print(f"  Encoding issue detected in {file_path}. Attempting to re-read with cp1252...")
        had_char_corruption_issue = True # Mark that an encoding issue was detected
        try:
            with open(file_path, 'r', encoding='cp1252', errors='replace') as f_cp1252:
                original_content = f_cp1252.read()
        except Exception as e:
            print(f"  ERROR: Could not read {file_path} even with cp1252: {e}")
            return False # Cannot proceed if file can't be read

    if original_content is None:
        return False # Should not happen if read attempts are successful

    # Aggressive cleanup:
    # 1. Remove all characters that are NOT printable ASCII (x20-x7E). This gets rid of control characters and non-ASCII.
    # 2. Replace backslashes that are NOT followed by a valid JSON escape character.
    cleaned_content_stage1 = re.sub(r'[^\x20-\x7E]', '', original_content)
    cleaned_content_stage2 = re.sub(r'\\(?!["\\/bfnrtu])', '', cleaned_content_stage1)

    if cleaned_content_stage2 != original_content:
        print(f"  Removed problematic non-ASCII/control characters or invalid escapes from {file_path}.")
        original_content = cleaned_content_stage2
        file_modified = True
        had_char_corruption_issue = True # Mark that character corruption was handled


    # --- Step 2: Attempt to parse and fix JSON syntax/truncation ---
    data = None
    try:
        data = json.loads(original_content)
    except json.JSONDecodeError as e:
        error_message = str(e)
        print(f"  JSONDecodeError in {file_path}: {error_message}")

        if "Invalid control character" in error_message or "Invalid \\escape" in error_message:
            had_char_corruption_issue = True # Mark that JSON itself had character-related syntax issues
        
        print("  Attempting robust iterative fix for JSON structural/syntax error (including partial values)...")
        
        temp_content = original_content.rstrip()
        fixed_parsing_succeeded = False

        # Attempt to complete a partial numeric value at the very end, like "totAm" -> "totAmt":100.00
        # This is a very specific heuristic for your 11046.txt issue.
        match_partial_field = re.search(r'("[a-zA-Z]+"\s*:\s*\d+\.\d{1,2}(?=[^,}]))$', temp_content)
        if match_partial_field:
            print(f"  Detected partial numeric field: {match_partial_field.group(1)}")
            # Try to complete it to a valid number with 2 decimal places if it's truncated
            value_part = re.search(r'\d+\.\d{1,2}', match_partial_field.group(0))
            if value_part and len(value_part.group(0).split('.')[1]) < 2:
                # Add trailing zeros to ensure 2 decimal places if truncated there
                temp_content = re.sub(r'(\d+\.\d{1})$', r'\10', temp_content)
                temp_content = re.sub(r'(\d+)$', r'\1.00', temp_content) # if no decimal at all
            
            # Now, attempt to add the closing structures
            temp_content += '}]}'
            try:
                data = json.loads(temp_content)
                print(f"  Successfully fixed JSON structure with partial numeric field for {file_path}.")
                file_modified = True
                fixed_parsing_succeeded = True
            except json.JSONDecodeError as inner_e:
                print(f"  Partial numeric field fix failed: {inner_e}. Falling back to general truncation.")
                # Reset temp_content to original for general truncation attempt
                temp_content = original_content.rstrip()


        if not fixed_parsing_succeeded:
            # Fallback to aggressive trimming if specific numeric fix failed or wasn't applicable
            initial_length = len(temp_content)
            common_closings = ['}', ']}', '"]}', '}]}'] 

            # Loop to try parsing increasingly shorter strings
            for i in range(initial_length, -1, -5): # Trim by 5 characters at a time for fine-grained attempts
                chunk = temp_content[:i]
                
                # Try appending various common closing structures
                for closing_suffix in common_closings:
                    test_content = chunk + closing_suffix
                    try:
                        data = json.loads(test_content)
                        print(f"  Successfully fixed JSON structure for {file_path} by general iterative truncation.")
                        file_modified = True
                        fixed_parsing_succeeded = True
                        break # Break inner loop
                    except json.JSONDecodeError:
                        continue # Try next closing suffix
                if fixed_parsing_succeeded:
                    break # Break outer loop
            
        if not fixed_parsing_succeeded:
            print(f"  Failed to fix structural JSON for {file_path} after all iterative attempts. Skipping.")
            return False # Could not fix structural error

    if data is None: # Should not happen if fixed_parsing_succeeded is True
        return False # If JSON parsing failed and no fix could be applied

    # --- Step 3: Apply logical data corrections - ONLY if character corruption was detected OR a structural fix occurred ---
    # The `had_char_corruption_issue` flag is now broadened to include structural fixes that might truncate data.
    if had_char_corruption_issue or file_modified:
        if "itemList" in data and isinstance(data["itemList"], list) and len(data["itemList"]) > 0:
            last_item = data["itemList"][-1]
            
            # Recalculate and fill in missing totAmt, taxblAmt, taxAmt if prc and taxTyCd 'B' are present
            prc = last_item.get("prc")
            tax_ty_cd = last_item.get("taxTyCd")

            if isinstance(prc, (int, float)) and tax_ty_cd == "B":
                tax_rate = 0.16
                
                # Ensure existing values are numeric before comparison
                current_taxblAmt = last_item.get("taxblAmt")
                current_taxAmt = last_item.get("taxAmt")
                current_totAmt = last_item.get("totAmt")

                calculated_taxblAmt = round(prc / (1 + tax_rate), 2)
                calculated_taxAmt = round(prc - calculated_taxblAmt, 2)
                calculated_totAmt = round(prc, 2) # totAmt = prc for tax inclusive price

                if not isinstance(current_taxblAmt, (int, float)) or abs(current_taxblAmt - calculated_taxblAmt) > 0.01:
                    last_item["taxblAmt"] = calculated_taxblAmt
                    file_modified = True
                    print(f"  Corrected taxblAmt for last item in {file_path} to {calculated_taxblAmt}.")
                
                if not isinstance(current_taxAmt, (int, float)) or abs(current_taxAmt - calculated_taxAmt) > 0.01:
                    last_item["taxAmt"] = calculated_taxAmt
                    file_modified = True
                    print(f"  Corrected taxAmt for last item in {file_path} to {calculated_taxAmt}.")

                if not isinstance(current_totAmt, (int, float)) or abs(current_totAmt - calculated_totAmt) > 0.01:
                    last_item["totAmt"] = calculated_totAmt
                    file_modified = True
                    print(f"  Corrected totAmt for last item in {file_path} to {calculated_totAmt}.")

            # Original logical correction for KENYATEST1
            current_item_cd = last_item.get("itemCd", "")
            current_item_cls_cd = last_item.get("itemClsCd", "")
            
            should_correct_logical_fields = False
            if current_item_cd == KENYATEST1_CORRECTION["itemCd"] or \
               current_item_cls_cd == KENYATEST1_CORRECTION["itemClsCd"]:
               should_correct_logical_fields = True
            elif not is_printable_ascii(current_item_cd):
               should_correct_logical_fields = True

            if should_correct_logical_fields:
                for key, expected_value in KENYATEST1_CORRECTION.items():
                    current_value = last_item.get(key)
                    if current_value != expected_value:
                        last_item[key] = expected_value
                        file_modified = True
                        print(f"  Correcting field '{key}' in {file_path}: changed to '{expected_value}' (KENYATEST1 related).")

    # --- Step 4: Write fixed data back to file if modified ---
    if file_modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, separators=(',', ':')) # No indentation, compact format
            print(f"  SUCCESS: {file_path} has been fixed and saved.")
            return True
        except Exception as e:
            print(f"  ERROR: Could not write fixed data to {file_path}: {e}")
            return False
    else:
        return False # File did not require any fixes
        

if __name__ == "__main__":
    while True:
        parent_directory = input("Please enter the parent path to fix JSON files (e.g., C:\\Users\\HP\\Desktop\\Temp\\DEJA012202500292\\JSON): ")
        if os.path.isdir(parent_directory):
            break
        else:
            print("Invalid path. Please enter a valid directory.")

    fixed_count = 0
    skipped_count = 0
    
    print(f"\nStarting automated fixes in: {parent_directory}\n")

    for root, _, files in os.walk(parent_directory):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                print(f"Processing: {file_path}")
                if fix_json_file(file_path):
                    fixed_count += 1
                else:
                    skipped_count += 1
                print("-" * 50) # Separator for readability

    print("\n--- Fixing Complete ---")
    print(f"Files Fixed: {fixed_count}")
    print(f"Files Skipped/Unable to Fix: {skipped_count}")

