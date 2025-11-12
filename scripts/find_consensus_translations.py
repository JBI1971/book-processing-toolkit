#!/usr/bin/env python3
"""
Find Consensus Wuxia Translations

Uses OpenAI to find the consensus English translations used by the wuxia community
for works and authors. Stores results in a separate table that can be joined with works.

This preserves the original CSV translations while providing community-accepted names.
"""

import sys
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.load_env_creds import get_openai_api_key
from openai import OpenAI

# Load API key
api_key = get_openai_api_key()
client = OpenAI(api_key=api_key)


def create_consensus_table(db_path: str):
    """Create table for consensus translations if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS works_consensus_translations (
            work_id INTEGER PRIMARY KEY,
            consensus_title_english TEXT,
            consensus_author_english TEXT,
            title_rationale TEXT,
            author_rationale TEXT,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (work_id) REFERENCES works(work_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✓ Consensus translations table ready")


def get_consensus_translation(
    title_chinese: str,
    author_chinese: str,
    current_title_english: Optional[str] = None
) -> Dict[str, str]:
    """
    Use OpenAI to find the consensus English translation used by the wuxia community.

    Args:
        title_chinese: Chinese title
        author_chinese: Chinese author name
        current_title_english: Current English translation (if any)

    Returns:
        Dictionary with consensus_title, consensus_author, title_rationale, author_rationale
    """
    prompt = f"""You are an expert on Chinese wuxia literature and the English-speaking wuxia fan community.

Chinese Work: {title_chinese}
Chinese Author: {author_chinese}
Current English Translation: {current_title_english or "None"}

Task: Find the CONSENSUS English translation used by the wuxia community for this work and author.

Important guidelines:
1. For famous works (especially Jin Yong), use the well-established community translations
2. For authors, use the standard romanization (e.g., "Jin Yong" not "Louis Cha")
3. Check what WuxiaWorld, Volare Novels, and the Reddit wuxia community use
4. If current translation is already the consensus, confirm it
5. If work is obscure with no established translation, create a literal but natural English title

Examples of consensus translations:
- 神鵰俠侶 → "The Return of the Condor Heroes" (NOT "The Legend of the Condor Heroes")
- 天龍八部 → "Demi-Gods and Semi-Devils" (NOT "Dragon Babu")
- 笑傲江湖 → "The Smiling, Proud Wanderer" (NOT "Swordsman")
- 鹿鼎記 → "The Deer and the Cauldron" (correct)
- 射鵰英雄傳 → "The Legend of the Condor Heroes" (correct)

Respond ONLY with valid JSON in this exact format:
{{
  "consensus_title_english": "The actual consensus English title",
  "consensus_author_english": "Author name in standard romanization",
  "title_rationale": "Brief explanation of why this is the consensus (1-2 sentences)",
  "author_rationale": "Brief explanation of author name choice (1 sentence)"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert on wuxia literature translations. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"  ✗ Error getting consensus for {title_chinese}: {e}")
        return {
            "consensus_title_english": current_title_english or title_chinese,
            "consensus_author_english": author_chinese,
            "title_rationale": f"Error: {str(e)}",
            "author_rationale": f"Error: {str(e)}"
        }


def process_works(db_path: str, limit: Optional[int] = None, skip_existing: bool = True):
    """
    Process all works and find consensus translations.

    Args:
        db_path: Path to database
        limit: Optional limit on number of works to process
        skip_existing: Skip works that already have consensus translations
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get works that need consensus translations
    query = """
        SELECT
            w.work_id,
            w.work_number,
            w.title_chinese,
            w.author_chinese,
            w.title_english,
            w.author_english,
            wc.consensus_title_english
        FROM works w
        LEFT JOIN works_consensus_translations wc ON w.work_id = wc.work_id
        WHERE w.title_chinese IS NOT NULL AND w.title_chinese != ''
    """

    if skip_existing:
        query += " AND wc.consensus_title_english IS NULL"

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    works = cursor.fetchall()

    total = len(works)
    print(f"\nProcessing {total} works...")
    print()

    processed = 0
    updated = 0
    skipped = 0

    for work_id, work_num, title_zh, author_zh, title_en, author_en, existing_consensus in works:
        processed += 1

        if skip_existing and existing_consensus:
            skipped += 1
            continue

        print(f"[{processed}/{total}] {work_num}: {title_zh} ({author_zh})")

        # Get consensus translation
        consensus = get_consensus_translation(title_zh, author_zh, title_en)

        # Store in database
        cursor.execute("""
            INSERT OR REPLACE INTO works_consensus_translations
            (work_id, consensus_title_english, consensus_author_english,
             title_rationale, author_rationale, searched_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            work_id,
            consensus['consensus_title_english'],
            consensus['consensus_author_english'],
            consensus['title_rationale'],
            consensus['author_rationale']
        ))

        conn.commit()

        print(f"  ✓ Title: {consensus['consensus_title_english']}")
        print(f"    Author: {consensus['consensus_author_english']}")
        print(f"    Reason: {consensus['title_rationale']}")
        print()

        updated += 1

        # Rate limiting - be nice to OpenAI API
        time.sleep(1)

    conn.close()

    print("=" * 70)
    print(f"Processing complete!")
    print(f"  Total works: {total}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print("=" * 70)


def show_comparison(db_path: str, limit: int = 10):
    """Show comparison between original and consensus translations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            w.work_number,
            w.title_chinese,
            w.author_chinese,
            w.title_english AS original_title,
            w.author_english AS original_author,
            wc.consensus_title_english,
            wc.consensus_author_english,
            wc.title_rationale
        FROM works w
        JOIN works_consensus_translations wc ON w.work_id = wc.work_id
        WHERE wc.consensus_title_english IS NOT NULL
        ORDER BY w.directory_number
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()
    conn.close()

    print("\n" + "=" * 100)
    print("ORIGINAL vs CONSENSUS TRANSLATIONS")
    print("=" * 100)

    for work_num, title_zh, author_zh, orig_title, orig_author, cons_title, cons_author, rationale in results:
        print(f"\nWork {work_num}: {title_zh}")
        print(f"  Chinese Author: {author_zh}")
        print()
        print(f"  Original Title:   {orig_title}")
        print(f"  Consensus Title:  {cons_title}")
        if orig_title != cons_title:
            print(f"  → CHANGED")
        print()
        print(f"  Original Author:  {orig_author}")
        print(f"  Consensus Author: {cons_author}")
        if orig_author != cons_author:
            print(f"  → CHANGED")
        print()
        print(f"  Rationale: {rationale}")
        print("-" * 100)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Find consensus wuxia translations using OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all works (skip those already done)
  %(prog)s --db-path /path/to/wuxia_catalog.db

  # Process first 10 works
  %(prog)s --db-path /path/to/wuxia_catalog.db --limit 10

  # Reprocess works even if already have consensus
  %(prog)s --db-path /path/to/wuxia_catalog.db --no-skip-existing

  # Show comparison of original vs consensus
  %(prog)s --db-path /path/to/wuxia_catalog.db --compare-only

  # Default database location
  %(prog)s
        """
    )

    parser.add_argument(
        '--db-path',
        default='/Users/jacki/project_files/translation_project/wuxia_catalog.db',
        help='Path to catalog database (default: /Users/jacki/project_files/translation_project/wuxia_catalog.db)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of works to process'
    )
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Reprocess works that already have consensus translations'
    )
    parser.add_argument(
        '--compare-only',
        action='store_true',
        help='Only show comparison, don\'t process new works'
    )
    parser.add_argument(
        '--compare-limit',
        type=int,
        default=10,
        help='Number of works to show in comparison (default: 10)'
    )

    args = parser.parse_args()

    db_path = args.db_path

    if not Path(db_path).exists():
        print(f"❌ Error: Database not found: {db_path}")
        return 1

    print("=" * 70)
    print("Wuxia Consensus Translations Finder")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()

    # Create table
    create_consensus_table(db_path)

    if args.compare_only:
        # Just show comparison
        show_comparison(db_path, args.compare_limit)
    else:
        # Process works
        process_works(
            db_path,
            limit=args.limit,
            skip_existing=not args.no_skip_existing
        )

        # Show sample comparison
        print("\nShowing sample comparison (first 10)...")
        show_comparison(db_path, min(10, args.compare_limit))

    return 0


if __name__ == "__main__":
    sys.exit(main())
