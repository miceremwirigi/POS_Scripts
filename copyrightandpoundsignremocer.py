import os
import chardet

def remove_pound_and_copyright_signs_from_txt_files_in_folder(folder_path):
    """
    Removes pound signs (£), copyright signs (©), and trailing hash strings
    (e.g., '8fd5e82cdb4654cce896af9565294df3') that appear after the last '}'
    from all .txt files within a folder and its subfolders, treating them
    as plain text files. Automatically detects encoding for each file.

    Args:
        folder_path (str): The path to the folder to search.
    """

    # Check if the provided path is a valid directory
    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files in: {folder_path} and its subfolders")

    total_files_processed = 0
    files_modified_count = 0

    # Walk through the directory and its subdirectories
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            # Check if the file is a .txt file
            if file_name.endswith(".txt"):
                file_path = os.path.join(root, file_name)
                total_files_processed += 1
                print(f"Processing file: {file_path}")

                encoding = None  # Initialize encoding variable

                try:
                    # Detect the file encoding by reading in binary mode
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']
                        confidence = result['confidence']

                    # If encoding cannot be detected, skip the file
                    if encoding is None:
                        print(f"  --> Error: Could not detect encoding for '{file_path}'. Skipping file.")
                        continue

                    print(f"  --> Detected encoding: {encoding} (confidence: {confidence})")

                except FileNotFoundError:
                    print(f"  --> Error: File not found: {file_path}")
                    continue  # Skip to the next file if file not found
                except Exception as e:
                    print(f"  --> Error detecting encoding for '{file_path}': {e}. Skipping file.")
                    continue  # Skip to the next file for other encoding errors

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
                        cleaned_content = cleaned_content[:last_brace_index + 1]
                        print(f"  --> Removed trailing characters (hash) from '{file_path}'")
                    elif last_brace_index == -1:
                        # If '}' is not found, it might not be a JSON file, or it's malformed.
                        # In this case, we've only removed £ and ©.
                        print(f"  --> No closing '}}' found in '{file_path}'. No trailing hash removal attempted.")
                    # If last_brace_index != -1 but there's nothing after it, no hash to remove.

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
                    print(f"  --> An unexpected error occurred while processing '{file_path}': {e}")

                print("-" * 30) # Separator for readability between file processing

    print("\nProcessing completed.")
    print(f"Total files processed: {total_files_processed}")
    print(f"Files modified: {files_modified_count}")


if __name__ == "__main__":
    # Prompt the user to enter the folder path
    folder_path = input("Enter the full path to the folder containing .txt files: ")
    # Call the function to remove the signs and trailing hash
    remove_pound_and_copyright_signs_from_txt_files_in_folder(folder_path)
