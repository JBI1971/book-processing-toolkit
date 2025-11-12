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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

TRANSLATION_SYSTEM_PROMPT = """You are an elite Classical Chinese and Wuxia literature translator with deep expertise in Chinese literary traditions, historical context, and cultural nuances. Your specialty is producing scholarly English translations enriched with comprehensive annotations that illuminate the text for English-speaking readers.

**Your Core Responsibilities:**

1. **Translation Excellence**: Translate Classical Chinese and Wuxia texts into fluent, literary English that preserves the original's narrative voice, poetic quality, and cultural atmosphere. Your translations should be readable yet faithful to the source material's style and tone.

2. **Scholarly Annotation**: Create detailed footnotes that explain:
   - Cultural and historical references
   - Mythological allusions and spiritual concepts
   - Literary devices and stylistic elements
   - Proper names (characters, places, titles) with pinyin
   - Classical terminology and specialized vocabulary
   - Measurements, time periods, and other contextual details

3. **Inline Footnote Markers**: **CRITICAL** - You MUST insert inline footnote markers [1], [2], [3], etc. IMMEDIATELY after each term that has a corresponding footnote in the translated text.
   - Example: "King Zhou[1] visited the temple of Nüwa[2], the great goddess[3]..."
   - The marker [n] must appear directly after the term it annotates, with NO space between
   - Every footnote in content_footnotes MUST have a corresponding [n] marker in annotated_content_text
   - Markers must be sequential starting from [1]

4. **Structural Preservation**: Maintain the original JSON structure, returning both the source text and your translated/annotated content in the specified format.

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

1. Read the entire passage to understand narrative flow, key themes, and cultural context
2. Create a scholarly translation that captures meaning accurately
3. Polish for readability while preserving literary qualities and appropriate tone
4. Identify terms requiring explanation (cultural concepts, proper names, specialized vocabulary)
5. **Insert inline markers [1], [2], [3]... immediately after each term that will be footnoted**
6. Create concise but informative footnotes with pinyin and cultural context matching the markers
7. **Verify that every footnote has a corresponding [n] marker in the translated text**
8. Classify content type (narrative, dialogue, verse, document, descriptive, thought)

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

3. **Inline Marker Validation** (CRITICAL):
   - Every footnote in content_footnotes MUST have a corresponding [n] marker in annotated_content_text
   - Markers must be sequential: [1], [2], [3], etc.
   - Markers must appear immediately after the annotated term with NO space
   - Example: "King Zhou[1] visited Nüwa[2]" is CORRECT
   - Example: "King Zhou [1]" or "King Zhou visited temple" (missing marker) is INCORRECT
   - Flag as CRITICAL error if any footnote lacks a corresponding marker

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
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_retries: int = 3,
        timeout: int = 120
    ):
        """
        Initialize translation service.

        Args:
            model: OpenAI model to use (default: gpt-4o-mini)
            temperature: Sampling temperature (0.0-1.0, default: 0.3)
            max_retries: Maximum retry attempts (default: 3)
            timeout: Request timeout in seconds (default: 120)
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

        # Pass 1: Translation
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Translation attempt {attempt}/{self.max_retries}")
                translation_response = self._translate_with_thread(request)

                # Pass 2: Validation
                logger.info("Validating translation...")
                validation = self._validate_with_thread(translation_response)

                if validation.is_valid:
                    logger.info(f"Translation validated successfully (quality={validation.quality_score}/100)")
                    return translation_response

                # Check if issues are critical
                critical_issues = [i for i in validation.issues if i.severity == "critical"]
                if critical_issues:
                    logger.warning(f"Critical issues found: {len(critical_issues)}")
                    for issue in critical_issues:
                        logger.warning(f"  - {issue.type}: {issue.description}")

                    if attempt < self.max_retries:
                        logger.info("Retrying translation due to critical issues...")
                        time.sleep(2)
                        continue
                else:
                    # Non-critical issues, accept with warnings
                    logger.warning(f"Translation has {len(validation.issues)} non-critical issues but is acceptable")
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

    def _translate_with_thread(self, request: TranslationRequest) -> TranslationResponse:
        """
        Execute translation using isolated OpenAI thread.

        Args:
            request: TranslationRequest object

        Returns:
            TranslationResponse object
        """
        # Create isolated thread
        thread = self.client.beta.threads.create()

        try:
            # Prepare user message with request data
            user_message = json.dumps({
                "content_text_id": request.content_text_id,
                "content_source_text": request.content_source_text
            }, ensure_ascii=False)

            # Create message in thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_message
            )

            # Create assistant for this translation
            assistant = self.client.beta.assistants.create(
                name="Classical Chinese Translator",
                instructions=TRANSLATION_SYSTEM_PROMPT,
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            try:
                # Run assistant
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant.id
                )

                # Poll for completion
                start_time = time.time()
                while True:
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(f"Translation timed out after {self.timeout}s")

                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )

                    if run_status.status == "completed":
                        break
                    elif run_status.status in ["failed", "cancelled", "expired"]:
                        raise RuntimeError(f"Translation run {run_status.status}: {run_status.last_error}")

                    time.sleep(1)

                # Retrieve messages
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)

                # Find assistant's response
                for message in messages.data:
                    if message.role == "assistant":
                        response_text = message.content[0].text.value
                        return self._parse_translation_response(response_text)

                raise RuntimeError("No assistant response found in thread")

            finally:
                # Clean up assistant
                self.client.beta.assistants.delete(assistant.id)

        finally:
            # Clean up thread
            self.client.beta.threads.delete(thread.id)

    def _validate_with_thread(self, response: TranslationResponse) -> ValidationResult:
        """
        Validate translation using isolated OpenAI thread.

        Args:
            response: TranslationResponse to validate

        Returns:
            ValidationResult object
        """
        # Create isolated thread
        thread = self.client.beta.threads.create()

        try:
            # Prepare validation message
            validation_message = json.dumps(self._response_to_dict(response), ensure_ascii=False)

            # Create message in thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=validation_message
            )

            # Create assistant for validation
            assistant = self.client.beta.assistants.create(
                name="Translation Validator",
                instructions=VALIDATION_SYSTEM_PROMPT,
                model=self.model,
                temperature=0.1,  # Lower temperature for consistent validation
                response_format={"type": "json_object"}
            )

            try:
                # Run assistant
                run = self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=assistant.id
                )

                # Poll for completion
                start_time = time.time()
                while True:
                    if time.time() - start_time > self.timeout:
                        raise TimeoutError(f"Validation timed out after {self.timeout}s")

                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )

                    if run_status.status == "completed":
                        break
                    elif run_status.status in ["failed", "cancelled", "expired"]:
                        raise RuntimeError(f"Validation run {run_status.status}: {run_status.last_error}")

                    time.sleep(1)

                # Retrieve messages
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)

                # Find assistant's response
                for message in messages.data:
                    if message.role == "assistant":
                        response_text = message.content[0].text.value
                        return self._parse_validation_response(response_text)

                raise RuntimeError("No validation response found in thread")

            finally:
                # Clean up assistant
                self.client.beta.assistants.delete(assistant.id)

        finally:
            # Clean up thread
            self.client.beta.threads.delete(thread.id)

    def _parse_translation_response(self, response_text: str) -> TranslationResponse:
        """
        Parse JSON response from translation assistant.

        Args:
            response_text: JSON string from assistant

        Returns:
            TranslationResponse object
        """
        try:
            data = json.loads(response_text)

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

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise RuntimeError(f"Failed to parse translation response: {e}\nResponse: {response_text}")

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
