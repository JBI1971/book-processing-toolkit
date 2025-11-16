#!/usr/bin/env python3
"""
Simple Glossary Matching Demonstration

Shows how glossary terms are detected and matched in sample wuxia text.
"""

import sys
import logging
from pathlib import Path


from utils.wuxia_glossary import WuxiaGlossary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample wuxia text passages
SAMPLE_TEXTS = [
    {
        "title": "Internal Energy Training",
        "text": "他自幼修煉內功，日夜不輟，內力深厚無比。少林派的易筋經與武當派的純陽無極功，都是武林中的上乘內功心法。"
    },
    {
        "title": "Lightness Skill Chase",
        "text": "那人輕功極高，身形飄忽，轉眼間已躍上屋頂。韋小寶施展輕功追趕，卻怎麼也追不上。"
    },
    {
        "title": "Martial Arts Duel",
        "text": "兩人在武林大會上比武較量，招式精妙絕倫。一個使出降龍十八掌，另一個則施展九陰真經中的武功。"
    },
    {
        "title": "Sword Technique",
        "text": "他手持寶劍，劍氣縱橫，劍法凌厲無匹。華山派的劍法名揚江湖，此刻展現得淋漓盡致。"
    },
    {
        "title": "Sect Background",
        "text": "少林寺乃武林正宗，武當山亦為名門大派。江湖中人無不敬仰這兩大門派的武學造詣。"
    }
]


def main():
    """Demonstrate glossary matching on sample texts"""

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

    print(f"\n{'='*80}")
    print(f"WUXIA GLOSSARY MATCHING DEMONSTRATION")
    print(f"{'='*80}\n")

    # Process each sample text
    for i, sample in enumerate(SAMPLE_TEXTS, 1):
        print(f"{'='*80}")
        print(f"SAMPLE {i}: {sample['title']}")
        print(f"{'='*80}\n")

        text = sample['text']
        print(f"Chinese Text:")
        print(f"  {text}\n")

        # Find glossary terms
        matches = glossary.find_in_text(text, max_matches=30)

        if matches:
            print(f"Glossary Terms Found: {len(matches)}\n")

            for j, (term, entry, pos) in enumerate(matches, 1):
                print(f"{j}. {term} (position {pos})")
                print(f"   Pinyin: {entry.pinyin}")
                print(f"   Translation Strategy: {entry.translation_strategy}")
                print(f"   Recommended Form: {entry.recommended_form}")
                print(f"   Category: {entry.category}")
                print(f"   Deduplication: {entry.deduplication_strategy}")
                print(f"   Frequency: {entry.expected_frequency}")
                print(f"\n   Footnote Template:")
                print(f"   {entry.footnote_template[:200]}...")
                print()

        else:
            print("No glossary terms found in this text.\n")

        print()

    # Show translation example with glossary integration
    print(f"{'='*80}")
    print(f"TRANSLATION INTEGRATION EXAMPLE")
    print(f"{'='*80}\n")

    example_text = SAMPLE_TEXTS[0]['text']
    matches = glossary.find_in_text(example_text, max_matches=30)

    print("When translating this text:")
    print(f"  {example_text}\n")
    print("The translator will receive these glossary instructions:\n")

    for i, (term, entry, _) in enumerate(matches, 1):
        print(f"{i}. {term}")
        print(f"   → Use EXACTLY: '{entry.recommended_form}' in translation")
        print(f"   → Use EXACTLY: '{entry.pinyin}' for pinyin")
        print(f"   → Use EXACTLY: '{entry.footnote_template[:100]}...' for footnote")
        print()

    print("This ensures:")
    print("  ✓ Consistent terminology across entire translation")
    print("  ✓ Exact pinyin romanization for deduplication")
    print("  ✓ Standardized footnotes for common wuxia concepts")
    print("  ✓ Proper handling based on deduplication strategy\n")

    # Statistics
    print(f"{'='*80}")
    print(f"GLOSSARY STATISTICS")
    print(f"{'='*80}\n")

    all_terms = set()
    for sample in SAMPLE_TEXTS:
        matches = glossary.find_in_text(sample['text'], max_matches=30)
        for term, _, _ in matches:
            all_terms.add(term)

    print(f"Unique terms matched across all samples: {len(all_terms)}")
    print(f"Terms: {', '.join(sorted(all_terms))}\n")

    # Show some high-frequency terms
    print("Sample High-Frequency Terms in Glossary:")
    high_freq = glossary.get_high_frequency_terms()
    for entry in high_freq[:10]:
        print(f"  {entry.chinese} → {entry.recommended_form} ({entry.expected_frequency})")

    print(f"\n{'='*80}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'='*80}\n")

    glossary.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
