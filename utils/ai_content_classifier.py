#!/usr/bin/env python3
"""
AI-Powered Content Classifier for EPUB Formatting

Uses OpenAI GPT-4o to semantically classify Chinese wuxia novel content
into categories relevant for EPUB formatting and translation.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
import time

# Load environment variables
from utils.load_env_creds import load_env_credentials
load_env_credentials()

from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


CLASSIFICATION_PROMPT = """You are an expert in Chinese wuxia (martial arts) literature and classical Chinese writing styles.

Analyze the following content block from a Chinese wuxia novel and classify it into ONE of these categories:

**Content Types:**
1. **narrative** - Standard narrative prose describing events, actions, settings
2. **dialogue** - Character speech, conversations
3. **internal_thought** - Character's internal monologue or thoughts
4. **descriptive** - Detailed descriptions of scenery, people, objects
5. **action_sequence** - Fight scenes, combat descriptions
6. **verse** - Classical Chinese poetry, verse, song lyrics
7. **letter** - Written correspondence, letters, notes
8. **document** - Official documents, edicts, decrees, proclamations
9. **inscription** - Tombstone inscriptions, plaques, couplets
10. **chapter_title** - Chapter headings
11. **transition** - Scene transitions, time jumps
12. **author_note** - Author's notes or commentary

**Additional Context to Identify:**
- **Formality level**: casual, formal, classical
- **Narrative perspective**: third_person, first_person, omniscient
- **Dominant emotion/tone**: neutral, tense, romantic, humorous, tragic, mysterious
- **Contains dialogue**: yes/no (even if mixed with narrative)
- **Literary devices**: metaphor, allusion, parallelism, etc.

**Content to analyze:**
{content}

**Instructions:**
1. Classify into ONE primary category
2. If mixed content, choose the DOMINANT type
3. Provide confidence score (0-100%)
4. Provide brief reasoning (1-2 sentences in English)

**Response format (JSON only):**
{{
  "primary_type": "category_name",
  "confidence": 85,
  "reasoning": "Brief explanation",
  "secondary_type": "category_name or null",
  "formality": "casual|formal|classical",
  "perspective": "third_person|first_person|omniscient",
  "tone": "neutral|tense|romantic|humorous|tragic|mysterious",
  "contains_dialogue": true/false,
  "formatting_suggestion": "specific EPUB formatting recommendation"
}}
"""


def classify_content_block(content: str, model: str = "gpt-4o") -> Dict[str, Any]:
    """Use OpenAI to classify a content block."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert literary analyst specializing in Chinese wuxia novels."},
                {"role": "user", "content": CLASSIFICATION_PROMPT.format(content=content[:1000])}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=300
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Classification error: {e}")
        return {
            "primary_type": "unknown",
            "confidence": 0,
            "reasoning": f"Error: {str(e)}",
            "secondary_type": None,
            "formality": "unknown",
            "perspective": "unknown",
            "tone": "unknown",
            "contains_dialogue": False,
            "formatting_suggestion": "default"
        }


def analyze_sample_blocks(file_path: Path, num_samples: int = 30) -> List[Dict[str, Any]]:
    """Analyze sample blocks from a cleaned JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    meta = data.get('meta', {})
    chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

    if not chapters:
        return []

    # Sample blocks from different chapters
    classified_blocks = []
    blocks_per_chapter = max(1, num_samples // min(3, len(chapters)))

    sample_chapters = chapters[:min(3, len(chapters))]

    for chapter in sample_chapters:
        content_blocks = chapter.get('content_blocks', [])

        # Skip heading blocks, focus on content
        text_blocks = [b for b in content_blocks if b.get('type') != 'heading']

        # Sample evenly across the chapter
        step = max(1, len(text_blocks) // blocks_per_chapter)
        sampled = text_blocks[::step][:blocks_per_chapter]

        for block in sampled:
            content = block.get('content', '')
            if len(content) < 10:  # Skip very short blocks
                continue

            print(f"  Classifying block ({len(content)} chars)...")

            classification = classify_content_block(content)
            classification['original_content'] = content[:200]  # Store snippet
            classification['block_id'] = block.get('id')
            classification['chapter_title'] = chapter.get('title')
            classification['work_title'] = meta.get('title')
            classification['author'] = meta.get('author')

            classified_blocks.append(classification)

            # Rate limiting
            time.sleep(0.5)

    return classified_blocks


def generate_classification_report(all_classifications: List[Dict[str, Any]]) -> str:
    """Generate comprehensive classification report."""
    lines = []
    lines.append("=" * 100)
    lines.append("AI CONTENT CLASSIFICATION REPORT")
    lines.append("Chinese Wuxia Novels - Semantic Content Type Analysis")
    lines.append("=" * 100)
    lines.append("")

    # Overall statistics
    lines.append("## CLASSIFICATION STATISTICS")
    lines.append(f"Total blocks classified: {len(all_classifications)}")
    lines.append("")

    # Primary type distribution
    primary_types = Counter(c['primary_type'] for c in all_classifications)
    lines.append("### Primary Content Types:")
    for ptype, count in primary_types.most_common():
        pct = (count / len(all_classifications)) * 100
        lines.append(f"  {ptype:25s}: {count:4d} ({pct:5.1f}%)")
    lines.append("")

    # Formality distribution
    formality = Counter(c.get('formality', 'unknown') for c in all_classifications)
    lines.append("### Formality Levels:")
    for form, count in formality.most_common():
        pct = (count / len(all_classifications)) * 100
        lines.append(f"  {form:15s}: {count:4d} ({pct:5.1f}%)")
    lines.append("")

    # Tone distribution
    tones = Counter(c.get('tone', 'unknown') for c in all_classifications)
    lines.append("### Tone Distribution:")
    for tone, count in tones.most_common():
        pct = (count / len(all_classifications)) * 100
        lines.append(f"  {tone:15s}: {count:4d} ({pct:5.1f}%)")
    lines.append("")

    # Dialogue presence
    dialogue_count = sum(1 for c in all_classifications if c.get('contains_dialogue'))
    lines.append(f"### Blocks containing dialogue: {dialogue_count} ({(dialogue_count/len(all_classifications)*100):.1f}%)")
    lines.append("")

    # Average confidence
    avg_confidence = sum(c.get('confidence', 0) for c in all_classifications) / len(all_classifications)
    lines.append(f"### Average classification confidence: {avg_confidence:.1f}%")
    lines.append("")

    # Examples by type
    lines.append("=" * 100)
    lines.append("## EXAMPLES BY CONTENT TYPE")
    lines.append("=" * 100)
    lines.append("")

    for ptype in primary_types.keys():
        examples = [c for c in all_classifications if c['primary_type'] == ptype][:3]
        if examples:
            lines.append(f"\n### {ptype.upper()}")
            lines.append("-" * 100)
            for i, ex in enumerate(examples, 1):
                lines.append(f"\nExample {i}:")
                lines.append(f"  Work: {ex.get('work_title')} - {ex.get('author')}")
                lines.append(f"  Chapter: {ex.get('chapter_title')}")
                lines.append(f"  Confidence: {ex.get('confidence')}%")
                lines.append(f"  Formality: {ex.get('formality')}")
                lines.append(f"  Tone: {ex.get('tone')}")
                lines.append(f"  Contains dialogue: {ex.get('contains_dialogue')}")
                lines.append(f"  Reasoning: {ex.get('reasoning')}")
                lines.append(f"  Formatting suggestion: {ex.get('formatting_suggestion')}")
                lines.append(f"  Content: {ex.get('original_content')}...")
                lines.append("")

    # Formatting recommendations summary
    lines.append("=" * 100)
    lines.append("## FORMATTING RECOMMENDATIONS SUMMARY")
    lines.append("=" * 100)
    lines.append("")

    formatting_suggestions = Counter(c.get('formatting_suggestion', 'default') for c in all_classifications)
    for suggestion, count in formatting_suggestions.most_common(10):
        lines.append(f"  {suggestion}: {count} blocks")
    lines.append("")

    return "\n".join(lines)


def main():
    """Main execution function."""
    sample_files = [
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0003/cleaned_D57c_倚天屠龍記三_金庸.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0374/cleaned_D1345_俠影紅顏_雲中岳.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0223/cleaned_D69c_尋秦記三_黃易.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0145/cleaned_I10L7_遊劍江湖_梁羽生.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0140/cleaned_D441_冰川天女傳_梁羽生.json",
    ]

    all_classifications = []

    print("AI Content Classification Analysis")
    print("Using model: gpt-4o")
    print(f"Analyzing {len(sample_files)} works...")
    print("=" * 100)

    for i, file_path in enumerate(sample_files, 1):
        file_name = Path(file_path).name
        print(f"\n[{i}/{len(sample_files)}] Processing: {file_name}")
        print("-" * 100)

        try:
            classifications = analyze_sample_blocks(Path(file_path), num_samples=30)
            all_classifications.extend(classifications)
            print(f"  Classified {len(classifications)} blocks from this work.")

        except Exception as e:
            print(f"  ERROR processing {file_name}: {e}")

    print("\n" + "=" * 100)
    print(f"Total blocks classified: {len(all_classifications)}")

    # Generate report
    report = generate_classification_report(all_classifications)

    # Save report
    output_path = Path("/Users/jacki/PycharmProjects/agentic_test_project/data/analysis/ai_classification_report.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    # Save raw data
    data_path = Path("/Users/jacki/PycharmProjects/agentic_test_project/data/analysis/classification_data.json")
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(all_classifications, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to: {output_path}")
    print(f"Raw data saved to: {data_path}")
    print("\n" + report)


if __name__ == "__main__":
    main()
