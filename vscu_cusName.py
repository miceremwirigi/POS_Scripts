import os
import json
import re
import chardet  # For detecting file encoding

# Custom JSONDecoder to allow unescaped control characters.
class NonStrictDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        kwargs['strict'] = False
        super().__init__(*args, **kwargs)

# Pattern to match control characters (non-printable ASCII).
CONTROL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')

# Pattern to match non-ASCII characters (e.g., characters outside U+0000-U+007F).
NON_ASCII_PATTERN = re.compile(r'[^\x00-\x7F]+')

# Combined pattern to match both control and non-ASCII characters - this will replace ALL problematic characters
UNDEFINED_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]|[^\x00-\x7F]+')

def detect_file_encoding(file_path, num_bytes=1000):
    """
    Detect the file's encoding by reading the first num_bytes.
    """
    with open(file_path, 'rb') as f:
        rawdata = f.read(num_bytes)
    result = chardet.detect(rawdata)
    encoding = result.get('encoding')
    print(f"Detected encoding for {file_path}: {encoding}")
    return encoding

def clean_string(text):
    """
    Replace ALL problematic characters within words with single spaces:
    - CONTROL_CHAR_PATTERN: Control characters (non-printable ASCII)
    - NON_ASCII_PATTERN: Non-ASCII characters 
    - UNDEFINED_CHAR_PATTERN: Combined pattern covering both above
    
    All these patterns are replaced with single spaces within words.
    Multiple consecutive spaces are normalized to single spaces.
    """
    # Replace ALL undefined characters (control + non-ASCII) with single spaces
    cleaned = UNDEFINED_CHAR_PATTERN.sub(' ', text)
    
    # Normalize multiple consecutive spaces to single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Strip leading and trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def replace_control_chars(obj, path=""):
    """
    Recursively traverse the JSON structure (dicts and lists) to find strings
    that contain problematic characters and automatically replace them with spaces.
    
    Replaces ALL characters matching these patterns within words:
    - CONTROL_CHAR_PATTERN: Control characters (non-printable ASCII)
    - NON_ASCII_PATTERN: Non-ASCII characters
    - UNDEFINED_CHAR_PATTERN: Combined pattern (used for actual replacement)
    
    Args:
        obj: The JSON data (nested dicts/lists).
        path: The current "path" in the JSON structure (for display purposes).
    
    Returns:
        A boolean flag indicating whether any changes were made.
    """
    changed = False

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, str) and UNDEFINED_CHAR_PATTERN.search(value):
                # Debug output: show what characters are being replaced
                original_repr = repr(value)
                cleaned_value = clean_string(value)
                
                if cleaned_value != value:
                    print(f"[AUTO-REPLACE] In key '{current_path}':")
                    print(f"  Original: {original_repr}")
                    print(f"  Cleaned:  {repr(cleaned_value)}")
                    obj[key] = cleaned_value
                    changed = True
            elif isinstance(value, (dict, list)):
                if replace_control_chars(value, current_path):
                    changed = True

    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            current_path = f"{path}[{index}]"
            if isinstance(item, str) and UNDEFINED_CHAR_PATTERN.search(item):
                original_repr = repr(item)
                cleaned_value = clean_string(item)
                
                if cleaned_value != item:
                    print(f"[AUTO-REPLACE] In {current_path}:")
                    print(f"  Original: {original_repr}")
                    print(f"  Cleaned:  {repr(cleaned_value)}")
                    obj[index] = cleaned_value
                    changed = True
            elif isinstance(item, (dict, list)):
                if replace_control_chars(item, current_path):
                    changed = True
    return changed

def process_file(file_path):
    """
    Reads a .txt file (assumed to contain JSON), processes it for unwanted characters,
    and writes back any changes (in a single line). Only files that contain these characters
    are modified. Files with non-UTF-8 encodings are handled by detecting the encoding first.
    """
    print(f"\nProcessing file: {file_path}")
    
    detected_encoding = detect_file_encoding(file_path)
    if not detected_encoding:
        print(f"Could not detect encoding for {file_path}. Skipping file.")
        return

    try:
        with open(file_path, 'r', encoding=detected_encoding) as f:
            data = json.load(f, cls=NonStrictDecoder)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    file_changed = replace_control_chars(data)

    if file_changed:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            print(f"File updated successfully: {file_path}")
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
    else:
        print(f"No unwanted characters found in {file_path}. File not modified.")

def main():
    directory = input("Enter the main directory path containing sub-directories with .txt files: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please try again.")
        return

    print("Starting automatic cleanup of undefined characters...")
    print("All characters matching these patterns will be replaced with single spaces:")
    print("- CONTROL_CHAR_PATTERN: Control characters (non-printable ASCII)")
    print("- NON_ASCII_PATTERN: Non-ASCII characters")
    print("- UNDEFINED_CHAR_PATTERN: Combined pattern covering both above")
    print("All problematic characters within words will be replaced with single spaces.\n")

    files_processed = 0
    files_modified = 0

    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith('.txt'):
                file_path = os.path.join(root, filename)
                files_processed += 1
                
                # Check if file was modified by looking at the output
                print_output_before = len([line for line in open(file_path, 'rb').readlines()])
                process_file(file_path)
                # This is a simple way to track, you could make it more sophisticated

    print(f"\nProcessing complete!")
    print(f"Total files processed: {files_processed}")

if __name__ == "__main__":
    main()