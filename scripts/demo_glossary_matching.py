#!/usr/bin/env python3
"""
Demonstrate Glossary Term Matching

Shows how glossary terms are detected and matched in Chinese source text
WITHOUT doing actual translation (faster demonstration).
"""

import sys
import json
import logging
from pathlib import Path


from utils.wuxia_glossary import WuxiaGlossary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Demonstrate glossary matching on wuxia_0004 source text"""

    # Load cleaned JSON (use wuxia_0004 which is "書劍恩仇錄")
    input_path = Path("/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0004/D58a_書劍恩仇錄上_金庸.json")

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        logger.error("Available alternatives:")
        alt_path = Path("/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0004/D58b_書劍恩仇錄下_金庸.json")
        if alt_path.exists():
            logger.info(f"  Found: {alt_path}")
        return 1

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        return 1

    # Load glossary
    glossary_path = Path(__file__).parent.parent / "wuxia_glossary.db"

    if not glossary_path.exists():
        logger.error(f"Glossary database not found: {glossary_path}")
        return 1

    try:
        glossary = WuxiaGlossary(glossary_path)
        logger.info(f"✓ Loaded wuxia glossary from {glossary_path}")
    except Exception as e:
        logger.error(f"Failed to load glossary: {e}")
        return 1

    # Extract book metadata
    meta = book_data.get('meta', {})
    title = meta.get('title', 'Unknown')
    author = meta.get('author', 'Unknown')

    print(f"\n{'='*80}")
    print(f"GLOSSARY TERM MATCHING DEMONSTRATION")
    print(f"{'='*80}")
    print(f"\nBook: {title} by {author}")
    print(f"Input: {input_path.name}\n")

    # Get chapters
    chapters = book_data.get('structure', {}).get('body', {}).get('chapters', [])

    if not chapters:
        logger.error("No chapters found")
        return 1

    print(f"Found {len(chapters)} chapters\n")
    print(f"{'='*80}\n")

    # Analyze first 3 chapters
    total_blocks = 0
    blocks_with_terms = 0
    all_matched_terms = set()

    for i, chapter in enumerate(chapters[:3], 1):
        chapter_title = chapter.get('title', 'Untitled')
        content_blocks = chapter.get('content_blocks', [])

        print(f"Chapter {i}: {chapter_title}")
        print(f"  Blocks: {len(content_blocks)}")

        chapter_terms = set()
        chapter_blocks_with_terms = 0

        # Analyze each block
        for block_idx, block in enumerate(content_blocks[:10], 1):  # First 10 blocks per chapter
            content = block.get('content', '')

            if not content or len(content) < 10:
                continue

            total_blocks += 1

            # Find glossary terms
            matches = glossary.find_in_text(content, max_matches=30)

            if matches:
                blocks_with_terms += 1
                chapter_blocks_with_terms += 1

                # Show first block with terms in detail
                if chapter_blocks_with_terms == 1:
                    print(f"\n  Sample Block {block_idx} (ID: {block.get('id', 'unknown')}):")
                    print(f"    Source text: {content[:150]}...")
                    print(f"    Glossary terms found: {len(matches)}")

                    for term, entry, pos in matches[:5]:  # Show first 5 terms
                        chapter_terms.add(term)
                        all_matched_terms.add(term)

                        print(f"\n    [{pos}] {term}")
                        print(f"      Pinyin: {entry.pinyin}")
                        print(f"      Strategy: {entry.translation_strategy}")
                        print(f"      Recommended Form: {entry.recommended_form}")
                        print(f"      Footnote (first 120 chars): {entry.footnote_template[:120]}...")
                        print(f"      Deduplication: {entry.deduplication_strategy}")
                        print(f"      Frequency: {entry.expected_frequency}")

                else:
                    # Just collect terms from other blocks
                    for term, entry, pos in matches:
                        chapter_terms.add(term)
                        all_matched_terms.add(term)

        print(f"\n  Unique terms in chapter: {len(chapter_terms)}")
        print(f"  Blocks with terms: {chapter_blocks_with_terms}/{len(content_blocks[:10])}")
        print(f"\n{'='*80}\n")

    # Summary statistics
    print(f"{'='*80}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*80}\n")
    print(f"Chapters analyzed: 3")
    print(f"Blocks analyzed: {total_blocks}")
    print(f"Blocks with glossary terms: {blocks_with_terms} ({blocks_with_terms/total_blocks*100:.1f}%)")
    print(f"Unique terms matched: {len(all_matched_terms)}")

    # Show all unique terms
    print(f"\n{'='*80}")
    print(f"ALL UNIQUE GLOSSARY TERMS FOUND ({len(all_matched_terms)} total)")
    print(f"{'='*80}\n")

    terms_with_entries = []
    for term in sorted(all_matched_terms):
        entry = glossary.lookup(term)
        if entry:
            terms_with_entries.append((term, entry))

    # Group by category
    from collections import defaultdict
    by_category = defaultdict(list)
    for term, entry in terms_with_entries:
        by_category[entry.category].append((term, entry))

    for category, terms in sorted(by_category.items()):
        print(f"{category} ({len(terms)} terms):")
        for term, entry in sorted(terms)[:10]:  # Show first 10 per category
            print(f"  {term} → {entry.recommended_form} ({entry.pinyin})")
        if len(terms) > 10:
            print(f"  ... and {len(terms) - 10} more")
        print()

    print(f"\n{'='*80}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'='*80}\n")

    glossary.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
