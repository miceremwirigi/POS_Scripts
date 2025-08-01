import os
import json
import re
import sys
import time

def process_files(parent_dir):
    """
    Processes .txt files within the given directory and its subdirectories,
    aggressively correcting malformed JSON content.
    """
    # Define the replacements for `itemClsCd`.
    item_cls_replacements = {
        "DEP 2": "99010000",
        "DEP 1": "99011108"
    }

    processed_files_count = 0
    fixed_files_count = 0
    spinner = ['\\', '|', '/', '-']
    spinner_index = 0

    print(f"Starting file processing in directory: {parent_dir}")

    for dirpath, dirnames, filenames in os.walk(parent_dir):
        for filename in filenames:
            if filename.endswith('.txt'):
                file_path = os.path.join(dirpath, filename)
                processed_files_count += 1
                
                sys.stdout.write(f"\rProcessing file {processed_files_count}: {file_path} {spinner[spinner_index]}")
                sys.stdout.flush()
                spinner_index = (spinner_index + 1) % len(spinner)

                try:
                    # Read file with 'ignore' to remove invalid Unicode characters.
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Use regex to remove any remaining non-printable ASCII characters.
                    cleaned_content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)

                    # Now, attempt to load the cleaned content as JSON.
                    data = json.loads(cleaned_content)
                    
                    is_modified = False
                    
                    if 'itemList' in data and isinstance(data['itemList'], list):
                        for item in data['itemList']:
                            if 'bcd' in item and isinstance(item['bcd'], str) and item['bcd'] != "":
                                item['bcd'] = ""
                                is_modified = True
                            
                            if 'itemClsCd' in item and item['itemCd'] in item_cls_replacements:
                                new_cls_code = item_cls_replacements[item['itemCd']]
                                if item['itemClsCd'] != new_cls_code:
                                    item['itemClsCd'] = new_cls_code
                                    is_modified = True
                    
                    # Save the modified JSON back to the file.
                    if is_modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f)
                        fixed_files_count += 1
                    
                except json.JSONDecodeError:
                    # If the file still can't be parsed, it means there are
                    # more complex structural errors. However, we still save
                    # the file with the invalid characters removed.
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    fixed_files_count += 1
                except IOError as e:
                    sys.stdout.write(f"\rError processing {file_path}: {e}\n")
                    sys.stdout.flush()
    
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    print("Script finished.")
    print(f"Total files processed: {processed_files_count}")
    print(f"Total files fixed: {fixed_files_count}")


def main():
    """
    Main function to get user input for the parent directory and start the processing.
    """
    parent_dir = input("Please enter the parent directory to start processing from: ")

    if not os.path.isdir(parent_dir):
        print(f"Error: The directory '{parent_dir}' does not exist.")
        return

    process_files(parent_dir)

if __name__ == "__main__":
    main()