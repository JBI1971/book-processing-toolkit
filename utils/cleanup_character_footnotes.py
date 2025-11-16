#!/usr/bin/env python3
"""
Character Footnote Cleanup Utility

Removes fictional character name footnotes while preserving historical figures,
legendary personages, and cultural notes. Also strips internal footnote references.

Usage:
    python utils/cleanup_character_footnotes.py --input file.json --output cleaned.json

Author: Claude Code
Date: 2025-11-15
"""

import json
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from tqdm import tqdm

# Workaround for Python 3.13.0 http.client bug
import sys as _sys
if _sys.version_info[:2] == (3, 13):
    try:
        import http.client
    except ModuleNotFoundError:
        # Create a minimal http.client module to satisfy imports
        import types
        _http_client = types.ModuleType('http.client')
        _sys.modules['http.client'] = _http_client
        # Now try importing http which should work
        import http
        http.client = _http_client

# Direct import to avoid __init__.py issues
try:
    from openai import OpenAI
except ImportError as e:
    print(f"Error: openai package not installed. Run: pip install openai")
    print(f"Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error importing openai: {type(e).__name__}: {e}")
    sys.exit(1)


def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it before running this script."
        )
    return OpenAI(api_key=api_key)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FootnoteClassification(BaseModel):
    """Classification result for a single footnote."""
    ideogram: str
    explanation: str
    classification_type: str  # FICTIONAL_CHARACTER, HISTORICAL_FIGURE, LEGENDARY_PERSONAGE, CULTURAL
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    original_explanation: str  # Before stripping internal refs
    internal_refs_removed: int = 0

    class Config:
        extra = "ignore"  # Ignore unexpected fields from API responses


class CleanupConfig(BaseModel):
    """Configuration for footnote cleanup."""
    model: str = "gpt-4.1-nano"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    batch_size: int = Field(default=25, gt=0)
    preserve_historical: bool = True
    preserve_legendary: bool = True
    preserve_cultural: bool = True
    create_backup: bool = True
    max_retries: int = Field(default=3, ge=1)


class CleanupResult(BaseModel):
    """Result of the cleanup operation."""
    total_footnotes: int = 0
    fictional_character_count: int = 0
    historical_figure_count: int = 0
    legendary_personage_count: int = 0
    cultural_count: int = 0
    removed_count: int = 0
    preserved_count: int = 0
    internal_refs_stripped: int = 0
    classifications: List[FootnoteClassification] = Field(default_factory=list)
    removed_footnotes: List[Dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": {
                "total_footnotes": self.total_footnotes,
                "fictional_character_count": self.fictional_character_count,
                "historical_figure_count": self.historical_figure_count,
                "legendary_personage_count": self.legendary_personage_count,
                "cultural_count": self.cultural_count,
                "removed_count": self.removed_count,
                "preserved_count": self.preserved_count,
                "internal_refs_stripped": self.internal_refs_stripped,
            },
            "classifications": [
                {
                    "ideogram": c.ideogram,
                    "explanation": c.explanation,
                    "original_explanation": c.original_explanation,
                    "type": c.classification_type,
                    "confidence": c.confidence,
                    "reasoning": c.reasoning,
                    "internal_refs_removed": c.internal_refs_removed,
                }
                for c in self.classifications
            ],
            "removed_footnotes": self.removed_footnotes,
            "removal_summary_by_type": {
                "FICTIONAL_CHARACTER": self.fictional_character_count,
                "HISTORICAL_FIGURE": self.historical_figure_count,
                "LEGENDARY_PERSONAGE": self.legendary_personage_count,
                "CULTURAL": self.cultural_count,
            }
        }


class CharacterFootnoteCleanup:
    """Removes fictional character footnotes while preserving others."""

    def __init__(self, config: CleanupConfig):
        """
        Initialize the cleanup processor.

        Args:
            config: Configuration for the cleanup operation
        """
        self.config = config
        self.client = get_openai_client()
        self.result = CleanupResult()

    def strip_internal_references(self, text: str) -> Tuple[str, int]:
        """
        Strip internal footnote references like [n] from explanation text.

        Args:
            text: Original explanation text

        Returns:
            Tuple of (cleaned_text, number_of_references_removed)
        """
        pattern = r'\[\d+\]'
        matches = re.findall(pattern, text)
        cleaned = re.sub(pattern, '', text)
        # Clean up any double spaces left behind
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned, len(matches)

    def extract_all_footnotes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all footnotes from the JSON structure.

        Args:
            data: Cleaned JSON data

        Returns:
            List of footnote dictionaries with metadata
        """
        footnotes = []
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        for chapter_idx, chapter in enumerate(chapters):
            chapter_id = chapter.get('id', f'chapter_{chapter_idx:04d}')
            chapter_title = chapter.get('title', 'Untitled')

            for block in chapter.get('content_blocks', []):
                block_id = block.get('id', 'unknown')

                for footnote in block.get('footnotes', []):
                    ideogram = footnote.get('ideogram', '')
                    explanation = footnote.get('explanation', '')

                    if not ideogram or not explanation:
                        continue

                    # Strip internal references BEFORE classification
                    cleaned_explanation, refs_removed = self.strip_internal_references(explanation)

                    footnotes.append({
                        'ideogram': ideogram,
                        'original_explanation': explanation,
                        'explanation': cleaned_explanation,
                        'pinyin': footnote.get('pinyin', ''),
                        'key': footnote.get('key'),
                        'chapter_id': chapter_id,
                        'chapter_title': chapter_title,
                        'block_id': block_id,
                        'internal_refs_removed': refs_removed,
                    })

                    self.result.internal_refs_stripped += refs_removed

        return footnotes

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def classify_footnotes_batch(
        self, footnotes: List[Dict[str, Any]]
    ) -> List[FootnoteClassification]:
        """
        Classify a batch of footnotes using OpenAI API.

        Args:
            footnotes: List of footnote dictionaries

        Returns:
            List of FootnoteClassification objects
        """
        # Build the prompt
        system_prompt = """You are an expert in Chinese literature and history. Classify footnotes into these categories:

1. FICTIONAL_CHARACTER - Fictional story characters, protagonists, antagonists, side characters in the narrative
2. HISTORICAL_FIGURE - Real historical persons (e.g., Emperor Kangxi 康熙帝, Confucius 孔子, historical officials)
3. LEGENDARY_PERSONAGE - Mythological or legendary figures (e.g., Guan Yu 關羽, Buddha 佛陀, deities, mythical heroes)
4. CULTURAL - Cultural concepts, places, events, terminology, weapons, items, idioms, literary devices, historical periods/dynasties

For each footnote, return:
- type: One of the four categories above
- confidence: 0.0 to 1.0
- reasoning: Brief explanation of classification

Return as JSON array with one object per footnote."""

        user_content = "Classify these footnotes:\n\n"
        for idx, fn in enumerate(footnotes):
            user_content += f"{idx + 1}. Ideogram: {fn['ideogram']}\n"
            user_content += f"   Explanation: {fn['explanation']}\n\n"

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )

            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)

            # Parse classifications with Pydantic validation
            classifications = []
            results_list = result_data.get('classifications', result_data.get('results', []))

            for idx, fn in enumerate(footnotes):
                try:
                    if idx < len(results_list):
                        res = results_list[idx]
                        # Use Pydantic model for validation
                        classification = FootnoteClassification(
                            ideogram=fn['ideogram'],
                            explanation=fn['explanation'],
                            classification_type=res.get('type', 'CULTURAL'),
                            confidence=float(res.get('confidence', 0.5)),
                            reasoning=res.get('reasoning', 'No reasoning provided'),
                            original_explanation=fn['original_explanation'],
                            internal_refs_removed=fn['internal_refs_removed'],
                        )
                        classifications.append(classification)
                    else:
                        # Fallback classification
                        logger.warning(
                            f"Missing classification for footnote {idx + 1}, "
                            f"defaulting to CULTURAL"
                        )
                        classification = FootnoteClassification(
                            ideogram=fn['ideogram'],
                            explanation=fn['explanation'],
                            classification_type='CULTURAL',
                            confidence=0.3,
                            reasoning='Fallback classification due to missing API result',
                            original_explanation=fn['original_explanation'],
                            internal_refs_removed=fn['internal_refs_removed'],
                        )
                        classifications.append(classification)
                except Exception as e:
                    # Pydantic validation error or other issues
                    logger.warning(
                        f"Error creating classification for footnote {idx + 1}: {e}. "
                        f"Using fallback classification."
                    )
                    # Fallback to CULTURAL with low confidence
                    fallback = FootnoteClassification(
                        ideogram=fn.get('ideogram', 'Unknown'),
                        explanation=fn.get('explanation', ''),
                        classification_type='CULTURAL',
                        confidence=0.1,
                        reasoning=f'Fallback due to validation error: {e}',
                        original_explanation=fn.get('original_explanation', ''),
                        internal_refs_removed=fn.get('internal_refs_removed', 0),
                    )
                    classifications.append(fallback)

            return classifications

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            raise
        except Exception as e:
            logger.error(f"Error classifying footnotes: {e}")
            raise

    def classify_all_footnotes(
        self, footnotes: List[Dict[str, Any]]
    ) -> Dict[str, FootnoteClassification]:
        """
        Classify all footnotes in batches.

        Args:
            footnotes: List of all footnotes to classify

        Returns:
            Dictionary mapping ideogram to classification
        """
        classifications = {}

        # Process in batches
        total_batches = (len(footnotes) + self.config.batch_size - 1) // self.config.batch_size

        with tqdm(total=len(footnotes), desc="Classifying footnotes") as pbar:
            for i in range(0, len(footnotes), self.config.batch_size):
                batch = footnotes[i:i + self.config.batch_size]
                batch_num = i // self.config.batch_size + 1

                logger.info(f"Processing batch {batch_num}/{total_batches}")

                try:
                    batch_classifications = self.classify_footnotes_batch(batch)

                    for classification in batch_classifications:
                        # Use ideogram as key for deduplication
                        classifications[classification.ideogram] = classification

                        # Update counters
                        if classification.classification_type == 'FICTIONAL_CHARACTER':
                            self.result.fictional_character_count += 1
                        elif classification.classification_type == 'HISTORICAL_FIGURE':
                            self.result.historical_figure_count += 1
                        elif classification.classification_type == 'LEGENDARY_PERSONAGE':
                            self.result.legendary_personage_count += 1
                        elif classification.classification_type == 'CULTURAL':
                            self.result.cultural_count += 1

                    pbar.update(len(batch))

                except Exception as e:
                    logger.error(f"Failed to classify batch {batch_num}: {e}")
                    # Continue with next batch
                    pbar.update(len(batch))

        self.result.classifications = list(classifications.values())
        return classifications

    def should_remove_footnote(
        self, classification: FootnoteClassification
    ) -> bool:
        """
        Determine if a footnote should be removed based on classification.

        Args:
            classification: The footnote classification

        Returns:
            True if footnote should be removed
        """
        if classification.classification_type == 'FICTIONAL_CHARACTER':
            return True  # Always remove fictional characters

        if classification.classification_type == 'HISTORICAL_FIGURE':
            return not self.config.preserve_historical

        if classification.classification_type == 'LEGENDARY_PERSONAGE':
            return not self.config.preserve_legendary

        if classification.classification_type == 'CULTURAL':
            return not self.config.preserve_cultural

        return False

    def cleanup_footnotes(
        self,
        data: Dict[str, Any],
        classifications: Dict[str, FootnoteClassification]
    ) -> Dict[str, Any]:
        """
        Remove footnotes based on classifications and renumber remaining ones.

        Args:
            data: Original JSON data
            classifications: Classification results by ideogram

        Returns:
            Modified JSON data with footnotes removed/renumbered
        """
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        # Track which ideograms we've seen across the ENTIRE work (for deduplication)
        seen_ideograms_global = set()

        for chapter in tqdm(chapters, desc="Cleaning chapters"):
            for block in chapter.get('content_blocks', []):
                if not block.get('footnotes'):
                    continue

                filtered_footnotes = []

                for footnote in block['footnotes']:
                    ideogram = footnote.get('ideogram', '')
                    classification = classifications.get(ideogram)

                    # Check if this ideogram has appeared anywhere in the work before
                    if ideogram in seen_ideograms_global:
                        # This is a duplicate across the entire work - remove it
                        self.result.removed_footnotes.append({
                            'ideogram': ideogram,
                            'explanation': footnote.get('explanation', ''),
                            'type': 'DUPLICATE',
                            'confidence': 100,
                            'reasoning': f"Duplicate occurrence of '{ideogram}' (already appeared earlier in work)",
                            'block_id': block.get('id'),
                        })
                        self.result.removed_count += 1
                        continue  # Skip this duplicate footnote

                    # Mark this ideogram as seen globally
                    seen_ideograms_global.add(ideogram)

                    if not classification:
                        # No classification found, preserve by default
                        logger.warning(
                            f"No classification for '{ideogram}', preserving"
                        )
                        filtered_footnotes.append(footnote)
                        self.result.preserved_count += 1
                        continue

                    # Update explanation with cleaned version (internal refs stripped)
                    footnote['explanation'] = classification.explanation

                    if self.should_remove_footnote(classification):
                        # Track removal
                        self.result.removed_footnotes.append({
                            'ideogram': ideogram,
                            'explanation': classification.explanation,
                            'type': classification.classification_type,
                            'confidence': classification.confidence,
                            'reasoning': classification.reasoning,
                            'block_id': block.get('id'),
                        })
                        self.result.removed_count += 1
                    else:
                        filtered_footnotes.append(footnote)
                        self.result.preserved_count += 1

                # Update footnotes list
                block['footnotes'] = filtered_footnotes

                # Renumber footnotes sequentially within this block
                for idx, footnote in enumerate(filtered_footnotes, start=1):
                    footnote['key'] = idx

                # Remove duplicate markers from translated_content
                # Keep only the first occurrence of each marker
                translated_content = block.get('translated_content', '')
                if translated_content:
                    # Track which markers we've seen
                    seen_markers = set()

                    def replace_marker(match):
                        """Replace duplicate markers with empty string, keep first occurrence."""
                        marker = match.group(1)
                        if marker in seen_markers:
                            # This is a duplicate - remove it
                            return ''
                        else:
                            # This is the first occurrence - keep it
                            seen_markers.add(marker)
                            return match.group(0)  # Return original [N]

                    # Replace all markers, removing duplicates
                    block['translated_content'] = re.sub(r'\[(\d+)\]', replace_marker, translated_content)

        return data

    def process_file(
        self,
        input_path: Path,
        output_path: Path,
        dry_run: bool = False
    ) -> CleanupResult:
        """
        Process a single JSON file.

        Args:
            input_path: Path to input JSON file
            output_path: Path to output JSON file
            dry_run: If True, don't write output file

        Returns:
            CleanupResult with statistics
        """
        logger.info(f"Processing: {input_path}")

        # Load input file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create backup if requested
        if self.config.create_backup and not dry_run:
            backup_path = input_path.with_suffix('.json.backup')
            if not backup_path.exists():
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"Created backup: {backup_path}")

        # Extract all footnotes
        logger.info("Extracting footnotes...")
        footnotes = self.extract_all_footnotes(data)
        self.result.total_footnotes = len(footnotes)
        logger.info(f"Found {len(footnotes)} total footnotes")
        logger.info(f"Stripped internal references from {self.result.internal_refs_stripped} footnotes")

        if not footnotes:
            logger.warning("No footnotes found in file")
            return self.result

        # Classify footnotes
        logger.info("Classifying footnotes with OpenAI...")
        classifications = self.classify_all_footnotes(footnotes)

        # Clean up footnotes
        if not dry_run:
            logger.info("Removing fictional character footnotes...")
            data = self.cleanup_footnotes(data, classifications)

            # Write output file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Wrote cleaned file to: {output_path}")
        else:
            logger.info("Dry run - no files written")

        return self.result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Remove fictional character footnotes while preserving others"
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input JSON file path'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output JSON file path (default: character_footnotes_cleaned/{filename})'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./character_footnotes_cleaned'),
        help='Output directory (default: ./character_footnotes_cleaned)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )
    parser.add_argument(
        '--log-dir',
        type=Path,
        default=Path('./logs'),
        help='Log directory (default: ./logs)'
    )
    parser.add_argument(
        '--model',
        default='gpt-4.1-nano',
        help='OpenAI model (default: gpt-4.1-nano)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Footnotes per API call (default: 25)'
    )
    parser.add_argument(
        '--no-preserve-historical',
        dest='preserve_historical',
        action='store_false',
        help='Remove historical figures (default: preserve)'
    )
    parser.add_argument(
        '--no-preserve-legendary',
        dest='preserve_legendary',
        action='store_false',
        help='Remove legendary personages (default: preserve)'
    )
    parser.add_argument(
        '--no-preserve-cultural',
        dest='preserve_cultural',
        action='store_false',
        help='Remove cultural footnotes (default: preserve)'
    )
    parser.add_argument(
        '--no-backup',
        dest='create_backup',
        action='store_false',
        help="Don't create backup file"
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.output_dir / args.input.name

    # Create config
    config = CleanupConfig(
        model=args.model,
        batch_size=args.batch_size,
        preserve_historical=args.preserve_historical,
        preserve_legendary=args.preserve_legendary,
        preserve_cultural=args.preserve_cultural,
        create_backup=args.create_backup,
    )

    # Process file
    processor = CharacterFootnoteCleanup(config)

    try:
        result = processor.process_file(
            input_path=args.input,
            output_path=output_path,
            dry_run=args.dry_run
        )

        # Print summary
        print("\n" + "=" * 80)
        print("CHARACTER FOOTNOTE CLEANUP SUMMARY")
        print("=" * 80)
        print(f"Total footnotes:           {result.total_footnotes}")
        print(f"Internal refs stripped:    {result.internal_refs_stripped}")
        print(f"Fictional characters:      {result.fictional_character_count}")
        print(f"Historical figures:        {result.historical_figure_count}")
        print(f"Legendary personages:      {result.legendary_personage_count}")
        print(f"Cultural notes:            {result.cultural_count}")
        print(f"Removed:                   {result.removed_count}")
        print(f"Preserved:                 {result.preserved_count}")
        print("=" * 80)

        # Save detailed log
        if not args.dry_run:
            log_path = args.log_dir / f"{args.input.stem}_character_cleanup_log.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

            print(f"\nDetailed log saved to: {log_path}")

        return 0

    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
