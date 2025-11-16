#!/usr/bin/env python3
"""
Content Type Analyzer for EPUB Formatting Strategy

Analyzes cleaned JSON files to identify content type patterns
and propose formatting rules for Chinese wuxia novels.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import random


class ContentTypeAnalyzer:
    """Analyzes content blocks to identify patterns for EPUB formatting."""

    def __init__(self):
        self.samples = []
        self.content_patterns = defaultdict(list)
        self.dialogue_patterns = []
        self.verse_patterns = []
        self.special_patterns = []

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single cleaned JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        meta = data.get('meta', {})
        structure = data.get('structure', {})
        body = structure.get('body', {})
        chapters = body.get('chapters', [])

        # Sample 2-3 chapters from the book
        sample_chapters = random.sample(chapters, min(3, len(chapters))) if chapters else []

        analysis = {
            'work_number': meta.get('work_number', 'Unknown'),
            'title': meta.get('title', 'Unknown'),
            'author': meta.get('author', 'Unknown'),
            'total_chapters': len(chapters),
            'sampled_chapters': len(sample_chapters),
            'content_types': Counter(),
            'block_length_stats': [],
            'dialogue_examples': [],
            'verse_examples': [],
            'narrative_examples': [],
            'special_content': [],
        }

        for chapter in sample_chapters:
            chapter_title = chapter.get('title', '')
            content_blocks = chapter.get('content_blocks', [])

            for block in content_blocks[:50]:  # Sample first 50 blocks per chapter
                block_type = block.get('type', 'text')
                content = block.get('content', '')

                analysis['content_types'][block_type] += 1
                analysis['block_length_stats'].append(len(content))

                # Identify dialogue patterns
                if self._is_dialogue(content):
                    if len(analysis['dialogue_examples']) < 5:
                        analysis['dialogue_examples'].append({
                            'chapter': chapter_title,
                            'content': content[:200],
                            'pattern': self._identify_dialogue_pattern(content)
                        })

                # Identify verse/poetry patterns
                if self._is_verse(content):
                    if len(analysis['verse_examples']) < 3:
                        analysis['verse_examples'].append({
                            'chapter': chapter_title,
                            'content': content[:300]
                        })

                # Identify narrative prose
                if self._is_narrative(content):
                    if len(analysis['narrative_examples']) < 5:
                        analysis['narrative_examples'].append({
                            'chapter': chapter_title,
                            'content': content[:200]
                        })

                # Identify special content (letters, documents, etc.)
                if self._is_special_content(content):
                    analysis['special_content'].append({
                        'chapter': chapter_title,
                        'content': content[:150],
                        'type': self._classify_special_content(content)
                    })

        return analysis

    def _is_dialogue(self, content: str) -> bool:
        """Detect if content is dialogue."""
        # Chinese quotation marks
        has_quotes = '「' in content or '『' in content or '"' in content
        # Common dialogue markers
        has_dialogue_verb = any(verb in content for verb in ['道：', '說：', '問：', '答：', '喝道：', '笑道：'])
        return has_quotes or has_dialogue_verb

    def _identify_dialogue_pattern(self, content: str) -> str:
        """Identify dialogue pattern type."""
        if content.startswith('「') or content.startswith('『'):
            return 'quote_first'
        elif '道：「' in content or '說：「' in content:
            return 'speaker_verb_quote'
        elif '」' in content and ('道' in content or '說' in content):
            return 'quote_speaker_verb'
        return 'mixed'

    def _is_verse(self, content: str) -> bool:
        """Detect if content is poetry/verse."""
        # Classical Chinese verse indicators
        # - Short lines (< 20 chars per line)
        # - Repetitive structure
        # - Parallel structure markers
        lines = content.split('\n') if '\n' in content else [content]
        if len(lines) >= 2:
            avg_line_length = sum(len(line.strip()) for line in lines) / len(lines)
            if avg_line_length < 25 and len(lines) >= 4:
                return True

        # Verse markers
        verse_markers = ['詩曰', '詞曰', '賦曰', '頌曰', '歌曰']
        return any(marker in content for marker in verse_markers)

    def _is_narrative(self, content: str) -> bool:
        """Detect if content is narrative prose."""
        # Longer paragraphs without dialogue markers
        if len(content) > 100 and not self._is_dialogue(content) and not self._is_verse(content):
            return True
        return False

    def _is_special_content(self, content: str) -> bool:
        """Detect special content like letters, documents, edicts."""
        special_markers = [
            '信上寫道', '書上寫', '信中', '函曰', '書曰',
            '詔曰', '令曰', '旨曰', '敕曰',
            '碑文', '墓誌銘', '匾額', '對聯'
        ]
        return any(marker in content for marker in special_markers)

    def _classify_special_content(self, content: str) -> str:
        """Classify type of special content."""
        if any(m in content for m in ['信上', '信中', '書曰', '函曰']):
            return 'letter/missive'
        elif any(m in content for m in ['詔曰', '令曰', '旨曰', '敕曰']):
            return 'edict/decree'
        elif any(m in content for m in ['碑文', '墓誌銘']):
            return 'inscription'
        elif any(m in content for m in ['匾額', '對聯']):
            return 'sign/couplet'
        return 'unknown_special'

    def generate_report(self, analyses: List[Dict[str, Any]]) -> str:
        """Generate comprehensive analysis report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CONTENT TYPE ANALYSIS REPORT")
        report_lines.append("Chinese Wuxia Novel Collection - EPUB Formatting Strategy")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Summary statistics
        report_lines.append("## SAMPLE OVERVIEW")
        report_lines.append(f"Total works analyzed: {len(analyses)}")
        total_chapters = sum(a['total_chapters'] for a in analyses)
        report_lines.append(f"Total chapters across all works: {total_chapters}")
        report_lines.append("")

        # Content type distribution
        report_lines.append("## CONTENT TYPE DISTRIBUTION")
        all_types = Counter()
        for analysis in analyses:
            all_types.update(analysis['content_types'])

        for content_type, count in all_types.most_common():
            percentage = (count / sum(all_types.values())) * 100
            report_lines.append(f"  {content_type:20s}: {count:6d} blocks ({percentage:5.2f}%)")
        report_lines.append("")

        # Block length statistics
        report_lines.append("## BLOCK LENGTH STATISTICS")
        all_lengths = []
        for analysis in analyses:
            all_lengths.extend(analysis['block_length_stats'])

        if all_lengths:
            avg_length = sum(all_lengths) / len(all_lengths)
            min_length = min(all_lengths)
            max_length = max(all_lengths)
            report_lines.append(f"  Average block length: {avg_length:.1f} characters")
            report_lines.append(f"  Min block length: {min_length} characters")
            report_lines.append(f"  Max block length: {max_length} characters")
        report_lines.append("")

        # Dialogue pattern examples
        report_lines.append("## DIALOGUE PATTERNS")
        dialogue_patterns_counter = Counter()
        for analysis in analyses:
            for example in analysis['dialogue_examples']:
                dialogue_patterns_counter[example['pattern']] += 1

        report_lines.append("Pattern distribution:")
        for pattern, count in dialogue_patterns_counter.most_common():
            report_lines.append(f"  {pattern:20s}: {count} occurrences")
        report_lines.append("")

        report_lines.append("Example dialogue blocks:")
        for i, analysis in enumerate(analyses[:5]):
            if analysis['dialogue_examples']:
                report_lines.append(f"\n  [{analysis['title']} - {analysis['author']}]")
                for ex in analysis['dialogue_examples'][:2]:
                    report_lines.append(f"    Pattern: {ex['pattern']}")
                    report_lines.append(f"    Content: {ex['content'][:150]}...")
                    report_lines.append("")

        # Verse examples
        report_lines.append("## VERSE/POETRY PATTERNS")
        verse_count = sum(len(a['verse_examples']) for a in analyses)
        report_lines.append(f"Total verse blocks identified: {verse_count}")
        report_lines.append("")

        if verse_count > 0:
            report_lines.append("Example verse blocks:")
            for analysis in analyses:
                if analysis['verse_examples']:
                    report_lines.append(f"\n  [{analysis['title']} - {analysis['author']}]")
                    for ex in analysis['verse_examples'][:1]:
                        report_lines.append(f"    {ex['content'][:200]}...")
                        report_lines.append("")

        # Special content
        report_lines.append("## SPECIAL CONTENT (Letters, Documents, Edicts)")
        all_special = []
        for analysis in analyses:
            all_special.extend(analysis['special_content'])

        special_types = Counter(item['type'] for item in all_special)
        report_lines.append(f"Total special content blocks: {len(all_special)}")
        report_lines.append("Types:")
        for special_type, count in special_types.most_common():
            report_lines.append(f"  {special_type:20s}: {count} occurrences")
        report_lines.append("")

        if all_special:
            report_lines.append("Examples:")
            for item in all_special[:5]:
                report_lines.append(f"  Type: {item['type']}")
                report_lines.append(f"    {item['content'][:120]}...")
                report_lines.append("")

        # Work-by-work summary
        report_lines.append("=" * 80)
        report_lines.append("## WORK-BY-WORK SUMMARY")
        report_lines.append("=" * 80)
        for analysis in analyses:
            report_lines.append(f"\n{analysis['work_number']}: {analysis['title']} - {analysis['author']}")
            report_lines.append(f"  Chapters: {analysis['total_chapters']} (sampled: {analysis['sampled_chapters']})")
            report_lines.append(f"  Content types:")
            for ctype, count in analysis['content_types'].most_common():
                report_lines.append(f"    - {ctype}: {count}")
            report_lines.append(f"  Dialogue examples: {len(analysis['dialogue_examples'])}")
            report_lines.append(f"  Verse examples: {len(analysis['verse_examples'])}")
            report_lines.append(f"  Special content: {len(analysis['special_content'])}")

        return "\n".join(report_lines)


def main():
    """Main execution function."""
    # Sample files
    sample_files = [
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0223/cleaned_D69c_尋秦記三_黃易.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0374/cleaned_D1345_俠影紅顏_雲中岳.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0445/cleaned_D1535_啞俠_倪匡.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0256/cleaned_D14BB6_風神七戒_黃鷹.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0565/cleaned_J090908f_崑崙六．天道卷_鳳歌.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0357/cleaned_D11L9_無情刀客有情天_雲中岳.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0518/cleaned_D14L3_響馬_獨孤紅.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0107/cleaned_D1192_殘劍孤星_高庸.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0076/cleaned_D16M5_千門卷三_方白羽.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0243/cleaned_D14X3_玉蜻蜓_黃鷹.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0181/cleaned_D1114_奪魂旗_諸葛青雲.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0332/cleaned_D1143_殘缺書生_蕭瑟.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0003/cleaned_D57c_倚天屠龍記三_金庸.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0519/cleaned_D14M3_玉龍美豪客_獨孤紅.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0425/cleaned_D1705b_泉會俠蹤．下_東方玉.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0145/cleaned_I10L7_遊劍江湖_梁羽生.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0140/cleaned_D441_冰川天女傳_梁羽生.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0344/cleaned_D13A3_京華魅影_雲中岳.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0452/cleaned_D16Q0_長虹貫日_倪匡.json",
        "/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0116/cleaned_D1379_偷拳_白羽.json",
    ]

    analyzer = ContentTypeAnalyzer()
    analyses = []

    print("Analyzing 20 sample works...")
    for i, file_path in enumerate(sample_files, 1):
        print(f"  [{i}/20] Processing {Path(file_path).name}...")
        try:
            analysis = analyzer.analyze_file(Path(file_path))
            analyses.append(analysis)
        except Exception as e:
            print(f"    ERROR: {e}")

    print(f"\nSuccessfully analyzed {len(analyses)} works.")

    # Generate report
    report = analyzer.generate_report(analyses)

    # Save report
    output_path = Path("/Users/jacki/PycharmProjects/agentic_test_project/data/analysis/content_type_analysis_report.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")
    print("\n" + "=" * 80)
    print(report)

    return analyses


if __name__ == "__main__":
    main()
