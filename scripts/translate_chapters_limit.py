#!/usr/bin/env python3
"""
Quick script to translate a limited number of chapters from D58 volume 1.
"""

import sys
import json
from pathlib import Path


from processors.translator import TranslationService
from processors.translation_config import TranslationConfig
from utils.load_env_creds import load_env_credentials
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment
    load_env_credentials()

    # Paths
    input_file = Path("/Users/jacki/project_files/translation_project/cleaned/COMPLETE_ALL_BOOKS/wuxia_0004/cleaned_D58a_書劍恩仇錄上_金庸.json")
    output_file = Path("translation_data/test_translations/D58/translated_D58a_first_5_chapters.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load book
    logger.info(f"Loading book from {input_file}")
    with open(input_file) as f:
        book_data = json.load(f)

    # Get chapters
    chapters = book_data.get('structure', {}).get('body', {}).get('chapters', [])
    logger.info(f"Found {len(chapters)} total chapters")

    # Limit to first 5 chapters
    chapters_to_translate = chapters[:5]
    logger.info(f"Translating first {len(chapters_to_translate)} chapters")

    # Initialize translation service
    config = TranslationConfig()
    service = TranslationService(
        model="gpt-4.1-nano",
        temperature=0.3,
        max_retries=3,
        timeout=120,
        glossary_path=Path("wuxia_glossary.db")
    )

    # Translate chapters
    from tqdm import tqdm
    translated_chapters = []

    for i, chapter in enumerate(tqdm(chapters_to_translate, desc="Translating chapters")):
        logger.info(f"\nChapter {i+1}/5: {chapter.get('title', 'Untitled')}")
        logger.info(f"  Blocks: {len(chapter.get('content_blocks', []))}")

        # Translate chapter blocks
        translated_blocks = []
        blocks = chapter.get('content_blocks', [])

        for block_idx, block in enumerate(tqdm(blocks, desc=f"  {chapter.get('title', 'Untitled')[:40]}", leave=False)):
            # Create request
            request = {
                'content_text_id': block_idx + 1,
                'content_source_text': block.get('content', ''),
                'content_type': block.get('type', 'narrative')
            }

            try:
                # Translate
                response = service.translate(request)

                # Extract translated content
                translated_content = response['translated_annotated_content']

                # Create translated block
                translated_block = {
                    **block,
                    'translated_text': translated_content.get('annotated_content_text', ''),
                    'footnotes': translated_content.get('content_footnotes', []),
                    'metadata': response.get('metadata', {})
                }

                translated_blocks.append(translated_block)

            except Exception as e:
                logger.error(f"Failed to translate block {block_idx+1}: {e}")
                # Keep original block
                translated_blocks.append(block)

        # Create translated chapter
        translated_chapter = {
            **chapter,
            'content_blocks': translated_blocks
        }
        translated_chapters.append(translated_chapter)

    # Create output with only first 5 chapters
    output_data = {
        **book_data,
        'structure': {
            **book_data['structure'],
            'body': {
                'chapters': translated_chapters
            }
        }
    }

    # Save
    logger.info(f"\nSaving to {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ Translated {len(translated_chapters)} chapters successfully")
    logger.info(f"✓ Output: {output_file}")

if __name__ == "__main__":
    main()
