"""
Update Knowledge Base - Code/API/Script-Preserving Re-Extraction
================================================================
Structure of each entry in knowledge_base.json:
{
    "id": "FB310854_RE_ Unable to download customs data",
    "problem": "...",
    "solution": "...",
    "keywords": [...],
    "category": "..."
}
The "id" matches the folder name under email_conversations_no_attachments.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT 1 — CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────
CLASSIFIER_PROMPT = """You are a technical content analyzer. Read the email conversation below and decide whether it contains any of the following:

- Code snippets (any programming language: Python, JavaScript, SQL, bash, etc.)
- API endpoints or URLs used in a technical/integration context
- curl commands or HTTP request/response examples
- JSON or XML request/response bodies
- Authentication headers, token formats, or API key formats
- Command-line instructions or terminal commands
- Configuration file content
- Script examples (automation, data processing, etc.)
- Any technical syntax that must be copied exactly to work correctly

## Decision Rules
- If the email contains ANY of the above → respond: NEEDS_UPDATE
- If the email is plain text explanation, a how-to guide with no code, or administrative content → respond: NO_UPDATE

Respond with ONLY one of these two words, nothing else:
NEEDS_UPDATE
NO_UPDATE"""


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT 2 — CODE-PRESERVING EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTOR_PROMPT = """You are an expert knowledge base builder specializing in technical customer support content.

Extract a clean, reusable knowledge entry from the provided email conversation.

═══════════════════════════════════════════════════════════
RULE #1 — ABSOLUTE CODE PRESERVATION (most important rule)
═══════════════════════════════════════════════════════════
Any technical content that must be used exactly as written MUST be copied verbatim — character for character. This includes:

▸ Code snippets (Python, JavaScript, SQL, bash, any language)
▸ API endpoint URLs (e.g. https://api.example.com/v1/users)
▸ curl commands and HTTP request examples
▸ JSON or XML request/response bodies
▸ Authentication headers and token formats (e.g. Authorization: Bearer <token>)
▸ Command-line instructions and terminal commands
▸ Configuration file content
▸ Function signatures, class names, parameter names
▸ Error messages with their exact text and codes

Always wrap technical content in appropriate markdown code blocks:
  ```python   for Python
  ```bash     for shell/curl/terminal
  ```json     for JSON
  ```sql      for SQL
  ```          for anything else

NEVER paraphrase, shorten, rename variables, or reformat code.

═══════════════════════════════════════════════
RULE #2 — STRUCTURE AROUND CODE, NOT INSTEAD
═══════════════════════════════════════════════
You may add:
▸ A brief sentence before a code block to explain what it does
▸ Numbered steps if the solution has multiple stages
▸ Short notes after a code block (e.g. "Replace <token> with your API key")

You may NOT:
▸ Replace code with a prose description
▸ Summarize what the code does instead of showing it
▸ Omit any part of a multi-step code solution

═══════════════════════════════════════════════
RULE #3 — ANONYMIZATION
═══════════════════════════════════════════════
Remove: personal names, individual email addresses, company/organization names.
Keep: product names, platform names, feature names, technical identifiers, error codes, version numbers, domain names that are part of API URLs.

═══════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON, nothing else
═══════════════════════════════════════════════
{
  "problem": "One or two sentences describing the technical issue from a user perspective. No personal names.",
  "solution": "Full solution with all code blocks preserved verbatim inside markdown code fences. Add only minimal structural text for clarity.",
  "keywords": ["keyword1", "keyword2", "..."],
  "category": "API / Script"
}

Categories: "Access Issue" | "Download Problem" | "Configuration" | "Error Resolution" | "Feature Explanation" | "How-to Guide" | "Integration Issue" | "API / Script" | "Platform Navigation"

Return ONLY the JSON object above — no extra text, no wrapper keys.
"""


def load_email_conversation(json_path: str) -> str:
    """Load conversation.json and return formatted text."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lines = []
        for email in reversed(data.get('emails', [])):
            lines.append(f"From: {email.get('from_name', 'Unknown')}")
            lines.append(f"To:   {email.get('to', 'Unknown')}")
            lines.append(f"Time: {email.get('sent_time', '')}")
            lines.append(f"Subject: {email.get('subject', '')}")
            lines.append(f"Body:\n{email.get('body_text', '')}")
            lines.append("=" * 80)
        return "\n".join(lines)
    except Exception as e:
        print(f"    ✗ Error loading {json_path}: {e}")
        return ""


def classify_email(email_text: str, api_key: str) -> Optional[str]:
    """Ask LLM: does this email contain code/API/scripts?"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user",   "content": email_text}
            ],
            max_tokens=10,
            temperature=0.0
        )
        verdict = response.choices[0].message.content.strip().upper()
        return verdict if verdict in ("NEEDS_UPDATE", "NO_UPDATE") else "NO_UPDATE"
    except Exception as e:
        print(f"    ✗ Classifier error: {e}")
        return None


def extract_with_openai(email_text: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Re-extract with full code-preserving prompt."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": EXTRACTOR_PROMPT},
                {"role": "user",   "content": email_text}
            ],
            max_tokens=1500,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    ✗ Extractor error: {e}")
        return None


def update_knowledge_base(
    knowledge_base_path: str,
    emails_folder: str,
    dry_run: bool = False,
    only_ids: List[str] = None
) -> None:

    kb_path  = Path(knowledge_base_path)
    base_dir = Path(emails_folder)
    api_key  = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌  OPENAI_API_KEY not set")
        sys.exit(1)

    if not kb_path.exists():
        print(f"❌  Not found: {kb_path}")
        sys.exit(1)

    with open(kb_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # Support both root-list and {"knowledge_base": [...]} structures
    if isinstance(raw, dict):
        knowledge_base = raw["knowledge_base"]
        root = raw  # keep reference to write back correctly
    else:
        knowledge_base = raw
        root = None

    print(f"📚  Loaded {len(knowledge_base)} entries from knowledge_base.json\n")

    # Filter by IDs if requested
    entries = [
        e for e in knowledge_base
        if isinstance(e, dict)
        and (only_ids is None or str(e.get("id", "")) in only_ids)
    ]

    print(f"🔍  Classifying {len(entries)} entries via LLM...")
    print("=" * 80)

    skipped_no_code = 0
    skipped_missing = 0
    updated         = 0
    failed          = 0

    for i, entry in enumerate(entries, 1):
        entry_id  = str(entry.get("id", ""))
        conv_file = base_dir / entry_id / "conversation.json"

        print(f"[{i}/{len(entries)}] ID: {entry_id}")

        if not conv_file.exists():
            print(f"    ✗ conversation.json not found — skipping")
            skipped_missing += 1
            continue

        email_text = load_email_conversation(str(conv_file))
        if not email_text:
            skipped_missing += 1
            continue

        # ── Step 1: LLM classification ────────────────────────────────────
        verdict = classify_email(email_text, api_key)

        if verdict is None:
            print(f"    ✗ Classification failed — skipping")
            failed += 1
            continue

        if verdict == "NO_UPDATE":
            print(f"    — no code/API detected, skipping")
            skipped_no_code += 1
            continue

        print(f"    ⚡ code/API detected — re-extracting")

        if dry_run:
            print(f"    [DRY RUN] Would update entry: {entry_id}")
            updated += 1
            continue

        # ── Step 2: Code-preserving re-extraction ─────────────────────────
        result = extract_with_openai(email_text, api_key)

        if result is None:
            print(f"    ✗ Extraction failed")
            failed += 1
            continue

        # Update fields directly on the entry (matching the actual JSON structure)
        for kb_entry in knowledge_base:
            if isinstance(kb_entry, dict) and str(kb_entry.get("id")) == entry_id:
                kb_entry["problem"]  = result.get("problem",  kb_entry.get("problem"))
                kb_entry["solution"] = result.get("solution", kb_entry.get("solution"))
                kb_entry["keywords"] = result.get("keywords", kb_entry.get("keywords"))
                kb_entry["category"] = result.get("category", kb_entry.get("category"))
                print(f"    ✓ Updated — Category: {kb_entry['category']}")
                updated += 1
                break

    # ── Save ─────────────────────────────────────────────────────────────────
    if not dry_run and updated > 0:
        backup = kb_path.with_suffix(".backup.json")
        # Save backup of original raw structure
        with open(backup, 'w', encoding='utf-8') as f:
            json.dump(root if root else knowledge_base, f, indent=2, ensure_ascii=False)
        print(f"\n💾  Backup saved → {backup.name}")

        # Write back preserving the original root structure
        output = root if root else knowledge_base
        if root:
            root["knowledge_base"] = knowledge_base
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"✅  knowledge_base.json updated")
    elif updated == 0 and not dry_run:
        print("\nℹ️   No entries needed updating.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"Scanned              : {len(entries)}")
    print(f"Skipped (no code)    : {skipped_no_code}")
    print(f"Skipped (missing)    : {skipped_missing}")
    print(f"Re-extracted/updated : {updated}")
    print(f"Failed               : {failed}")
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Re-extract emails with code/API/scripts, preserving them verbatim."
    )
    parser.add_argument("--kb",            type=str,  help="Path to knowledge_base.json")
    parser.add_argument("--emails-folder", type=str,  help="Path to email_conversations_no_attachments folder")
    parser.add_argument("--ids",           type=str,  nargs="+", help="Only process specific IDs")
    parser.add_argument("--dry-run",       action="store_true",  help="Preview without saving")
    args = parser.parse_args()

    parent_dir    = Path(__file__).parent
    kb_path       = args.kb            or str(parent_dir / "knowledge_base.json")
    emails_folder = args.emails_folder or str(parent_dir / "email_conversations_no_attachments")

    print("=" * 80)
    print("🔧  Update Knowledge Base — LLM Code/API Detection + Verbatim Re-Extraction")
    print("=" * 80)
    print(f"📄  knowledge_base.json : {kb_path}")
    print(f"📁  Emails folder       : {emails_folder}")
    if args.ids:     print(f"🎯  Targeting IDs       : {', '.join(args.ids)}")
    if args.dry_run: print("📋  DRY RUN — nothing will be saved")
    print()

    update_knowledge_base(kb_path, emails_folder, dry_run=args.dry_run, only_ids=args.ids)


if __name__ == "__main__":
    main()