#!/usr/bin/env python3
"""
Autonomous Test and Fix Agent

This agent orchestrates an iterative debugging workflow:
1. Run test plan (early-exit test on sample)
2. Analyze failures
3. Propose and apply fixes
4. Regression test previously passing files
5. Repeat until all tests pass

Architecture:
- Test Agent: Runs tests and collects results
- Analysis Agent: Analyzes failures and proposes fixes
- Fix Agent: Applies fixes to code
- Regression Agent: Validates no regressions
"""

import json
import logging
import sys
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result from a single test run"""
    status: str  # "pass", "fail", "error"
    file_path: str
    toc_count: int
    body_count: int
    missing_from_toc: List[int]
    extra_in_toc: List[int]
    error_message: Optional[str] = None


@dataclass
class TestPlanResult:
    """Result from entire test plan"""
    timestamp: str
    iteration: int
    total_files: int
    passed: int
    failed: int
    errors: int
    failures: List[TestResult]
    passed_files: List[str]


@dataclass
class FixProposal:
    """Proposed fix for an issue"""
    issue_type: str
    description: str
    file_to_modify: str
    proposed_change: str
    confidence: float


class TestOrchestrator:
    """Orchestrates the test-fix-verify loop"""

    # Non-book file patterns to skip
    SKIP_PATTERNS = [
        r'.*_haodoo_page\.json$',  # Haodoo website metadata
        r'.*wuxia_work_summary.*\.json$',  # Work summaries
        r'.*summary_translated.*\.json$',  # Translated summaries
        r'.*invalid.*\.json$',  # Files marked as invalid
    ]

    def __init__(
        self,
        source_dir: Path,
        output_dir: Path,
        catalog_path: Path,
        max_iterations: int = 5,
        test_sample_size: int = 10
    ):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.catalog_path = catalog_path
        self.max_iterations = max_iterations
        self.test_sample_size = test_sample_size

        # State tracking
        self.iteration = 0
        self.test_history = []
        self.fix_history = []
        self.passed_files = set()

        # Create log directory
        self.log_dir = Path("autonomous_test_logs")
        self.log_dir.mkdir(exist_ok=True)

    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped based on patterns"""
        filename = file_path.name
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, filename):
                return True
        return False

    def run_test_plan(self, limit: int = None) -> TestPlanResult:
        """
        Run the early-exit test plan

        Returns test results with pass/fail status for each file
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"ITERATION {self.iteration + 1}: Running test plan")
        logger.info(f"{'='*80}\n")

        # Import test modules
                from processors.json_cleaner import clean_book_json
        from utils.toc_body_count_validator import validate_toc_body_alignment

        test_limit = limit or self.test_sample_size
        source_dirs = sorted([d for d in self.source_dir.iterdir() if d.is_dir()])[:test_limit]

        results = []
        passed_files = []

        for dir_idx, book_dir in enumerate(source_dirs, 1):
            json_files = list(book_dir.glob("*.json"))
            if not json_files:
                continue

            for json_file in json_files:
                # Skip non-book files
                if self.should_skip_file(json_file):
                    logger.debug(f"[{dir_idx}/{len(source_dirs)}] Skipping: {book_dir.name}/{json_file.name}")
                    continue

                logger.info(f"[{dir_idx}/{len(source_dirs)}] Testing: {book_dir.name}/{json_file.name}")

                try:
                    # Clean the file
                    output_subdir = self.output_dir / book_dir.name
                    output_subdir.mkdir(parents=True, exist_ok=True)
                    output_file = output_subdir / f"cleaned_{json_file.name}"

                    cleaned_data = clean_book_json(
                        str(json_file),
                        catalog_path=str(self.catalog_path),
                        directory_name=book_dir.name
                    )

                    # Save cleaned file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

                    # Validate
                    validation = validate_toc_body_alignment(cleaned_data)

                    if validation['valid']:
                        logger.info(f"  ✓ PASS")
                        results.append(TestResult(
                            status="pass",
                            file_path=str(json_file),
                            toc_count=validation['toc_count'],
                            body_count=validation['body_count'],
                            missing_from_toc=[],
                            extra_in_toc=[]
                        ))
                        passed_files.append(str(json_file))
                    else:
                        logger.warning(f"  ✗ FAIL - TOC: {validation['toc_count']}, Body: {validation['body_count']}")
                        results.append(TestResult(
                            status="fail",
                            file_path=str(json_file),
                            toc_count=validation['toc_count'],
                            body_count=validation['body_count'],
                            missing_from_toc=validation.get('missing_from_toc', []),
                            extra_in_toc=validation.get('extra_in_toc', [])
                        ))

                except Exception as e:
                    logger.error(f"  ✗ ERROR: {e}")
                    results.append(TestResult(
                        status="error",
                        file_path=str(json_file),
                        toc_count=0,
                        body_count=0,
                        missing_from_toc=[],
                        extra_in_toc=[],
                        error_message=str(e)
                    ))

        # Summarize results
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        errors = sum(1 for r in results if r.status == "error")

        failures = [r for r in results if r.status in ("fail", "error")]

        plan_result = TestPlanResult(
            timestamp=datetime.now().isoformat(),
            iteration=self.iteration,
            total_files=len(results),
            passed=passed,
            failed=failed,
            errors=errors,
            failures=failures,
            passed_files=passed_files
        )

        # Save results
        result_file = self.log_dir / f"test_results_iter_{self.iteration:02d}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(plan_result), f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*80}")
        logger.info(f"TEST RESULTS - Iteration {self.iteration + 1}")
        logger.info(f"{'='*80}")
        logger.info(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
        logger.info(f"Success Rate: {passed/len(results)*100:.1f}%")
        logger.info(f"{'='*80}\n")

        return plan_result

    def analyze_failures(self, test_result: TestPlanResult) -> List[FixProposal]:
        """
        Analyze test failures and propose fixes

        Categories of issues:
        1. Empty structure (0 TOC, 0 chapters) - total extraction failure
        2. Missing TOC (0 TOC, N chapters) - TOC generation failure
        3. Missing chapters (N TOC, 0 chapters) - chapter extraction failure
        4. Misalignment (N TOC != M chapters) - alignment issue
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"ANALYZING FAILURES")
        logger.info(f"{'='*80}\n")

        proposals = []

        # Group failures by pattern
        empty_structures = []
        missing_tocs = []
        missing_chapters = []
        misalignments = []

        for failure in test_result.failures:
            if failure.toc_count == 0 and failure.body_count == 0:
                empty_structures.append(failure)
            elif failure.toc_count == 0 and failure.body_count > 0:
                missing_tocs.append(failure)
            elif failure.toc_count > 0 and failure.body_count == 0:
                missing_chapters.append(failure)
            else:
                misalignments.append(failure)

        logger.info(f"Failure patterns:")
        logger.info(f"  - Empty structures: {len(empty_structures)}")
        logger.info(f"  - Missing TOCs: {len(missing_tocs)}")
        logger.info(f"  - Missing chapters: {len(missing_chapters)}")
        logger.info(f"  - Misalignments: {len(misalignments)}")

        # Analyze empty structures (highest priority)
        if empty_structures:
            logger.info(f"\n🔍 Analyzing empty structure failures...")

            # Load first failing file to inspect structure
            first_fail = empty_structures[0]
            logger.info(f"   Inspecting: {first_fail.file_path}")

            # Read source file
            try:
                with open(first_fail.file_path, 'r', encoding='utf-8') as f:
                    source_data = json.load(f)

                # Analyze structure
                has_chapters = 'chapters' in source_data
                has_sections = 'sections' in source_data
                has_parts = 'parts' in source_data
                has_content = 'content' in source_data

                logger.info(f"   Source structure: chapters={has_chapters}, sections={has_sections}, "
                           f"parts={has_parts}, content={has_content}")

                if has_chapters:
                    chapter_count = len(source_data.get('chapters', []))
                    logger.info(f"   Source has {chapter_count} chapters")

                    if chapter_count > 0:
                        first_chapter = source_data['chapters'][0]
                        logger.info(f"   First chapter keys: {list(first_chapter.keys())}")
                        logger.info(f"   First chapter title: {first_chapter.get('title', 'N/A')[:50]}")

                        # Check content structure
                        content = first_chapter.get('content')
                        if content:
                            logger.info(f"   Content type: {type(content)}")
                            if isinstance(content, list) and len(content) > 0:
                                logger.info(f"   First content item type: {type(content[0])}")

                        proposals.append(FixProposal(
                            issue_type="empty_structure",
                            description=f"Source has {chapter_count} chapters but extraction resulted in 0. "
                                       f"Likely issue with content extraction from nested structure.",
                            file_to_modify="processors/json_cleaner.py",
                            proposed_change="Review extract_blocks_from_nodes() for this file's structure",
                            confidence=0.8
                        ))

            except Exception as e:
                logger.error(f"   Failed to analyze source: {e}")

        # Analyze missing TOCs
        if missing_tocs:
            proposals.append(FixProposal(
                issue_type="missing_toc",
                description=f"{len(missing_tocs)} files have chapters but no TOC. "
                           f"TOC generation may be failing.",
                file_to_modify="processors/json_cleaner.py",
                proposed_change="Review generate_toc_from_chapters() logic",
                confidence=0.7
            ))

        # Analyze misalignments
        if misalignments:
            proposals.append(FixProposal(
                issue_type="toc_chapter_mismatch",
                description=f"{len(misalignments)} files have TOC/chapter count mismatch. "
                           f"May be missing chapter extraction or TOC over-generation.",
                file_to_modify="processors/json_cleaner.py",
                proposed_change="Review split_combined_title_and_chapter() and TOC generation",
                confidence=0.6
            ))

        # Save proposals
        proposal_file = self.log_dir / f"fix_proposals_iter_{self.iteration:02d}.json"
        with open(proposal_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(p) for p in proposals], f, ensure_ascii=False, indent=2)

        logger.info(f"\n📋 Generated {len(proposals)} fix proposals")
        for i, proposal in enumerate(proposals, 1):
            logger.info(f"   {i}. [{proposal.issue_type}] {proposal.description[:80]}...")

        return proposals

    def regression_test(self, previous_passed: List[str]) -> Tuple[int, int]:
        """
        Test previously passing files to ensure no regressions

        Returns: (still_passing, now_failing)
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"REGRESSION TEST")
        logger.info(f"{'='*80}\n")
        logger.info(f"Testing {len(previous_passed)} previously passing files...")

        # Import modules
                from processors.json_cleaner import clean_book_json
        from utils.toc_body_count_validator import validate_toc_body_alignment

        still_passing = 0
        now_failing = 0

        for file_path in previous_passed:
            try:
                json_file = Path(file_path)
                book_dir = json_file.parent

                # Clean
                output_subdir = self.output_dir / book_dir.name
                output_subdir.mkdir(parents=True, exist_ok=True)
                output_file = output_subdir / f"cleaned_{json_file.name}"

                cleaned_data = clean_book_json(
                    str(json_file),
                    catalog_path=str(self.catalog_path),
                    directory_name=book_dir.name
                )

                # Validate
                validation = validate_toc_body_alignment(cleaned_data)

                if validation['valid']:
                    still_passing += 1
                    logger.info(f"  ✓ {json_file.name}")
                else:
                    now_failing += 1
                    logger.error(f"  ✗ REGRESSION: {json_file.name}")

            except Exception as e:
                now_failing += 1
                logger.error(f"  ✗ ERROR in {json_file.name}: {e}")

        logger.info(f"\nRegression Results:")
        logger.info(f"  Still passing: {still_passing}/{len(previous_passed)}")
        logger.info(f"  Now failing: {now_failing}/{len(previous_passed)}")

        return still_passing, now_failing

    def run(self):
        """
        Run the autonomous test-fix-verify loop
        """
        logger.info(f"\n{'#'*80}")
        logger.info(f"AUTONOMOUS TEST AND FIX AGENT")
        logger.info(f"{'#'*80}\n")
        logger.info(f"Configuration:")
        logger.info(f"  Source: {self.source_dir}")
        logger.info(f"  Output: {self.output_dir}")
        logger.info(f"  Catalog: {self.catalog_path}")
        logger.info(f"  Max iterations: {self.max_iterations}")
        logger.info(f"  Test sample size: {self.test_sample_size}")
        logger.info(f"  Log directory: {self.log_dir}")
        logger.info(f"\n{'#'*80}\n")

        for iteration in range(self.max_iterations):
            self.iteration = iteration

            # Run test plan
            test_result = self.run_test_plan()
            self.test_history.append(test_result)

            # Check if all tests passed
            if test_result.failed == 0 and test_result.errors == 0:
                logger.info(f"\n{'='*80}")
                logger.info(f"🎉 ALL TESTS PASSED!")
                logger.info(f"{'='*80}\n")
                logger.info(f"Success achieved in {iteration + 1} iteration(s)")
                break

            # Analyze failures and propose fixes
            proposals = self.analyze_failures(test_result)

            if not proposals:
                logger.warning(f"\n⚠️  No fix proposals generated. Manual intervention needed.")
                break

            # Present proposals for manual review
            logger.info(f"\n{'='*80}")
            logger.info(f"FIX PROPOSALS - MANUAL REVIEW REQUIRED")
            logger.info(f"{'='*80}\n")

            for i, proposal in enumerate(proposals, 1):
                logger.info(f"\n[Proposal {i}]")
                logger.info(f"Issue Type: {proposal.issue_type}")
                logger.info(f"Description: {proposal.description}")
                logger.info(f"File to modify: {proposal.file_to_modify}")
                logger.info(f"Suggested change: {proposal.proposed_change}")
                logger.info(f"Confidence: {proposal.confidence * 100:.0f}%")

            logger.info(f"\n{'='*80}")
            logger.info(f"⏸️  PAUSING FOR MANUAL FIX")
            logger.info(f"{'='*80}\n")
            logger.info(f"Review the proposals above and apply fixes to the code.")
            logger.info(f"Then re-run this script to continue testing.")

            # Save checkpoint
            checkpoint = {
                'iteration': iteration,
                'test_result': asdict(test_result),
                'proposals': [asdict(p) for p in proposals],
                'next_action': 'apply_fixes_and_rerun'
            }

            checkpoint_file = self.log_dir / f"checkpoint_iter_{iteration:02d}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)

            logger.info(f"Checkpoint saved to: {checkpoint_file}")

            # Regression test if we have previous passing files
            if self.passed_files:
                still_passing, now_failing = self.regression_test(list(self.passed_files))

                if now_failing > 0:
                    logger.error(f"\n⚠️  REGRESSIONS DETECTED: {now_failing} previously passing files now fail!")
                    logger.error(f"Review fixes before proceeding.")

            # Update passed files set
            self.passed_files.update(test_result.passed_files)

            # Exit for manual fix
            break

        else:
            logger.warning(f"\n⚠️  Maximum iterations ({self.max_iterations}) reached without full success.")

        # Final summary
        logger.info(f"\n{'#'*80}")
        logger.info(f"FINAL SUMMARY")
        logger.info(f"{'#'*80}\n")
        logger.info(f"Iterations completed: {len(self.test_history)}")

        for i, result in enumerate(self.test_history):
            logger.info(f"  Iteration {i+1}: {result.passed}/{result.total_files} passed "
                       f"({result.passed/result.total_files*100:.1f}%)")

        logger.info(f"\nLogs saved to: {self.log_dir}")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Autonomous test and fix agent for book processing pipeline'
    )
    parser.add_argument(
        '--source-dir',
        type=Path,
        required=True,
        help='Source directory containing book subdirectories'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        required=True,
        help='Output directory for cleaned files'
    )
    parser.add_argument(
        '--catalog-path',
        type=Path,
        required=True,
        help='Path to SQLite catalog database'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=5,
        help='Maximum number of test-fix iterations'
    )
    parser.add_argument(
        '--test-sample-size',
        type=int,
        default=10,
        help='Number of files to test in each iteration'
    )

    args = parser.parse_args()

    orchestrator = TestOrchestrator(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        catalog_path=args.catalog_path,
        max_iterations=args.max_iterations,
        test_sample_size=args.test_sample_size
    )

    orchestrator.run()


if __name__ == '__main__':
    main()
