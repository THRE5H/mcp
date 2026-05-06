"""
Knowledge Base Aggregator
Collects all useful email summaries into a single JSON file for the chatbot
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import sys
from datetime import datetime


def collect_useful_summaries(base_folder: str, output_file: str = "knowledge_base.json") -> None:
    """Collect all useful email summaries into a single knowledge base file"""
    
    base_path = Path(base_folder)
    
    if not base_path.exists():
        print(f"❌ Folder not found: {base_folder}")
        return
    
    knowledge_base = []
    stats = {
        "total_folders": 0,
        "useful_count": 0,
        "useless_count": 0,
        "error_count": 0,
        "categories": {}
    }
    
    print("\n📚 Collecting useful summaries for knowledge base...")
    print("=" * 80)
    
    # Get all email folders
    email_folders = sorted([f for f in base_path.iterdir() if f.is_dir()])
    stats["total_folders"] = len(email_folders)
    
    for email_folder in email_folders:
        summary_file = email_folder / "summary.json"
        
        # Skip if no summary exists
        if not summary_file.exists():
            continue
        
        try:
            # Load summary
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Check if useful
            if summary_data.get('is_useful', False):
                # Create knowledge entry with original folder name as ID
                entry = {
                    "id": email_folder.name,  # Original folder name as unique ID
                    "problem": summary_data['summary']['problem'],
                    "solution": summary_data['summary']['solution'],
                    "keywords": summary_data['summary']['keywords'],
                    "category": summary_data['summary']['category']
                }
                
                knowledge_base.append(entry)
                stats["useful_count"] += 1
                
                # Track category statistics
                category = summary_data['summary']['category']
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                
                print(f"  ✓ Added: {email_folder.name[:60]}... [{category}]")
            else:
                stats["useless_count"] += 1
                
        except Exception as e:
            print(f"  ✗ Error processing {email_folder.name[:60]}...: {e}")
            stats["error_count"] += 1
    
    # Create final knowledge base structure
    knowledge_base_output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_entries": len(knowledge_base),
            "source_folder": str(base_path),
            "statistics": stats
        },
        "knowledge_base": knowledge_base
    }
    
    # Save to file
    output_path = Path(base_folder).parent / output_file
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base_output, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 80)
        print("✅ KNOWLEDGE BASE CREATED SUCCESSFULLY")
        print("=" * 80)
        print(f"📄 Output file: {output_path}")
        print(f"📊 Total useful entries: {len(knowledge_base)}")
        print(f"📂 Categories breakdown:")
        for category, count in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
            print(f"   - {category}: {count}")
        print("=" * 80)
        
        # Show sample entries
        if knowledge_base:
            print("\n📝 Sample entries:")
            print("-" * 80)
            for i, entry in enumerate(knowledge_base[:3], 1):
                print(f"\n{i}. ID: {entry['id'][:50]}...")
                print(f"   Category: {entry['category']}")
                print(f"   Problem: {entry['problem'][:80]}...")
                print(f"   Keywords: {', '.join(entry['keywords'][:5])}")
            print("-" * 80)
        
    except Exception as e:
        print(f"\n❌ Error saving knowledge base: {e}")


def search_knowledge_base(knowledge_file: str, query: str) -> None:
    """Test search functionality in the knowledge base"""
    
    try:
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        knowledge_base = data.get('knowledge_base', [])
        
        print(f"\n🔍 Searching for: '{query}'")
        print("=" * 80)
        
        results = []
        query_lower = query.lower()
        
        for entry in knowledge_base:
            # Simple keyword matching
            if (query_lower in entry['problem'].lower() or 
                query_lower in entry['solution'].lower() or
                any(query_lower in keyword.lower() for keyword in entry['keywords'])):
                results.append(entry)
        
        if results:
            print(f"Found {len(results)} matching entries:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. [{result['category']}]")
                print(f"   ID: {result['id'][:50]}...")
                print(f"   Problem: {result['problem'][:100]}...")
                print(f"   Solution: {result['solution'][:100]}...")
                print(f"   Keywords: {', '.join(result['keywords'][:5])}")
                print()
        else:
            print("No matching entries found.")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error searching knowledge base: {e}")


def export_by_category(knowledge_file: str, output_folder: str = "knowledge_by_category") -> None:
    """Export knowledge base split by category"""
    
    try:
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        knowledge_base = data.get('knowledge_base', [])
        
        # Group by category
        by_category = {}
        for entry in knowledge_base:
            category = entry['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(entry)
        
        # Create output folder
        output_path = Path(knowledge_file).parent / output_folder
        output_path.mkdir(exist_ok=True)
        
        print(f"\n📁 Exporting knowledge base by category to: {output_path}")
        print("=" * 80)
        
        # Save each category
        for category, entries in by_category.items():
            category_file = output_path / f"{category.lower().replace(' ', '_')}.json"
            
            category_data = {
                "category": category,
                "total_entries": len(entries),
                "entries": entries
            }
            
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(category_data, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ {category}: {len(entries)} entries → {category_file.name}")
        
        print("=" * 80)
        print(f"✅ Exported {len(by_category)} category files")
        
    except Exception as e:
        print(f"❌ Error exporting by category: {e}")


def show_stats(knowledge_file: str) -> None:
    """Display detailed statistics about the knowledge base"""
    
    try:
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        knowledge_base = data.get('knowledge_base', [])
        
        print("\n📊 KNOWLEDGE BASE STATISTICS")
        print("=" * 80)
        print(f"Generated: {metadata.get('generated_at', 'Unknown')}")
        print(f"Total entries: {metadata.get('total_entries', 0)}")
        print(f"Source: {metadata.get('source_folder', 'Unknown')}")
        print()
        
        stats = metadata.get('statistics', {})
        print(f"Total folders processed: {stats.get('total_folders', 0)}")
        print(f"Useful emails: {stats.get('useful_count', 0)}")
        print(f"Useless emails: {stats.get('useless_count', 0)}")
        print(f"Errors: {stats.get('error_count', 0)}")
        
        if stats.get('useful_count', 0) > 0 and stats.get('total_folders', 0) > 0:
            percentage = (stats['useful_count'] / stats['total_folders']) * 100
            print(f"Usefulness rate: {percentage:.1f}%")
        
        print("\n📂 Categories:")
        categories = stats.get('categories', {})
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: {count}")
        
        # Keyword analysis
        all_keywords = []
        for entry in knowledge_base:
            all_keywords.extend(entry.get('keywords', []))
        
        if all_keywords:
            from collections import Counter
            top_keywords = Counter(all_keywords).most_common(10)
            print("\n🔑 Top 10 Keywords:")
            for keyword, count in top_keywords:
                print(f"   {keyword}: {count}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error reading knowledge base: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Base Aggregator")
    parser.add_argument("--folder", type=str, help="Path to email conversations folder")
    parser.add_argument("--output", type=str, default="knowledge_base.json", help="Output JSON file name")
    parser.add_argument("--search", type=str, help="Search the knowledge base")
    parser.add_argument("--export-by-category", action="store_true", help="Export knowledge base split by category")
    parser.add_argument("--stats", action="store_true", help="Show knowledge base statistics")
    
    args = parser.parse_args()
    
    # Determine folder path
    if args.folder:
        base_folder = args.folder
    else:
        # Default path
        parent_dir = Path(__file__).parent.parent
        base_folder = str(parent_dir / "email_conversations (2)" / "email_conversations_no_attachments")
    
    # Determine knowledge base file path
    knowledge_file = str(Path(base_folder).parent / args.output)
    
    # Stats mode
    if args.stats:
        show_stats(knowledge_file)
        return
    
    # Search mode
    if args.search:
        search_knowledge_base(knowledge_file, args.search)
        return
    
    # Export by category mode
    if args.export_by_category:
        export_by_category(knowledge_file)
        return
    
    # Default: collect summaries
    print(f"📁 Source folder: {base_folder}")
    print(f"📄 Output file: {knowledge_file}")
    
    collect_useful_summaries(base_folder, args.output)


if __name__ == "__main__":
    main()