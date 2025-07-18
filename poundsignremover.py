import os
import chardet

def remove_pound_signs_from_txt_files_in_folder(folder_path):
    """
    Removes pound signs (£) from all .txt files within a folder and its subfolders,
    treating them as plain text files.  Automatically detects encoding for each file.

    Args:
        folder_path (str): The path to the folder to search.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files in: {folder_path} and its subfolders")

    total_files_processed = 0
    files_modified_count = 0

    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".txt"):
                file_path = os.path.join(root, file_name)
                total_files_processed += 1
                print(f"Processing file: {file_path}")

                encoding = None  # Initialize encoding
                try:
                    # Detect the file encoding
                    with open(file_path, 'rb') as f:  # Open in binary mode for detection
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']
                        confidence = result['confidence']

                    if encoding is None:
                        print(f"  --> Error: Could not detect encoding for '{file_path}'. Skipping file.")
                        continue

                    print(f"  --> Detected encoding: {encoding} (confidence: {confidence})")

                except FileNotFoundError:
                    print(f"  --> Error: File not found: {file_path}")
                    continue  # Skip to the next file
                except Exception as e:
                    print(f"  --> Error detecting encoding: {e}")
                    continue # Skip to the next file

                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()

                    # Remove pound signs
                    cleaned_content = content.replace('£', '')

                    # Write the cleaned content back to the file, using the detected encoding
                    with open(file_path, 'w', encoding=encoding) as f:
                        f.write(cleaned_content)

                    files_modified_count += 1
                    print(f"  --> Successfully removed pound signs from '{file_path}'")

                except FileNotFoundError:
                    print(f"  --> Error: File not found: {file_path}") #Redundant, but kept for clarity
                except UnicodeDecodeError as e:
                    print(f"  --> Error decoding file with {encoding} encoding: {e}")
                    print("  --> The detected encoding may be incorrect.  Consider manual inspection.")
                except Exception as e:
                    print(f"  --> An unexpected error occurred: {e}")


                print("-" * 30)

    print("\nProcessing completed.")
    print(f"Total files processed: {total_files_processed}")
    print(f"Files modified: {files_modified_count}")


if __name__ == "__main__":
    folder_path = input("Enter the full path to the folder: ")
    remove_pound_signs_from_txt_files_in_folder(folder_path)