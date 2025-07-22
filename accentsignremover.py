import os
import chardet
import unicodedata


def remove_accents_from_txt_files_in_folder(folder_path):
    """
    Removes accents from all .txt files within a folder and its subfolders,
    treating them as plain text files. Automatically detects encoding for each file.

    Args:
        folder_path (str): The path to the folder to search.
    """

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory.")
        return

    print(f"Processing .txt files in: {folder_path} and its subfolders")

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    # Detect the encoding of the file
                    with open(file_path, 'rb') as f:
                        raw_data = f.read()
                        result = chardet.detect(raw_data)
                        encoding = result['encoding']

                    if encoding:
                        # Read the file with the detected encoding
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()

                        # Explicitly replace 'ó' with 'o'
                        content = content.replace('ó', 'o')

                        # Normalize the Unicode string to remove other accents
                        normalized_content = ''.join(
                            c for c in unicodedata.normalize('NFKD', content)
                            if unicodedata.category(c) != 'Mn'
                        )

                        # Write the modified content back to the file using UTF-8 encoding
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(normalized_content)

                        print(f"Successfully processed: {file_path}")
                    else:
                        print(f"Warning: Could not detect encoding for {file_path}. Skipping.")

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    folder_path = input("Please enter the folder path: ")

    remove_accents_from_txt_files_in_folder(folder_path)
    print("Accent removal process completed.")