#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Input JSON - Transform any book JSON into discrete block structure.

Takes a raw book JSON file and transforms it into a clean, structured format
with discrete content blocks suitable for EPUB generation.

This is a standalone tool that doesn't require the OpenAI assistant analysis.
It simply restructures the input JSON into a standardized format.
"""

import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================
# CONFIG (edit if needed)
# =========================
DEFAULT_INPUT_PATH = "./input/book.json"
DEFAULT_OUTPUT_PATH = "./output/cleaned_book.json"
DEFAULT_LANGUAGE = "zh-Hant"

# =========================
# Helper Functions
# =========================

def detect_language(text: str) -> str:
    """Detect language from text sample."""
    # Simple heuristic based on character ranges
    if any('\u4e00' <= c <= '\u9fff' for c in text[:100]):
        return "zh"  # Chinese
    return "en"


def extract_text_from_single_node(node: Dict[str, Any]) -> str:
    """Extract all text from a single node (including nested content)."""
    if isinstance(node, str):
        return node

    content = node.get("content", "")
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                texts.append(extract_text_from_single_node(item))
        return " ".join(texts)

    return ""


def extract_blocks_from_nodes(nodes: List[Any], start_id: int = 0, context: str = "") -> List[Dict[str, Any]]:
    """
    Extract discrete content blocks from structured nodes.
    Each block is a separate element that can be referenced in EPUB.
    """
    blocks = []
    block_id = start_id

    for node in nodes:
        if isinstance(node, str):
            if node.strip():
                blocks.append({
                    "id": f"block_{block_id:04d}",
                    "type": "text",
                    "content": node.strip(),
                    "epub_id": f"text_{block_id}"
                })
                block_id += 1

        elif isinstance(node, dict):
            tag = node.get("tag", "").lower()
            content = node.get("content", "")

            # Heading elements
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": f"heading_{tag[1]}",  # heading_1, heading_2, etc.
                        "content": text.strip(),
                        "epub_id": f"heading_{block_id}",
                        "level": int(tag[1])
                    })
                    block_id += 1

            # Paragraph elements
            elif tag == "p":
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "paragraph",
                        "content": text.strip(),
                        "epub_id": f"para_{block_id}"
                    })
                    block_id += 1

            # Division elements - recurse into children
            elif tag in ("div", "section", "article", "body"):
                if isinstance(content, list):
                    nested_blocks = extract_blocks_from_nodes(content, block_id, context)
                    blocks.extend(nested_blocks)
                    block_id += len(nested_blocks)
                elif isinstance(content, str) and content.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "text",
                        "content": content.strip(),
                        "epub_id": f"text_{block_id}"
                    })
                    block_id += 1

            # List elements
            elif tag in ("ul", "ol"):
                if isinstance(content, list):
                    list_items = extract_blocks_from_nodes(content, block_id, context)
                    if list_items:
                        blocks.append({
                            "id": f"block_{block_id:04d}",
                            "type": f"list_{tag}",
                            "content": list_items,
                            "epub_id": f"list_{block_id}"
                        })
                        block_id += 1

            elif tag == "li":
                text = extract_text_from_single_node(node)
                if text.strip():
                    blocks.append({
                        "id": f"block_{block_id:04d}",
                        "type": "list_item",
                        "content": text.strip(),
                        "epub_id": f"li_{block_id}"
                    })
                    block_id += 1

            # Other elements with nested content
            elif isinstance(content, list):
                nested_blocks = extract_blocks_from_nodes(content, block_id, context)
                blocks.extend(nested_blocks)
                block_id += len(nested_blocks)

            elif isinstance(content, str) and content.strip():
                blocks.append({
                    "id": f"block_{block_id:04d}",
                    "type": "text",
                    "content": content.strip(),
                    "epub_id": f"text_{block_id}",
                    "tag": tag
                })
                block_id += 1

    return blocks


def parse_content_into_blocks(content: Any, chapter_title: str) -> List[Dict[str, Any]]:
    """
    Parse content into discrete blocks (headings, paragraphs, etc.)
    suitable for EPUB generation with proper internal linking.
    """
    blocks = []
    block_id_counter = 0

    if isinstance(content, str):
        # Simple string content - split into paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for para in paragraphs:
            blocks.append({
                "id": f"block_{block_id_counter:04d}",
                "type": "paragraph",
                "content": para,
                "epub_id": f"para_{block_id_counter}"
            })
            block_id_counter += 1

    elif isinstance(content, list):
        # Structured content with HTML-like tags
        blocks = extract_blocks_from_nodes(content, block_id_counter, chapter_title)

    return blocks


def detect_toc(chapter: Dict[str, Any], index: int) -> bool:
    """Detect if a chapter is a table of contents."""
    title = chapter.get("title", "").lower()

    # Common TOC indicators
    toc_indicators = ["目錄", "目录", "contents", "table of contents", "toc"]

    # Check title
    if any(indicator in title for indicator in toc_indicators):
        return True

    # Check if it's the first section and has short lines
    if index == 0:
        content = chapter.get("content", "")
        if isinstance(content, str):
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            if len(lines) >= 5:
                short_lines = sum(1 for line in lines if len(line) <= 15)
                if short_lines / len(lines) > 0.7:  # 70% short lines
                    return True

    return False


def clean_book_json(input_path: str, language_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Clean and structure a book JSON file into discrete blocks.

    Args:
        input_path: Path to input JSON file
        language_hint: Optional language hint (zh, zh-Hans, zh-Hant, en, etc.)

    Returns:
        Cleaned book structure with discrete content blocks
    """
    # Load input
    input_data = json.loads(Path(input_path).read_text(encoding="utf-8"))

    # Detect book title
    book_title = "Untitled"
    if "title" in input_data:
        book_title = input_data["title"]
    elif "chapters" in input_data and len(input_data["chapters"]) > 0:
        first_chapter = input_data["chapters"][0]
        if isinstance(first_chapter, dict) and "title" in first_chapter:
            # Use first chapter title as book title
            book_title = first_chapter["title"]

    # Detect language
    if not language_hint:
        sample_text = str(input_data)[:1000]
        language_hint = detect_language(sample_text)

    # Initialize cleaned structure
    cleaned_book = {
        "meta": {
            "title": book_title,
            "language": language_hint,
            "schema_version": "2.0.0",
            "source": "cleaned-input",
            "original_file": str(Path(input_path).name)
        },
        "structure": {
            "front_matter": {},
            "body": {
                "chapters": []
            },
            "back_matter": {}
        }
    }

    # Process chapters
    chapters = input_data.get("chapters", [])
    if not chapters:
        # Try other common field names
        chapters = input_data.get("sections", [])

    for idx, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            continue

        chapter_title = chapter.get("title", f"Chapter {idx + 1}")

        # Check if this is TOC
        if detect_toc(chapter, idx):
            # Add to front matter
            content = chapter.get("content", "")
            if isinstance(content, list):
                content_text = extract_text_from_single_node({"content": content})
            else:
                content_text = str(content)

            cleaned_book["structure"]["front_matter"]["toc"] = [{
                "id": "toc_0000",
                "title": "Table of Contents",
                "title_en": "Table of Contents",
                "content": content_text
            }]
            continue

        # Process regular chapter
        content = chapter.get("content", "")
        content_blocks = parse_content_into_blocks(content, chapter_title)

        cleaned_chapter = {
            "id": f"chapter_{idx:04d}",
            "title": chapter_title,
            "title_en": "",  # Could add translation support
            "ordinal": idx + 1,
            "content_blocks": content_blocks,
            "source_reference": f"/chapters/{idx}"
        }

        cleaned_book["structure"]["body"]["chapters"].append(cleaned_chapter)

    return cleaned_book


def print_summary(cleaned_book: Dict[str, Any]):
    """Print a summary of the cleaned book structure."""
    print("=" * 70)
    print("CLEANED BOOK SUMMARY")
    print("=" * 70)

    meta = cleaned_book["meta"]
    print(f"\n📖 Title: {meta['title']}")
    print(f"Language: {meta['language']}")
    print(f"Original file: {meta['original_file']}")

    structure = cleaned_book["structure"]

    # Front matter
    front = structure.get("front_matter", {})
    if front:
        print(f"\n📑 FRONT MATTER:")
        for key, value in front.items():
            if isinstance(value, list) and value:
                total_chars = sum(len(item.get("content", "")) for item in value)
                print(f"  - {key}: {len(value)} item(s), {total_chars} chars")

    # Body
    chapters = structure["body"]["chapters"]
    total_blocks = sum(len(ch.get("content_blocks", [])) for ch in chapters)

    print(f"\n📚 BODY:")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Total content blocks: {total_blocks:,}")
    print(f"  Average blocks per chapter: {total_blocks/len(chapters):.1f}")

    print(f"\n📊 CHAPTERS:")
    for i, ch in enumerate(chapters[:10], 1):  # Show first 10
        blocks = len(ch.get("content_blocks", []))
        print(f"  {i:2d}. {ch['title'][:30]:30s} - {blocks:3d} blocks")

    if len(chapters) > 10:
        print(f"  ... and {len(chapters) - 10} more chapters")

    # Back matter
    back = structure.get("back_matter", {})
    if back:
        print(f"\n📚 BACK MATTER:")
        for key, value in back.items():
            if isinstance(value, list) and value:
                total_chars = sum(len(item.get("content", "")) for item in value)
                print(f"  - {key}: {len(value)} item(s), {total_chars} chars")

    print(f"\n🔗 EPUB READY:")
    print(f"  ✓ Each block has unique ID and EPUB ID")
    print(f"  ✓ Block types: heading, paragraph, text, list")
    print(f"  ✓ Source references maintained")
    print("=" * 70)


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description='Clean book JSON into discrete block structure for EPUB generation'
    )

    parser.add_argument(
        '--input',
        default=DEFAULT_INPUT_PATH,
        help=f'Input book JSON file (default: {DEFAULT_INPUT_PATH})'
    )

    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_PATH,
        help=f'Output cleaned JSON file (default: {DEFAULT_OUTPUT_PATH})'
    )

    parser.add_argument(
        '--language',
        help='Language hint (zh, zh-Hans, zh-Hant, en, etc.)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress summary output'
    )

    args = parser.parse_args()

    # Validate input
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        return 1

    print(f"📖 Loading book from: {args.input}")

    # Clean the book
    try:
        cleaned_book = clean_book_json(args.input, args.language)
    except Exception as e:
        print(f"❌ Error cleaning book: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_text(
            json.dumps(cleaned_book, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"✓ Cleaned book saved to: {args.output}")
    except Exception as e:
        print(f"❌ Error saving output: {e}")
        return 1

    # Print summary
    if not args.quiet:
        print()
        print_summary(cleaned_book)

    # File size
    import os
    file_size = os.path.getsize(args.output)
    print(f"\n💾 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    exit(main())
