import os
import chardet
import sys


def detect_text_in_files(folder_path, search_text):
    """
    Detects .txt files containing a particular text in a file system and reports
    the files found, along with a count of the files containing the text.
    Includes a loading animation.

    Args:
        folder_path (str): The path to the folder to search.
        search_text (str): The text to search for within the files.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Scanning .txt files in: {folder_path} and its subfolders for text: '{search_text}'")

    files_with_text = []
    total_files_scanned = 0
    animation = ["|", "/", "-", "\\"]
    idx = 0

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                total_files_scanned += 1
                file_path = os.path.join(root, file)

                # Loading animation
                print(f"Scanning: {file_path} {animation[idx % len(animation)]}", end="\r")
                idx += 1
                sys.stdout.flush()  # Ensure the output is flushed immediately

                try:
                    # Detect the encoding of the file
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']

                    if encoding:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()

                            if search_text in content:
                                files_with_text.append(file_path)
                                print(f"\nFile containing text '{search_text}': {file_path}")  # Newline

                        except Exception as e:
                            print(f"\nError processing {file_path}: {e}")  # Newline

                    else:
                        print(f"\nWarning: Could not detect encoding for {file_path}. Skipping.")  # Newline

                except Exception as e:
                    print(f"\nError processing {file_path}: {e}")  # Newline

    # Clear the loading animation after completion
    print(" " * 80, end="\r")  # Overwrite the animation with spaces
    sys.stdout.flush()

    num_files_with_text = len(files_with_text)

    if files_with_text:
        print("\n--- Summary ---")
        print("The following files contain the specified text:")
        for file_path in files_with_text:
            print(file_path)
        print(f"\nTotal files containing text '{search_text}': {num_files_with_text}")
    else:
        print(f"No files containing the text '{search_text}' were found.")

    print(f"Total files scanned: {total_files_scanned}")


if __name__ == "__main__":
    folder_path = input("Please enter the folder path to scan: ")
    search_text = input("Please enter the text to search for: ")
    detect_text_in_files(folder_path, search_text)
    print("Scanning process completed.")