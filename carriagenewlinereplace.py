import os
import json

def process_text_files_as_json(folder_path):
    """
    Reads all .txt files in a folder, treats them as JSON, removes newline characters (\n and \r)
    from the text, and recombines the text into a single line.  Keeps count of files modified.

    Args:
        folder_path (str): The path to the folder containing the .txt files (assumed to be JSON).
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files (as JSON) in: {folder_path}")

    total_files_processed = 0
    files_modified_count = 0
    newline_removed_count = 0  # Counter for files with newlines removed

    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".txt"):  # Process only .txt files
                file_path = os.path.join(root, file_name)
                total_files_processed += 1
                print(f"Processing file: {file_path}")

                try:
                    # Read the file content
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()

                    # Check if newline characters are present BEFORE removal
                    if '\n' in content or '\r' in content:
                        newline_removed = True  # Flag to indicate newlines were present
                    else:
                        newline_removed = False

                    # Remove newline characters
                    cleaned_content = content.replace('\n', '').replace('\r', '')

                    # Attempt to parse as JSON to validate
                    try:
                        json.loads(cleaned_content)
                    except json.JSONDecodeError as e:
                        print(f"  --> Error: Cleaned content is not valid JSON: {e}")
                        print("  --> Skipping write due to invalid JSON.")
                        continue  # Skip writing the invalid JSON

                    # Write the cleaned content back to the file
                    if newline_removed:  # Only write if newlines were actually removed
                        with open(file_path, 'w', encoding='utf-8') as file:
                            file.write(cleaned_content)
                        files_modified_count += 1
                        newline_removed_count += 1  # Increment the newline counter
                        print(f"  --> Successfully removed newline characters and updated: {file_path}")
                    else:
                        print("  --> No newline characters found. Skipping update.")

                except Exception as e:
                    print(f"  --> Error processing file '{file_path}': {e}")
                print("-" * 30)

    print("\nProcessing completed.")
    print(f"Total files processed: {total_files_processed}")
    print(f"Files modified: {files_modified_count}")
    print(f"Files with newline characters removed: {newline_removed_count}")  # Print the newline count


if __name__ == "__main__":
    # Get user input
    folder_to_search = input("Enter the full path to the folder: ")

    # Call the function to process the files
    process_text_files_as_json(folder_to_search)