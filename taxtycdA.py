import os
import json

def process_invoices(folder_path):
    """
    Processes all .txt files in the given folder and its subfolders,
    correcting tax codes and verifying tax amounts, with progress printed to the terminal,
    and saves the output as unformatted JSON.
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

                    # Correct taxTyCd and calculate taxblAmtA
                    taxbl_amt_a_sum = 0.0
                    modified = False
                    for item in data['itemList']:
                        if item['taxTyCd'] == '0':
                            item['taxTyCd'] = 'A'
                            modified = True
                        if item['taxTyCd'] == 'A':
                            taxbl_amt_a_sum += float(item['taxblAmt'])

                    taxbl_amt_a_sum = round(taxbl_amt_a_sum, 2)
                    if data['taxblAmtA'] != taxbl_amt_a_sum:
                        data['taxblAmtA'] = taxbl_amt_a_sum
                        modified = True

                    # Write the modified data back to the file (unformatted)
                    if modified:
                        with open(file_path, 'w') as f:
                            json.dump(data, f)  # Removed indent parameter
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