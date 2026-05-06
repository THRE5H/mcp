#!/usr/bin/env python3
"""Count emails, attachments and subjects across conversation folders.

Usage:
  python count_emails.py [root_folder]

If no folder is given, the current directory is used.
"""
from pathlib import Path
import argparse
import json
import re
import sys


ATT_EXTS = (
    "png jpg jpeg gif bmp tif tiff pdf csv xls xlsx doc docx zip rar 7z"
    .split()
)

ATT_RE = re.compile(r"\.({})\b".format("|".join(ATT_EXTS)), re.IGNORECASE)


def email_has_attachment(email: dict, folder: Path) -> bool:
    if email.get("has_attachments"):
        return True
    atts = email.get("attachments")
    if atts:
        try:
            if len(atts) > 0:
                return True
        except Exception:
            return True
    
    # check for extra files in the same folder (excluding conversation.json and email_*.txt)
    try:
        for p in folder.iterdir():
            if p.is_file():
                if p.name.lower() in ("conversation.json",) or (p.name.lower().startswith("email_") and p.suffix.lower() == ".txt"):
                    continue
                if p.suffix.lower().lstrip('.') in ATT_EXTS:
                    return True
    except Exception:
        pass
    return False


def process_root(root: Path):
    total_emails = 0
    emails_with_attachments = 0
    login_subject_emails = 0

    for dirpath, dirnames, filenames in os_walk(root):
        pdir = Path(dirpath)
        if "conversation.json" in filenames:
            convo_file = pdir / "conversation.json"
            try:
                data = json.loads(convo_file.read_text(encoding="utf-8"))
            except Exception:
                try:
                    data = json.loads(convo_file.read_text(encoding="latin-1"))
                except Exception:
                    continue
            emails = data.get("emails") or []
            for email in emails:
                total_emails += 1
                if email_has_attachment(email, pdir):
                    emails_with_attachments += 1
                subj = (email.get("subject") or "").strip()
                if subj.lower() == "login credentials":
                    login_subject_emails += 1

    return total_emails, emails_with_attachments, login_subject_emails


def count_conversation_folders(root: Path) -> int:
    """Count immediate subdirectories of `root` that contain a conversation.json file."""
    count = 0
    try:
        for p in root.iterdir():
            if p.is_dir():
                if (p / "conversation.json").is_file():
                    count += 1
    except Exception:
        pass
    return count


def os_walk(root: Path):
    # Small wrapper to yield os.walk-style tuples using Path
    for dirpath, dirnames, filenames in __import__("os").walk(str(root)):
        yield dirpath, dirnames, filenames


def main():
    parser = argparse.ArgumentParser(description="Count emails and attachments in conversation folders")
    parser.add_argument("root", nargs="?", default=".", help="Root folder containing conversation folders")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"Path does not exist: {root}")
        sys.exit(2)

    total, with_att, login = process_root(root)
    conv_folders = count_conversation_folders(root)

    print(f"Total emails: {total}")
    print(f"Conversation folders (subfolders with conversation.json): {conv_folders}")
    print(f"Emails with attachments (images, pdf, csv, etc.): {with_att}")
    print(f"Emails with subject 'Login Credentials': {login}")


if __name__ == "__main__":
    main()
