import os

# Replace this with the path to your folder
folder_path = "email_conversations_no_attachments"  # Windows example
# folder_path = "/path/to/your/folder"  # Linux / macOS example

# List all items in the folder and filter only directories
subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

# Count and print
print(f"Number of subfolders:", len(subfolders))
