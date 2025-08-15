import os
import chardet
import sys
import json
import re

def detect_text_in_files(folder_path, search_text):
    """
    Detects .txt files containing a particular text in a file system and reports
    the files found, along with unique customer names and buyer PINs.
    Includes a loading animation.

    Args:
        folder_path (str): The path to the folder to search.
        search_text (str): The text to search for within the files.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Scanning .txt files in: {folder_path} and its subfolders for text: '{search_text}'")

    found_entries = {}
    total_files_scanned = 0
    animation = ["|", "/", "-", "\\"]
    idx = 0

    # Regex for when 'custNm' comes before 'custTin'
    regex1 = re.compile(r'"custNm":"(.*?)"(?:.*?")custTin":"(.*?)"')
    # Regex for when 'custTin' comes before 'custNm'
    regex2 = re.compile(r'"custTin":"(.*?)"(?:.*?")custNm":"(.*?)"')

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                total_files_scanned += 1
                file_path = os.path.join(root, file)

                # Loading animation
                print(f"Scanning: {file_path} {animation[idx % len(animation)]}", end="\r")
                idx += 1
                sys.stdout.flush()

                try:
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']
                    
                    if encoding:
                        try:
                            content = raw_data.decode(encoding, errors='ignore')
                            if search_text in content:
                                match = regex1.search(content)
                                if match:
                                    cust_name = match.group(1)
                                    cust_tin = match.group(2)
                                else:
                                    match = regex2.search(content)
                                    if match:
                                        cust_tin = match.group(1)
                                        cust_name = match.group(2)
                                    else:
                                        cust_name = "Not Found"
                                        cust_tin = "Not Found"
                                        print(f"\nWarning: Text found but could not extract data from {file_path}.")

                                if (cust_name, cust_tin) not in found_entries:
                                    found_entries[(cust_name, cust_tin)] = []
                                found_entries[(cust_name, cust_tin)].append(file_path)
                                    
                        except Exception as e:
                            print(f"\nError processing {file_path}: {e}")
                    else:
                        print(f"\nWarning: Could not detect encoding for {file_path}. Skipping.")

                except Exception as e:
                    print(f"\nError processing {file_path}: {e}")

    # Clear the loading animation after completion
    print(" " * 80, end="\r")
    sys.stdout.flush()

    if found_entries:
        print("\n--- Summary ---")
        print("The following unique customers and PINs contain the specified text:")
        for (name, pin), files in found_entries.items():
            print(f"Customer Name: {name}, Buyer's PIN: {pin}")
            print("  Files:")
            for file_path in files:
                print(f"    - {file_path}")
        print(f"\nTotal unique customers found: {len(found_entries)}")
        
        # New section for the clean list
        print("\n--- Unique Customer & PIN List ---")
        print("{:<40} {:<20}".format("Customer Name", "Buyer's PIN"))
        print("-" * 60)
        for (name, pin), _ in sorted(found_entries.items()):
            print("{:<40} {:<20}".format(name, pin))

    else:
        print(f"No files containing the text '{search_text}' were found.")

    print(f"Total files scanned: {total_files_scanned}")

if __name__ == "__main__":
    folder_path = input("Please enter the folder path to scan: ")
    search_char = input("Please enter the single character to search for (e.g., ^A): ")
    
    # Convert the user input for control characters
    if len(search_char) == 2 and search_char.startswith('^'):
        search_text = chr(ord(search_char[1]) - ord('@'))
    else:
        search_text = search_char

    detect_text_in_files(folder_path, search_text)
    print("Scanning process completed.")