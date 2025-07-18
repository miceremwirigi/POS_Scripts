import os

def replace_text_in_folder(folder_path, old_text, new_text):
	"""
	serches for a specified text in all files in a given folder
	(including subfoldrs) and replaces it with new text.

	Args:
		folder_path (str): The path to the folder to search in.
		old_text (str): The text to find and replace.
		new_text (str): The text to replace with.
	"""

	if not os.path.isdir(folder_path):
		print("Error: The provided path '{folder_path}' is not a valid directory.")
		return

	print(f"Starting text replacement in: {folder_path}")
	print(f"Searching for: '{old_text}'")
	print(f"replacing with: '{new_text}'")

	found_and_modified_count = 0
	total_files_processed = 0

	# Walk through the directory tree
	for root, _, files in os.walk(folder_path):
		for file_name in files:
			file_path = os.path.join(root, file_name)
			total_files_processed +=1
			print(f"Processing file: {file_path}")

			try:
				# Read the file content
				# 'r' for read mode, 'encoding' to handle various text encodings
				with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
					content = file.read()

				# Check if the old_text is pathresent in the content
				if old_text in content:
					print(f"  --> Found '{old_text}' in this file. Replacing...")
					new_content = content.replace(old_text, new_text)

					# Write the modified content back to the file
					# 'w' for write mode (overwrites existing content)
					with open(file_path, 'w', encoding='utf-8') as file:
						file.write(new_content)
					found_and_modified_count +=1
					print(f" --> Successfully replaced and updated: {file_path}")
				else:
					print(" --> Text not found in this file. Skipping.")

			except Exception as e:
				print(f" --> Error parsing file '{file_path}': {e}")
			print("-" * 30)

	print("\n Replacement process completed.")
	print(f" Total files processed: '{total_files_processed}'")
	print(f" Files modified: '{found_and_modified_count}'")

if __name__ == "__main__":
	# Get user input
	folder_to_search = input("Enter the full path to the folder: ")
	text_to_find = input("Enter the text/word to find and replace: ")
	text_to_replace_with = input("Enter the text/word to replace it with: ")

	# Call the function to perform the replacement
	replace_text_in_folder(folder_to_search, text_to_find, text_to_replace_with)

