import os
import chardet


def remove_control_characters_from_txt_files(folder_path):
    """
    Removes DT1 (Device Control 1, 0x11), ETX (End of Text, 0x03), BS (Backspace, 0x08),
    SYN (Synchronous Idle, 0x16), and ACK (Acknowledge, 0x06) characters from all .txt
    files within a folder and its subfolders.  Automatically detects encoding for each file.

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

                        # Remove DT1 (0x11), ETX (0x03), BS (0x08), SYN (0x16), and ACK (0x06) characters
                        content = content.replace('\x11', '').replace('\x03', '').replace('\x08', '').replace('\x16', '').replace('\x06', '')

                        # Write the modified content back to the file using the detected encoding
                        with open(file_path, 'w', encoding=encoding) as f:
                            f.write(content)

                        print(f"Successfully processed: {file_path}")
                    else:
                        print(f"Warning: Could not detect encoding for {file_path}. Skipping.")

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    folder_path = input("Please enter the folder path: ")
    remove_control_characters_from_txt_files(folder_path)
    print("Control character removal process completed.")