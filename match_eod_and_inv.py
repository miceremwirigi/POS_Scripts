import json
import os
import sys
import logging
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_backup_directory(backup_dir_path):
    """
    Processes all JSON files in the given backup directory, focusing on "Inv" and "End" subfolders within the "JSON" folder.

    Args:
        backup_dir_path (str): The path to the backup directory.

    Returns:
        tuple: A tuple containing two dictionaries:
            - receipts_by_date (dict): Receipts data, organized by date.
            - eod_reports_by_date (dict): EOD reports data, organized by date.
    """
    receipts_by_date = defaultdict(list)
    eod_reports_by_date = defaultdict(list)
    animation = "|/-\\"
    idx = 0

    total_files = 0
    for root, _, files in os.walk(backup_dir_path):
        if "JSON" in root:
            if "Inv" in root or "End" in root:
                total_files += len([f for f in files if f.endswith(".txt")])

    processed_files = 0

    for root, _, files in os.walk(backup_dir_path):
        if "JSON" in root:
            if "Inv" in root:
                for filename in files:
                    if filename.endswith(".txt"):
                        filepath = os.path.join(root, filename)
                        idx = (idx + 1) % len(animation)
                        loading_animation = animation[idx]
                        print(f"\rProcessing: {filename} {loading_animation}", end="")
                        sys.stdout.flush()

                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                invoice_date = data.get("InvoiceDate")
                                if invoice_date:
                                    date = invoice_date[:10]  # Extract date part
                                    receipts_by_date[date].append(data)
                            processed_files += 1
                        except Exception as e:
                            logging.error(f"Error processing receipt file {filename}: {e}")
                        time.sleep(0.1)  # Add a small delay to control animation speed
            elif "End" in root:
                for filename in files:
                    if filename.endswith(".txt"):
                        filepath = os.path.join(root, filename)
                        idx = (idx + 1) % len(animation)
                        loading_animation = animation[idx]
                        print(f"\rProcessing: {filename} {loading_animation}", end="")
                        sys.stdout.flush()

                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                eod_data = data.get("REQUEST", {}).get("EODSummaryHeader", {})
                                date_of_eod = eod_data.get("DateOfEODSummary")
                                if date_of_eod:
                                    eod_reports_by_date[date_of_eod].append(eod_data)
                            processed_files += 1
                        except Exception as e:
                            logging.error(f"Error processing EOD report file {filename}: {e}")
                        time.sleep(0.1)  # Add a small delay to control animation speed

    print("\nFile processing complete.")  # Print a newline after the animation

    return receipts_by_date, eod_reports_by_date


def compare_and_report(receipts_by_date, eod_reports_by_date):
    """
    Compares receipts and EOD reports data and generates a detailed report.

    Args:
        receipts_by_date (dict): Receipts data, organized by date.
        eod_reports_by_date (dict): EOD reports data, organized by date.

    Returns:
        str: A report string summarizing the comparison results.
    """
    report_lines = ["Sales Reconciliation Report\n", "-" * 30 + "\n"]

    all_dates = set(receipts_by_date.keys()).union(eod_reports_by_date.keys())

    for date in sorted(all_dates):
        report_lines.append(f"Date: {date}\n")

        receipts = receipts_by_date.get(date, [])
        eod_reports = eod_reports_by_date.get(date, [])

        total_receipts = sum(float(receipt.get("TotalInvoiceAmount", 0)) for receipt in receipts)
        total_eod = 0
        if eod_reports:  # Ensure there are EOD reports for the date
            total_eod = float(eod_reports[0].get("TotalInoviceAmountOfTheDay", 0))

        # Extracting more details from receipts
        invoice_count = len(receipts)
        taxable_amount = sum(float(receipt.get("TotalTaxableAmount", 0)) for receipt in receipts)
        tax_amount = sum(float(receipt.get("TotalTaxAmount", 0)) for receipt in receipts)

        report_lines.append(f"  Invoice Count: {invoice_count}\n")
        report_lines.append(f"  Taxable Amount: ${taxable_amount:.2f}\n")
        report_lines.append(f"  Tax Amount: ${tax_amount:.2f}\n")
        report_lines.append(f"  Total Receipts: ${total_receipts:.2f}\n")
        report_lines.append(f"  Total EOD Reports: ${total_eod:.2f}\n")

        difference = total_receipts - total_eod
        report_lines.append(f"  Difference: ${difference:.2f}\n")

        if abs(difference) > 0.01:  # Threshold for discrepancy
            report_lines.append("  DISCREPANCY FOUND!\n")

        report_lines.append("-" * 20 + "\n")

    return "".join(report_lines)


def main():
    print("Sales Report Reconciliation Tool (JSON Directory Version)")
    print("-" * 60)

    # Get backup directory path from user
    if len(sys.argv) > 1:
        backup_dir_path = sys.argv[1]
    else:
        backup_dir_path = input("Enter the path to your backup directory (e.g., C:\\Users\\HP\\Desktop\\backups): ")

    # Process backup directory
    print("\nProcessing files...")
    receipts_by_date, eod_reports_by_date = process_backup_directory(backup_dir_path)

    if not receipts_by_date and not eod_reports_by_date:
        print("Could not find sufficient data to generate a report.")
        return

    # Generate comparison report
    print("\nComparing data and generating report...")
    report = compare_and_report(receipts_by_date, eod_reports_by_date)

    # Save report to file
    report_file = "sales_reconciliation_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport generated successfully and saved to {report_file}")
    print("\n" + "=" * 50)
    print(report)
    print("=" * 50)


if __name__ == "__main__":
    main()