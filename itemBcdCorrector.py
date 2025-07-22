import os
import chardet
import json
import re


def remove_control_characters(s):
    """Removes control characters from a string."""
    if isinstance(s, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]+', '', s)  # Includes most common control chars, + for multiple
    return s


def fix_item_codes_robust_decode(folder_path, search_by="itemNm", search_value="BEVERAGES", new_code="KENYATEST1"):
    """
    Loops through .txt files, attempts to fix JSON decoding errors by removing
    invalid characters, then cleans control characters from relevant fields,
    finds items where the *cleaned* `itemNm` or `itemClsCd` matches the search
    value, and replaces the `itemCd` and `bcd` fields.  Saves the JSON without
    formatting.

    Args:
        folder_path (str): The path to the folder to search.
        search_by (str, optional): "itemNm" or "itemClsCd".  Defaults to "itemNm".
        search_value (str, optional): The value to search for. Defaults to "BEVERAGES".
        new_code (str, optional): The new item code. Defaults to "KENYATEST1".
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files in: {folder_path} and its subfolders")

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    # Detect the encoding of the file
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']

                    if encoding:
                        try:
                            # First, try to read the file normally
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()
                            data = json.loads(content)

                        except json.JSONDecodeError as e:
                            print(f"JSONDecodeError in {file_path}: {e}. Attempting to fix...")
                            # If normal decoding fails, try removing control characters *before* parsing
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()
                            content = remove_control_characters(content)  # Remove from the entire content
                            try:
                                data = json.loads(content)
                                print(f"Successfully fixed JSON decoding in {file_path} by removing control characters before parsing.")
                            except json.JSONDecodeError as e2:
                                print(f"Failed to fix JSON decoding in {file_path}: {e2}. Skipping file.")
                                continue  # Skip to the next file
                        except Exception as e:
                            print(f"Error reading or initial parsing {file_path}: {e}")
                            continue

                        # Process itemList
                        if "itemList" in data and isinstance(data["itemList"], list):
                            for item in data["itemList"]:
                                # Clean all relevant string fields in the item
                                for key in ["itemNm", "itemClsCd", "itemCd", "bcd"]:
                                    if key in item and isinstance(item[key], str):
                                        item[key] = remove_control_characters(item[key])

                                # Clean the search field (itemNm or itemClsCd) for comparison
                                if search_by == "itemNm":
                                    cleaned_search_value = item.get("itemNm", "")
                                elif search_by == "itemClsCd":
                                    cleaned_search_value = item.get("itemClsCd", "")
                                else:
                                    print(f"Invalid search_by value: {search_by}. Skipping item.")
                                    continue

                                # Compare the cleaned value to the search term
                                if cleaned_search_value == search_value:
                                    item["itemCd"] = new_code
                                    item["bcd"] = new_code
                                    print(f"Replaced item codes in {file_path} for item: {item.get('itemNm')}")

                        # Process receipt address, if it exists
                        if "receipt" in data and "adrs" in data["receipt"] and isinstance(data["receipt"]["adrs"], str):
                            data["receipt"]["adrs"] = remove_control_characters(data["receipt"]["adrs"])

                        # Write the modified JSON back to the file WITHOUT formatting
                        with open(file_path, 'w', encoding=encoding) as f:
                            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)  # No spaces

                        print(f"Successfully processed and updated: {file_path}")

                    else:
                        print(f"Warning: Could not detect encoding for {file_path}. Skipping.")

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    folder_path = input("Please enter the folder path: ")
    search_by = input("Search by (itemNm or itemClsCd, default: itemNm): ") or "itemNm"
    search_value = input(f"Enter the value to search for in {search_by} (default: BEVERAGES): ") or "BEVERAGES"
    new_code = input("Enter the new item code (default: KENYATEST1): ") or "KENYATEST1"

    fix_item_codes_robust_decode(folder_path, search_by, search_value, new_code)

    print("Item code fixing process completed.")