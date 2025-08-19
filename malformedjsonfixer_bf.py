import os
import json
import re

# Define the expected values for KENYATEST1
KENYATEST1_CORRECTION = {
    "itemCd": "DEP 1", # Assuming 'DEP 1' is a specific item code that needs consistent values
    "itemClsCd": "99000000",
    "itemNm": "CLEANING&FUMUGAT",
    "bcd": ""
}

# Define all expected top-level fields and their default empty values/types
DEFAULT_TOP_LEVEL_FIELDS = {
    "invcNo": 0,
    "orgInvcNo": 0,
    "custNo": "",
    "custTin": "",
    "custBhfId": "",
    "custNm": "",
    "salesTyCd": "N",
    "rcptTyCd": "S",
    "pmtTyCd": "01",
    "salesSttsCd": "02",
    "cfmDt": "",
    "salesDt": "",
    "stockRlsDt": "",
    "cnclReqDt": "",
    "cnclDt": "",
    "rfdDt": "",
    "rfdRsnCd": "",
    "totItemCnt": 0,
    "taxblAmtA": 0.0,
    "taxblAmtB": 0.0,
    "taxblAmtC": 0.0,
    "taxblAmtD": 0.0,
    "taxblAmtE": 0.0,
    "taxRtA": 0.0,
    "taxRtB": 0.0,
    "taxRtC": 0.0,
    "taxRtD": 0.0,
    "taxRtE": 0.0,
    "taxAmtA": 0.0,
    "taxAmtB": 0.0,
    "taxAmtC": 0.0,
    "taxAmtD": 0.0,
    "taxAmtE": 0.0,
    "totTaxblAmt": 0.0,
    "totTaxAmt": 0.0,
    "totAmt": 0.0,
    "prchrAcptcYn": "Y", 
    "remark": "",
    "regrId": "", 
    "regrNm": "", 
    "modrId": "", 
    "modrNm": "", 
    "receipt": {}, 
    "itemList": [] 
}


def is_printable_ascii(s):
    """Checks if a string contains only printable ASCII characters (0x20-0x7E)."""
    return all(32 <= ord(char) <= 126 for char in s)

def _robust_json_clean_string(text_content):
    """
    Performs aggressive, character-by-character cleaning to make a string safely parseable by json.loads().
    It removes illegal control characters and unwanted specific Unicode characters (like ÿ) and ensures quotes/backslashes are escaped correctly.
    """
    cleaned_chars = []
    in_string = False
    escaped = False # Tracks if the previous char was a backslash for escaping purposes

    for char_idx, char in enumerate(text_content):
        ord_char = ord(char)
        # Define characters to be removed (C0, C1 controls, DEL, and ÿ/0xFF)
        is_unwanted_char = (
            (0x00 <= ord_char <= 0x1F) or # C0 control characters
            (0x80 <= ord_char <= 0x9F) or # C1 control characters
            (ord_char == 0x7F) or        # DEL character
            (ord_char == 0xFF)           # Latin Small Letter Y with Diaeresis (ÿ / 0xFF)
        )

        if in_string:
            if escaped:
                cleaned_chars.append(char)
                escaped = False
            elif char == '\\':
                cleaned_chars.append(char)
                escaped = True
            elif char == '"':
                cleaned_chars.append(char)
                in_string = False
            elif is_unwanted_char:
                pass # Remove the unwanted character
            else:
                cleaned_chars.append(char)
        else: # Not in a string
            if char == '"':
                cleaned_chars.append(char)
                in_string = True
            elif char in (' ', '\t', '\n', '\r'):
                cleaned_chars.append(char)
            elif is_unwanted_char:
                pass # Remove the unwanted character
            else:
                cleaned_chars.append(char)
    
    return "".join(cleaned_chars)


def _attempt_structural_fix_and_parse(text_content):
    """
    Attempts to parse text_content. If it fails, tries multi-tiered structural fixes.
    Returns the parsed data and a boolean indicating if structural modification occurred.
    """
    modified_in_this_function = False # Tracks if _this_ function performed a structural fix
    
    # Attempt 1: Direct parse - if already valid after char cleaning
    try:
        data = json.loads(text_content)
        return data, modified_in_this_function
    except json.JSONDecodeError as e:
        print(f"  Structural JSONDecodeError: {str(e)}. Attempting advanced structural repair.")
        modified_in_this_function = True # A fix is needed

        # Strategy A: Aggressive trimming to find *any* parsable JSON prefix
        longest_valid_prefix = "{}" # Default if nothing else works
        
        # Iterate backwards, trimming the content
        current_attempt_text = text_content.strip()
        trim_steps = [500, 200, 100, 50, 20, 10, 5, 1] 

        for step in trim_steps:
            for i in range(len(current_attempt_text), -1, -step):
                chunk = current_attempt_text[:i]
                
                common_closings = ['}', ']}', '"]}', '}]}'] 
                
                for suffix in common_closings:
                    test_string = chunk + suffix
                    try:
                        json.loads(test_string) 
                        if len(test_string) > len(longest_valid_prefix):
                            longest_valid_prefix = test_string
                        # Found a valid one, might still find longer.
                    except json.JSONDecodeError:
                        pass # This combination is not valid
            if len(longest_valid_prefix) > len("{}"): 
                break 

        # Now, try to parse the best prefix found
        try:
            data = json.loads(longest_valid_prefix)
            print("  Successfully parsed via aggressive longest prefix strategy.")
            return data, modified_in_this_function # Success
        except json.JSONDecodeError as e:
            print(f"  Aggressive longest prefix strategy failed: {str(e)}. Falling back to minimal JSON.")
            # If even the most aggressive prefix find fails, return a minimal valid JSON
            return {}, True # Return empty dict, implies heavy modification

    # This part should ideally not be reached if first try-block succeeded
    # or the aggressive prefix find returned valid JSON.
    return {}, True # Fallback if unforeseen path leads here, signifies failure and forced minimal


def _extract_all_item_fields_from_raw(raw_item_string):
    """
    Attempts to extract all known item fields from a raw, potentially corrupted item string
    using regex, as a last resort before defaulting to 0.0 or empty string.
    """
    extracted_data = {}
    
    # Define regex patterns for all fields. Use non-greedy matching and allow various characters.
    patterns = {
        "itemSeq": r'"itemSeq":\s*(\d+)',
        "itemCd": r'"itemCd":"(.*?)(?:"|,|\})', 
        "itemClsCd": r'"itemClsCd":"(.*?)(?:"|,|\})',
        "itemNm": r'"itemNm":"(.*?)(?:"|,|\})',
        "bcd": r'"bcd":"(.*?)(?:"|,|\})',
        "pkgUnitCd": r'"pkgUnitCd":"(.*?)(?:"|,|\})',
        "pkg": r'"pkg":\s*([\d.]+)',
        "qtyUnitCd": r'"qtyUnitCd":"(.*?)(?:"|,|\})',
        "qty": r'"qty":\s*([\d.]+)',
        "prc": r'"prc":\s*([\d.]+)',
        "splyAmt": r'"splyAmt":\s*([\d.]+)',
        "dcRt": r'"dcRt":\s*([\d.]+)',
        "dcAmt": r'"dcAmt":\s*([\d.]+)',
        "isrccCd": r'"isrccCd":"(.*?)(?:"|,|\})',
        "isrccNm": r'"isrccNm":"(.*?)(?:"|,|\})',
        "isrcRt": r'"isrcRt":\s*([\d.]+)',
        "isrcAmt": r'"isrcAmt":\s*([\d.]+)',
        "taxTyCd": r'"taxTyCd":"(.*?)(?:"|,|\})',
        "taxblAmt": r'"taxblAmt":\s*([\d.]+)',
        "taxAmt": r'"taxAmt":\s*([\d.]+)',
        "totAmt": r'"totAmt":\s*([\d.]+)'
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw_item_string)
        if match:
            value = match.group(1)
            if field in ["itemSeq", "pkg", "qty", "prc", "splyAmt", "dcRt", "dcAmt", 
                         "isrcRt", "isrcAmt", "taxblAmt", "taxAmt", "totAmt"]:
                try:
                    extracted_data[field] = float(value) if '.' in value else int(value)
                except ValueError:
                    pass 
            else: # String fields
                try:
                    # Defensive check: ensure _robust_json_clean_string is callable
                    if callable(_robust_json_clean_string):
                        # Wrap value in quotes to ensure it's treated as a JSON string literal for cleaning
                        cleaned_val_with_quotes = _robust_json_clean_string(f'"{value}"')
                        if isinstance(cleaned_val_with_quotes, str): 
                            extracted_data[field] = cleaned_val_with_quotes.strip('"')
                        else:
                            print(f"  Warning: _robust_json_clean_string returned non-string for field {field} (value: '{value}'): {cleaned_val_with_quotes}")
                            extracted_data[field] = "" # Default if cleaning failed to produce string
                    else:
                        print(f"  CRITICAL ERROR: _robust_json_clean_string is not callable (it is type {type(_robust_json_clean_string).__name__}). Defaulting field '{field}'.")
                        extracted_data[field] = "" # Default if function itself is corrupted
                except Exception as e:
                    print(f"  ERROR processing field '{field}' with value '{value}': {type(e).__name__}: {e}")
                    extracted_data[field] = "" # Default on any error
    
    return extracted_data


def fix_json_file(file_path):
    """
    Attempts to fix common JSON errors in a single file:
    1. Robustly reads file content, handling encoding errors.
    2. Aggressively cleans raw content: removes non-printable ASCII, invalid escapes, and control characters (including ÿ).
    3. Guarantees JSON parseability by finding the longest valid prefix and/or reconstructing core structures.
    4. Reconstructs missing data in itemList items with defaults, prioritizing original prc/qty if available.
    5. Applies logical corrections for KENYATEST1 fields if character corruption was involved.
    6. Validates and recalculates all financial totals (item-level and top-level) based on prc/qty/taxTyCd.
    """
    original_content_raw_read = None 
    original_content_cleaned_chars = None 
    file_modified = False
    had_char_corruption_issue = False 
    
    # --- Step 1: Robustly read file content and perform initial aggressive character cleanup ---
    try:
        with open(file_path, 'rb') as f: 
            raw_bytes = f.read()
            original_content_raw_read = raw_bytes.decode('latin-1', errors='replace') 
    except Exception as e:
        print(f"  ERROR: Could not read {file_path} in binary mode: {e}")
        return False

    # Check for BOM and remove it
    if original_content_raw_read.startswith('\ufeff'):
        original_content_raw_read = original_content_raw_read.lstrip('\ufeff')
        file_modified = True

    # Apply aggressive character/escape cleaning before any JSON parsing attempt
    cleaned_content_for_parse = _robust_json_clean_string(original_content_raw_read)
    original_content_cleaned_chars = cleaned_content_for_parse 

    if cleaned_content_for_parse != original_content_raw_read:
        print(f"  Performed robust string literal and control character repair on {file_path}.")
        file_modified = True
        had_char_corruption_issue = True 


    # --- Prevent Unnecessary Modification of Good Files ---
    try:
        temp_data_for_check = json.loads(original_content_cleaned_chars)
        
        temp_calc_tot_item_cnt = 0
        temp_calc_tot_taxbl_amt = 0.0
        temp_calc_tot_tax_amt = 0.0
        temp_calc_tot_amt = 0.0
        
        for item in temp_data_for_check.get("itemList", []):
            prc = item.get("prc", 0.0)
            qty = item.get("qty", 0.0)
            tax_ty_cd = item.get("taxTyCd", "B")
            
            if isinstance(prc, (int, float)) and prc >= 0 and isinstance(qty, (int, float)) and qty >= 0:
                item_calculated_tot_amt = round(prc * qty, 2)
                item_calculated_taxbl_amt = item_calculated_tot_amt
                item_calculated_tax_amt = 0.0
                if tax_ty_cd == "B" and item_calculated_tot_amt > 0:
                    item_calculated_taxbl_amt = round(item_calculated_tot_amt / 1.16, 2)
                    item_calculated_tax_amt = round(item_calculated_tot_amt - item_calculated_taxbl_amt, 2)
                
                temp_calc_tot_taxbl_amt += item_calculated_taxbl_amt
                temp_calc_tot_tax_amt += item_calculated_tax_amt
                temp_calc_tot_amt += item_calculated_tot_amt
            temp_calc_tot_item_cnt += 1

        temp_calc_tot_taxbl_amt = round(temp_calc_tot_taxbl_amt, 2)
        temp_calc_tot_tax_amt = round(temp_calc_tot_tax_amt, 2)
        temp_calc_tot_amt = round(temp_calc_tot_amt, 2)

        is_logically_consistent = (
            temp_data_for_check.get("totItemCnt") == temp_calc_tot_item_cnt and
            abs(temp_data_for_check.get("totTaxblAmt", 0.0) - temp_calc_tot_taxbl_amt) < 0.01 and
            abs(temp_data_for_check.get("totTaxAmt", 0.0) - temp_calc_tot_tax_amt) < 0.01 and
            abs(temp_data_for_check.get("totAmt", 0.0) - temp_calc_tot_amt) < 0.01
        )
        
        if not had_char_corruption_issue and is_logically_consistent:
            print(f"  {file_path} parsed cleanly with no character issues and is logically consistent. Skipping further modifications.")
            return False 
    except json.JSONDecodeError:
        pass # Not clean, proceed with full fixing


    # --- Step 2: Guarantee JSON Parseability and Structural Integrity ---
    data, structural_fix_applied = _attempt_structural_fix_and_parse(original_content_cleaned_chars)
    
    if structural_fix_applied:
        file_modified = True
        if not data: 
            had_char_corruption_issue = True 
        print(f"  Successfully parsed {file_path} after structural repair. Structural fix applied: {structural_fix_applied}")

    if data is None: 
        print(f"  ERROR: Data is None after structural repair for {file_path}. Skipping file.")
        return False
    
    # --- Step 2.6 (NEW): Consolidate/Recover ALL Top-Level Fields from raw data hints ---
    
    temp_recovered_top_level_fields = {} 

    for key, default_value in DEFAULT_TOP_LEVEL_FIELDS.items():
        if key == "itemList": 
            continue 

        if key in data and (isinstance(data[key], type(default_value)) or (default_value == {} and isinstance(data[key], dict)) or (default_value == [] and isinstance(data[key], list))):
            temp_recovered_top_level_fields[key] = data[key]
        else:
            if isinstance(default_value, str) or default_value == "":
                match = re.search(rf'"{key}":"(.*?)(?:"|,|\}})', original_content_raw_read)
                if match:
                    temp_recovered_top_level_fields[key] = _robust_json_clean_string(f'"{match.group(1)}"').strip('"')
                    file_modified = True
            elif isinstance(default_value, (int, float)):
                match = re.search(rf'"{key}":\s*([\d.]+)', original_content_raw_read)
                if match:
                    try:
                        val = float(match.group(1)) if '.' in match.group(1) else int(match.group(1))
                        temp_recovered_top_level_fields[key] = val
                        file_modified = True
                    except ValueError:
                        pass
            elif isinstance(default_value, bool):
                match = re.search(rf'"{key}":\s*(true|false)', original_content_raw_read, re.IGNORECASE)
                if match:
                    temp_recovered_top_level_fields[key] = (match.group(1).lower() == 'true')
                    file_modified = True
            elif default_value == {}: 
                # CORRECTED LINE FOR SYNTAX ERROR
                # Doubled backslashes to escape literal curly braces for regex within an f-string
                match = re.search(rf'"{key}":(\\{{.*?\\}})', original_content_raw_read, re.DOTALL)
                if match:
                    raw_obj_string = match.group(1)
                    try:
                        cleaned_obj_string = _robust_json_clean_string(raw_obj_string)
                        parsed_obj = json.loads(cleaned_obj_string)
                        if isinstance(parsed_obj, dict):
                            temp_recovered_top_level_fields[key] = parsed_obj
                            file_modified = True
                    except json.JSONDecodeError:
                        pass 
            
            if key not in temp_recovered_top_level_fields:
                temp_recovered_top_level_fields[key] = default_value
                if key not in data: 
                    file_modified = True


    for key, value in temp_recovered_top_level_fields.items():
        if key != "itemList": 
            data[key] = value

    # --- Step 2.7 (Refined): Consolidate/Recover itemList with raw data hints ---
    final_item_list_for_processing = []
    processed_item_ids = set() 

    # 1. Add items that were successfully parsed from the current 'data' object
    if "itemList" in data and isinstance(data["itemList"], list):
        for parsed_item_candidate in data["itemList"]:
            if isinstance(parsed_item_candidate, dict):
                item_id = f"{parsed_item_candidate.get('itemSeq', 'N/A')}-{parsed_item_candidate.get('itemCd', 'N/A')}"
                if item_id not in processed_item_ids:
                    final_item_list_for_processing.append(parsed_item_candidate)
                    processed_item_ids.add(item_id)
            else:
                print(f"  Warning: Non-dict item found in parsed itemList: {parsed_item_candidate}")
                file_modified = True

    # 2. Aggressively regex-recover items from the original raw content that might have been missed.
    
    itemlist_array_match = re.search(r'"itemList":\[(.*?)\]', original_content_raw_read, re.DOTALL)

    if itemlist_array_match:
        raw_items_content = itemlist_array_match.group(1)
        raw_item_candidates = re.findall(r'\{.*?\}', raw_items_content, re.DOTALL)
        
        for raw_item_string_candidate in raw_item_candidates:
            try:
                cleaned_item_string_candidate = _robust_json_clean_string(raw_item_string_candidate)
                parsed_item = json.loads(cleaned_item_string_candidate)
                
                item_id = f"{parsed_item.get('itemSeq', 'N/A')}-{parsed_item.get('itemCd', 'N/A')}"
                if isinstance(parsed_item, dict) and item_id not in processed_item_ids:
                    final_item_list_for_processing.append(parsed_item)
                    processed_item_ids.add(item_id)
                    file_modified = True
                    had_char_corruption_issue = True
            except json.JSONDecodeError:
                extracted_fields = _extract_all_item_fields_from_raw(raw_item_string_candidate)
                item_id = f"{extracted_fields.get('itemSeq', 'N/A')}-{extracted_fields.get('itemCd', 'N/A')}"
                if extracted_fields and item_id not in processed_item_ids:
                    final_item_list_for_processing.append(extracted_fields)
                    processed_item_ids.add(item_id)
                    file_modified = True
                    had_char_corruption_issue = True

    original_had_itemlist_marker_overall = '"itemList":[' in original_content_raw_read 
    if not final_item_list_for_processing and original_had_itemlist_marker_overall:
        print(f"  No valid items recovered. Forcing minimal item for {file_path}.")
        final_item_list_for_processing = [{}] 
        file_modified = True
        had_char_corruption_issue = True

    data["itemList"] = final_item_list_for_processing


    # --- Step 3: Apply logical data corrections & Totals Validation ---
    if file_modified: 
        calculated_tot_item_cnt = 0
        calculated_tot_taxbl_amt = 0.0
        calculated_tot_tax_amt = 0.0
        calculated_tot_amt = 0.0

        processed_item_list_final = [] 
        for i, item_raw in enumerate(data.get("itemList", [])): 
            item = {} 
            
            if isinstance(item_raw, dict):
                item.update(item_raw)
            else:
                print(f"  Warning: Item {i} in itemList of {file_path} is not a dictionary ({type(item_raw)}). Replacing with minimal structure.")
                file_modified = True
            
            item.setdefault("itemSeq", i + 1)
            item.setdefault("itemCd", "")
            item.setdefault("itemClsCd", "")
            item.setdefault("itemNm", "")
            item.setdefault("bcd", "")
            item.setdefault("pkgUnitCd", "")
            item.setdefault("pkg", 0.0)
            item.setdefault("qtyUnitCd", "")
            item.setdefault("qty", 0.0)
            item.setdefault("prc", 0.0)
            item.setdefault("splyAmt", 0.0)
            item.setdefault("dcRt", 0.0)
            item.setdefault("dcAmt", 0.0)
            item.setdefault("isrccCd", "")
            item.setdefault("isrccNm", "")
            item.setdefault("isrcRt", 0.0)
            item.setdefault("isrcAmt", 0.0)
            item.setdefault("taxTyCd", "B") 
            item.setdefault("taxblAmt", 0.0)
            item.setdefault("taxAmt", 0.0)
            item.setdefault("totAmt", 0.0)
            
            current_item_cd = item.get("itemCd", "")
            current_item_cls_cd = item.get("itemClsCd", "")
            
            should_correct_logical_fields = False
            if had_char_corruption_issue and (current_item_cd == KENYATEST1_CORRECTION["itemCd"] or current_item_cls_cd == KENYATEST1_CORRECTION["itemClsCd"] or not is_printable_ascii(current_item_cd)): 
               should_correct_logical_fields = True

            if should_correct_logical_fields:
                for key, expected_value in KENYATEST1_CORRECTION.items():
                    current_value = item.get(key)
                    if current_value != expected_value:
                        item[key] = expected_value
                        file_modified = True
                        print(f"  Correcting field '{key}' in item {i} of {file_path}: changed to '{expected_value}' (KENYATEST1 related).")

            prc = item.get("prc")
            qty = item.get("qty")
            tax_ty_cd = item.get("taxTyCd")

            if isinstance(prc, (int, float)) and prc >= 0 and isinstance(qty, (int, float)) and qty >= 0:
                item_calculated_tot_amt = round(prc * qty, 2)
                
                item_calculated_taxbl_amt = 0.0
                item_calculated_tax_amt = 0.0
                
                if tax_ty_cd == "B": 
                    if item_calculated_tot_amt > 0:
                        item_calculated_taxbl_amt = round(item_calculated_tot_amt / 1.16, 2)
                        item_calculated_tax_amt = round(item_calculated_tot_amt - item_calculated_taxbl_amt, 2)
                    else:
                        item_calculated_taxbl_amt = 0.0
                        item_calculated_tax_amt = 0.0
                else: 
                    item_calculated_taxbl_amt = item_calculated_tot_amt
                    item_calculated_tax_amt = 0.0

                if abs(item.get("totAmt", 0.0) - item_calculated_tot_amt) > 0.01:
                    item["totAmt"] = item_calculated_tot_amt
                    file_modified = True
                    print(f"  Corrected item {i}'s totAmt in {file_path} to {item_calculated_tot_amt}.")
                
                if abs(item.get("taxblAmt", 0.0) - item_calculated_taxbl_amt) > 0.01:
                    item["taxblAmt"] = item_calculated_taxbl_amt
                    file_modified = True
                    print(f"  Corrected item {i}'s taxblAmt in {file_path} to {item_calculated_tax_amt}.")
                
                if abs(item.get("taxAmt", 0.0) - item_calculated_tax_amt) > 0.01:
                    item["taxAmt"] = item_calculated_tax_amt
                    file_modified = True
                    print(f"  Corrected item {i}'s taxAmt in {file_path} to {item_calculated_tax_amt}.")
                
                calculated_tot_taxbl_amt += item_calculated_taxbl_amt
                calculated_tot_tax_amt += item_calculated_tax_amt
                calculated_tot_amt += item_calculated_tot_amt
            
            calculated_tot_item_cnt += 1 
            processed_item_list_final.append(item) 

        data["itemList"] = processed_item_list_final

        calculated_tot_taxbl_amt = round(calculated_tot_taxbl_amt, 2)
        calculated_tot_tax_amt = round(calculated_tot_tax_amt, 2)
        calculated_tot_amt = round(calculated_tot_amt, 2)

        if data.get("totItemCnt") != calculated_tot_item_cnt:
            data["totItemCnt"] = calculated_tot_item_cnt
            file_modified = True
            print(f"  Corrected top-level totItemCnt in {file_path} to {calculated_tot_item_cnt}.")

        if abs(data.get("totTaxblAmt", 0.0) - calculated_tot_taxbl_amt) > 0.01:
            data["totTaxblAmt"] = calculated_tot_taxbl_amt
            file_modified = True
            print(f"  Corrected top-level totTaxblAmt in {file_path} to {calculated_tot_taxbl_amt}.")

        if abs(data.get("totTaxAmt", 0.0) - calculated_tot_tax_amt) > 0.01:
            data["totTaxAmt"] = calculated_tot_tax_amt
            file_modified = True
            print(f"  Corrected top-level totTaxAmt in {file_path} to {calculated_tot_tax_amt}.")

        if abs(data.get("totAmt", 0.0) - calculated_tot_amt) > 0.01:
            data["totAmt"] = calculated_tot_amt
            file_modified = True
            print(f"  Corrected top-level totAmt in {file_path} to {calculated_tot_amt}.")


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
        return False
        

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
