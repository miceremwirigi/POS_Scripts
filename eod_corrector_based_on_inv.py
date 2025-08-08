import json
import os
import sys
import logging
from collections import defaultdict
import time
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Fixed suffix for the HASH field, as identified from the examples.
# This should not change.
HASH_SUFFIX = "A001579204VKRAMW017202208137251"

def process_backup_directory(backup_dir_path):
    """
    Processes all JSON files in the given backup directory, focusing on "Inv" and "End"
    subfolders within the "JSON" folder.

    Args:
        backup_dir_path (str): The path to the backup directory.

    Returns:
        tuple: A tuple containing two dictionaries:
            - receipts_by_date (dict): Receipts data, organized by date.
            - eod_reports_by_date (dict): EOD reports data and file paths, organized by date.
    """
    receipts_by_date = defaultdict(list)
    eod_reports_by_date = {}
    animation = "|/-\\"
    idx = 0

    print("Counting files to process...")
    total_files = sum(len([f for f in files if f.endswith(".txt")])
                      for root, _, files in os.walk(backup_dir_path)
                      if "JSON" in root and ("Inv" in root or "End" in root))

    if total_files == 0:
        print("No files found to process.")
        return receipts_by_date, eod_reports_by_date

    processed_files = 0
    start_time = time.time()

    for root, _, files in os.walk(backup_dir_path):
        if "JSON" in root:
            if "Inv" in root:
                for filename in files:
                    if filename.endswith(".txt"):
                        filepath = os.path.join(root, filename)
                        processed_files += 1
                        idx = (idx + 1) % len(animation)
                        loading_animation = animation[idx]
                        progress_percent = (processed_files / total_files) * 100
                        print(f"\rProcessing [{progress_percent:6.2f}%] {loading_animation} File: {filename}", end="")
                        sys.stdout.flush()

                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                invoice_date = data.get("InvoiceDate")
                                if invoice_date:
                                    date = invoice_date[:10]
                                    receipts_by_date[date].append(data)
                        except Exception as e:
                            logging.error(f"Error processing receipt file {filename}: {e}")

            elif "End" in root:
                for filename in files:
                    if filename.endswith(".txt"):
                        filepath = os.path.join(root, filename)
                        processed_files += 1
                        idx = (idx + 1) % len(animation)
                        loading_animation = animation[idx]
                        progress_percent = (processed_files / total_files) * 100
                        print(f"\rProcessing [{progress_percent:6.2f}%] {loading_animation} File: {filename}", end="")
                        sys.stdout.flush()

                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                eod_data = data.get("REQUEST", {}).get("EODSummaryHeader", {})
                                date_of_eod = eod_data.get("DateOfEODSummary")
                                if date_of_eod:
                                    if date_of_eod in eod_reports_by_date:
                                        logging.warning(f"Multiple EOD reports found for {date_of_eod}. Using the last one.")
                                    eod_reports_by_date[date_of_eod] = {'data': data, 'filepath': filepath}
                        except Exception as e:
                            logging.error(f"Error processing EOD report file {filename}: {e}")

    print("\nFile processing complete.")
    return receipts_by_date, eod_reports_by_date

def generate_corrected_eod(receipts_by_date, eod_reports_by_date):
    """
    Generates and saves corrected EOD reports for dates with discrepancies.
    Deletes the backup file upon successful correction.

    Args:
        receipts_by_date (dict): Receipts data, organized by date.
        eod_reports_by_date (dict): EOD reports data and file paths, organized by date.
    """
    all_dates = set(receipts_by_date.keys()).union(eod_reports_by_date.keys())
    corrected_files_count = 0

    if not all_dates:
        print("No data found to reconcile.")
        return

    print("\nStarting EOD reconciliation and correction...")

    sorted_dates = sorted(list(all_dates))

    last_transmission_number = None

    for date in sorted_dates:
        receipts = receipts_by_date.get(date, [])
        eod_report = eod_reports_by_date.get(date)

        if not eod_report:
            logging.info(f"No EOD report found for date {date}. Skipping correction.")
            # We cannot continue the sequence without a previous value, so we reset.
            last_transmission_number = None
            continue

        original_eod_full_data = eod_report['data']
        original_eod_header = original_eod_full_data.get("REQUEST", {}).get("EODSummaryHeader", {})
        eod_filepath = eod_report['filepath']
        
        # Calculate correct totals from receipts
        correct_invoice_count = len(receipts)
        correct_taxable_amount = sum(float(receipt.get("TotalTaxableAmount", 0)) for receipt in receipts)
        correct_tax_amount = sum(float(receipt.get("TotalTaxAmount", 0)) for receipt in receipts)
        correct_total_amount = sum(float(receipt.get("TotalInvoiceAmount", 0)) for receipt in receipts)
        
        # Determine the correct DateOfTransmission
        eod_total_amount = float(original_eod_header.get("TotalInoviceAmountOfTheDay", 0))
        original_transmission_number = int(original_eod_header.get("DateOfTransmission", "0"))

        new_transmission_number = 0
        if last_transmission_number is None:
            # If it's the first date, use its original transmission number
            new_transmission_number = original_transmission_number
        else:
            # Otherwise, use the new rule
            new_transmission_number = last_transmission_number + correct_invoice_count

        # Update last_transmission_number for the next iteration
        last_transmission_number = new_transmission_number

        # Check for discrepancy in any field (totals or DateOfTransmission)
        discrepancy_found = abs(correct_total_amount - eod_total_amount) > 0.01 or \
                            new_transmission_number != original_transmission_number

        if discrepancy_found:
            print(f"Discrepancy found for {date}. Correcting EOD file...")

            backup_filepath = eod_filepath + ".bak"
            shutil.copyfile(eod_filepath, backup_filepath)
            print(f"  --> Original file backed up to: {backup_filepath}")

            date_part = date.replace("-", "")
            new_hash = f"A{date_part}{correct_invoice_count}{HASH_SUFFIX}"

            corrected_eod_header = original_eod_header.copy()
            corrected_eod_header["NumberOfInvoicesSentOfTheDay"] = str(correct_invoice_count)
            corrected_eod_header["TotalTaxableAmountOfTheDay"] = f"{correct_taxable_amount:.2f}"
            corrected_eod_header["TotalTaxAmountOfTheDay"] = f"{correct_tax_amount:.2f}"
            corrected_eod_header["TotalInoviceAmountOfTheDay"] = f"{correct_total_amount:.2f}"
            corrected_eod_header["DateOfTransmission"] = str(new_transmission_number)

            corrected_eod_full_data = {
                "REQUEST": {
                    "HASH": new_hash,
                    "EODSummaryHeader": corrected_eod_header
                }
            }
            
            try:
                with open(eod_filepath, 'w', encoding='utf-8') as f:
                    json.dump(corrected_eod_full_data, f, separators=(',', ':'))
                
                os.remove(backup_filepath)
                print(f"  --> Successfully corrected and saved file for {date}: {eod_filepath}")
                print(f"  --> Backup file deleted.")
                corrected_files_count += 1
            except Exception as e:
                logging.error(f"Error writing corrected EOD file for {date}: {e}")
        else:
            print(f"No discrepancy for {date}. No action needed.")

    print(f"\nReconciliation and correction complete. Corrected {corrected_files_count} files.")


def main():
    print("EOD Reconciliation and Correction Tool")
    print("-" * 50)

    if len(sys.argv) > 1:
        backup_dir_path = sys.argv[1]
    else:
        backup_dir_path = input("Enter the path to your backup directory: ")

    if not os.path.isdir(backup_dir_path):
        print("Error: The provided path is not a valid directory.")
        return

    print("\nProcessing files...")
    receipts_by_date, eod_reports_by_date = process_backup_directory(backup_dir_path)

    if not receipts_by_date and not eod_reports_by_date:
        print("Could not find sufficient data to reconcile.")
        return

    generate_corrected_eod(receipts_by_date, eod_reports_by_date)

    print("\n" + "=" * 50)
    print("Process finished.")
    print("=" * 50)

if __name__ == "__main__":
    main()