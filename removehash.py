import os
import json

def remove_suffix_from_json_files_in_folder(folder_path):
    """
    Removes a non-JSON suffix from .txt files containing JSON data within a folder and its subfolders.

    Args:
        folder_path (str): The path to the folder to search.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files (as JSON) in: {folder_path} and its subfolders")

    total_files_processed = 0
    files_modified_count = 0

    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".txt"):
                file_path = os.path.join(root, file_name)
                total_files_processed += 1
                print(f"Processing file: {file_path}")

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Attempt to load the entire content as JSON.  If it fails, it likely has a suffix.
                    try:
                        json.loads(content)
                        print(f"  --> File '{file_path}' is already valid JSON. No suffix to remove.")
                    except json.JSONDecodeError:
                        print(f"  --> File '{file_path}' has an invalid JSON format, attempting to remove suffix.")
                        # Find the last closing brace '}'
                        last_brace_index = content.rfind('}')

                        if last_brace_index != -1:
                            # Extract the JSON part
                            json_string = content[:last_brace_index + 1]

                            # Validate the extracted JSON
                            try:
                                json.loads(json_string)
                                # If valid, write back to the file
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(json_string)
                                files_modified_count += 1
                                print(f"  --> Successfully removed suffix from '{file_path}'")

                            except json.JSONDecodeError as e:
                                print(f"  --> Error: Could not parse JSON even after suffix removal: {e}")
                                print("  --> File may be corrupted or have a more complex issue.")

                        else:
                            print("  --> Error: No closing brace '}' found in the file.")
                            print("  --> Could not identify JSON portion.")

                except FileNotFoundError:
                    print(f"  --> Error: File not found: {file_path}")
                except Exception as e:
                    print(f"  --> An unexpected error occurred: {e}")
                print("-" * 30)

    print("\nProcessing completed.")
    print(f"Total files processed: {total_files_processed}")
    print(f"Files modified: {files_modified_count}")


if __name__ == "__main__":
    folder_path = input("Enter the full path to the folder: ")
    remove_suffix_from_json_files_in_folder(folder_path)