import os
import json
import math
import sys
import shutil

def correct_faulty_invoice_amounts(folder_path):
    """
    Verifies and corrects discrepancies in invoice JSON files.
    Only corrects files that are found to have discrepancies.
    The corrected files are saved in an unformatted, single-line JSON format.

    Args:
        folder_path (str): The path to the folder containing the .txt files with JSON data.
    """
    if not os.path.isdir(folder_path):
        print(f"❌ Error: Folder '{folder_path}' not found. Please provide a valid folder path.")
        return

    print(f"🔍 Starting verification & correction of faulty invoices in: '{folder_path}'")
    print("-" * 50)

    files_processed = 0
    files_corrected = 0
    files_skipped = 0
    tolerance = 1e-2

    # Loading indicator setup
    loading_chars = ['-', '\\', '|', '/']
    char_index = 0

    # Use os.walk() to iterate through the folder and all its subfolders
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)

            if filename.endswith('.txt'):
                files_processed += 1
                
                # Update and print the loading indicator on the same line
                sys.stdout.write(f"\rProcessing file {files_processed}... {loading_chars[char_index]}")
                sys.stdout.flush()
                char_index = (char_index + 1) % len(loading_chars)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    data = json.loads(content)

                    # --- 1. Get Parent Fields and Item Details ---
                    total_taxable_amount_str = data.get("TotalTaxableAmount")
                    total_tax_amount_str = data.get("TotalTaxAmount")
                    total_invoice_amount_str = data.get("TotalInvoiceAmount")
                    item_details = data.get("ItemDetails")
                    
                    # Basic validation for essential keys
                    if any(x is None for x in [total_taxable_amount_str, total_tax_amount_str, total_invoice_amount_str, item_details]) or not isinstance(item_details, list):
                        # Clear the loading indicator line
                        sys.stdout.write('\r' + ' ' * 70 + '\r')
                        sys.stdout.flush()
                        print(f"❗ Skipping {filepath}: Essential keys are missing or malformed.")
                        files_skipped += 1
                        continue

                    # --- 2. Calculate sums from ItemDetails for verification ---
                    sum_item_amounts_taxable_16_percent = 0.0
                    sum_item_amounts_zero_tax = 0.0
                    sum_all_item_tax_amounts = 0.0
                    malformed_item_found = False

                    for i, item in enumerate(item_details):
                        try:
                            item_amount = float(item.get("ItemAmount", "0.0"))
                            tax_rate = float(item.get("TaxRate", "0.0"))
                            item_tax_amount = float(item.get("TaxAmount", "0.0"))

                            if math.isclose(tax_rate, 16.00, rel_tol=tolerance, abs_tol=tolerance):
                                sum_item_amounts_taxable_16_percent += item_amount
                            elif math.isclose(tax_rate, 0.00, rel_tol=tolerance, abs_tol=tolerance):
                                sum_item_amounts_zero_tax += item_amount

                            sum_all_item_tax_amounts += item_tax_amount

                        except (ValueError, TypeError):
                            malformed_item_found = True
                            break

                    if malformed_item_found:
                        # Clear the loading indicator line
                        sys.stdout.write('\r' + ' ' * 70 + '\r')
                        sys.stdout.flush()
                        print(f"❗ Skipping {filepath}: Malformed data found in item details.")
                        files_skipped += 1
                        continue
                    
                    # --- 3. Compare calculated sums to existing totals for verification ---
                    current_taxable_amount = float(total_taxable_amount_str)
                    current_tax_amount = float(total_tax_amount_str)
                    current_invoice_amount = float(total_invoice_amount_str)

                    expected_total_invoice_amount = sum_item_amounts_taxable_16_percent + sum_item_amounts_zero_tax + sum_all_item_tax_amounts
                    
                    has_discrepancy = (
                        not math.isclose(current_taxable_amount, sum_item_amounts_taxable_16_percent, rel_tol=tolerance, abs_tol=tolerance) or
                        not math.isclose(current_tax_amount, sum_all_item_tax_amounts, rel_tol=tolerance, abs_tol=tolerance) or
                        not math.isclose(current_invoice_amount, expected_total_invoice_amount, rel_tol=tolerance, abs_tol=tolerance)
                    )

                    # --- 4. If a discrepancy is found, correct and overwrite the file ---
                    if has_discrepancy:
                        # Correct parent fields
                        data["TotalTaxableAmount"] = f"{round(sum_item_amounts_taxable_16_percent, 2):.2f}"
                        data["TotalTaxAmount"] = f"{round(sum_all_item_tax_amounts, 2):.2f}"
                        data["TotalInvoiceAmount"] = f"{round(expected_total_invoice_amount, 2):.2f}"

                        # Overwrite the file with the corrected, unformatted JSON
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, separators=(',', ':'))  # No indent=4 to keep it on one line

                        files_corrected += 1
                        
                        # Clear the loading indicator line
                        sys.stdout.write('\r' + ' ' * 70 + '\r')
                        sys.stdout.flush()
                        print(f"✅ Corrected {filepath} with new totals.")

                except (json.JSONDecodeError, ValueError, Exception) as e:
                    # Clear the loading indicator line
                    sys.stdout.write('\r' + ' ' * 70 + '\r')
                    sys.stdout.flush()
                    print(f"❌ Failed to process {filepath}: {e}")
                    files_skipped += 1
                    continue
    
    # Final clear of the loading line before printing the final summary
    sys.stdout.write('\r' + ' ' * 70 + '\r')
    sys.stdout.flush()

    print(f"\nCorrection Complete.")
    print(f"Total files processed: {files_processed}")
    print(f"Total files corrected: {files_corrected} 🎉")
    print(f"Total files skipped due to errors: {files_skipped} ❗")
    print(f"Total files verified as correct (no action taken): {files_processed - files_corrected - files_skipped} ✅")

# --- Main execution ---
if __name__ == "__main__":
    folder_to_correct = input("Enter the folder path containing the .txt invoice files to correct: ")
    correct_faulty_invoice_amounts(folder_to_correct)