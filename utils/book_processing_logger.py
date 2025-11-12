#!/usr/bin/env python3
"""
Book Processing Logger - Generate detailed per-book processing logs

Creates a log file in each output directory documenting:
- Processing stages completed
- Any issues or warnings encountered
- Modifications made (chapters split, TOC regenerated, etc.)
- Validation results
- Final status
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def generate_book_processing_log(
    output_dir: Path,
    filename: str,
    result: Dict[str, Any]
) -> Path:
    """
    Generate a detailed processing log for a single book

    Args:
        output_dir: Directory where the cleaned book and log will be saved
        filename: Name of the output file (e.g., "cleaned_book.json")
        result: Processing result dict from batch processor

    Returns:
        Path to the generated log file
    """
    # Create log filename
    log_filename = filename.replace('.json', '_processing.log')
    log_path = output_dir / log_filename

    # Build log content
    lines = []
    lines.append("="*80)
    lines.append("BOOK PROCESSING LOG")
    lines.append("="*80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Book: {result.get('folder', 'Unknown')}/{result.get('file', filename)}")
    lines.append(f"Status: {result.get('status', 'UNKNOWN')}")
    lines.append("")

    # Metadata
    if 'metadata' in result and result['metadata']:
        lines.append("METADATA")
        lines.append("-" * 40)
        metadata = result['metadata']
        if metadata.get('work_number'):
            lines.append(f"  Work Number: {metadata['work_number']}")
        if metadata.get('title_chinese'):
            lines.append(f"  Title: {metadata['title_chinese']}")
        if metadata.get('author_chinese'):
            lines.append(f"  Author: {metadata['author_chinese']}")
        if metadata.get('volume'):
            lines.append(f"  Volume: {metadata['volume']}")
        lines.append("")

    # Processing stages
    if 'stages' in result:
        lines.append("PROCESSING STAGES")
        lines.append("-" * 40)

        for stage_name, stage_data in result['stages'].items():
            if isinstance(stage_data, dict):
                success = stage_data.get('success', False)
                status_mark = "✓" if success else "✗"
                lines.append(f"  {status_mark} {stage_name.upper()}")

                if not success and 'error' in stage_data:
                    lines.append(f"      Error: {stage_data['error']}")

                # Stage-specific details
                if stage_name == 'topology' and success:
                    if 'estimated_tokens' in stage_data:
                        lines.append(f"      Tokens: {stage_data['estimated_tokens']:,}")
                    if 'max_depth' in stage_data:
                        lines.append(f"      Max Depth: {stage_data['max_depth']}")

                elif stage_name == 'sanity_check':
                    if 'sequence_issues' in stage_data and stage_data['sequence_issues']:
                        lines.append(f"      Sequence Issues: {len(stage_data['sequence_issues'])}")
                        for issue in stage_data['sequence_issues'][:5]:  # Show first 5
                            lines.append(f"        - [{issue.get('severity', 'UNKNOWN')}] {issue.get('message', '')}")
                        if len(stage_data['sequence_issues']) > 5:
                            lines.append(f"        ... and {len(stage_data['sequence_issues']) - 5} more")

                elif stage_name == 'alignment':
                    if 'changes_made' in stage_data:
                        lines.append(f"      Changes: {stage_data['changes_made']}")
                    if 'fixes' in stage_data and stage_data['fixes']:
                        lines.append("      Fixes Applied:")
                        for fix in stage_data['fixes'][:5]:
                            lines.append(f"        - {fix}")
                        if len(stage_data['fixes']) > 5:
                            lines.append(f"        ... and {len(stage_data['fixes']) - 5} more")

                elif stage_name == 'validation':
                    if 'confidence_score' in stage_data:
                        lines.append(f"      Confidence: {stage_data['confidence_score']}%")
                    if 'toc_count' in stage_data and 'chapter_count' in stage_data:
                        lines.append(f"      TOC Entries: {stage_data['toc_count']}")
                        lines.append(f"      Body Chapters: {stage_data['chapter_count']}")
                    if 'matched_count' in stage_data:
                        lines.append(f"      Matched: {stage_data['matched_count']}")

        lines.append("")

    # Issues and warnings
    if result.get('issues') or result.get('warnings'):
        lines.append("ISSUES & WARNINGS")
        lines.append("-" * 40)

        if result.get('issues'):
            lines.append("  Issues:")
            for issue in result['issues']:
                lines.append(f"    • {issue}")

        if result.get('warnings'):
            lines.append("  Warnings:")
            for warning in result['warnings']:
                lines.append(f"    • {warning}")

        lines.append("")

    # Validation details
    if 'validation_issues' in result and result['validation_issues']:
        lines.append("VALIDATION DETAILS")
        lines.append("-" * 40)

        for issue in result['validation_issues'][:10]:  # Show first 10
            severity = issue.get('severity', 'INFO')
            issue_type = issue.get('type', 'unknown')
            message = issue.get('message', '')
            lines.append(f"  [{severity.upper()}] {issue_type}: {message}")

            if 'suggested_fix' in issue:
                lines.append(f"    💡 Suggested: {issue['suggested_fix']}")

        if len(result['validation_issues']) > 10:
            lines.append(f"  ... and {len(result['validation_issues']) - 10} more issues")

        lines.append("")

    # Auto-fix actions
    if 'auto_fixes' in result and result['auto_fixes']:
        lines.append("AUTO-FIX ACTIONS")
        lines.append("-" * 40)
        for fix in result['auto_fixes']:
            lines.append(f"  • {fix}")
        lines.append("")

    # Statistics
    if 'stats' in result:
        lines.append("STATISTICS")
        lines.append("-" * 40)
        for key, value in result['stats'].items():
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    lines.append(f"  {key.replace('_', ' ').title()}: {value:.2f}")
                else:
                    lines.append(f"  {key.replace('_', ' ').title()}: {value:,}")
        lines.append("")

    # Skip reason
    if 'skip_reason' in result:
        lines.append("SKIP REASON")
        lines.append("-" * 40)
        lines.append(f"  {result['skip_reason']}")
        lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 40)
    status = result.get('status', 'UNKNOWN')
    if status == 'SUCCESS':
        lines.append("  ✓ Processing completed successfully")
    elif status == 'COMPLETED_WITH_ISSUES':
        lines.append("  ⚠ Processing completed with issues (see above)")
    elif status == 'FAILED':
        lines.append("  ✗ Processing failed")
    elif status == 'SKIPPED':
        lines.append("  ⊘ Processing skipped")
    else:
        lines.append(f"  Status: {status}")

    lines.append("")
    lines.append("="*80)
    lines.append(f"End of log - Generated by Book Processing Toolkit")
    lines.append("="*80)

    # Write log file
    log_content = "\n".join(lines)
    log_path.write_text(log_content, encoding='utf-8')

    return log_path


def generate_log_from_file_result(
    output_base: Path,
    result: Dict[str, Any]
) -> Path:
    """
    Generate log from a file processing result

    Determines the output directory based on folder name in result
    and generates the log there.

    Args:
        output_base: Base output directory
        result: Processing result dict

    Returns:
        Path to generated log file
    """
    folder_name = result.get('folder', 'unknown')
    file_name = result.get('file', 'unknown.json')

    # Create output directory for this book
    output_dir = output_base / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename (typically "cleaned_*.json")
    cleaned_filename = file_name
    if not cleaned_filename.startswith('cleaned_'):
        cleaned_filename = f"cleaned_{file_name}"

    return generate_book_processing_log(output_dir, cleaned_filename, result)


def generate_logs_from_batch_report(
    batch_report_path: Path,
    output_base: Path
) -> List[Path]:
    """
    Generate individual book logs from a batch report JSON

    Args:
        batch_report_path: Path to batch_report_*.json
        output_base: Base output directory

    Returns:
        List of paths to generated log files
    """
    with open(batch_report_path, 'r', encoding='utf-8') as f:
        batch_report = json.load(f)

    log_files = []

    for file_result in batch_report.get('files', []):
        try:
            log_path = generate_log_from_file_result(output_base, file_result)
            log_files.append(log_path)
        except Exception as e:
            print(f"Warning: Failed to generate log for {file_result.get('file')}: {e}")

    return log_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate per-book processing logs from batch report'
    )
    parser.add_argument(
        '--batch-report',
        required=True,
        help='Path to batch_report_*.json file'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Base output directory where book folders exist'
    )

    args = parser.parse_args()

    batch_report_path = Path(args.batch_report)
    output_base = Path(args.output_dir)

    if not batch_report_path.exists():
        print(f"Error: Batch report not found: {batch_report_path}")
        exit(1)

    if not output_base.exists():
        print(f"Error: Output directory not found: {output_base}")
        exit(1)

    print(f"Generating logs from: {batch_report_path}")
    print(f"Output base: {output_base}")
    print()

    log_files = generate_logs_from_batch_report(batch_report_path, output_base)

    print(f"✓ Generated {len(log_files)} log files")
    for log_file in log_files[:10]:
        print(f"  {log_file}")
    if len(log_files) > 10:
        print(f"  ... and {len(log_files) - 10} more")
