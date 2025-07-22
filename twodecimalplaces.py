import os
import json
import re

def format_float_string(value):
    """
    Formats a float string to two decimal places if it currently has one decimal place.
    """
    if isinstance(value, str) and re.match(r'^\d+\.\d$', value):
        return value + '0'
    return value

def process_json(data):
    """
    Recursively processes a JSON-like data structure to format float strings.
    """
    modified = False
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (int, float)):
                str_value = str(float(value))
                formatted_value = format_float_string(str_value)
                if formatted_value != str_value:
                    data[key] = formatted_value
                    modified = True
            elif isinstance(value, (dict, list)):
                sub_modified = process_json(value)
                if sub_modified:
                    modified = True
    elif isinstance(data, list):
        for i, item in enumerate(data):
            sub_modified = process_json(item)
            if sub_modified:
                modified = True
    return modified

def process_invoices(folder_path):
    """
    Processes all .txt files in the given folder and its subfolders,
    correcting tax codes, verifying tax amounts, ensuring two decimal places,
    with progress printed to the terminal, and saves the output as unformatted JSON.
    """
    total_files_processed = 0
    total_files_modified = 0

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.endswith(".txt"):
                total_files_processed += 1
                file_path = os.path.join(root, filename)
                print(f"Processing file: {file_path}")

                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                    modified = False

                    # Correct taxTyCd and calculate taxblAmtA
                    taxbl_amt_a_sum = 0.0
                    if 'itemList' in data and isinstance(data['itemList'], list):
                        for item in data['itemList']:
                            if item.get('taxTyCd') == '0':
                                item['taxTyCd'] = 'A'
                                modified = True
                            if item.get('taxTyCd') == 'A':
                                taxbl_amt_a_sum += float(item['taxblAmt'])

                    taxbl_amt_a_sum = round(taxbl_amt_a_sum, 2)
                    if 'taxblAmtA' in data:
                        if abs(float(data['taxblAmtA']) - taxbl_amt_a_sum) > 0.001:  # Using a tolerance for comparison
                            data['taxblAmtA'] = str(taxbl_amt_a_sum)
                            modified = True

                    # Process the entire JSON to format float strings
                    modified = process_json(data) or modified

                    # Write the modified data back to the file (unformatted)
                    if modified:
                        with open(file_path, 'w') as f:
                            json.dump(data, f, ensure_ascii=False)  # Removed indent parameter
                        print(f"Modified file: {filename}")
                        total_files_modified += 1
                    else:
                        print(f"No changes needed for file: {filename}")

                except json.JSONDecodeError:
                    print(f"Error decoding JSON in: {filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

    print(f"Processing complete. Total files processed: {total_files_processed}, Total files modified: {total_files_modified}")

if __name__ == "__main__":
    folder_path = input("Enter the path to the folder containing the invoice files: ")
    process_invoices(folder_path)