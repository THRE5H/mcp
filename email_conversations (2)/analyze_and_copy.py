#!/usr/bin/env python3
"""Analyze email conversations and copy ones without attachments to a new folder.

Usage:
  python analyze_and_copy.py [root_folder]

This script:
1. Counts conversations with and without attachments
2. Copies conversations that contain only emails.txt and conversation.json to a new folder
"""
from pathlib import Path
import json
import shutil
import sys
import re


ATT_EXTS = (
    "png jpg jpeg gif bmp tif tiff pdf csv xls xlsx doc docx zip rar 7z"
    .split()
)

ATT_RE = re.compile(r"\.({})\b".format("|".join(ATT_EXTS)), re.IGNORECASE)


def has_attachments(folder: Path) -> bool:
    """Check if a conversation folder has any attachments (files other than email_*.txt and conversation.json)."""
    try:
        for item in folder.iterdir():
            if item.is_file():
                # Allow only conversation.json and email_N.txt files
                if item.name.lower() == "conversation.json":
                    continue
                if item.name.lower().startswith("email_") and item.suffix.lower() == ".txt":
                    continue
                # Any other file is considered an attachment
                return True
    except Exception as e:
        print(f"Error checking folder {folder}: {e}")
        return True  # If we can't check, assume it has attachments
    
    return False


def analyze_conversations(root: Path):
    """Analyze all conversation folders."""
    conversations_with_att = []
    conversations_without_att = []
    
    try:
        for item in root.iterdir():
            if item.is_dir():
                conv_json = item / "conversation.json"
                if conv_json.is_file():
                    if has_attachments(item):
                        conversations_with_att.append(item)
                    else:
                        conversations_without_att.append(item)
    except Exception as e:
        print(f"Error scanning root folder: {e}")
        return [], []
    
    return conversations_with_att, conversations_without_att


def copy_conversations(source_folders: list, dest_root: Path):
    """Copy conversation folders to destination."""
    dest_root.mkdir(parents=True, exist_ok=True)
    
    copied = 0
    failed = 0
    
    for source in sorted(source_folders):
        try:
            dest = dest_root / source.name
            if dest.exists():
                print(f"  Skipping (already exists): {source.name}")
                continue
            
            shutil.copytree(source, dest)
            copied += 1
            print(f"  ✓ Copied: {source.name}")
        except Exception as e:
            failed += 1
            print(f"  ✗ Failed to copy {source.name}: {e}")
    
    return copied, failed


def main():
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        root = Path("email_conversations")
    
    if not root.exists():
        print(f"Error: Path does not exist: {root}")
        sys.exit(1)
    
    print(f"Analyzing conversations in: {root}\n")
    
    with_att, without_att = analyze_conversations(root)
    
    print(f"Analysis Results:")
    print(f"  Conversations WITH attachments: {len(with_att)}")
    print(f"  Conversations WITHOUT attachments: {len(without_att)}")
    print(f"  Total conversations: {len(with_att) + len(without_att)}")
    print()
    
    if without_att:
        print(f"Copying {len(without_att)} conversations without attachments...")
        dest_folder = root.parent / "email_conversations_no_attachments"
        print(f"Destination: {dest_folder}\n")
        
        copied, failed = copy_conversations(without_att, dest_folder)
        
        print(f"\nCopy Results:")
        print(f"  Successfully copied: {copied}")
        print(f"  Failed: {failed}")
        print(f"  Total copied to: {dest_folder}")
    else:
        print("No conversations without attachments found.")


if __name__ == "__main__":
    main()
