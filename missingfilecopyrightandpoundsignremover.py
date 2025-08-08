import os
import shutil # New import for file copying
import chardet

def restore_and_clean_txt_files(main_folder_path, backup_folder_path):
    """
    Restores missing .txt files from a backup folder to the main folder,
    starting only from a specified file number (e.g., 66670.txt).
    Then, for all .txt files in the main folder (including restored ones),
    it removes pound signs (£), copyright signs (©), and trailing hash strings.
    Automatically detects encoding for each file.

    Args:
        main_folder_path (str): The path to the main folder where files should exist and be cleaned.
        backup_folder_path (str): The path to the backup folder containing the source of truth files.
    """

    # Validate main folder path
    if not os.path.isdir(main_folder_path):
        print(f"Error: The main folder path '{main_folder_path}' is not a valid directory.")
        return
    # Validate backup folder path
    if not os.path.isdir(backup_folder_path):
        print(f"Error: The backup folder path '{backup_folder_path}' is not a valid directory.")
        return

    print(f"Starting selective restoration and cleaning process:")
    print(f"  Main folder: {main_folder_path}")
    print(f"  Backup folder: {backup_folder_path}")
    print("-" * 50)

    total_files_processed = 0
    files_modified_count = 0
    files_restored_count = 0

    # Define the starting point for restoration (the invoice number from which to start restoring)
    START_INV_NO_FOR_RESTORATION = 66670

    # Phase 1: Iterate through the backup directory to find and selectively restore missing files
    print(f"\nPhase 1: Identifying and selectively restoring missing files from backup (starting from {START_INV_NO_FOR_RESTORATION}.txt)...")
    for root_backup, _, files_backup in os.walk(backup_folder_path):
        for file_name in files_backup:
            if file_name.endswith(".txt"):
                # Extract the invoice number from the file name (e.g., '66670' from '66670.txt')
                try:
                    invoice_number_str = os.path.splitext(file_name)[0]
                    current_invoice_number = int(invoice_number_str)
                except ValueError:
                    print(f"  --> Warning: Could not parse invoice number from file name '{file_name}'. Skipping restoration check for this file.")
                    continue # Skip this file if its name isn't a simple number.txt

                # Only proceed with restoration if the current file's invoice number is >= the start number
                if current_invoice_number >= START_INV_NO_FOR_RESTORATION:
                    backup_file_path = os.path.join(root_backup, file_name)
                    # Calculate the relative path from the backup folder
                    relative_path = os.path.relpath(backup_file_path, backup_folder_path)
                    # Construct the corresponding path in the main folder
                    main_file_path = os.path.join(main_folder_path, relative_path)

                    if not os.path.exists(main_file_path):
                        print(f"  --> Missing file detected and within restoration range: '{main_file_path}'")
                        try:
                            # Ensure the directory structure exists in the main folder
                            os.makedirs(os.path.dirname(main_file_path), exist_ok=True)
                            # Copy the file from backup to the main location
                            shutil.copy2(backup_file_path, main_file_path)
                            files_restored_count += 1
                            print(f"  --> Successfully restored '{file_name}' from backup to '{main_file_path}'")
                        except Exception as e:
                            print(f"  --> Error restoring '{file_name}' to '{main_file_path}': {e}")
                # else:
                #     print(f"  --> Skipping '{file_name}' (invoice number {current_invoice_number} is below {START_INV_NO_FOR_RESTORATION})")


    print("\nPhase 2: Cleaning all .txt files in the main folder (including restored ones)...")
    # Second pass: Iterate through the main directory (which now includes restored files) for cleaning
    for root_main, _, files_main in os.walk(main_folder_path):
        for file_name in files_main:
            if file_name.endswith(".txt"):
                file_path = os.path.join(root_main, file_name)
                total_files_processed += 1
                print(f"Processing file for cleaning: {file_path}")

                encoding = None # Initialize encoding variable

                try:
                    # Detect the file encoding by reading in binary mode
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']
                        confidence = result['confidence']

                    # If encoding cannot be detected, skip the file
                    if encoding is None:
                        print(f"  --> Error: Could not detect encoding for '{file_path}'. Skipping cleaning.")
                        continue

                    print(f"  --> Detected encoding: {encoding} (confidence: {confidence})")

                except FileNotFoundError:
                    # This should ideally not happen after restoration, but good for robustness
                    print(f"  --> Error: File not found during cleaning: {file_path}. Skipping cleaning.")
                    continue
                except Exception as e:
                    print(f"  --> Error detecting encoding for '{file_path}': {e}. Skipping cleaning.")
                    continue

                try:
                    # Read the file content using the detected encoding
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()

                    # --- Start of modifications for removing hash and existing special characters ---

                    # First, remove pound signs (£) and copyright signs (©)
                    # The replace method is chained to remove both characters
                    cleaned_content = content.replace('£', '').replace('©', '')

                    # Find the last occurrence of '}' in the cleaned content
                    # This assumes the hash always follows the JSON structure
                    last_brace_index = cleaned_content.rfind('}')

                    # If '}' is found and there are characters after it,
                    # slice the string to remove everything after the last '}'
                    if last_brace_index != -1 and last_brace_index + 1 < len(cleaned_content):
                        # Ensure we don't accidentally cut valid JSON if '}' is not the last character
                        # and there's just whitespace or a newline, not a hash.
                        # We'll be more robust by stripping whitespace before checking for hash-like content
                        potential_hash_segment = cleaned_content[last_brace_index + 1:].strip()
                        # Check if the stripped segment after '}' looks like a hash (e.g., alphanumeric)
                        # A simple check for now: if it's not empty and contains only hex chars or digits
                        if potential_hash_segment and all(c.isalnum() for c in potential_hash_segment):
                             cleaned_content = cleaned_content[:last_brace_index + 1]
                             print(f"  --> Removed trailing characters (hash) from '{file_path}'")
                        elif potential_hash_segment:
                             print(f"  --> Trailing non-hash characters found after '}}' in '{file_path}'. Not removed.")
                    elif last_brace_index == -1:
                        # If '}' is not found, it might not be a JSON file, or it's malformed.
                        # In this case, we've only removed £ and ©.
                        print(f"  --> No closing '}}' found in '{file_path}'. No trailing hash removal attempted.")

                    # --- End of modifications ---

                    # Write the cleaned content back to the file, using the detected encoding
                    # Only write if there was a change to prevent unnecessary file writes
                    if content != cleaned_content:
                        with open(file_path, 'w', encoding=encoding) as f:
                            f.write(cleaned_content)
                        files_modified_count += 1
                        print(f"  --> Content modified and saved for '{file_path}'")
                    else:
                        print(f"  --> No changes needed for '{file_path}' (pound/copyright signs or hash not found).")

                except UnicodeDecodeError as e:
                    print(f"  --> Error decoding file '{file_path}' with {encoding} encoding: {e}")
                    print("  --> The detected encoding may be incorrect. Consider manual inspection.")
                except Exception as e:
                    print(f"  --> An unexpected error occurred while cleaning '{file_path}': {e}")

                print("-" * 30) # Separator for readability between file processing

    print("\nProcessing completed.")
    print(f"Total files processed for cleaning: {total_files_processed}")
    print(f"Files modified (cleaned): {files_modified_count}")
    print(f"Files restored from backup: {files_restored_count}")


if __name__ == "__main__":
    main_folder = input("Enter the full path to the main folder (e.g., E:\\JSON\\InvNew\\): ")
    backup_folder = input("Enter the full path to the backup folder (e.g., C:\\Users\\HP\\Documents\\SELENITE SD BACKUP\\JSON\\InvNew\\): ")
    restore_and_clean_txt_files(main_folder, backup_folder)
