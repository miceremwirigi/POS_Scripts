# Sales Report Reconciliation Tool

A Python script for matching End of Day (EOD) sales reports with corresponding receipt totals.

## Purpose

This tool helps reconcile financial data by:
1. Scanning through backup directories
2. Parsing receipt files and EOD report files
3. Organizing receipts by date and calculating totals
4. Comparing with EOD summary reports to identify discrepancies
5. Generating a detailed reconciliation report

## Usage

```
python match_sales_reports.py [backup_directory_path]
```

Example:
```
python match_sales_reports.py "C:\Users\HP\Desktop\backups"
```

If no path is provided when running the script, you will be prompted to enter one.

## Report Information

The script generates a comprehensive report that includes:

- Analysis by date
- Invoice counts
- Taxable amounts
- Tax amounts
- Total invoice amounts
- Clear indicators for matches and discrepancies
- File paths for investigating issues

The report is both displayed in the console and saved as a text file named `sales_reconciliation_report.txt`.

## Requirements

- Python 3.6 or higher
- No external dependencies required (uses only standard library)

## File Structure

The script expects to find files in this structure:
- `[backup_directory]\...\[terminal_folder]\JSON\Inv\[range]\[receipt_number].txt`  
- `[backup_directory]\...\[terminal_folder]\JSON\End\[range]\[report_number].txt`

Where `[terminal_folder]` contains "KRAMW" in its name.