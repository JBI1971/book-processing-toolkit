#!/usr/bin/env python3
"""
TOC Alignment Validator
Uses OpenAI to validate that TOC entries match actual chapter titles
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AlignmentIssue:
    """An issue found in TOC/chapter alignment"""
    severity: str  # "error", "warning", "info"
    toc_index: int
    chapter_index: int
    issue_type: str
    message: str
    toc_entry: str
    chapter_title: str
    confidence: float = 0.0
    suggested_fix: Optional[str] = None


@dataclass
class AlignmentResult:
    """Result of TOC alignment validation"""
    is_valid: bool
    issues: List[AlignmentIssue] = field(default_factory=list)
    total_pairs: int = 0
    matched_pairs: int = 0
    confidence_score: float = 0.0
    summary: str = ""


class TOCAlignmentValidator:
    """Validate TOC/chapter alignment using OpenAI"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        """
        Initialize validator.

        Args:
            model: OpenAI model to use
            temperature: Temperature for generation (low for consistency)
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        logger.info(f"TOC Alignment Validator initialized with model: {model}")

    def validate(self, cleaned_json: Dict[str, Any]) -> AlignmentResult:
        """
        Validate TOC entries match chapter titles.

        Args:
            cleaned_json: Cleaned book JSON with TOC and chapters

        Returns:
            AlignmentResult with issues found
        """
        logger.info("Starting TOC alignment validation...")

        result = AlignmentResult(is_valid=True)

        try:
            # Extract TOC entries
            toc_data = cleaned_json.get('structure', {}).get('front_matter', {}).get('toc', [])
            if not toc_data or len(toc_data) == 0:
                result.is_valid = False
                result.summary = "No TOC found"
                return result

            toc_entries = toc_data[0].get('entries', [])
            if not toc_entries:
                result.is_valid = False
                result.summary = "TOC has no entries"
                return result

            # Extract chapters
            chapters = cleaned_json.get('structure', {}).get('body', {}).get('chapters', [])
            if not chapters:
                result.is_valid = False
                result.summary = "No chapters found"
                return result

            result.total_pairs = min(len(toc_entries), len(chapters))

            # Build comparison pairs
            pairs = []
            for i in range(result.total_pairs):
                toc_entry = toc_entries[i]
                chapter = chapters[i]

                toc_text = toc_entry.get('full_title', toc_entry.get('chapter_title', ''))
                chapter_title = chapter.get('title', '')

                pairs.append({
                    'index': i,
                    'toc': toc_text,
                    'chapter': chapter_title
                })

            # Validate in batches (to avoid token limits)
            batch_size = 20
            for batch_start in range(0, len(pairs), batch_size):
                batch_end = min(batch_start + batch_size, len(pairs))
                batch = pairs[batch_start:batch_end]

                batch_issues = self._validate_batch(batch)
                result.issues.extend(batch_issues)

            # Calculate statistics
            result.matched_pairs = result.total_pairs - len([i for i in result.issues if i.severity == 'error'])
            result.confidence_score = (result.matched_pairs / result.total_pairs * 100) if result.total_pairs > 0 else 0

            # Determine validity
            error_count = sum(1 for issue in result.issues if issue.severity == 'error')
            result.is_valid = error_count == 0

            # Build summary
            result.summary = f"{result.matched_pairs}/{result.total_pairs} TOC entries match ({result.confidence_score:.1f}%)"
            if error_count > 0:
                result.summary += f" - {error_count} errors"

            logger.info(f"Validation complete: {result.summary}")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            result.is_valid = False
            result.summary = f"Validation error: {str(e)}"

        return result

    def _validate_batch(self, pairs: List[Dict]) -> List[AlignmentIssue]:
        """
        Validate a batch of TOC/chapter pairs using OpenAI.

        Args:
            pairs: List of {index, toc, chapter} dicts

        Returns:
            List of AlignmentIssue objects
        """
        # Build prompt
        pairs_text = "\n".join([
            f"{i+1}. TOC: '{pair['toc']}' | Chapter: '{pair['chapter']}'"
            for i, pair in enumerate(pairs)
        ])

        prompt = f"""You are validating that Table of Contents (TOC) entries match actual chapter titles in a Chinese wuxia novel.

For each pair, determine if they match semantically. Consider:
- Chinese numeral variations (第一章, 第廿一章, 第卅章)
- Spacing and formatting differences
- Minor typos or transcription errors
- The TOC entry should reasonably identify the chapter

Pairs to validate:
{pairs_text}

Respond with a JSON object containing an array of issues. For each mismatch, provide:
{{
  "issues": [
    {{
      "pair_number": <number 1-{len(pairs)}>,
      "severity": "error" | "warning" | "info",
      "issue_type": "mismatch" | "number_mismatch" | "missing_chapter" | "typo",
      "message": "Brief description of the issue",
      "confidence": <0.0-1.0 how confident this is a real issue>,
      "suggested_fix": "What the TOC entry should say (optional)"
    }}
  ]
}}

Only report actual mismatches. If all pairs match, return {{"issues": []}}.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise book structure validator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            issues = []
            for issue_data in data.get('issues', []):
                pair_num = issue_data.get('pair_number', 1) - 1
                if 0 <= pair_num < len(pairs):
                    pair = pairs[pair_num]
                    issues.append(AlignmentIssue(
                        severity=issue_data.get('severity', 'warning'),
                        toc_index=pair['index'],
                        chapter_index=pair['index'],
                        issue_type=issue_data.get('issue_type', 'mismatch'),
                        message=issue_data.get('message', 'TOC/chapter mismatch'),
                        toc_entry=pair['toc'],
                        chapter_title=pair['chapter'],
                        confidence=issue_data.get('confidence', 0.5),
                        suggested_fix=issue_data.get('suggested_fix')
                    ))

            return issues

        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            return []

    def validate_file(self, json_file: str) -> AlignmentResult:
        """
        Validate TOC alignment from a file.

        Args:
            json_file: Path to cleaned JSON file

        Returns:
            AlignmentResult
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.validate(data)


def main():
    """CLI testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python toc_alignment_validator.py <cleaned_json_file>")
        return 1

    json_file = sys.argv[1]

    print(f"\n{'='*80}")
    print(f"TOC ALIGNMENT VALIDATION")
    print(f"{'='*80}\n")

    validator = TOCAlignmentValidator()
    result = validator.validate_file(json_file)

    print(f"Summary: {result.summary}")
    print(f"Valid: {result.is_valid}")
    print(f"Confidence: {result.confidence_score:.1f}%")

    if result.issues:
        print(f"\n{'='*80}")
        print(f"ISSUES FOUND ({len(result.issues)})")
        print(f"{'='*80}\n")

        for issue in result.issues:
            icon = "✗" if issue.severity == "error" else "⚠" if issue.severity == "warning" else "ℹ"
            print(f"{icon} [{issue.severity.upper()}] {issue.message}")
            print(f"   TOC:     '{issue.toc_entry}'")
            print(f"   Chapter: '{issue.chapter_title}'")
            if issue.suggested_fix:
                print(f"   Fix:     '{issue.suggested_fix}'")
            print(f"   Confidence: {issue.confidence:.0%}\n")

    print(f"{'='*80}\n")

    return 0 if result.is_valid else 1


if __name__ == "__main__":
    exit(main())
