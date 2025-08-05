import os
import json
import sys
import re
from datetime import date, timedelta
from collections import defaultdict

def get_end_files_sorted(end_folder):
    """Retrieves and sorts End files numerically."""
    file_list = []
    for root, _, files in os.walk(end_folder):
        for filename in files:
            if filename.endswith('.txt'):
                try:
                    num = int(re.search(r'(\d+)\.txt$', filename).group(1))
                    file_list.append((num, os.path.join(root, filename)))
                except (AttributeError, ValueError):
                    print(f"Warning: Skipping file '{filename}' due to non-numeric name.")
    return [path for num, path in sorted(file_list)]

def correct_end_files(base_path):
    """
    Corrects End files based on the corresponding Inv files, handling empty
    and malformed JSON files by inferring the date and invoice details.

    Args:
        base_path (str): The base directory containing the 'JSON' folder.
    """
    json_folder = os.path.join(base_path, 'JSON')
    end_folder = os.path.join(json_folder, 'End')
    inv_folder = os.path.join(json_folder, 'Inv')

    if not os.path.exists(end_folder) or not os.path.exists(inv_folder):
        print(f"Error: The 'JSON/End' or 'JSON/Inv' folders were not found in {base_path}.")
        return

    # Step 1: Process all 'Inv' files to aggregate totals and invoice numbers by date
    inv_files = [os.path.join(root, f) for root, _, files in os.walk(inv_folder) for f in files if f.endswith('.txt')]
    inv_daily_data = defaultdict(lambda: {'TotalTaxableAmount': 0.0, 'TotalTaxAmount': 0.0, 'TotalInvoiceAmount': 0.0, 'InvoiceCount': 0, 'MaxInvoiceNum': 0})

    print("\nProcessing 'Inv' files...")
    total_inv_files = len(inv_files)
    animation_chars = ['|', '/', '-', '\\']
    
    # Store all inv dates and max invoice numbers to find the last available one
    all_inv_dates = []

    for i, file_path in enumerate(inv_files):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
                    invoice_date_full = data.get('InvoiceDate', '').split('T')[0]
                    if invoice_date_full:
                        taxable_amount = float(data.get('TotalTaxableAmount', '0.0'))
                        tax_amount = float(data.get('TotalTaxAmount', '0.0'))
                        total_amount = float(data.get('TotalInvoiceAmount', '0.0'))
                        invoice_number = int(data.get('TraderSystemInvoiceNumber', '0'))
                        
                        inv_daily_data[invoice_date_full]['TotalTaxableAmount'] += taxable_amount
                        inv_daily_data[invoice_date_full]['TotalTaxAmount'] += tax_amount
                        inv_daily_data[invoice_date_full]['TotalInvoiceAmount'] += total_amount
                        inv_daily_data[invoice_date_full]['InvoiceCount'] += 1
                        inv_daily_data[invoice_date_full]['MaxInvoiceNum'] = max(inv_daily_data[invoice_date_full]['MaxInvoiceNum'], invoice_number)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        animation_char = animation_chars[i % len(animation_chars)]
        sys.stdout.write(f"\r{animation_char} Processed {i+1}/{total_inv_files} 'Inv' files...")
        sys.stdout.flush()
    sys.stdout.write("\n")

    # Step 2: Process 'End' files and correct them
    print("Processing and correcting 'End' files...")
    corrected_files = []
    end_files_sorted = get_end_files_sorted(end_folder)
    total_end_files = len(end_files_sorted)
    
    last_valid_date = None
    last_available_invoice_num = "0"
    sorted_inv_dates = sorted(inv_daily_data.keys())

    def get_last_invoice_num(target_date_str):
        nonlocal last_available_invoice_num
        target_date = date.fromisoformat(target_date_str)
        
        # Find the most recent date with sales before or on the target date
        for inv_date_str in reversed(sorted_inv_dates):
            inv_date = date.fromisoformat(inv_date_str)
            if inv_date <= target_date:
                return str(inv_daily_data[inv_date_str]['MaxInvoiceNum'])
        return "0"

    for i, file_path in enumerate(end_files_sorted):
        filename = os.path.basename(file_path)
        content = ""
        is_empty = False
        is_malformed = False
        eod_date = None
        end_data = None
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            if not content.strip():
                is_empty = True
            else:
                end_data = json.loads(content)
                current_date_str = end_data.get('REQUEST', {}).get('EODSummaryHeader', {}).get('DateOfEODSummary')
                if current_date_str:
                    last_valid_date = date.fromisoformat(current_date_str)
        except json.JSONDecodeError:
            is_malformed = True
            
        # Determine the date for the current file
        if not is_empty and not is_malformed and last_valid_date:
            eod_date = last_valid_date.isoformat()
        elif last_valid_date:
            last_valid_date += timedelta(days=1)
            eod_date = last_valid_date.isoformat()
        else:
            sys.stdout.write(f"\rSkipping {filename}: no previous date to infer from. Please ensure the first file is valid.\n")
            sys.stdout.flush()
            continue

        if eod_date:
            daily_inv_data = inv_daily_data.get(eod_date, {'TotalTaxableAmount': 0.0, 'TotalTaxAmount': 0.0, 'TotalInvoiceAmount': 0.0, 'InvoiceCount': 0, 'MaxInvoiceNum': 0})
            
            correct_taxable = daily_inv_data['TotalTaxableAmount']
            correct_tax = daily_inv_data['TotalTaxAmount']
            correct_total = daily_inv_data['TotalInvoiceAmount']
            correct_invoice_count = str(daily_inv_data['InvoiceCount'])
            correct_max_invoice_num = get_last_invoice_num(eod_date)

            correction_needed = False
            correction_reason = ""
            if is_empty:
                correction_needed = True
                correction_reason = "Empty file fixed."
            elif is_malformed:
                correction_needed = True
                correction_reason = "Malformed file fixed."
            else:
                current_totals = end_data['REQUEST']['EODSummaryHeader']
                current_taxable = float(current_totals.get('TotalTaxableAmountOfTheDay', '0.0'))
                current_tax = float(current_totals.get('TotalTaxAmountOfTheDay', '0.0'))
                current_total = float(current_totals.get('TotalInoviceAmountOfTheDay', '0.0'))
                current_invoice_count = current_totals.get('NumberOfInvoicesSentOfTheDay', '0')
                current_max_invoice_num = current_totals.get('DateOfTransmission', '0')
                
                if (abs(current_taxable - correct_taxable) > 1e-6 or
                    abs(current_tax - correct_tax) > 1e-6 or
                    abs(current_total - correct_total) > 1e-6 or
                    current_invoice_count != correct_invoice_count or
                    current_max_invoice_num != correct_max_invoice_num):
                    correction_needed = True
                    correction_reason = "Incorrect totals/details fixed."
            
            if correction_needed:
                corrected_data = {
                    "REQUEST": {
                        "HASH": f"D{eod_date}0A004706464FKRAMW017202207095777",
                        "EODSummaryHeader": {
                            "DateOfTransmission": correct_max_invoice_num,
                            "DateOfEODSummary": eod_date,
                            "PINOfSupplier": "A004706464F",
                            "NumberOfInvoicesSentOfTheDay": correct_invoice_count,
                            "TotalTaxableAmountOfTheDay": f"{correct_taxable:.2f}",
                            "TotalTaxAmountOfTheDay": f"{correct_tax:.2f}",
                            "TotalInoviceAmountOfTheDay": f"{correct_total:.2f}"
                        }
                    }
                }

                with open(file_path, 'w') as out_f:
                    json.dump(corrected_data, out_f, separators=(',', ':'))
                corrected_files.append((file_path, (correct_taxable, correct_tax, correct_total), correction_reason))

        animation_char = animation_chars[i % len(animation_chars)]
        sys.stdout.write(f"\r{animation_char} Processed {i+1}/{total_end_files} 'End' files...")
        sys.stdout.flush()

    sys.stdout.write("\n")

    # Step 3: Print a summary
    print("\n--- Correction Summary ---")
    if corrected_files:
        print("The following 'End' files were corrected:")
        for path, (taxable, tax, total), reason in corrected_files:
            print(f"  - {path} ({reason}): New Totals -> Taxable: {taxable:.2f}, Tax: {tax:.2f}, Total: {total:.2f}")
    else:
        print("No 'End' files required correction.")


def main():
    """
    Main function to get user input and run the correction script.
    """
    print("Welcome to the Sales Data Corrector.")
    print("This script will find and correct discrepancies between daily sales totals.")
    
    default_path = r"C:\Users\HP\Desktop\Temp\KRAMW017202207095777"
    user_input = input(f"Please enter the parent directory path (e.g., '{default_path}'): ").strip()
    
    base_directory = user_input if user_input else default_path
    
    if not os.path.exists(base_directory):
        print(f"Error: The specified path does not exist. Please check the path and try again.")
        return
        
    print(f"\nSearching for 'JSON' folder in: {base_directory}")
    correct_end_files(base_directory)

if __name__ == "__main__":
    main()