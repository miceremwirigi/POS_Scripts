import os
import json
import re  # Import the regular expression module

def read_json_from_file(file_path):
    """Reads JSON data from a file and returns it as a dictionary."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file: {file_path}")
        return None

def main():
    """Main function to loop through files and compare invoice data."""
    directory = r"C:\Users\HP\Desktop\scripts\exceltxt"  # Replace with your directory path
    invoice_directory = r"C:\Users\HP\Desktop\backups\july\11072025\KRAMW017202207050334\JSON\Inv\1-100"  # Root directory for related files
    zeroTaxErrorCount = 0

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            data1 = read_json_from_file(file_path)

            if data1:
                relevant_invoice_number = data1.get("RelevantInvoiceNumber", "")
                tax_amount1 = data1.get("TotalTaxAmount", None)

                if relevant_invoice_number:
                    # Extract the last digits after the zeros using regular expression
                    match = re.search(r"000*(\d+)$", relevant_invoice_number)
                    if match:
                        related_file_name = match.group(1) + ".txt"
                        related_file_path = os.path.join(invoice_directory, related_file_name)
                        data2 = read_json_from_file(related_file_path)

                        if data2:
                            trader_system_invoice_number = data2.get("TraderSystemInvoiceNumber", "")
                            tax_amount2 = data2.get("TotalTaxAmount", None)

                            if trader_system_invoice_number and relevant_invoice_number.endswith(trader_system_invoice_number) and tax_amount1 == tax_amount2:
                                print(f"Match found for {filename}:")
                                print(f"  RelevantInvoiceNumber ({filename}): {relevant_invoice_number}")
                                print(f"  TraderSystemInvoiceNumber ({related_file_name}): {trader_system_invoice_number}")
                                print(f"  TaxAmount ({filename}): {tax_amount1}")
                                print(f"  TaxAmount ({related_file_name}): {tax_amount2}")
                            else:
                                print(f"Mismatch found for {filename}:")
                                print(f"  RelevantInvoiceNumber ({filename}): {relevant_invoice_number}")
                                print(f"  TraderSystemInvoiceNumber ({related_file_name}): {trader_system_invoice_number}")
                                print(f"  TaxAmount ({filename}): {tax_amount1}")
                                print(f"  TaxAmount ({related_file_name}): {tax_amount2}")
                                if tax_amount1 == "0.00" or tax_amount2 == "0.00":
                                    zeroTaxErrorCount += 1
                                    print(f"Zero tax error found in {filename} or {related_file_name}")
                        else:
                            print(f"Could not read related file: {related_file_path}")
                    else:
                        print(f"Could not extract digits from RelevantInvoiceNumber in {filename}")
                else:
                    print(f"RelevantInvoiceNumber not found in {filename}")    
    print(f".... Total zero tax errors: {zeroTaxErrorCount} ....")
if __name__ == "__main__":
    main()