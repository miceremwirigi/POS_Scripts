import json
import os
import sys
import logging
from collections import defaultdict
import shutil
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Fixed suffix for the HASH field, as identified from the examples.
HASH_SUFFIX = "P051507499ZKRAMW017202207095019"
PIN_OF_SUPPLIER = "P051507499Z"

def process_backup_directory(backup_dir_path):
    """
    Processes all JSON files in the given backup directory, focusing on "Inv" and "End"
    subfolders within the "JSON" folder.
    """
    receipts_by_date = defaultdict(list)
    initial_eod_data = None
    eod_path = None
    
    # Pre-scan for folder paths
    for root, dirs, _ in os.walk(backup_dir_path):
        if "JSON" in root:
            if "Inv" in dirs:
                inv_path = os.path.join(root, "Inv")
            if "End" in dirs:
                eod_path = os.path.join(root, "End")
    
    if not inv_path or not eod_path:
        print("Error: 'JSON/Inv' or 'JSON/End' folder not found.")
        return receipts_by_date, None, None

    print("Processing all invoice and EOD files to gather data...")
    
    # Process Inv files
    for root, _, files in os.walk(inv_path):
        for filename in files:
            if filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        invoice_date = data.get("InvoiceDate")
                        if invoice_date:
                            date = invoice_date[:10]
                            receipts_by_date[date].append(data)
                except Exception as e:
                    logging.error(f"Error processing receipt file {filename}: {e}")
                    
    # Find the initial EOD file (1.txt) to get the starting date
    eod_1_path = os.path.join(eod_path, '1-100', '1.txt')
    if os.path.exists(eod_1_path):
        try:
            with open(eod_1_path, 'r', encoding='utf-8') as f:
                initial_eod_data = json.load(f)
                logging.info("Found initial EOD file (1.txt). Will use its date.")
        except Exception as e:
            logging.error(f"Error reading initial EOD file {eod_1_path}: {e}")
            initial_eod_data = None
    else:
        logging.warning("Initial EOD file (1.txt) not found. Will use the first invoice date as the starting date.")

    print("Data collection complete.")
    return receipts_by_date, initial_eod_data, eod_path

def generate_and_save_eods(receipts_by_date, initial_eod_data, eod_folder_path):
    """
    Generates a new, complete, and chronologically ordered set of EOD reports
    and saves them in the correct folder structure.
    """
    all_invoice_dates = sorted(list(receipts_by_date.keys()))
    
    if not all_invoice_dates:
        print("No invoice data found to generate EOD reports.")
        return
    
    # Determine the start date for the sequence
    start_date = None
    if initial_eod_data:
        eod_header = initial_eod_data.get("REQUEST", {}).get("EODSummaryHeader", {})
        start_date_str = eod_header.get("DateOfEODSummary")
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            logging.error("Initial EOD file is missing DateOfEODSummary. Defaulting to first invoice date.")
            start_date = datetime.strptime(all_invoice_dates[0], '%Y-%m-%d')
    else:
        start_date = datetime.strptime(all_invoice_dates[0], '%Y-%m-%d')
    
    end_date = datetime.strptime(all_invoice_dates[-1], '%Y-%m-%d')
    date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    
    # Delete all old EOD files and subfolders
    print("\nDeleting all old EOD files to start with a clean slate...")
    for root, dirs, files in os.walk(eod_folder_path, topdown=False):
        for file in files:
            if file.endswith('.txt'):
                os.remove(os.path.join(root, file))
        for dir_name in dirs:
            shutil.rmtree(os.path.join(root, dir_name))
    print("Old EOD files deleted.")

    print("\nGenerating new EOD reports in chronological order...")

    last_transmission_number = 0
    generated_files_count = 0
    
    for i, date_obj in enumerate(date_range):
        date_str = date_obj.strftime('%Y-%m-%d')
        receipts = receipts_by_date.get(date_str, [])
        
        # Calculate correct totals for the current day
        correct_invoice_count = len(receipts)
        correct_taxable_amount = sum(float(receipt.get("TotalTaxableAmount", 0)) for receipt in receipts)
        correct_tax_amount = sum(float(receipt.get("TotalTaxAmount", 0)) for receipt in receipts)
        correct_total_amount = sum(float(receipt.get("TotalInvoiceAmount", 0)) for receipt in receipts)

        # Determine the cumulative DateOfTransmission
        if i == 0:
            # First EOD report: 0 if no invoices, otherwise the count for the day
            new_transmission_number = correct_invoice_count
        else:
            # Subsequent EOD reports: cumulative sum
            new_transmission_number = last_transmission_number + correct_invoice_count

        # Build the new EOD JSON structure
        # The HASH now includes hyphens in the date to match the example
        new_hash = f"D{date_str}{correct_invoice_count}{HASH_SUFFIX}"

        new_eod_header = {
            "DateOfTransmission": str(new_transmission_number),
            "DateOfEODSummary": date_str,
            "PINOfSupplier": PIN_OF_SUPPLIER,
            "NumberOfInvoicesSentOfTheDay": str(correct_invoice_count),
            "TotalTaxableAmountOfTheDay": f"{correct_taxable_amount:.2f}",
            "TotalTaxAmountOfTheDay": f"{correct_tax_amount:.2f}",
            "TotalInoviceAmountOfTheDay": f"{correct_total_amount:.2f}"
        }
        
        new_eod_full_data = {
            "REQUEST": {
                "HASH": new_hash,
                "EODSummaryHeader": new_eod_header
            }
        }
        
        # Determine the file number and folder path
        file_number = i + 1
        folder_start = ((file_number - 1) // 100) * 100 + 1
        folder_end = folder_start + 99
        target_folder_name = f"{folder_start}-{folder_end}"
        target_folder_path = os.path.join(eod_folder_path, target_folder_name)
        os.makedirs(target_folder_path, exist_ok=True)
        
        eod_filepath = os.path.join(target_folder_path, f"{file_number}.txt")

        # Save the new EOD report
        try:
            with open(eod_filepath, 'w', encoding='utf-8') as f:
                json.dump(new_eod_full_data, f, separators=(',', ':'))
            generated_files_count += 1
            print(f"\rGenerated file {file_number}/{len(date_range)} for {date_str}", end="")
            sys.stdout.flush()
        except Exception as e:
            logging.error(f"\nError writing new EOD file for {date_str}: {e}")

        # Update last_transmission_number for the next iteration
        last_transmission_number = new_transmission_number
    
    print(f"\n\nGeneration complete. Successfully created {generated_files_count} new EOD files.")

def main():
    print("EOD Chronological Correction and Generation Tool")
    print("-" * 50)

    if len(sys.argv) > 1:
        backup_dir_path = sys.argv[1]
    else:
        backup_dir_path = input("Enter the path to your backup directory: ")

    if not os.path.isdir(backup_dir_path):
        print("Error: The provided path is not a valid directory.")
        return

    receipts_by_date, initial_eod_data, eod_path = process_backup_directory(backup_dir_path)

    if not receipts_by_date and not initial_eod_data:
        print("Could not find sufficient data (invoices or initial EOD report) to generate EOD reports.")
        return
    
    if not eod_path:
        print("Error: 'End' directory not found. Cannot save new EOD reports.")
        return

    generate_and_save_eods(receipts_by_date, initial_eod_data, eod_path)

    print("\n" + "=" * 50)
    print("Process finished.")
    print("=" * 50)

if __name__ == "__main__":
    main()