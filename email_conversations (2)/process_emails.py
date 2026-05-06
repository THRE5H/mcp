"""
Email Conversation Knowledge Extractor using OpenAI API
Processes email JSON files and extracts useful problem-solution pairs for knowledge base
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# System prompt template for knowledge extraction
SYSTEM_PROMPT = """You are an expert email analyst specialized in extracting actionable knowledge from customer support conversations. Your task is to analyze email threads and determine whether they contain reusable solutions that can help answer future customer queries.

## Your Role
Analyze the provided email conversation and extract problem-solution pairs ONLY if the email contains useful, actionable, and TIMELESS information. Focus on the semantic meaning and technical content, not on specific names or organizations.

## Classification Rules

### USEFUL EMAILS - Extract Summary
An email is useful if it contains:
- A clear technical problem with a COMPLETE and REUSABLE solution
- Step-by-step instructions or procedures that can be applied in the future
- Configuration changes or settings that solve a recurring issue
- Explanations of features with actionable guidance
- Error messages with their permanent resolutions
- How-to guides or workarounds that are still valid
- Links to resources with context (only if the resource is permanent, not temporary)
- Format changes, system updates, or migration instructions that are complete

### USELESS EMAILS - Return Empty Summary
An email is NOT useful if it:
- Only provides credentials, passwords, or one-time access grants
- Simply adds/removes users from mailing lists or distribution groups
- Contains only acknowledgments ("Thank you", "Received", "OK")
- Is purely administrative (scheduling, internal coordination)
- Shows UNRESOLVED problems or ONGOING investigations
- Mentions tickets being created, bugs being investigated, or issues being escalated
- Requires manual support intervention without a reusable pattern
- Contains incomplete conversations without final resolution
- Only has greetings, sign-offs, or courtesy messages
- Promises future fixes ("will be resolved", "ticket created", "working on it")
- Contains temporary workarounds that are no longer valid
- References time-specific events or one-time custom solutions
- Solution is "contact support" or "we'll handle this manually"

## CRITICAL: Timeless Knowledge Rule
The solution must be COMPLETE and APPLICABLE IN THE FUTURE. Reject emails where:
- The issue was escalated but not resolved
- A ticket was created but no fix is described
- The solution is "we're working on it" or "investigating"
- The solution involves custom/manual work by support team
- The outcome is uncertain or pending

## Output Requirements

Return ONLY a valid JSON object in this exact format:

For USEFUL emails:
{
  "is_useful": true,
  "summary": {
    "problem": "Description of the issue from user perspective, without mentioning specific names",
    "solution": "Complete, actionable, and reusable solution that can be applied by future users or a chatbot",
    "keywords": ["relevant", "technical", "terms"],
    "category": "Issue category"
  }
}

For USELESS emails:
{
  "is_useful": false,
  "summary": null
}

## Extraction Guidelines

1. **Anonymize**: Remove all personal names, company names, and email addresses from the summary
2. **Focus on patterns**: Extract the general problem pattern, not the specific instance
3. **Be complete**: Include all steps and details needed to reproduce the solution
4. **Use technical terms**: Preserve product names, feature names, error codes, and technical terminology
5. **Keep it actionable**: The solution should be clear enough for a chatbot to provide as an answer WITHOUT human intervention
6. **Generate smart keywords**: Include variations and synonyms that users might search for
7. **Categorize consistently**: Use standard categories like:
   - "Access Issue"
   - "Download Problem" 
   - "Configuration"
   - "Error Resolution"
   - "Feature Explanation"
   - "How-to Guide"
   - "Integration Issue"
   - "Platform Navigation"

8. **Exclude temporary information**: 
   - Remove mentions of ticket numbers, ongoing investigations
   - Remove promises of future fixes
   - Remove "we will look into this" type statements
   - Focus only on what WAS solved and HOW

## Example Transformations

### Example 1: USEFUL
Input: "Download button not working in TradeMatrix. Issue resolved. Download button is now functional. Users should use new code format 'sucden-xxxx-xxxx' instead of deprecated 'dnexr-xxxx-xxxx' format for automatic updates."

Output:
{
  "is_useful": true,
  "summary": {
    "problem": "Download button not functional in TradeMatrix interface",
    "solution": "To access TradeMatrix downloads, use the new code format 'sucden-xxxx-xxxx' instead of the deprecated 'dnexr-xxxx-xxxx' format. The new format ensures dynamic updates and changes to resources are automatically reflected. Access TradeMatrix using URLs in the format: https://[domain]/fundamentals/tradematrix/sucden-[uuid]. The download button is located in the interface toolbar.",
    "keywords": ["TradeMatrix", "download", "button", "not working", "code format", "sucden", "dnexr", "deprecated", "migration"],
    "category": "Download Problem"
  }
}

### Example 2: USELESS (Ticket created, no resolution)
Input: "User requests dataset for feed grain. Tradematrix created at link X. Issue with saving forecasts - ticket created to fix the bug."

Output:
{
  "is_useful": false,
  "summary": null
}

Reason: Mentions "ticket created" and unresolved bug. Not a complete solution.

### Example 3: USELESS (Mailing list)
Input: "Please add user@company.com to mailing list. Response: Done, user added successfully."

Output:
{
  "is_useful": false,
  "summary": null
}

### Example 4: USELESS (Access credentials)
Input: "Can you give me access to environment? Response: User: user@domain.com Password: xyz123"

Output:
{
  "is_useful": false,
  "summary": null
}

### Example 5: USEFUL (Complete how-to)
Input: "How to export data from TradeMatrix? Click the export button in top right, select CSV format, choose date range, click download. File will download to your browser's download folder."

Output:
{
  "is_useful": true,
  "summary": {
    "problem": "User needs to export data from TradeMatrix platform",
    "solution": "To export data from TradeMatrix: 1) Click the export button located in the top right corner of the interface, 2) Select CSV format from the format dropdown, 3) Choose your desired date range, 4) Click the download button. The file will automatically download to your browser's default download folder.",
    "keywords": ["TradeMatrix", "export", "data", "CSV", "download", "how to"],
    "category": "How-to Guide"
  }
}

### Example 6: USELESS (Ongoing investigation)
Input: "Error 500 when loading page. We're investigating the issue. Will update you once fixed."

Output:
{
  "is_useful": false,
  "summary": null
}

Reason: No solution provided, still under investigation.

## Important Notes

- Do NOT include any conversational text, only the JSON output
- Do NOT mention specific user names, support agent names, or company names in the summary
- DO preserve product names, feature names, and technical identifiers
- Focus on extracting knowledge that would help OTHER users with SIMILAR problems
- If the solution is incomplete or mentions "ticket created", "investigating", "will fix", mark as NOT useful
- If in doubt about usefulness, err on the side of marking it as NOT useful
- The problem and solution should make sense even without knowing who was involved
- The solution must be something a chatbot can provide without human intervention

Now analyze the provided email conversation and return the appropriate JSON response."""


def load_email_conversation(json_path: str) -> str:
    """Load email conversation from JSON file and format it as text"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        emails = data.get('emails', [])
        conversation_text = []
        
        # Process emails in reverse order (oldest first)
        for email in reversed(emails):
            from_name = email.get('from_name', 'Unknown')
            to_name = email.get('to', 'Unknown')
            subject = email.get('subject', 'No Subject')
            body = email.get('body_text', '')
            sent_time = email.get('sent_time', 'Unknown time')
            
            conversation_text.append(f"From: {from_name}")
            conversation_text.append(f"To: {to_name}")
            conversation_text.append(f"Time: {sent_time}")
            conversation_text.append(f"Subject: {subject}")
            conversation_text.append(f"Body:\n{body}")
            conversation_text.append("=" * 80)
        
        return "\n".join(conversation_text)
    except Exception as e:
        print(f"Error loading JSON from {json_path}: {e}")
        return ""


def extract_knowledge_with_openai(email_content: str, openai_api_key: str) -> Optional[Dict[str, Any]]:
    """Send email content to OpenAI and extract knowledge"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # Use "gpt-4o" for better quality
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": email_content
                }
            ],
            max_tokens=800,
            temperature=0.1,  # Very low temperature for consistent extraction
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON response
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            print(f"  ✗ Failed to parse JSON response: {e}")
            print(f"  Raw response: {content[:200]}...")
            return None
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


def delete_all_summaries(base_folder: str) -> int:
    """Delete all summary.json files in the folder structure"""
    base_path = Path(base_folder)
    deleted_count = 0
    
    if not base_path.exists():
        print(f"Folder not found: {base_folder}")
        return 0
    
    print("\n🗑️  Deleting existing summary files...")
    print("=" * 80)
    
    # Get folders in natural order (as they appear in filesystem)
    email_folders = [f for f in base_path.iterdir() if f.is_dir()]
    
    for email_folder in email_folders:
        summary_file = email_folder / "summary.json"
        
        if summary_file.exists():
            try:
                summary_file.unlink()
                print(f"  ✓ Deleted: {email_folder.name}/summary.json")
                deleted_count += 1
            except Exception as e:
                print(f"  ✗ Error deleting {email_folder.name}/summary.json: {e}")
    
    print("=" * 80)
    print(f"Total summaries deleted: {deleted_count}\n")
    
    return deleted_count


def process_email_folder(base_folder: str, openai_api_key: str, dry_run: bool = False) -> None:
    """Process all email folders and generate knowledge extractions in filesystem order"""
    
    base_path = Path(base_folder)
    
    if not base_path.exists():
        print(f"Folder not found: {base_folder}")
        return
    
    # Count statistics
    total_processed = 0
    useful_emails = 0
    useless_emails = 0
    failed_extractions = 0
    
    # Get all email folders in natural filesystem order
    email_folders = sorted([f for f in base_path.iterdir() if f.is_dir()])
    total_folders = len(email_folders)
    
    print("\n📧 Processing email conversations for knowledge extraction...")
    print("=" * 80)
    
    # Iterate through each email folder
    for index, email_folder in enumerate(email_folders, 1):
        json_file = email_folder / "conversation.json"
        summary_file = email_folder / "summary.json"
        
        # Check if JSON file exists
        if not json_file.exists():
            print(f"[{index}/{total_folders}] ✗ No conversation.json: {email_folder.name}")
            continue
        
        print(f"[{index}/{total_folders}] ▶ Processing: {email_folder.name}...")
        total_processed += 1
        
        # Load email content
        email_content = load_email_conversation(str(json_file))
        if not email_content:
            print(f"  ✗ Failed to load email content")
            failed_extractions += 1
            continue
        
        if dry_run:
            print(f"  [DRY RUN] Would save extraction to: {summary_file.name}")
            useful_emails += 1
            continue
        
        # Extract knowledge
        extraction = extract_knowledge_with_openai(email_content, openai_api_key)
        
        if extraction:
            # Save extraction to file
            try:
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(extraction, f, indent=2, ensure_ascii=False)
                
                # Check if useful or not
                if extraction.get('is_useful', False):
                    print(f"  ✓ USEFUL - Knowledge extracted successfully")
                    print(f"    Category: {extraction['summary'].get('category', 'N/A')}")
                    useful_emails += 1
                else:
                    print(f"  ○ USELESS - No actionable knowledge")
                    useless_emails += 1
                    
            except Exception as e:
                print(f"  ✗ Error saving extraction: {e}")
                failed_extractions += 1
        else:
            print(f"  ✗ Failed to extract knowledge")
            failed_extractions += 1
    
    # Print statistics
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total folders found: {total_folders}")
    print(f"Total processed: {total_processed}")
    print(f"Useful emails (knowledge extracted): {useful_emails}")
    print(f"Useless emails (no actionable info): {useless_emails}")
    print(f"Failed extractions: {failed_extractions}")
    
    if useful_emails > 0:
        print(f"\n📊 Knowledge Base Coverage: {(useful_emails/total_processed*100):.1f}% of emails contain useful information")
    
    print("=" * 80)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Email Knowledge Extractor with OpenAI")
    parser.add_argument("--folder", type=str, help="Path to email conversations folder")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving (test mode)")
    parser.add_argument("--delete-summaries", action="store_true", help="Delete all existing summary files before processing")
    
    args = parser.parse_args()
    
    # Get API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key in the .env file or environment variables")
        sys.exit(1)
    
    # Determine folder path
    if args.folder:
        base_folder = args.folder
    else:
        # Default: look for email_conversations_no_attachments in parent directory
        parent_dir = Path(__file__).parent.parent
        base_folder = str(parent_dir / "email_conversations (2)" / "email_conversations_no_attachments")
    
    print(f"📁 Processing emails from: {base_folder}")
    print(f"🔑 Using OpenAI API key: {openai_api_key[:8]}...")
    
    if args.dry_run:
        print("📋 DRY RUN MODE (no files will be saved)")
    
    # Delete existing summaries if requested
    if args.delete_summaries:
        delete_all_summaries(base_folder)
    
    # Process emails
    process_email_folder(base_folder, openai_api_key, dry_run=args.dry_run)


if __name__ == "__main__":
    main()