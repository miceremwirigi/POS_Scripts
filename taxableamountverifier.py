import os
import json
import math
import sys
import time

def verify_invoice_amounts(folder_path):
    """
    Verifies various amount calculations within invoice JSON files.
    Only reports files that have discrepancies directly to the terminal.
    Now also looks into subfolders and shows a processing indicator.

    Args:
        folder_path (str): The path to the folder containing the .txt files with JSON data.
    """
    if not os.path.isdir(folder_path):
        print(f"❌ Error: Folder '{folder_path}' not found. Please provide a valid folder path.")
        return

    print(f"🔍 Starting enhanced verification in folder: '{folder_path}'")
    print("-" * 50)

    files_processed = 0
    discrepancies_found_in_files = 0
    tolerance = 1e-2
    
    # Loading indicator setup
    loading_chars = ['-', '\\', '|', '/']
    char_index = 0
    
    # Use os.walk() to iterate through the folder and all its subfolders
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)

            # Process only .txt files
            if filename.endswith('.txt'):
                files_processed += 1
                file_has_discrepancy = False
                discrepancy_messages = []

                # Update and print the loading indicator on the same line
                sys.stdout.write(f"\rProcessing file {files_processed} of unknown total... {loading_chars[char_index]}")
                sys.stdout.flush()
                char_index = (char_index + 1) % len(loading_chars)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    data = json.loads(content)

                    # --- 1. Get Parent Fields ---
                    total_taxable_amount_str = data.get("TotalTaxableAmount")
                    total_tax_amount_str = data.get("TotalTaxAmount")
                    total_invoice_amount_str = data.get("TotalInvoiceAmount")
                    item_details = data.get("ItemDetails")

                    # Basic validation for essential keys
                    if any(x is None for x in [total_taxable_amount_str, total_tax_amount_str, total_invoice_amount_str, item_details]):
                        discrepancy_messages.append("   ❗ Error: One or more essential keys are missing or malformed.")
                        file_has_discrepancy = True
                        if file_has_discrepancy:
                            # Clear the loading indicator line
                            sys.stdout.write('\r' + ' ' * 70 + '\r')
                            sys.stdout.flush()
                            print(f"❌ Discrepancies found in {filepath}:")
                            for msg in discrepancy_messages:
                                print(msg)
                            print("-" * 50)
                            discrepancies_found_in_files += 1
                        continue

                    if not isinstance(item_details, list):
                        discrepancy_messages.append("   ❗ Error: 'ItemDetails' is not a list.")
                        file_has_discrepancy = True
                        if file_has_discrepancy:
                            # Clear the loading indicator line
                            sys.stdout.write('\r' + ' ' * 70 + '\r')
                            sys.stdout.flush()
                            print(f"❌ Discrepancies found in {filepath}:")
                            for msg in discrepancy_messages:
                                print(msg)
                            print("-" * 50)
                            discrepancies_found_in_files += 1
                        continue

                    total_taxable_amount = float(total_taxable_amount_str)
                    total_tax_amount = float(total_tax_amount_str)
                    total_invoice_amount = float(total_invoice_amount_str)

                    # --- 2. Calculate sums from ItemDetails based on new requirements ---
                    sum_item_amounts_taxable_16_percent = 0.0
                    sum_item_amounts_zero_tax = 0.0
                    sum_all_item_tax_amounts = 0.0

                    for i, item in enumerate(item_details):
                        item_amount_str = item.get("ItemAmount")
                        tax_rate_str = item.get("TaxRate")
                        item_tax_amount_str = item.get("TaxAmount")

                        if any(x is None for x in [item_amount_str, tax_rate_str, item_tax_amount_str]):
                            discrepancy_messages.append(f"     ❗ Warning: Missing keys in item {i+1}. Skipping this item.")
                            file_has_discrepancy = True
                            continue

                        try:
                            item_amount = float(item_amount_str)
                            tax_rate = float(tax_rate_str)
                            item_tax_amount = float(item_tax_amount_str)

                            if math.isclose(tax_rate, 16.00, rel_tol=tolerance, abs_tol=tolerance):
                                sum_item_amounts_taxable_16_percent += item_amount
                            elif math.isclose(tax_rate, 0.00, rel_tol=tolerance, abs_tol=tolerance):
                                sum_item_amounts_zero_tax += item_amount

                            sum_all_item_tax_amounts += item_tax_amount

                            # --- Check 4: Tax rate * Item amount product vs. Item Tax Amount ---
                            expected_item_tax = item_amount * (tax_rate / 100.0)
                            if not math.isclose(item_tax_amount, expected_item_tax, rel_tol=tolerance, abs_tol=tolerance):
                                discrepancy_messages.append(
                                    f"     ❌ Item {i+1}: TaxAmount mismatch! Expected {expected_item_tax:.2f} "
                                    f"((ItemAmount {item_amount:.2f} * TaxRate {tax_rate:.2f}%)) "
                                    f"but got {item_tax_amount:.2f}."
                                )
                                file_has_discrepancy = True
                        except ValueError as e:
                            discrepancy_messages.append(f"     ❗ Error: Invalid number format in item {i+1}: {e}.")
                            file_has_discrepancy = True
                            continue

                    # --- Check 1: Sum of ItemAmounts (TaxRate 16.00) vs. TotalTaxableAmount ---
                    if not math.isclose(sum_item_amounts_taxable_16_percent, total_taxable_amount, rel_tol=tolerance, abs_tol=tolerance):
                        discrepancy_messages.append(
                            f"   ❌ Discrepancy: Sum of ItemAmounts with 16% TaxRate ({sum_item_amounts_taxable_16_percent:.2f}) "
                            f"DOES NOT match TotalTaxableAmount ({total_taxable_amount:.2f})."
                        )
                        file_has_discrepancy = True

                    # --- Check 2: Sum of ALL Item TaxAmounts vs. TotalTaxAmount ---
                    if not math.isclose(sum_all_item_tax_amounts, total_tax_amount, rel_tol=tolerance, abs_tol=tolerance):
                        discrepancy_messages.append(
                            f"   ❌ Discrepancy: Sum of ALL Item TaxAmounts ({sum_all_item_tax_amounts:.2f}) "
                            f"DOES NOT match TotalTaxAmount ({total_tax_amount:.2f})."
                        )
                        file_has_discrepancy = True

                    # --- Check 3: Calculated Total Invoice Amount vs. TotalInvoiceAmount ---
                    expected_total_invoice_amount = sum_item_amounts_taxable_16_percent + sum_item_amounts_zero_tax + sum_all_item_tax_amounts
                    if not math.isclose(total_invoice_amount, expected_total_invoice_amount, rel_tol=tolerance, abs_tol=tolerance):
                        discrepancy_messages.append(
                            f"   ❌ Discrepancy: TotalInvoiceAmount ({total_invoice_amount:.2f}) "
                            f"DOES NOT match (Calculated Taxable Items @16% ({sum_item_amounts_taxable_16_percent:.2f}) + "
                            f"Calculated Zero-Tax Items ({sum_item_amounts_zero_tax:.2f}) + "
                            f"Calculated Total Tax ({sum_all_item_tax_amounts:.2f})) "
                            f"= {expected_total_invoice_amount:.2f}."
                        )
                        file_has_discrepancy = True

                except json.JSONDecodeError:
                    discrepancy_messages.append("   ❗ Error: Could not decode JSON. Please check file content.")
                    file_has_discrepancy = True
                except ValueError as e:
                    discrepancy_messages.append(f"   ❗ Error: Data conversion error: {e}.")
                    file_has_discrepancy = True
                except Exception as e:
                    discrepancy_messages.append(f"   ❗ An unexpected error occurred: {e}")
                    file_has_discrepancy = True
                
                if file_has_discrepancy:
                    # Clear the loading indicator line before printing the error
                    sys.stdout.write('\r' + ' ' * 70 + '\r')
                    sys.stdout.flush()
                    print(f"❌ Discrepancies found in {filepath}:")
                    for msg in discrepancy_messages:
                        print(msg)
                    print("-" * 50)
                    discrepancies_found_in_files += 1
    
    # Final clear of the loading line before printing the final summary
    sys.stdout.write('\r' + ' ' * 70 + '\r')
    sys.stdout.flush()

    print(f"\nVerification Complete.")
    print(f"Total files processed: {files_processed}")
    if discrepancies_found_in_files > 0:
        print(f"Total files with discrepancies found: {discrepancies_found_in_files} 🚩")
    else:
        print("No discrepancies found in any files. All checks passed! 🎉")

# --- Main execution ---
if __name__ == "__main__":
    # To test, uncomment the lines below to create dummy files
    # import os
    # if not os.path.exists('invoice_data'):
    #     os.makedirs('invoice_data')
    # if not os.path.exists('invoice_data/sub_folder'):
    #     os.makedirs('invoice_data/sub_folder')
    #
    # # Example: All amounts match
    # with open('invoice_data/invoice_all_match.txt', 'w') as f:
    #     f.write('''{"TotalTaxableAmount":"300.00","TotalTaxAmount":"48.00","TotalInvoiceAmount":"348.00","ItemDetails":[{"ItemAmount":"100.00","TaxRate":"16.00","TaxAmount":"16.00"},{"ItemAmount":"200.00","TaxRate":"16.00","TaxAmount":"32.00"}]}''')
    #
    # # Example: Mismatch in TotalTaxableAmount
    # with open('invoice_data/invoice_taxable_mismatch.txt', 'w') as f:
    #     f.write('''{"TotalTaxableAmount":"600.00","TotalTaxAmount":"48.00","TotalInvoiceAmount":"348.00","ItemDetails":[{"ItemAmount":"100.00","TaxRate":"16.00","TaxAmount":"16.00"},{"ItemAmount":"200.00","TaxRate":"16.00","TaxAmount":"32.00"}]}''')
    #
    # # Example: Mismatch in a subfolder
    # with open('invoice_data/sub_folder/invoice_sub_folder_mismatch.txt', 'w') as f:
    #     f.write('''{"TotalTaxableAmount":"300.00","TotalTaxAmount":"50.00","TotalInvoiceAmount":"350.00","ItemDetails":[{"ItemAmount":"100.00","TaxRate":"16.00","TaxAmount":"16.00"},{"ItemAmount":"200.00","TaxRate":"16.00","TaxAmount":"32.00"}]}''')

    folder_to_check = input("Enter the folder path containing the .txt invoice files: ")
    verify_invoice_amounts(folder_to_check)