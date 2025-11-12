#!/usr/bin/env python3
"""
Chinese Chapter Sequence Validator
Validates chapter numbering sequences in Chinese text to detect missing/skipped chapters
"""

import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Chinese number mappings
CHINESE_NUMBERS = {
    '零': 0, '〇': 0,
    '一': 1, '壹': 1,
    '二': 2, '貳': 2,
    '三': 3, '參': 3, '叁': 3,
    '四': 4, '肆': 4,
    '五': 5, '伍': 5,
    '六': 6, '陸': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '十': 10, '拾': 10,
    '廿': 20, '卅': 30, '卌': 40
}

POSITION_MULTIPLIERS = {
    '十': 10, '拾': 10,
    '百': 100, '佰': 100,
    '千': 1000, '仟': 1000
}


@dataclass
class ChapterNumber:
    """Parsed chapter number"""
    raw_text: str
    number: Optional[int]
    prefix: str  # e.g., "第", "Chapter"
    suffix: str  # e.g., "回", "章", "節"
    is_arabic: bool
    is_chinese: bool


@dataclass
class SequenceIssue:
    """Issue found in chapter sequence"""
    severity: str  # "error", "warning", "info"
    chapter_index: int
    chapter_title: str
    issue_type: str
    message: str
    expected: Optional[int] = None
    actual: Optional[int] = None


class ChineseChapterSequenceValidator:
    """Validate Chinese chapter numbering sequences"""

    # Common chapter prefixes in Chinese novels
    CHAPTER_PATTERNS = [
        r'第([零〇一二三四五六七八九十廿卅百千壹貳參叁肆伍陸柒捌玖拾佰仟]+)回',  # 第X回
        r'第([零〇一二三四五六七八九十廿卅百千壹貳參叁肆伍陸柒捌玖拾佰仟]+)章',  # 第X章
        r'第([零〇一二三四五六七八九十廿卅百千壹貳參叁肆伍陸柒捌玖拾佰仟]+)節',  # 第X節
        r'第([零〇一二三四五六七八九十廿卅百千壹貳參叁肆伍陸柒捌玖拾佰仟]+)集',  # 第X集
        r'第([零〇一二三四五六七八九十廿卅百千壹貳參叁肆伍陸柒捌玖拾佰仟一]+)回',  # Alternative
        r'第(\d+)回',  # Arabic: 第1回
        r'第(\d+)章',  # Arabic: 第1章
        r'Chapter\s*(\d+)',  # English: Chapter 1
        r'^([一二三四五六七八九十廿]+)(?:　|\s)',  # Just number: 一、二、三
    ]

    def __init__(self):
        """Initialize validator"""
        self.issues = []

    def parse_chinese_number(self, text: str) -> Optional[int]:
        """
        Parse Chinese number to integer.

        Examples:
            一 -> 1
            十 -> 10
            十一 -> 11
            二十 -> 20
            二十一 -> 21
            二一 -> 21 (two-digit format: 2*10 + 1)
            三五 -> 35 (two-digit format: 3*10 + 5)
            四十 -> 40
            三十 -> 30
            一百 -> 100
            一百零一 -> 101

        Args:
            text: Chinese number text

        Returns:
            Integer value or None if cannot parse
        """
        try:
            # Handle simple cases
            if len(text) == 1 and text in CHINESE_NUMBERS:
                return CHINESE_NUMBERS[text]

            # Handle 十 (10) at start
            if text.startswith('十') or text.startswith('拾'):
                if len(text) == 1:
                    return 10
                # 十一 = 11
                rest = text[1:]
                if rest in CHINESE_NUMBERS:
                    return 10 + CHINESE_NUMBERS[rest]

            # Handle 廿 (20) at start
            if text.startswith('廿'):
                if len(text) == 1:
                    return 20
                # 廿一 = 21, 廿二 = 22, etc.
                rest = text[1:]
                if rest in CHINESE_NUMBERS:
                    return 20 + CHINESE_NUMBERS[rest]

            # Handle 卅 (30) at start
            if text.startswith('卅'):
                if len(text) == 1:
                    return 30
                # 卅一 = 31, 卅二 = 32, etc.
                rest = text[1:]
                if rest in CHINESE_NUMBERS:
                    return 30 + CHINESE_NUMBERS[rest]

            # Handle 卌 (40) at start
            if text.startswith('卌'):
                if len(text) == 1:
                    return 40
                # 卌一 = 41, 卌二 = 42, etc.
                rest = text[1:]
                if rest in CHINESE_NUMBERS:
                    return 40 + CHINESE_NUMBERS[rest]

            # NEW: Handle two-digit format (二一 = 21, 三五 = 35, etc.)
            # This format is used in some books where each digit is written separately
            # Pattern: [一-九][一-九] without 十/百/千 multipliers
            if len(text) == 2:
                first_char = text[0]
                second_char = text[1]

                # Check if both are single digits (1-9)
                if (first_char in CHINESE_NUMBERS and second_char in CHINESE_NUMBERS and
                    CHINESE_NUMBERS[first_char] <= 9 and CHINESE_NUMBERS[second_char] <= 9):
                    # This is the two-digit format: AB means A*10 + B
                    return CHINESE_NUMBERS[first_char] * 10 + CHINESE_NUMBERS[second_char]

            # Handle compound numbers with position multipliers
            result = 0
            temp = 0
            multiplier = 1

            i = 0
            while i < len(text):
                char = text[i]

                if char in POSITION_MULTIPLIERS:
                    multiplier = POSITION_MULTIPLIERS[char]
                    if temp == 0:
                        temp = 1  # 十 means 1*10
                    result += temp * multiplier
                    temp = 0
                    multiplier = 1
                elif char in CHINESE_NUMBERS:
                    temp = CHINESE_NUMBERS[char]
                else:
                    logger.warning(f"Unknown character in Chinese number: {char}")
                    return None

                i += 1

            result += temp
            return result if result > 0 else None

        except Exception as e:
            logger.error(f"Error parsing Chinese number '{text}': {e}")
            return None

    def extract_chapter_number(self, title: str) -> Optional[ChapterNumber]:
        """
        Extract chapter number from title.

        Args:
            title: Chapter title

        Returns:
            ChapterNumber or None if no number found
        """
        # Try each pattern
        for pattern in self.CHAPTER_PATTERNS:
            match = re.search(pattern, title)
            if match:
                number_text = match.group(1)

                # Check if Arabic
                if number_text.isdigit():
                    return ChapterNumber(
                        raw_text=match.group(0),
                        number=int(number_text),
                        prefix=title[:match.start()],
                        suffix=title[match.end():],
                        is_arabic=True,
                        is_chinese=False
                    )
                else:
                    # Chinese number
                    number = self.parse_chinese_number(number_text)
                    if number is not None:
                        return ChapterNumber(
                            raw_text=match.group(0),
                            number=number,
                            prefix=title[:match.start()],
                            suffix=title[match.end():],
                            is_arabic=False,
                            is_chinese=True
                        )

        return None

    def validate_sequence(
        self,
        chapters: List[Dict],
        strict: bool = False,
        volume: Optional[str] = None
    ) -> Tuple[bool, List[SequenceIssue]]:
        """
        Validate chapter numbering sequence.

        Args:
            chapters: List of chapter dicts with 'title' field
            strict: If True, any issue is an error; if False, some are warnings
            volume: Volume number (e.g., '001', '002') for continuation detection

        Returns:
            (is_valid, list of issues)
        """
        self.issues = []

        # Extract chapter numbers
        chapter_numbers = []
        for i, chapter in enumerate(chapters):
            title = chapter.get('title', '')
            ch_num = self.extract_chapter_number(title)

            if ch_num and ch_num.number is not None:
                chapter_numbers.append((i, title, ch_num.number))
            else:
                # Could not extract number
                self.issues.append(SequenceIssue(
                    severity="info",
                    chapter_index=i,
                    chapter_title=title,
                    issue_type="no_number",
                    message=f"Could not extract chapter number from title"
                ))

        if not chapter_numbers:
            logger.info("No numbered chapters found - skipping sequence validation")
            return True, self.issues

        # Check for gaps and duplicates
        seen_numbers = set()
        expected_next = None

        for i, (chapter_idx, title, number) in enumerate(chapter_numbers):
            # Check for duplicates
            if number in seen_numbers:
                self.issues.append(SequenceIssue(
                    severity="error",
                    chapter_index=chapter_idx,
                    chapter_title=title,
                    issue_type="duplicate",
                    message=f"Duplicate chapter number: {number}",
                    actual=number
                ))

            seen_numbers.add(number)

            # Check sequence
            if expected_next is not None:
                if number != expected_next:
                    gap = number - expected_next

                    if gap > 0:
                        # Missing chapters
                        severity = "error" if strict else "warning"
                        self.issues.append(SequenceIssue(
                            severity=severity,
                            chapter_index=chapter_idx,
                            chapter_title=title,
                            issue_type="gap",
                            message=f"Chapter numbering gap: expected {expected_next}, got {number} (missing {gap} chapter{'s' if gap > 1 else ''})",
                            expected=expected_next,
                            actual=number
                        ))
                    elif gap < 0:
                        # Out of order
                        self.issues.append(SequenceIssue(
                            severity="error",
                            chapter_index=chapter_idx,
                            chapter_title=title,
                            issue_type="out_of_order",
                            message=f"Chapter out of sequence: expected {expected_next}, got {number}",
                            expected=expected_next,
                            actual=number
                        ))

            expected_next = number + 1

        # Check if sequence starts at 1
        if chapter_numbers and chapter_numbers[0][2] != 1:
            start_num = chapter_numbers[0][2]

            # Check if this is a continuation volume (volume 002+)
            is_continuation = False
            if volume:
                try:
                    volume_num = int(volume)
                    is_continuation = volume_num > 1
                except (ValueError, TypeError):
                    pass

            if is_continuation:
                # This is expected for continuation volumes
                self.issues.append(SequenceIssue(
                    severity="info",
                    chapter_index=chapter_numbers[0][0],
                    chapter_title=chapter_numbers[0][1],
                    issue_type="continuation_volume",
                    message=f"Continuation volume - chapters start at {start_num}",
                    actual=start_num
                ))
            else:
                # Not a continuation volume - this is unusual
                self.issues.append(SequenceIssue(
                    severity="info",
                    chapter_index=chapter_numbers[0][0],
                    chapter_title=chapter_numbers[0][1],
                    issue_type="nonstandard_start",
                    message=f"Chapter numbering starts at {start_num} (not 1)",
                    actual=start_num
                ))

        # Determine if valid
        has_errors = any(issue.severity == "error" for issue in self.issues)
        return not has_errors, self.issues

    def get_chapter_sequence_summary(self, chapters: List[Dict]) -> Dict:
        """
        Get summary of chapter numbering.

        Args:
            chapters: List of chapter dicts

        Returns:
            Summary dict with statistics
        """
        numbered = []
        unnumbered = []

        for i, chapter in enumerate(chapters):
            title = chapter.get('title', '')
            ch_num = self.extract_chapter_number(title)

            if ch_num and ch_num.number is not None:
                numbered.append(ch_num.number)
            else:
                unnumbered.append(title)

        if numbered:
            return {
                'total_chapters': len(chapters),
                'numbered_chapters': len(numbered),
                'unnumbered_chapters': len(unnumbered),
                'sequence_start': min(numbered),
                'sequence_end': max(numbered),
                'expected_count': max(numbered) - min(numbered) + 1,
                'actual_count': len(numbered),
                'missing_count': (max(numbered) - min(numbered) + 1) - len(numbered),
                'has_duplicates': len(numbered) != len(set(numbered)),
                'unnumbered_titles': unnumbered[:5]  # First 5
            }
        else:
            return {
                'total_chapters': len(chapters),
                'numbered_chapters': 0,
                'unnumbered_chapters': len(chapters),
                'unnumbered_titles': unnumbered[:5]
            }


def main():
    """CLI testing"""
    # Test cases
    validator = ChineseChapterSequenceValidator()

    test_titles = [
        "第一回　風雪驚變",
        "第二回　江湖險惡",
        "第三回　深宵怪客",
        "第五回　黑衣女子",  # Gap!
        "第六回　橫拖倒曳",
        "第二十一回　千鈞巨岩",
        "第三十回　一燈大師",
        "第一百零一回　平手相鬥",
    ]

    print("Testing chapter number extraction:")
    for title in test_titles:
        ch_num = validator.extract_chapter_number(title)
        if ch_num:
            print(f"  '{title}' -> {ch_num.number}")
        else:
            print(f"  '{title}' -> COULD NOT EXTRACT")

    print("\nTesting sequence validation:")
    chapters = [{'title': t} for t in test_titles]
    is_valid, issues = validator.validate_sequence(chapters)

    print(f"  Valid: {is_valid}")
    print(f"  Issues: {len(issues)}")
    for issue in issues:
        print(f"    [{issue.severity}] {issue.issue_type}: {issue.message}")

    return 0


if __name__ == "__main__":
    exit(main())
