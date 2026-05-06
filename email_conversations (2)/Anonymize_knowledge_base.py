"""
Anonymize Knowledge Base - Post-Processing Step
================================================
Scans the updated knowledge_base.json and anonymizes sensitive data
in solution/problem fields:
  - Real URLs with org/env codes → [env/org].dnext.io/...
  - TradeMatrix codes → [env/org]-tradematrix_code
  - Real emails → xxx.xxx@org.xx
  - Passwords → xxxxx
  - Personal names → removed
  - Organisation-specific UUIDs in URLs → [uuid]
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


ANONYMIZER_PROMPT = """You are a data anonymization specialist. Your task is to anonymize sensitive information in a knowledge base entry while preserving its technical meaning and usefulness.

## What to anonymize

### URLs containing organisation/environment codes
Real URLs like:
  https://ngco.dnext.io/datasets/ngco-a410fb85-d8ab-11ef-82fc-06cd53a4d901
  https://zimb.dnext.io/fundamentals/tradematrix/zimb-77299e24-d469-47fd-b7fb-f7f2d4abaa9a
  https://demo.dnext.io

Must become:
  https://[env/org].dnext.io/datasets/[env/org]-[resource-type]
  https://[env/org].dnext.io/fundamentals/tradematrix/[env/org]-[uuid]
  https://[env/org].dnext.io

Keep the URL structure and path (datasets/, fundamentals/tradematrix/, etc.) so the reader understands what type of resource it is. Only replace the specific org/env prefix and UUIDs.

### TradeMatrix codes / dataset codes
Real codes like:
  zimb-77299e24-d469-47fd-b7fb-f7f2d4abaa9a
  ngco-a410fb85-d8ab-11ef-82fc-06cd53a4d901

Must become:
  [env/org]-[uuid]

### Email addresses
Real emails like:
  guillaume.goudy@dnext.io
  user@company.com

Must become:
  xxx.xxx@org.xx

### Passwords / credentials
Real passwords like:
  gF3H8z94ojL9
  Password123

Must become:
  xxxxx

### Personal names
Remove specific first name + last name combinations (e.g. "Alexander Prindle", "Guillaume Goudy").
Replace with generic phrasing like "the user" or "the client".

### Organisation/client names (non-platform)
Remove client or partner company names (e.g. "Trafigura", "Wilmar", "Shell", "Axxela").
Replace with "the client" or "the organisation".

## What NOT to anonymize
- Product names: TradeMatrix, Dnext, Dashboard, Datasets, Freights
- Feature names: Export, Download, Summarized Data, Panel View
- Technical terms: API, Bearer token, curl, JSON, CSV, xlsx
- Generic domain structure: dnext.io (the platform domain itself is fine to keep)
- Step-by-step instructions
- Error messages
- Category names or keywords

## Rules
1. Keep code blocks intact — only anonymize the sensitive VALUES inside them, not the code structure
2. Preserve all markdown formatting (``` fences, numbered lists, bullet points)
3. Do not change the meaning or completeness of the solution
4. If nothing needs anonymizing, return the fields unchanged

## Output Format
Return ONLY this JSON object, nothing else:
{
  "problem": "anonymized problem text",
  "solution": "anonymized solution text",
  "keywords": ["keyword1", "keyword2"],
  "category": "same category as input"
}

Do not add any explanation outside the JSON.
"""


def anonymize_entry(entry: Dict[str, Any], api_key: str) -> Optional[Dict[str, Any]]:
    """Send one entry to LLM for anonymization."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        content = json.dumps({
            "problem":  entry.get("problem", ""),
            "solution": entry.get("solution", ""),
            "keywords": entry.get("keywords", []),
            "category": entry.get("category", "")
        }, ensure_ascii=False)

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": ANONYMIZER_PROMPT},
                {"role": "user",   "content": content}
            ],
            max_tokens=1500,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"    ✗ API error: {e}")
        return None


def needs_anonymization(entry: Dict[str, Any]) -> bool:
    """
    Quick pre-check: does this entry likely contain sensitive data?
    Looks for dnext.io URLs with org prefixes, emails, passwords, UUIDs.
    """
    text = json.dumps(entry).lower()
    signals = [
        "dnext.io",          # any dnext URL
        "@",                  # email address
        "password",           # password mention
        "credentials",        # credentials mention
        # UUID pattern rough check
        "-47fd-", "-11ef-", "-d8ab-", "-d469-",
    ]
    return any(s in text for s in signals)


def anonymize_knowledge_base(
    knowledge_base_path: str,
    dry_run: bool = False,
    only_ids: List[str] = None
) -> None:

    kb_path = Path(knowledge_base_path)
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌  OPENAI_API_KEY not set")
        sys.exit(1)

    if not kb_path.exists():
        print(f"❌  Not found: {kb_path}")
        sys.exit(1)

    with open(kb_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        knowledge_base = raw["knowledge_base"]
        root = raw
    else:
        knowledge_base = raw
        root = None

    print(f"📚  Loaded {len(knowledge_base)} entries\n")

    entries = [
        e for e in knowledge_base
        if isinstance(e, dict)
        and (only_ids is None or str(e.get("id", "")) in only_ids)
    ]

    print(f"🔍  Scanning {len(entries)} entries for sensitive data...")
    print("=" * 80)

    skipped    = 0
    updated    = 0
    failed     = 0

    for i, entry in enumerate(entries, 1):
        entry_id = str(entry.get("id", ""))
        print(f"[{i}/{len(entries)}] ID: {entry_id}")

        # Quick pre-check to avoid unnecessary API calls
        if not needs_anonymization(entry):
            print(f"    — no sensitive data detected, skipping")
            skipped += 1
            continue

        print(f"    ⚠️  sensitive data detected — anonymizing")

        if dry_run:
            print(f"    [DRY RUN] Would anonymize entry: {entry_id}")
            updated += 1
            continue

        result = anonymize_entry(entry, api_key)

        if result is None:
            print(f"    ✗ Anonymization failed")
            failed += 1
            continue

        # Update only the content fields, keep id intact
        for kb_entry in knowledge_base:
            if isinstance(kb_entry, dict) and str(kb_entry.get("id")) == entry_id:
                kb_entry["problem"]  = result.get("problem",  kb_entry["problem"])
                kb_entry["solution"] = result.get("solution", kb_entry["solution"])
                kb_entry["keywords"] = result.get("keywords", kb_entry["keywords"])
                kb_entry["category"] = result.get("category", kb_entry["category"])
                print(f"    ✓ Anonymized")
                updated += 1
                break

    # ── Save ─────────────────────────────────────────────────────────────────
    if not dry_run and updated > 0:
        backup = kb_path.with_suffix(".pre_anonymize.json")
        with open(backup, 'w', encoding='utf-8') as f:
            json.dump(root if root else knowledge_base, f, indent=2, ensure_ascii=False)
        print(f"\n💾  Backup saved → {backup.name}")

        if root:
            root["knowledge_base"] = knowledge_base
        with open(kb_path, 'w', encoding='utf-8') as f:
            json.dump(root if root else knowledge_base, f, indent=2, ensure_ascii=False)
        print(f"✅  knowledge_base.json anonymized and saved")
    elif updated == 0 and not dry_run:
        print("\nℹ️   No entries needed anonymization.")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"Scanned              : {len(entries)}")
    print(f"Skipped (clean)      : {skipped}")
    print(f"Anonymized           : {updated}")
    print(f"Failed               : {failed}")
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Anonymize sensitive data in knowledge_base.json entries."
    )
    parser.add_argument("--kb",      type=str, help="Path to knowledge_base.json")
    parser.add_argument("--ids",     type=str, nargs="+", help="Only process specific IDs")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    parent_dir = Path(__file__).parent
    kb_path    = args.kb or str(parent_dir / "knowledge_base.json")

    print("=" * 80)
    print("🔒  Anonymize Knowledge Base — Remove Sensitive Data")
    print("=" * 80)
    print(f"📄  knowledge_base.json : {kb_path}")
    if args.ids:     print(f"🎯  Targeting IDs       : {', '.join(args.ids)}")
    if args.dry_run: print("📋  DRY RUN — nothing will be saved")
    print()

    anonymize_knowledge_base(kb_path, dry_run=args.dry_run, only_ids=args.ids)


if __name__ == "__main__":
    main()