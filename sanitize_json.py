import os
import json
import argparse
import re
from tqdm import tqdm  # For progress bar

def sanitize_json(content):
    """Clean known problematic fields before JSON parsing"""
    # First, replace specific known raw control characters with their JSON escaped versions.
    # This handles cases where chr(29) or chr(15) are literally in the string.
    content = content.replace('\\x1d', '\\\\u001d')  # GROUP SEPARATOR
    content = content.replace('\\x0f', '\\\\u000f')  # SHIFT IN
    # Add other specific character replacements here if more are identified.

    # Remove all ASCII control characters (except \n, \r, \t)
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)

    # Then, apply broader sanitizations for specific fields by replacing their values.
    # Fix itemClsCd (ÿÿÿÿ... patterns)
    content = re.sub(r'"itemClsCd":"[^"]*"', r'"itemClsCd":"CLEANED"', content)
    # Fix bcd (binary data / control characters by replacing the whole value)
    content = re.sub(r'"bcd":"[^"]*"', r'"bcd":""', content)
    # Add fix for itemCd, as it seems to have similar issues to bcd.
    # This will replace the entire itemCd value with an empty string.
    # content = re.sub(r'"itemCd":"[^"]*"', r'"itemCd":""', content)
    return content

def read_file_safely(file_path):
    """Read a file with encoding fallback and sanitization"""
    try:
        # Try UTF-8 first
        with open(file_path, 'r', encoding='utf-8') as f:
            return sanitize_json(f.read())
    except UnicodeDecodeError:
        # Fallback to latin-1 if UTF-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return sanitize_json(f.read())

def get_sorted_folders(root_path):
    """Get numerically sorted folders (e.g., 21301-21400, 21401-21500)"""
    folders = []
    for name in os.listdir(root_path):
        if os.path.isdir(os.path.join(root_path, name)) and re.match(r'^\d+-\d+$', name):
            folders.append(name)
    # Sort folders by their starting number
    folders.sort(key=lambda x: int(x.split('-')[0]))
    return folders

def process_folder(folder_path, item_cls_cd_mapping, new_bcd, new_item_cd, pbar): # Added new_item_cd
    """Process all JSON files in a single folder"""
    modified_files = 0
    processed_files = 0
    
    # Get and sort files
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    txt_files.sort(key=lambda f: int(re.search(r'(\d+)', f).group(1)) if re.search(r'(\d+)', f) else 0)
    
    for filename in txt_files:
        file_path = os.path.join(folder_path, filename)
        try:
            content = read_file_safely(file_path)
            data = json.loads(content)
            processed_files += 1
            
            modified = False
            if 'itemList' in data and isinstance(data['itemList'], list):
                for item in data['itemList']:
                    # Process itemClsCd
                    if 'itemCd' in item and 'itemClsCd' in item:
                        item_cd_original = item['itemCd'].strip() # Use original itemCd for mapping
                        if item_cd_original in item_cls_cd_mapping:
                            new_item_cls_cd = item_cls_cd_mapping[item_cd_original]
                            if item['itemClsCd'] != new_item_cls_cd:
                                item['itemClsCd'] = new_item_cls_cd
                                modified = True
                        elif 'DEFAULT' in item_cls_cd_mapping:
                            new_item_cls_cd = item_cls_cd_mapping['DEFAULT']
                            if item['itemClsCd'] != new_item_cls_cd:
                                item['itemClsCd'] = new_item_cls_cd
                                modified = True
                    
                    # Process bcd
                    if new_bcd is not None: # If --bcd was provided by the user
                        if item.get('bcd') != new_bcd:
                            item['bcd'] = new_bcd
                            modified = True
                    
                    # Process itemCd
                    if new_item_cd and 'itemCd' in item: # Check if new_item_cd is provided
                        if item['itemCd'] != new_item_cd:
                            item['itemCd'] = new_item_cd
                            modified = True
                
                if modified:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                    modified_files += 1
            
            pbar.update(1)
            pbar.set_postfix({'Folder': os.path.basename(folder_path), 'File': filename})
            
        except Exception as e:
            print(f"\nError processing {file_path}: {str(e)}")
    
    return processed_files, modified_files

def modify_json_files(root_path, item_cls_cd_mapping, new_bcd=None, new_item_cd=None, start_folder=None, start_file=None): # Changed default for new_bcd
    """Main processing function with progress tracking"""
    folders = get_sorted_folders(root_path)
    
    # Calculate total files for progress bar
    total_files = 0
    for folder in folders:
        folder_path = os.path.join(root_path, folder)
        if os.path.isdir(folder_path):
            total_files += len([f for f in os.listdir(folder_path) if f.endswith('.txt')])
    
    # Initialize progress bar
    with tqdm(total=total_files, desc="Processing files", unit="file") as pbar:
        start_processing = not (start_folder or start_file)
        processed_files = 0
        modified_files = 0
        
        for folder in folders:
            folder_path = os.path.join(root_path, folder)
            
            # Skip folders until start_folder is reached
            if not start_processing and start_folder:
                if folder == start_folder:
                    start_processing = True
                else:
                    # Skip counting files in folders we're skipping
                    pbar.update(len([f for f in os.listdir(folder_path) if f.endswith('.txt')])) # Ensure this line is correctly indented
                    continue
            
            # Process the folder
            p, m = process_folder(folder_path, item_cls_cd_mapping, new_bcd, new_item_cd, pbar) # Pass new_item_cd
            processed_files += p
            modified_files += m
    
    print(f"\nProcessing complete!")
    print(f"Total folders processed: {len(folders)}")
    print(f"Total files processed: {processed_files}")
    print(f"Total files modified: {modified_files}")

def main():
    parser = argparse.ArgumentParser(description='Modify JSON data in text files')
    parser.add_argument('path', help='Path to the root directory containing JSON files')
    parser.add_argument('--dep1-cls-cd', default='99000000', help='Value for itemClsCd when itemCd is "DEP 1"')
    parser.add_argument('--dep2-cls-cd', default='99010000', help='Value for itemClsCd when itemCd is "DEP 2"')
    parser.add_argument('--default-cls-cd', default='99000000', help='Default value for itemClsCd for unknown itemCd')
    parser.add_argument('--bcd', nargs='?', const='', default=None, help='New value for bcd field. Use --bcd or --bcd "" to set to an empty string. If omitted, bcd is not changed.')
    parser.add_argument('--new-item-cd', help='New value for itemCd field for all items. If provided, itemClsCd mapping will be based on the original itemCd.')
    parser.add_argument('--start-folder', help='Folder to start processing from (e.g., "21301-21400")')
    parser.add_argument('--start-file', help='File to start processing from (e.g., "121355.txt")')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.path):
        print(f"Error: Directory '{args.path}' does not exist.")
        return
    
    item_cls_cd_mapping = {
        'DEP 1': args.dep1_cls_cd,
        'DEP 2': args.dep2_cls_cd,
        'DEFAULT': args.default_cls_cd
    }
    
    modify_json_files(args.path, item_cls_cd_mapping, args.bcd, args.new_item_cd, args.start_folder, args.start_file) # Pass args.new_item_cd

if __name__ == "__main__":
    main()