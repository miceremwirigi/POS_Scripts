import os
import chardet
import re
import time
import sys


def has_unconventional_chars(text):
    """
    Detects the presence of control characters, high Unicode characters,
    and specific byte-like patterns (e.g., ÿÿÿÿ) in a string.

    Args:
        text (str): The string to check.

    Returns:
        bool: True if unconventional characters are found, False otherwise.
    """
    # Regular expression to detect control characters (0x00-0x1F, 0x7F-0x9F)
    control_char_regex = r"[\x00-\x1F\x7F-\x9F]"

    # Regular expression to detect characters outside the BMP (Basic Multilingual Plane)
    high_unicode_regex = r"[\U00010000-\U0010FFFF]"

    # Regular expression to detect byte-like patterns (e.g., ÿÿÿÿ)
    byte_pattern_regex = r"[\u00FF]{2,}"  # Two or more consecutive "ÿ" characters

    if (
        re.search(control_char_regex, text)
        or re.search(high_unicode_regex, text)
        or re.search(byte_pattern_regex, text)
    ):
        return True
    return False


def clean_unconventional_chars(text):
    """
    Removes control characters, high Unicode characters, and specific byte-like
    patterns (e.g., ÿÿÿÿ) from a string.

    Args:
        text (str): The string to clean.

    Returns:
        str: The cleaned string.
    """
    # Regular expression to detect control characters (0x00-0x1F, 0x7F-0x9F)
    control_char_regex = r"[\x00-\x1F\x7F-\x9F]"

    # Regular expression to detect characters outside the BMP (Basic Multilingual Plane)
    high_unicode_regex = r"[\U00010000-\U0010FFFF]"

    # Regular expression to detect byte-like patterns (e.g., ÿÿÿÿ)
    byte_pattern_regex = r"[\u00FF]{2,}"  # Two or more consecutive "ÿ" characters

    # Use re.sub() to replace all matches with an empty string
    cleaned_text = re.sub(control_char_regex, "", text)
    cleaned_text = re.sub(high_unicode_regex, "", cleaned_text)
    cleaned_text = re.sub(byte_pattern_regex, "", cleaned_text)

    return cleaned_text


def delete_bad_chars_in_files(folder_path):
    """
    Deletes unconventional characters (control characters, high Unicode,
    byte-like patterns) from .txt files in a file system.
    Includes a loading animation.

    Args:
        folder_path (str): The path to the folder to search.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Scanning and cleaning .txt files in: {folder_path} and its subfolders")

    files_cleaned = []
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
                sys.stdout.flush()

                try:
                    # Detect the encoding of the file
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']

                    if encoding:
                        try:
                            # Read the file content
                            with open(file_path, 'r', encoding=encoding) as f:
                                content = f.read()

                            if has_unconventional_chars(content):
                                # Clean the content
                                cleaned_content = clean_unconventional_chars(content)
                                # Write the cleaned content back to the file
                                with open(file_path, 'w', encoding=encoding) as f:
                                    f.write(cleaned_content)
                                files_cleaned.append(file_path)
                                print(f"\nCleaned unconventional characters from: {file_path}")  # Newline to separate from animation

                        except Exception as e:
                            print(f"\nError processing {file_path}: {e}")  # Newline

                    else:
                        print(f"\nWarning: Could not detect encoding for {file_path}. Skipping.")  # Newline

                except Exception as e:
                    print(f"\nError processing {file_path}: {e}")  # Newline

    # Clear the loading animation after completion
    print(" " * 80, end="\r")  # Overwrite the animation with spaces
    sys.stdout.flush()

    num_files_cleaned = len(files_cleaned)

    if files_cleaned:
        print("\n--- Summary ---")
        print("The following files were cleaned:")
        for file_path in files_cleaned:
            print(file_path)
        print(f"\nTotal files cleaned: {num_files_cleaned}")
    else:
        print("No files with unconventional characters were found to clean.")

    print(f"Total files scanned: {total_files_scanned}")


if __name__ == "__main__":
    folder_path = input("Please enter the folder path to scan and clean: ")
    delete_bad_chars_in_files(folder_path)
    print("Scanning and cleaning process completed.")