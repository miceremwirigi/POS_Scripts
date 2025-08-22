import os
import json
import sys

def find_and_fix_reset():
    """
    Detects and fixes a TotRcptNo reset using the formula: last_valid_value + existing_value + 1.
    Writes the corrected JSON to the file without any spacing or indentation.
    """
    root_folder = input("Please enter the full path to the JSON folder (e.g., C:\\Users\\HP\\Desktop\\Temp\\DEJA012202500072\\JSON): ")
    inv_folder = os.path.join(root_folder, 'Inv_New')

    if not os.path.isdir(inv_folder):
        print(f"Error: 'Inv_New' folder not found at {inv_folder}. Please check the path and try again.")
        return

    files = []
    for subfolder_root, _, filenames in os.walk(inv_folder):
        for filename in filenames:
            if filename.endswith('.txt') and filename.startswith('1'):
                files.append(os.path.join(subfolder_root, filename))
    files.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))

    if not files:
        print("No invoice files found in the 'Inv_New' folder.")
        return

    last_valid_tot_rcpt_no = -1
    modified_count = 0
    total_files = len(files)

    print("\nProcessing files...")

    for i, file_path in enumerate(files):
        sys.stdout.write(f"\r  Processing file {i + 1}/{total_files}: {os.path.basename(file_path)}")
        sys.stdout.flush()

        with open(file_path, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                sys.stdout.write(f"\rError decoding JSON in {os.path.basename(file_path)}. Skipping file.      \n")
                sys.stdout.flush()
                continue

        if 'receipt' in data and 'totRcptNo' in data['receipt']:
            current_tot_rcpt_no = data['receipt']['totRcptNo']

            if last_valid_tot_rcpt_no == -1:
                last_valid_tot_rcpt_no = current_tot_rcpt_no
                continue
            
            if current_tot_rcpt_no != last_valid_tot_rcpt_no + 1:
                if current_tot_rcpt_no < last_valid_tot_rcpt_no:
                    new_tot_rcpt_no = last_valid_tot_rcpt_no + current_tot_rcpt_no + 1
                    data['receipt']['totRcptNo'] = new_tot_rcpt_no
                    
                    # Key change: no indent and compact separators
                    with open(file_path, 'w') as f:
                        json.dump(data, f, separators=(',', ':'))
                    
                    modified_count += 1
                    last_valid_tot_rcpt_no = new_tot_rcpt_no
                else:
                    last_valid_tot_rcpt_no = current_tot_rcpt_no
            else:
                last_valid_tot_rcpt_no = current_tot_rcpt_no

    print("\n\n--- Process Complete ---")
    if modified_count > 0:
        print(f"Successfully fixed {modified_count} file(s).")
    else:
        print("No files were modified. No receipt number resets were detected.")

if __name__ == "__main__":
    find_and_fix_reset()