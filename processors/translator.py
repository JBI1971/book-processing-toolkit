#!/usr/bin/env python3
"""
Translation Service for Classical Chinese and Wuxia Literature

Provides scholarly, PhD-level translation with comprehensive cultural/historical
annotations. Uses OpenAI GPT-4o-mini with two-pass validation and thread isolation.
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from openai import OpenAI

# Add import for wuxia glossary
import sys
from utils.wuxia_glossary import WuxiaGlossary, GlossaryEntry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

TRANSLATION_SYSTEM_PROMPT = """You are an elite translator of Classical Chinese and Wuxia literature, specializing in producing natural, fluent English prose that reads smoothly while preserving the spirit and cultural richness of the original.

**CRITICAL TRANSLATION PRINCIPLES:**

1. **Natural, Flowing English**:
   - Write in smooth, readable prose that native English speakers would naturally use
   - Avoid awkward constructions like "One saw..." - use clear subjects and active voice
   - Maintain consistent narrative past tense throughout (avoid mixing "would be," "had been," etc.)
   - Sentences should flow together naturally, not feel disjointed or blocky
   - WRONG: "One saw the teacher sitting cross-legged on the chair, a faint smile on her face"
   - RIGHT: "The teacher sat cross-legged on her chair with a faint smile on her face"

2. **Tense Consistency**:
   - Use simple past tense as the default narrative tense
   - "hopped" not "was hopping" (unless progressive aspect is specifically needed)
   - "finished" not "had finished" (unless pluperfect is essential for sequence)
   - "feared" not "was fearing"
   - Keep it simple and direct

3. **Sentence Construction**:
   - Break up overly long sentences that would sound unnatural in English
   - Each sentence should have a clear subject performing a clear action
   - Use transitional phrases sparingly and naturally
   - Prefer active voice over passive voice where appropriate

4. **Word Choice**:
   - Use natural, conversational English (while maintaining literary quality)
   - WRONG: "this thing more entertaining" - RIGHT: "this skill more entertaining" or "this trick more fascinating"
   - WRONG: "feared that the teacher might still be napping and that entering would be troublesome"
   - RIGHT: "worried the teacher might still be napping, so she didn't want to disturb him"

5. **Pinyin with Tone Marks in English Text**: **CRITICAL** - Use pinyin WITH TONE MARKS for Chinese names and terms in the English translation:
   - Character names: Use pinyin with tones (e.g., "Yáng Lùchán[1]" NOT "Yang Luchan[1]")
   - Place names: Use pinyin with tones (e.g., "Hénán" NOT "Henan")
   - Technical terms: Use pinyin with tones (e.g., "tàijíquán[2]" NOT "taijiquan[2]")
   - WRONG: "Yang Luchan[1] traveled to Henan and learned taijiquan from Chen Qingping[2]"
   - RIGHT: "Yáng Lùchán[1] traveled to Hénán and learned tàijíquán from Chén Qīngpíng[2]"
   - Exception: Well-known English terms are acceptable (e.g., "Tai Chi" for casual reference)

6. **Scholarly Annotation**: Create detailed footnotes that explain:
   - Cultural and historical references
   - Proper names (characters, places, titles) with pinyin
   - Specialized martial arts or classical terminology
   - Historical context and allusions
   - Keep footnotes focused on cultural/historical facts, not narrative interpretation

7. **Inline Footnote Markers**: **IMPORTANT** - Insert inline footnote markers [1], [2], [3], etc. immediately after each term that has a corresponding footnote.
   - Example: "King Zhou[1] visited the temple of Nüwa[2], the great goddess[3]..."
   - Place marker [n] directly after the term it annotates (no space between term and marker)
   - Every footnote in content_footnotes should have a corresponding [n] marker in annotated_content_text
   - Markers should be sequential starting from [1]
   - If a term appears multiple times, mark it on first occurrence only

**Output Requirements:**

Return ONLY valid JSON in this exact format (no markdown, no explanation):

{
  "content_text_id": <original_id>,
  "content_source_text": "<original_chinese_text>",
  "translated_annotated_content": {
    "annotated_content_text": "<full_english_translation_with_inline_markers_like_this[1]_and_this[2]>",
    "content_footnotes": [
      {
        "footnote_key": 1,
        "footnote_details": {
          "footnote_ideogram": "<chinese_characters>",
          "footnote_pinyin": "<romanized_pronunciation>",
          "footnote_explanation": "<cultural_historical_explanation>"
        }
      }
    ],
    "content_type": "<narrative|dialogue|verse|document|descriptive|thought>"
  }
}

**CRITICAL: The annotated_content_text MUST contain inline markers [1], [2], [3] immediately after each annotated term.**
Example: "King Zhou[1] gazed upon the beauty of Nüwa[2], sovereign of ten thousand chariots[3]..."

**Translation Methodology:**

1. Read the entire passage to understand narrative flow, character voices, and cultural context
2. Translate into natural, fluent English - imagine you're retelling the story to a friend
3. Use simple past tense consistently - avoid complex tense constructions
4. Each sentence should have a clear subject and flow smoothly into the next
5. Identify terms needing cultural explanation (proper names, historical references, specialized terms)
6. **Insert inline markers [1], [2], [3]... immediately after each term that will be footnoted**
7. Create footnotes with pinyin and cultural/historical context (factual, not interpretive)
8. **Verify every footnote has a corresponding [n] marker in the translated text**
9. Classify content type (narrative, dialogue, verse, document, descriptive, thought)

**EXAMPLES OF GOOD vs BAD TRANSLATION:**

BAD (awkward, unnatural):
"One saw the teacher sitting cross-legged on the chair, a faint smile on her face, her right hand raised slightly toward the air, and with a soft sound, as if something brushed against the paneled wall."

GOOD (natural, clear):
"The teacher sat cross-legged on her chair with a faint smile on her face. She raised her right hand slightly, and there was a soft sound, as if something had struck the wooden wall."

BAD (unclear subject, passive):
"The girl, outside the study door, feared that the teacher might still be napping and that entering would be troublesome, so she moved quietly around to the window."

GOOD (clear subject, active):
"Outside the study door, the girl worried the teacher might still be napping. Not wanting to disturb him, she crept quietly around to the window instead."

**Footnote Principles:**

- Annotate terms that enhance understanding, not obvious translations
- Write explanations for general readers, avoiding academic jargon
- Help readers appreciate cultural context without overwhelming them
- Use consistent terminology across all footnotes
- Balance detail with brevity—enough to illuminate, not to distract
- Include pinyin for all Chinese terms using standard Hanyu Pinyin
- Focus on factual cultural/historical context, NOT character analysis

**Content Type Classification:**

- `narrative`: Descriptive storytelling, scene-setting, action sequences
- `dialogue`: Character speech and conversation
- `verse`: Poetry, songs, or verse passages
- `document`: Letters, proclamations, written texts within the story
- `descriptive`: Pure description of settings, characters, or objects
- `thought`: Internal monologue or character reflection

**Quality Standards:**

- PhD-level scholarly quality suitable for academic or commercial publication
- Footnotes demonstrate deep cultural knowledge while remaining accessible
- Every annotation adds genuine value
- Deterministic, consistent output format
"""

VALIDATION_SYSTEM_PROMPT = """You are a validation specialist for Classical Chinese translations. Your role is to verify translation quality and footnote accuracy.

**Validation Criteria:**

1. **Translation Quality**:
   - Accuracy to source text
   - Literary quality and readability
   - Appropriate tone and register
   - Preservation of narrative voice

2. **Footnote Quality**:
   - Pinyin accuracy (standard Hanyu Pinyin)
   - Cultural/historical accuracy
   - Appropriate depth and clarity
   - No character analysis (factual context only)
   - Consistent terminology

3. **Inline Marker Validation** (IMPORTANT):
   - Every footnote in content_footnotes SHOULD have a corresponding [n] marker in annotated_content_text
   - Markers should be sequential: [1], [2], [3], etc.
   - Markers should appear immediately after the annotated term
   - Example: "King Zhou[1] visited Nüwa[2]" is CORRECT
   - Example: "King Zhou [1]" (extra space) is acceptable as MINOR issue
   - Flag as MAJOR error only if 50% or more footnotes lack markers
   - Flag as MINOR warning if markers have spacing issues or are slightly misplaced
   - Be lenient: If most markers are present, accept with minor warnings

4. **Format Compliance**:
   - Valid JSON structure
   - All required fields present
   - Footnote keys sequential and correct
   - Content type appropriate

**Output Format:**

Return ONLY valid JSON (no markdown):

{
  "is_valid": true|false,
  "quality_score": <0-100>,
  "issues": [
    {
      "type": "translation|footnote|format|pinyin",
      "severity": "critical|major|minor",
      "description": "<detailed_issue_description>",
      "location": "<specific_location>"
    }
  ],
  "suggestions": [
    "<improvement_suggestion_1>",
    "<improvement_suggestion_2>"
  ]
}

**Severity Levels:**

- `critical`: Must fix (incorrect translation, invalid format, missing required fields)
- `major`: Should fix (inaccurate footnotes, poor pinyin, inconsistent terminology)
- `minor`: Nice to fix (style improvements, additional context)

Be thorough but fair. Recognize scholarly quality when present.
"""


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FootnoteDetails:
    """Details for a single footnote"""
    footnote_ideogram: str
    footnote_pinyin: str
    footnote_explanation: str


@dataclass
class ContentFootnote:
    """A single footnote with key and details"""
    footnote_key: int
    footnote_details: FootnoteDetails


@dataclass
class TranslatedAnnotatedContent:
    """Translated and annotated content"""
    annotated_content_text: str
    content_footnotes: List[ContentFootnote]
    content_type: str


@dataclass
class TranslationRequest:
    """Request format for translation"""
    content_text_id: int
    content_source_text: str


@dataclass
class TranslationResponse:
    """Response format for translation"""
    content_text_id: int
    content_source_text: str
    translated_annotated_content: TranslatedAnnotatedContent


@dataclass
class ValidationIssue:
    """Validation issue details"""
    type: str  # translation|footnote|format|pinyin
    severity: str  # critical|major|minor
    description: str
    location: str


@dataclass
class ValidationResult:
    """Validation result"""
    is_valid: bool
    quality_score: int
    issues: List[ValidationIssue]
    suggestions: List[str]


# =============================================================================
# TRANSLATION SERVICE
# =============================================================================

class TranslationService:
    """
    Translation service with two-pass validation and thread isolation.

    Uses OpenAI GPT-4o-mini for scholarly translation of Classical Chinese
    and Wuxia literature with comprehensive cultural annotations.
    """

    def __init__(
        self,
        model: str = "gpt-4.1-nano",
        temperature: float = 0.3,
        max_retries: int = 2,
        timeout: int = 120,
        glossary_path: Optional[Path] = None
    ):
        """
        Initialize translation service.

        Args:
            model: OpenAI model to use (default: gpt-4.1-nano)
            temperature: Sampling temperature (0.0-1.0, default: 0.3)
            max_retries: Maximum retry attempts (default: 2)
            timeout: Request timeout in seconds (default: 120)
            glossary_path: Path to wuxia_glossary.db (default: wuxia_glossary.db in project root)
        """
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        logger.info(f"Initialized TranslationService with model={model}, temperature={temperature}")

        # Initialize wuxia glossary
        if glossary_path is None:
            glossary_path = Path(__file__).parent.parent / "wuxia_glossary.db"

        try:
            self.glossary = WuxiaGlossary(glossary_path)
            logger.info(f"Loaded wuxia glossary from {glossary_path}")
        except FileNotFoundError:
            logger.warning(f"Wuxia glossary not found at {glossary_path}, proceeding without glossary")
            self.glossary = None

    def _scan_glossary_terms(self, source_text: str) -> List[Tuple[str, GlossaryEntry, int]]:
        """
        Scan source text for glossary terms.

        Args:
            source_text: Chinese source text

        Returns:
            List of (term, entry, position) tuples
        """
        if not self.glossary:
            return []

        matches = self.glossary.find_in_text(source_text, max_matches=30)
        logger.info(f"Found {len(matches)} glossary terms in source text")

        for term, entry, pos in matches:
            logger.debug(f"  - {term} ({entry.pinyin}) @ position {pos}")

        return matches

    def _build_glossary_context(self, matches: List[Tuple[str, GlossaryEntry, int]]) -> str:
        """
        Build glossary context to pass to translator.

        Args:
            matches: List of glossary matches

        Returns:
            Formatted glossary context string
        """
        if not matches:
            return ""

        context_parts = [
            "\n\n**GLOSSARY TERMS FOUND IN THIS TEXT:**",
            "\nThe following wuxia/cultural terms appear in this passage. Use EXACTLY these forms and footnotes:\n"
        ]

        for i, (term, entry, _) in enumerate(matches, 1):
            context_parts.append(f"\n{i}. **{term}** ({entry.chinese})")
            context_parts.append(f"   - Pinyin: {entry.pinyin}")
            context_parts.append(f"   - Translation Strategy: {entry.translation_strategy}")
            context_parts.append(f"   - Recommended Form: {entry.recommended_form}")
            context_parts.append(f"   - Footnote Template: {entry.footnote_template}")
            context_parts.append(f"   - Deduplication: {entry.deduplication_strategy}")

        context_parts.append("\n\n**INSTRUCTIONS:**")
        context_parts.append("- Use the EXACT 'Recommended Form' when translating each term")
        context_parts.append("- Use the EXACT 'Footnote Template' for footnotes")
        context_parts.append("- Use the EXACT 'Pinyin' (with tone marks) for consistency")
        context_parts.append("- Add footnotes for ALL occurrences (deduplication happens later)")
        context_parts.append("- Ensure glossary footnotes and custom footnotes use the same JSON structure\n")

        return "".join(context_parts)

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text with two-pass validation.

        Args:
            request: TranslationRequest object

        Returns:
            TranslationResponse object with translation and annotations

        Raises:
            RuntimeError: If translation fails after all retries
        """
        logger.info(f"Starting translation for content_text_id={request.content_text_id}")

        # Scan for glossary terms
        glossary_matches = self._scan_glossary_terms(request.content_source_text)

        # Pass 1: Translation
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Translation attempt {attempt}/{self.max_retries}")
                translation_response = self._translate_with_thread(request, glossary_matches)

                # Pass 2: Validation
                logger.info("Validating translation...")
                validation = self._validate_with_thread(translation_response)

                if validation.is_valid:
                    logger.info(f"Translation validated successfully (quality={validation.quality_score}/100)")
                    return translation_response

                # Check if issues are critical
                critical_issues = [i for i in validation.issues if i.severity == "critical"]
                major_issues = [i for i in validation.issues if i.severity == "major"]

                if critical_issues:
                    logger.warning(f"Critical issues found: {len(critical_issues)}")
                    for issue in critical_issues:
                        logger.warning(f"  - {issue.type}: {issue.description}")

                    if attempt < self.max_retries:
                        logger.info("Retrying translation due to critical issues...")
                        time.sleep(2)
                        continue
                elif major_issues and attempt < self.max_retries:
                    # Try once more for major issues, but don't insist
                    logger.warning(f"Major issues found: {len(major_issues)}")
                    for issue in major_issues:
                        logger.warning(f"  - {issue.type}: {issue.description}")
                    logger.info("Retrying translation once for major issues...")
                    time.sleep(2)
                    continue
                else:
                    # Non-critical/minor issues, or last attempt with major issues - accept with warnings
                    if validation.issues:
                        logger.warning(f"Translation has {len(validation.issues)} issues but is acceptable")
                        for issue in validation.issues:
                            logger.warning(f"  - [{issue.severity}] {issue.type}: {issue.description}")
                    return translation_response

            except Exception as e:
                logger.error(f"Translation attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Translation failed after {self.max_retries} attempts: {e}")

        raise RuntimeError(f"Translation failed validation after {self.max_retries} attempts")

    def _translate_with_thread(
        self,
        request: TranslationRequest,
        glossary_matches: List[Tuple[str, GlossaryEntry, int]] = None
    ) -> TranslationResponse:
        """
        Execute translation using Chat Completions API.

        Args:
            request: TranslationRequest object
            glossary_matches: Optional list of glossary term matches

        Returns:
            TranslationResponse object
        """
        # Prepare base message
        message_content = json.dumps({
            "content_text_id": request.content_text_id,
            "content_source_text": request.content_source_text
        }, ensure_ascii=False)

        # Add glossary context if terms found
        if glossary_matches:
            glossary_context = self._build_glossary_context(glossary_matches)
            user_message = message_content + glossary_context
        else:
            user_message = message_content

        # Call Chat Completions API
        try:
            # GPT-5-nano only supports temperature=1 (default)
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                "response_format": {"type": "json_object"},
                "timeout": self.timeout
            }

            # Only set temperature if not using GPT-4.1-nano
            if "gpt-4.1-nano" not in self.model.lower():
                api_params["temperature"] = self.temperature

            response = self.client.chat.completions.create(**api_params)

            response_text = response.choices[0].message.content
            return self._parse_translation_response(response_text)

        except Exception as e:
            raise RuntimeError(f"Translation failed: {e}")

    def _validate_with_thread(self, response: TranslationResponse) -> ValidationResult:
        """
        Validate translation using Chat Completions API.

        Args:
            response: TranslationResponse to validate

        Returns:
            ValidationResult object
        """
        # Prepare validation message
        validation_message = json.dumps(self._response_to_dict(response), ensure_ascii=False)

        # Call Chat Completions API
        try:
            # GPT-5-nano only supports temperature=1 (default)
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": validation_message}
                ],
                "response_format": {"type": "json_object"},
                "timeout": self.timeout
            }

            # Only set temperature if not using GPT-4.1-nano
            if "gpt-4.1-nano" not in self.model.lower():
                api_params["temperature"] = 0.1  # Lower temperature for consistent validation

            api_response = self.client.chat.completions.create(**api_params)

            response_text = api_response.choices[0].message.content
            return self._parse_validation_response(response_text)

        except Exception as e:
            raise RuntimeError(f"Validation failed: {e}")

    def _parse_translation_response(self, response_text: str) -> TranslationResponse:
        """
        Parse JSON response from translation assistant.

        Args:
            response_text: JSON string from assistant

        Returns:
            TranslationResponse object
        """
        try:
            # First attempt: parse as-is
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Second attempt: Fix common JSON issues
            logger.warning(f"Initial JSON parse failed: {e}. Attempting to fix JSON formatting issues...")
            try:
                import re
                fixed_text = response_text

                # Fix 1: Unquoted Chinese characters in footnote_ideogram
                # Pattern: "footnote_ideogram": 陸高止, -> "footnote_ideogram": "陸高止",
                fixed_text = re.sub(
                    r'"footnote_ideogram":\s*([^",\[\]{}\s][^,\}]*),',
                    r'"footnote_ideogram": "\1",',
                    fixed_text
                )

                # Fix 2: Trailing commas in arrays and objects
                # Remove comma before ] or }
                fixed_text = re.sub(r',(\s*[\]}])', r'\1', fixed_text)

                # Fix 3: Missing quotes around field names (rare but possible)
                # This is a more aggressive fix, only applies if still failing

                data = json.loads(fixed_text)
                logger.info("Successfully fixed JSON formatting issues")
            except json.JSONDecodeError as e2:
                # Try one more aggressive fix: remove all trailing commas
                try:
                    fixed_text = re.sub(r',(\s*[\]}])', r'\1', response_text)
                    data = json.loads(fixed_text)
                    logger.info("Successfully fixed JSON with aggressive trailing comma removal")
                except json.JSONDecodeError as e3:
                    raise RuntimeError(f"Failed to parse translation response even after multiple fix attempts.\nOriginal error: {e}\nSecond error: {e2}\nThird error: {e3}\nResponse: {response_text[:500]}...")

        try:
            # Parse footnotes
            footnotes = []
            for fn in data["translated_annotated_content"]["content_footnotes"]:
                footnote = ContentFootnote(
                    footnote_key=fn["footnote_key"],
                    footnote_details=FootnoteDetails(**fn["footnote_details"])
                )
                footnotes.append(footnote)

            # Build response
            translated_content = TranslatedAnnotatedContent(
                annotated_content_text=data["translated_annotated_content"]["annotated_content_text"],
                content_footnotes=footnotes,
                content_type=data["translated_annotated_content"]["content_type"]
            )

            return TranslationResponse(
                content_text_id=data["content_text_id"],
                content_source_text=data["content_source_text"],
                translated_annotated_content=translated_content
            )

        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Failed to parse translation response structure: {e}\nResponse: {response_text}")

    def _parse_validation_response(self, response_text: str) -> ValidationResult:
        """
        Parse JSON response from validation assistant.

        Args:
            response_text: JSON string from assistant

        Returns:
            ValidationResult object
        """
        try:
            data = json.loads(response_text)

            # Parse issues
            issues = [ValidationIssue(**issue) for issue in data.get("issues", [])]

            return ValidationResult(
                is_valid=data["is_valid"],
                quality_score=data["quality_score"],
                issues=issues,
                suggestions=data.get("suggestions", [])
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise RuntimeError(f"Failed to parse validation response: {e}\nResponse: {response_text}")

    def _response_to_dict(self, response: TranslationResponse) -> Dict[str, Any]:
        """
        Convert TranslationResponse to dictionary for JSON serialization.

        Args:
            response: TranslationResponse object

        Returns:
            Dictionary representation
        """
        return {
            "content_text_id": response.content_text_id,
            "content_source_text": response.content_source_text,
            "translated_annotated_content": {
                "annotated_content_text": response.translated_annotated_content.annotated_content_text,
                "content_footnotes": [
                    {
                        "footnote_key": fn.footnote_key,
                        "footnote_details": {
                            "footnote_ideogram": fn.footnote_details.footnote_ideogram,
                            "footnote_pinyin": fn.footnote_details.footnote_pinyin,
                            "footnote_explanation": fn.footnote_details.footnote_explanation
                        }
                    }
                    for fn in response.translated_annotated_content.content_footnotes
                ],
                "content_type": response.translated_annotated_content.content_type
            }
        }

    def translate_from_dict(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience method for dictionary-based translation.

        Args:
            request_dict: Dictionary with content_text_id and content_source_text

        Returns:
            Dictionary with translation response
        """
        request = TranslationRequest(
            content_text_id=request_dict["content_text_id"],
            content_source_text=request_dict["content_source_text"]
        )

        response = self.translate(request)
        return self._response_to_dict(response)

    def translate_batch(
        self,
        requests: List[Dict[str, Any]],
        output_dir: Optional[Path] = None,
        save_individual: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Translate multiple texts (sequential processing).

        Args:
            requests: List of request dictionaries
            output_dir: Optional directory to save individual results
            save_individual: Whether to save each result individually

        Returns:
            List of response dictionaries
        """
        results = []

        if output_dir and save_individual:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        for i, request_dict in enumerate(requests, 1):
            logger.info(f"Processing batch item {i}/{len(requests)}")

            try:
                result = self.translate_from_dict(request_dict)
                results.append(result)

                if output_dir and save_individual:
                    output_file = output_dir / f"translation_{request_dict['content_text_id']}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    logger.info(f"Saved individual result to {output_file}")

            except Exception as e:
                logger.error(f"Failed to translate item {i}: {e}")
                results.append({
                    "content_text_id": request_dict.get("content_text_id"),
                    "error": str(e)
                })

        return results


# =============================================================================
# MAIN / TEST
# =============================================================================

def main():
    """Test the translation service"""

    # Sample request
    test_request = {
        "content_text_id": 1,
        "content_source_text": "且言紂王只因進香之後，看見女媧美貌，朝暮思想，寒暑盡忘。"
    }

    try:
        service = TranslationService()
        result = service.translate_from_dict(test_request)

        print("\n=== TRANSLATION RESULT ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        logger.error(f"Translation test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
