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
    "prchrAcptcYn": "Y", # Default to Y as per example
    "remark": "",
    "regrId": "", # Changed from '1' to '' as '1' is a specific value, not a generic default
    "regrNm": "", # Changed from 'A' to ''
    "modrId": "", # Changed from '1' to ''
    "modrNm": "", # Changed from 'A' to ''
    "receipt": {}, # This is an object
    "itemList": [] # This is a list, handled separately
}


def is_printable_ascii(s):
    """Checks if a string contains only printable ASCII characters (0x20-0x7E)."""
    return all(32 <= ord(char) <= 126 for char in s)

def _robust_json_clean_string(text_content):
    """
    Performs aggressive, character-by-character cleaning to make a string safely parseable by json.loads().
    It removes illegal control characters and ensures quotes/backslashes are escaped correctly.
    """
    cleaned_chars = []
    in_string = False
    escaped = False # Tracks if the previous char was a backslash for escaping purposes

    for char_idx, char in enumerate(text_content):
        if in_string:
            if escaped:
                # If previous was escape char, this char is part of the escape sequence.
                # Only valid escapes are allowed by JSON. Pass them through directly.
                cleaned_chars.append(char)
                escaped = False
            elif char == '\\':
                # Start of an escape sequence. Append and mark.
                cleaned_chars.append(char)
                escaped = True
            elif char == '"':
                # End of string. Append and exit string mode.
                cleaned_chars.append(char)
                in_string = False
            # Explicitly remove C0 (0x00-0x1F), C1 (0x80-0x9F) control characters and DEL (0x7F) inside strings
            # These are strictly illegal in unescaped JSON strings.
            elif (0x00 <= ord(char) <= 0x1F) or (0x80 <= ord(char) <= 0x9F) or (ord(char) == 0x7F):
                pass # Remove the illegal control character
            else:
                # Regular character inside string.
                cleaned_chars.append(char)
        else: # Not in a string
            if char == '"':
                # Start of a string. Append and enter string mode.
                cleaned_chars.append(char)
                in_string = True
            elif char in (' ', '\t', '\n', '\r'):
                # Whitespace outside string. Keep it (JSON allows this).
                cleaned_chars.append(char)
            # Explicitly remove C0 (0x00-0x1F), C1 (0x80-0x9F) control characters and DEL (0x7F) outside strings
            elif (0x00 <= ord(char) <= 0x1F) or (0x80 <= ord(char) <= 0x9F) or (ord(char) == 0x7F):
                pass # Remove it
            else:
                # Other characters outside string. Append them.
                # These could be structural JSON chars like {, }, :, ,, [, ].
                cleaned_chars.append(char)
    
    # This function's sole focus is to make individual string *content* valid.
    # Structural closure (e.g., adding a final '"}' for unterminated strings at EOF)
    # is handled by _attempt_structural_fix_and_parse.
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
    # Note: These regexes are designed to be resilient to some corruption within the value.
    patterns = {
        "itemSeq": r'"itemSeq":\s*(\d+)',
        "itemCd": r'"itemCd":"(.*?)(?:"|,|\})', # Capture until next quote or JSON structure
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
            # Attempt type conversion for numeric fields
            if field in ["itemSeq", "pkg", "qty", "prc", "splyAmt", "dcRt", "dcAmt", 
                         "isrcRt", "isrcAmt", "taxblAmt", "taxAmt", "totAmt"]:
                try:
                    extracted_data[field] = float(value) if '.' in value else int(value)
                except ValueError:
                    pass # Keep default
            else: # String fields
                # Attempt to clean the extracted string value just in case
                cleaned_value = _robust_json_clean_string(f'"{value}"').strip('"')
                extracted_data[field] = cleaned_value
    
    return extracted_data


def fix_json_file(file_path):
    """
    Attempts to fix common JSON errors in a single file:
    1. Robustly reads file content, handling encoding errors.
    2. Aggressively cleans raw content: removes non-printable ASCII, invalid escapes, and control characters.
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
    original_content_cleaned_chars = cleaned_content_for_parse # Store this version for later comparison/recovery

    if cleaned_content_for_parse != original_content_raw_read:
        print(f"  Performed robust string literal and control character repair on {file_path}.")
        file_modified = True
        had_char_corruption_issue = True # Consider this a character corruption fix


    # --- Prevent Unnecessary Modification of Good Files ---
    # Try parsing the character-cleaned content directly. If successful AND no char corruption, assume good.
    try:
        temp_data_for_check = json.loads(original_content_cleaned_chars)
        
        # Recalculate totals for the test_data
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
        
        # If no character issues AND everything is already logically consistent, skip.
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
    # This addresses the problem of losing fields like prchrAcptcYn, remark, regrId, receipt section etc.
    # It tries to extract these directly from the original raw content if they were lost during parsing.
    
    # Create a temporary dict to hold recovered top-level fields
    recovered_top_level_fields = {}
    
    # Attempt to extract fields from the raw content using regex
    # This is a broad regex to get key-value pairs at the top level outside of itemList
    # It's an aggressive attempt to recover lost fields.
    top_level_matches = re.findall(r'"(\w+)":\s*(true|false|null|-?\d+\.?\d*|\[.*?\]|\{.*?\}|".*?")', original_content_raw_read, re.DOTALL)
    
    for key, value_str in top_level_matches:
        if key in DEFAULT_TOP_LEVEL_FIELDS and key not in ["itemList"]: # Avoid processing itemList here
            try:
                # Attempt to parse the value string
                if value_str.startswith('"') and value_str.endswith('"'):
                    # It's a string, clean it and remove outer quotes
                    parsed_value = _robust_json_clean_string(value_str).strip('"')
                elif value_str.startswith('{') and value_str.endswith('}'):
                    # It's an object, try to load it
                    parsed_value = json.loads(_robust_json_clean_string(value_str))
                elif value_str.startswith('[') and value_str.endswith(']'):
                    # It's an array, try to load it (less common for top-level, but for completeness)
                    parsed_value = json.loads(_robust_json_clean_string(value_str))
                else:
                    # It's a number, boolean, or null
                    parsed_value = json.loads(value_str)
                
                recovered_top_level_fields[key] = parsed_value
                # print(f"  Recovered top-level field '{key}': {parsed_value}") # Debugging
            except json.JSONDecodeError:
                pass # Failed to parse this specific top-level value, skip

    # Update the 'data' object with recovered top-level fields, prioritizing them.
    # Existing fields in 'data' will be preserved unless explicitly overwritten by a recovered field.
    for key, default_value in DEFAULT_TOP_LEVEL_FIELDS.items():
        if key != "itemList": # itemList is handled separately
            if key in recovered_top_level_fields:
                if data.get(key) != recovered_top_level_fields[key]: # Only update if different
                    data[key] = recovered_top_level_fields[key]
                    file_modified = True
                    print(f"  Updated top-level field '{key}' with recovered value.")
            elif key not in data: # If not recovered AND not in data, set default
                data[key] = default_value
                file_modified = True
                print(f"  Defaulted missing top-level field '{key}'.")
    
    # Special handling for receipt, if still missing or empty after generic recovery
    if "receipt" not in data or not isinstance(data["receipt"], dict) or not data["receipt"]:
        receipt_match = re.search(r'"receipt":(\{.*?\})', original_content_raw_read, re.DOTALL)
        if receipt_match:
            raw_receipt_string = receipt_match.group(1)
            try:
                cleaned_receipt_string = _robust_json_clean_string(raw_receipt_string)
                parsed_receipt = json.loads(cleaned_receipt_string)
                if isinstance(parsed_receipt, dict):
                    data["receipt"] = parsed_receipt
                    file_modified = True
                    print(f"  Recovered 'receipt' object from raw content.")
            except json.JSONDecodeError:
                pass # Failed to recover receipt fully
        if "receipt" not in data or not isinstance(data["receipt"], dict):
            data["receipt"] = {} # Ensure it's at least an empty dict
            file_modified = True
            print(f"  Defaulted 'receipt' to empty dictionary.")

    # --- Step 2.7 (Refined): Consolidate/Recover itemList with raw data hints ---
    # This step ensures the itemList is robustly populated, prioritizing original content.

    final_item_list_for_processing = []
    
    # Use a set to track processed items by a unique identifier to avoid duplicates
    processed_item_ids = set() 

    # Attempt to extract items directly from the parsed 'data' first.
    # This ensures we get any items that were correctly parsed by json.loads in Step 2.
    if "itemList" in data and isinstance(data["itemList"], list):
        for parsed_item_candidate in data["itemList"]:
            if isinstance(parsed_item_candidate, dict):
                # Use itemSeq + itemCd as a simple unique identifier for deduplication
                item_id = f"{parsed_item_candidate.get('itemSeq')}-{parsed_item_candidate.get('itemCd')}"
                if parsed_item_candidate.get("itemSeq") is not None and item_id not in processed_item_ids:
                    final_item_list_for_processing.append(parsed_item_candidate)
                    processed_item_ids.add(item_id)
            else:
                print(f"  Warning: Non-dict item found in parsed itemList: {parsed_item_candidate}")
                file_modified = True

    # Aggressive regex recovery from raw content for items not yet captured.
    original_had_itemlist_marker = '"itemList":[' in original_content_raw_read
    
    if original_had_itemlist_marker:
        # This regex now targets the content specifically within the itemList array.
        itemlist_array_content_match = re.search(r'"itemList":\[(.*?)\]', original_content_raw_read, re.DOTALL)
        
        if itemlist_array_content_match:
            raw_items_content = itemlist_array_content_match.group(1)
            # Find individual item objects within this raw_items_content.
            # Look for patterns that strongly suggest an item object, e.g., starting with "itemSeq".
            raw_item_candidates = re.findall(r'\{[^}]*"itemSeq":\s*\d+[^}]*?\}', raw_items_content, re.DOTALL)
            
            for raw_item_string_candidate in raw_item_candidates:
                try:
                    cleaned_item_string_candidate = _robust_json_clean_string(raw_item_string_candidate)
                    parsed_item = json.loads(cleaned_item_string_candidate)
                    
                    item_id = f"{parsed_item.get('itemSeq')}-{parsed_item.get('itemCd')}"
                    if isinstance(parsed_item, dict) and parsed_item.get("itemSeq") is not None and item_id not in processed_item_ids:
                        final_item_list_for_processing.append(parsed_item)
                        processed_item_ids.add(item_id)
                        file_modified = True
                        had_char_corruption_issue = True
                except json.JSONDecodeError:
                    # If direct parse fails, try field-by-field extraction from raw string
                    extracted_fields = _extract_all_item_fields_from_raw(raw_item_string_candidate)
                    item_id = f"{extracted_fields.get('itemSeq')}-{extracted_fields.get('itemCd')}"
                    if extracted_fields and item_id not in processed_item_ids:
                        final_item_list_for_processing.append(extracted_fields)
                        processed_item_ids.add(item_id)
                        file_modified = True
                        had_char_corruption_issue = True
        
        # If after all recovery attempts, the item list is still empty but was hinted at originally, force a minimal item.
        if not final_item_list_for_processing and original_had_itemlist_marker:
            print(f"  No valid items recovered from raw content despite marker. Forcing minimal item for {file_path}.")
            final_item_list_for_processing = [{}] 
            file_modified = True
            had_char_corruption_issue = True
    elif not original_had_itemlist_marker and (not final_item_list_for_processing):
        # If no itemList marker was found originally at all, default to empty list if it's currently empty.
        # This prevents injecting empty items when itemList wasn't expected.
        print(f"  No 'itemList' marker found in original raw content for {file_path}. Initializing as empty list if needed.")
        if "itemList" not in data or not isinstance(data["itemList"], list):
             data["itemList"] = []
             file_modified = True

    # Update data's itemList with the (potentially recovered and consolidated) list for Step 3
    data["itemList"] = final_item_list_for_processing


    # --- Step 3: Apply logical data corrections & Totals Validation ---
    if file_modified: 
        calculated_tot_item_cnt = 0
        calculated_tot_taxbl_amt = 0.0
        calculated_tot_tax_amt = 0.0
        calculated_tot_amt = 0.0

        processed_item_list_final = [] # This list will be written back to data["itemList"]
        for i, item_raw in enumerate(data.get("itemList", [])): 
            item = {} 
            
            # Start with a clean dictionary, then update from item_raw if it's a dict
            if isinstance(item_raw, dict):
                item.update(item_raw)
            else:
                print(f"  Warning: Item {i} in itemList of {file_path} is not a dictionary ({type(item_raw)}). Replacing with minimal structure.")
                file_modified = True
            
            # Default all expected fields for the item if missing, after potential extraction
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
            
            # Logical correction for KENYATEST1
            current_item_cd = item.get("itemCd", "")
            current_item_cls_cd = item.get("itemClsCd", "")
            
            should_correct_logical_fields = False
            # Only correct to KENYATEST1 if there was original corruption AND itemCd is garbage or explicitly matching partial KENYATEST1
            if had_char_corruption_issue or not is_printable_ascii(current_item_cd): 
               if current_item_cd.startswith("KENYATEST") or current_item_cls_cd == KENYATEST1_CORRECTION["itemClsCd"] or not is_printable_ascii(current_item_cd):
                   should_correct_logical_fields = True

            if should_correct_logical_fields:
                for key, expected_value in KENYATEST1_CORRECTION.items():
                    current_value = item.get(key)
                    if current_value != expected_value:
                        item[key] = expected_value
                        file_modified = True
                        print(f"  Correcting field '{key}' in item {i} of {file_path}: changed to '{expected_value}' (KENYATEST1 related).")

            # Recalculate item-level financials (qty, prc must be >= 0 for meaningful calculation)
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
                    print(f"  Corrected item {i}'s taxblAmt in {file_path} to {item_calculated_taxbl_amt}.")
                
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
