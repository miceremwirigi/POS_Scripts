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

def validate_invoice(data, filename):
    """
    Validates the invoice calculations and reports any discrepancies.
    """
    discrepancies = []
    tolerance = 0.02  # Increased tolerance for tax amount comparisons

    # 1. Validate tax calculations for each item
    item_taxbl_amt_sum = 0.0
    item_tax_amt_sum = 0.0
    item_tot_amt_sum = 0.0
    item_count = 0

    if 'itemList' in data and isinstance(data['itemList'], list):
        item_count = len(data['itemList'])
        for item in data['itemList']:
            tax_ty_cd = item.get('taxTyCd')
            taxbl_amt = float(item.get('taxblAmt', 0.0))
            tax_amt = float(item.get('taxAmt', 0.0))
            tot_amt = float(item.get('totAmt', 0.0))

            if tax_ty_cd == 'A':
                if abs(tax_amt) > 0.001:  # Tolerance for floating-point comparison
                    discrepancies.append(f"Item {item.get('itemSeq')}: taxTyCd is A, but taxAmt is not 0.00 (taxAmt={tax_amt})")
                if abs(taxbl_amt - tot_amt) > 0.001:
                    discrepancies.append(f"Item {item.get('itemSeq')}: taxTyCd is A, but taxblAmt != totAmt (taxblAmt={taxbl_amt}, totAmt={tot_amt})")
            elif tax_ty_cd == 'B':
                expected_tax_amt = round(taxbl_amt * 0.16, 2)
                if abs(tax_amt - expected_tax_amt) > tolerance:  # Increased tolerance
                    discrepancies.append(f"Item {item.get('itemSeq')}: taxTyCd is B, but taxAmt is not 16% of taxblAmt (taxblAmt={taxbl_amt}, taxAmt={tax_amt}, expectedTaxAmt={expected_tax_amt})")

            item_taxbl_amt_sum += taxbl_amt
            item_tax_amt_sum += tax_amt
            item_tot_amt_sum += tot_amt

    # 2. Validate totals against item sums
    if 'totItemCnt' in data:
        tot_item_cnt = float(data.get('totItemCnt', 0.0))
        if abs(tot_item_cnt - item_count) > 0.001:
            discrepancies.append(f"Total item count mismatch: totItemCnt={tot_item_cnt}, actual item count={item_count}")
    if 'totTaxblAmt' in data:
        tot_taxbl_amt = float(data.get('totTaxblAmt', 0.0))
        if abs(tot_taxbl_amt - item_taxbl_amt_sum) > 0.01:
            discrepancies.append(f"Total taxblAmt mismatch: totTaxblAmt={tot_taxbl_amt}, sum of item taxblAmt={item_taxbl_amt_sum}")

    # Validate tax amounts A and B
    taxbl_amt_a = float(data.get('taxblAmtA', 0.0))
    taxbl_amt_b = float(data.get('taxblAmtB', 0.0))
    tax_amt_a = float(data.get('taxAmtA', 0.0))
    tax_amt_b = float(data.get('taxAmtB', 0.0))

    calculated_taxbl_amt_a = sum(float(item.get('taxblAmt', 0.0)) for item in data['itemList'] if item.get('taxTyCd') == 'A')
    calculated_taxbl_amt_b = sum(float(item.get('taxblAmt', 0.0)) for item in data['itemList'] if item.get('taxTyCd') == 'B')
    calculated_tax_amt_a = sum(float(item.get('taxAmt', 0.0)) for item in data['itemList'] if item.get('taxTyCd') == 'A')
    calculated_tax_amt_b = sum(float(item.get('taxAmt', 0.0)) for item in data['itemList'] if item.get('taxTyCd') == 'B')

    if abs(taxbl_amt_a - calculated_taxbl_amt_a) > 0.01:
        discrepancies.append(f"Mismatch in taxblAmtA: Expected {calculated_taxbl_amt_a}, got {taxbl_amt_a}")
    if abs(taxbl_amt_b - calculated_taxbl_amt_b) > 0.01:
        discrepancies.append(f"Mismatch in taxblAmtB: Expected {calculated_taxbl_amt_b}, got {taxbl_amt_b}")
    if abs(tax_amt_a - calculated_tax_amt_a) > 0.01:
        discrepancies.append(f"Mismatch in taxAmtA: Expected {calculated_tax_amt_a}, got {tax_amt_a}")
    if abs(tax_amt_b - calculated_tax_amt_b) > 0.01:
        discrepancies.append(f"Mismatch in taxAmtB: Expected {calculated_tax_amt_b}, got {tax_amt_b}")

    if 'totTaxAmt' in data:
        tot_tax_amt = float(data.get('totTaxAmt', 0.0))
        if abs(tot_tax_amt - item_tax_amt_sum) > 0.01:
            discrepancies.append(f"Total taxAmt mismatch: totTaxAmt={tot_tax_amt}, sum of item taxAmt={item_tax_amt_sum}")
    if 'totAmt' in data:
        tot_amt = float(data.get('totAmt', 0.0))
        if abs(tot_amt - item_tot_amt_sum) > 0.01:
            discrepancies.append(f"Total totAmt mismatch: totAmt={tot_amt}, sum of item totAmt={item_tot_amt_sum}")

    if discrepancies:
        print(f"Discrepancies found in file: {filename}")
        for discrepancy in discrepancies:
            print(f"  - {discrepancy}")
    else:
        print(f"No discrepancies found in file: {filename}")

def process_invoices(folder_path):
    """
    Processes all .txt files in the given folder and its subfolders,
    validating calculations and reporting discrepancies.
    """
    total_files_processed = 0

    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.endswith(".txt"):
                total_files_processed += 1
                file_path = os.path.join(root, filename)
                print(f"Processing file: {file_path}")

                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                    # Process the entire JSON to format float strings
                    process_json(data)

                    # Validate the invoice calculations
                    validate_invoice(data, filename)

                except json.JSONDecodeError:
                    print(f"Error decoding JSON in: {filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

    print(f"Validation complete. Total files processed: {total_files_processed}")

if __name__ == "__main__":
    folder_path = input("Enter the path to the folder containing the invoice files: ")
    process_invoices(folder_path)