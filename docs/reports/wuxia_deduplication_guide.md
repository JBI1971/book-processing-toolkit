# Wuxia Translation Deduplication Implementation Guide

## Overview

This guide explains how the translation service should implement intelligent footnote deduplication across an entire book, reducing redundancy while maintaining clarity for readers.

## Core Principle

**The goal**: Train readers in wuxia vocabulary through repetition, not through repeated footnotes. Once a term is explained, the reader should encounter it naturally in subsequent passages, building familiarity through context.

## Deduplication Strategies

### 1. FIRST_OCCURRENCE_ONLY

**When to use**: Core concepts and relationship terms that appear frequently throughout the book.

**Examples**: *qì*, *nèigōng*, *shīfù*, *shīxiōng*, *jiānghú*, *gōnglì*, *qīnggōng*

**Implementation**:
- **First occurrence** (anywhere in book): Full footnote with complete explanation
- **All subsequent occurrences**: Just italicized pinyin in text, NO footnote

**Tracking requirement**:
```python
# Book-level tracking dictionary
first_occurrence_terms = {
    "qì": {"chapter": 1, "content_text_id": 5, "footnote_given": True},
    "shīfù": {"chapter": 2, "content_text_id": 12, "footnote_given": True},
    # ... etc
}

# Check before generating footnote
if term in first_occurrence_terms and first_occurrence_terms[term]["footnote_given"]:
    # Return text with just italics, no footnote marker
    return "*qì*"  # NOT "*qì*[1]"
else:
    # Generate full footnote
    first_occurrence_terms[term] = {
        "chapter": current_chapter,
        "content_text_id": current_id,
        "footnote_given": True
    }
    return "*qì*[1]"
```

**Rationale**: These terms appear 50+ times in a typical wuxia novel. After the first explanation, readers should learn them through natural repetition. Repeated footnotes become noise.

### 2. RECURRING_BRIEF

**When to use**:
- Named techniques that appear multiple times
- Specific locations or organizations
- Character titles used repeatedly
- Technical terms that benefit from occasional reminders

**Examples**: *Jiàng Lóng Shíbā Zhǎng* (18 Dragon-Subduing Palms), *Wǔdāng Shān*, *zǒuhuǒ rùmó*, specific acupoint names

**Implementation**:
- **First occurrence in book**: Full footnote with complete explanation
- **Same chapter, subsequent occurrences**: Brief reference footnote
- **New chapter, first occurrence**: Brief reminder footnote
- **Same chapter, 3+ occurrences**: No footnote after 2nd mention

**Tracking requirement**:
```python
# Chapter-level + book-level tracking
recurring_brief_terms = {
    "zǒuhuǒ rùmó": {
        "first_occurrence": {"chapter": 3, "content_text_id": 45},
        "full_footnote_given": True,
        "current_chapter_occurrences": [45, 67],  # Reset per chapter
        "last_chapter_with_footnote": 3
    }
}

def get_footnote_for_recurring_term(term, current_chapter, current_id):
    if term not in recurring_brief_terms:
        # First time ever - full footnote
        recurring_brief_terms[term] = {
            "first_occurrence": {"chapter": current_chapter, "content_text_id": current_id},
            "full_footnote_given": True,
            "current_chapter_occurrences": [current_id],
            "last_chapter_with_footnote": current_chapter
        }
        return FULL_FOOTNOTE

    term_data = recurring_brief_terms[term]

    # Check if new chapter
    if current_chapter != term_data["last_chapter_with_footnote"]:
        # New chapter - give brief reminder
        term_data["current_chapter_occurrences"] = [current_id]
        term_data["last_chapter_with_footnote"] = current_chapter
        return BRIEF_REMINDER_FOOTNOTE

    # Same chapter
    if len(term_data["current_chapter_occurrences"]) == 0:
        # First in this chapter
        term_data["current_chapter_occurrences"].append(current_id)
        return BRIEF_REMINDER_FOOTNOTE
    elif len(term_data["current_chapter_occurrences"]) == 1:
        # Second in this chapter - give brief reminder
        term_data["current_chapter_occurrences"].append(current_id)
        return BRIEF_REMINDER_FOOTNOTE
    else:
        # Third+ in this chapter - no footnote
        term_data["current_chapter_occurrences"].append(current_id)
        return NO_FOOTNOTE
```

**Footnote formats**:

**Full footnote** (first occurrence):
```
Qi deviation (走火入魔 *zǒuhuǒ rùmó*): A dangerous derangement caused by improper internal cultivation, literally 'walking into fire and entering demons.' Results in madness, internal injury, or death. A major plot device in wuxia fiction.
```

**Brief reminder** (same chapter, 2nd occurrence):
```
Qi deviation (走火入魔 *zǒuhuǒ rùmó*) [see earlier]
```

**Brief reminder** (new chapter):
```
Qi deviation (走火入魔 *zǒuhuǒ rùmó*): Dangerous derangement from improper cultivation leading to madness or death.
```

**Rationale**: These terms are less frequent but still recurring. A brief reminder helps readers who've forgotten the term or are skimming, without repeating the full scholarly explanation.

### 3. EVERY_OCCURRENCE

**When to use**:
- Rare or obscure terms appearing only 1-2 times
- Critical plot-specific items unique to this book
- Highly technical acupoint names that vary by context
- Terms readers are unlikely to remember

**Examples**: 腎兪 (kidney shu point), rare weapon names, book-specific artifacts, obscure poisons

**Implementation**:
- **Every occurrence**: Full footnote (or reference if identical context)

**Tracking requirement**:
```python
# Track for reference purposes, but always footnote
every_occurrence_terms = {
    "shènyú": {
        "occurrences": [
            {"chapter": 5, "content_text_id": 78, "context": "strike to kidney shu"},
            {"chapter": 12, "content_text_id": 234, "context": "healing kidney shu"}
        ]
    }
}

def get_footnote_for_rare_term(term, current_chapter, current_id, context):
    if term not in every_occurrence_terms:
        every_occurrence_terms[term] = {"occurrences": []}

    # Check if EXACT same context as previous
    for prev in every_occurrence_terms[term]["occurrences"]:
        if prev["context"] == context:
            # Same context - can reference earlier footnote
            return f"[see footnote in Chapter {prev['chapter']}]"

    # Different context or first time - full footnote
    every_occurrence_terms[term]["occurrences"].append({
        "chapter": current_chapter,
        "content_text_id": current_id,
        "context": context
    })
    return FULL_FOOTNOTE
```

**Rationale**: These terms are so rare that readers won't remember them from previous chapters. Better to over-explain than leave readers confused.

## Expected Frequency Mapping

The `Expected_Frequency` column helps determine deduplication strategy:

| Frequency | Occurrences | Default Strategy | Rationale |
|-----------|-------------|------------------|-----------|
| VERY_HIGH | 50+ times | FIRST_OCCURRENCE_ONLY | Core vocabulary - teach through repetition |
| HIGH | 20-50 times | FIRST_OCCURRENCE_ONLY or RECURRING_BRIEF | Common enough to learn quickly |
| MEDIUM | 5-20 times | RECURRING_BRIEF | Needs occasional reminders |
| LOW | 2-5 times | RECURRING_BRIEF or EVERY_OCCURRENCE | Context-dependent |
| RARE | 1-2 times | EVERY_OCCURRENCE | Too rare to expect retention |

## Implementation in Translation Service

### Data Structure

```python
class FootnoteTracker:
    def __init__(self):
        self.book_id = None
        self.first_occurrence_terms = {}  # Term -> {chapter, id, footnote_given}
        self.recurring_brief_terms = {}   # Term -> {first_occurrence, chapter_occurrences, last_chapter}
        self.every_occurrence_terms = {}  # Term -> {occurrences: [{chapter, id, context}]}

    def should_generate_footnote(self, term: str, strategy: str,
                                 chapter: int, content_id: int,
                                 context: str = None) -> dict:
        """
        Returns:
        {
            "generate_footnote": True/False,
            "footnote_type": "full" | "brief" | "reference" | None,
            "reference_info": {chapter, content_id} if applicable
        }
        """
        if strategy == "FIRST_OCCURRENCE_ONLY":
            return self._handle_first_occurrence_only(term, chapter, content_id)
        elif strategy == "RECURRING_BRIEF":
            return self._handle_recurring_brief(term, chapter, content_id)
        elif strategy == "EVERY_OCCURRENCE":
            return self._handle_every_occurrence(term, chapter, content_id, context)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _handle_first_occurrence_only(self, term, chapter, content_id):
        if term in self.first_occurrence_terms:
            # Already footnoted - no more footnotes
            return {
                "generate_footnote": False,
                "footnote_type": None,
                "reference_info": self.first_occurrence_terms[term]
            }
        else:
            # First time - full footnote
            self.first_occurrence_terms[term] = {
                "chapter": chapter,
                "content_text_id": content_id,
                "footnote_given": True
            }
            return {
                "generate_footnote": True,
                "footnote_type": "full",
                "reference_info": None
            }

    def _handle_recurring_brief(self, term, chapter, content_id):
        # Implementation as shown above
        pass

    def _handle_every_occurrence(self, term, chapter, content_id, context):
        # Implementation as shown above
        pass
```

### Integration with Translation Workflow

```python
class TranslationService:
    def __init__(self, openai_api_key: str, glossary_path: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.glossary = self.load_glossary(glossary_path)
        self.footnote_tracker = FootnoteTracker()

    def translate_book(self, book_requests: list[dict]) -> list[dict]:
        """
        Translate entire book with intelligent deduplication.

        book_requests: List of {content_text_id, content_source_text, chapter_number}
        """
        results = []

        for request in book_requests:
            chapter = request.get("chapter_number", 1)
            content_id = request["content_text_id"]
            source_text = request["content_source_text"]

            # Translate with deduplication awareness
            result = self.translate_with_deduplication(
                source_text, chapter, content_id
            )
            results.append(result)

        return results

    def translate_with_deduplication(self, source_text: str,
                                    chapter: int, content_id: int) -> dict:
        """
        Translate text and apply intelligent footnote deduplication.
        """
        # Get raw translation from OpenAI (with ALL potential footnotes)
        raw_translation = self.translate_with_footnotes(source_text)

        # Filter footnotes based on deduplication strategy
        filtered_footnotes = []
        for footnote in raw_translation["footnotes"]:
            term_chinese = footnote["footnote_ideogram"]
            term_pinyin = footnote["footnote_pinyin"]

            # Look up term in glossary
            glossary_entry = self.glossary.get(term_chinese)
            if not glossary_entry:
                # Not in glossary - include footnote
                filtered_footnotes.append(footnote)
                continue

            strategy = glossary_entry["Deduplication_Strategy"]

            # Check if we should generate footnote
            decision = self.footnote_tracker.should_generate_footnote(
                term=term_chinese,
                strategy=strategy,
                chapter=chapter,
                content_id=content_id,
                context=source_text  # For EVERY_OCCURRENCE context checking
            )

            if decision["generate_footnote"]:
                if decision["footnote_type"] == "brief":
                    # Shorten footnote to brief reminder
                    footnote["footnote_explanation"] = self._create_brief_explanation(
                        glossary_entry["Footnote_Template"]
                    )
                elif decision["footnote_type"] == "reference":
                    # Create reference to earlier footnote
                    ref_info = decision["reference_info"]
                    footnote["footnote_explanation"] = (
                        f"[see footnote in Chapter {ref_info['chapter']}]"
                    )

                filtered_footnotes.append(footnote)

        # Renumber footnotes sequentially after filtering
        for i, footnote in enumerate(filtered_footnotes, start=1):
            footnote["footnote_key"] = i

        # Update text with correct footnote markers
        translated_text = self._update_footnote_markers(
            raw_translation["translated_text"],
            raw_translation["footnotes"],
            filtered_footnotes
        )

        return {
            "translated_text": translated_text,
            "footnotes": filtered_footnotes
        }

    def _create_brief_explanation(self, full_template: str) -> str:
        """
        Create brief reminder from full footnote template.
        Extract first sentence or first 100 chars.
        """
        # Split on '. ' to get first sentence
        sentences = full_template.split('. ')
        if len(sentences) > 1:
            return sentences[0] + '.'

        # If no period, just truncate
        if len(full_template) > 100:
            return full_template[:100] + '...'

        return full_template
```

## Persistence and State Management

### Option 1: In-Memory (Single Session)

For processing an entire book in one session, keep `FootnoteTracker` in memory:

```python
# Process all chapters sequentially
tracker = FootnoteTracker()
service = TranslationService(api_key, glossary_path)
service.footnote_tracker = tracker

for chapter_requests in book_chapters:
    results = service.translate_book(chapter_requests)
```

### Option 2: Persistent Storage (Incremental Processing)

For processing books incrementally or resuming interrupted sessions, persist tracker state:

```python
import json

class PersistentFootnoteTracker(FootnoteTracker):
    def __init__(self, state_file: str = None):
        super().__init__()
        self.state_file = state_file
        if state_file and os.path.exists(state_file):
            self.load_state()

    def save_state(self):
        """Save tracker state to JSON file."""
        state = {
            "first_occurrence_terms": self.first_occurrence_terms,
            "recurring_brief_terms": self.recurring_brief_terms,
            "every_occurrence_terms": self.every_occurrence_terms
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_state(self):
        """Load tracker state from JSON file."""
        with open(self.state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        self.first_occurrence_terms = state.get("first_occurrence_terms", {})
        self.recurring_brief_terms = state.get("recurring_brief_terms", {})
        self.every_occurrence_terms = state.get("every_occurrence_terms", {})

# Usage
tracker = PersistentFootnoteTracker(state_file="book_123_footnote_state.json")
service = TranslationService(api_key, glossary_path)
service.footnote_tracker = tracker

# Process chapters
for chapter_requests in book_chapters:
    results = service.translate_book(chapter_requests)
    tracker.save_state()  # Save after each chapter
```

## Testing Deduplication

### Unit Test Example

```python
def test_first_occurrence_only_deduplication():
    tracker = FootnoteTracker()

    # First occurrence - should generate
    decision1 = tracker.should_generate_footnote(
        term="qì",
        strategy="FIRST_OCCURRENCE_ONLY",
        chapter=1,
        content_id=5
    )
    assert decision1["generate_footnote"] == True
    assert decision1["footnote_type"] == "full"

    # Second occurrence - should NOT generate
    decision2 = tracker.should_generate_footnote(
        term="qì",
        strategy="FIRST_OCCURRENCE_ONLY",
        chapter=2,
        content_id=45
    )
    assert decision2["generate_footnote"] == False

    # Third occurrence in chapter 5 - still NO
    decision3 = tracker.should_generate_footnote(
        term="qì",
        strategy="FIRST_OCCURRENCE_ONLY",
        chapter=5,
        content_id=123
    )
    assert decision3["generate_footnote"] == False

def test_recurring_brief_deduplication():
    tracker = FootnoteTracker()

    # Chapter 1, first occurrence - FULL
    d1 = tracker.should_generate_footnote("zǒuhuǒ rùmó", "RECURRING_BRIEF", 1, 10)
    assert d1["footnote_type"] == "full"

    # Chapter 1, second occurrence - BRIEF
    d2 = tracker.should_generate_footnote("zǒuhuǒ rùmó", "RECURRING_BRIEF", 1, 20)
    assert d2["footnote_type"] == "brief"

    # Chapter 1, third occurrence - NONE
    d3 = tracker.should_generate_footnote("zǒuhuǒ rùmó", "RECURRING_BRIEF", 1, 30)
    assert d3["generate_footnote"] == False

    # Chapter 2, first occurrence - BRIEF (new chapter)
    d4 = tracker.should_generate_footnote("zǒuhuǒ rùmó", "RECURRING_BRIEF", 2, 5)
    assert d4["footnote_type"] == "brief"
```

## Quality Assurance Report

After processing a book, generate a deduplication report:

```python
def generate_deduplication_report(tracker: FootnoteTracker) -> dict:
    """
    Generate summary of footnote deduplication for QA.
    """
    return {
        "first_occurrence_terms": {
            "count": len(tracker.first_occurrence_terms),
            "terms": list(tracker.first_occurrence_terms.keys()),
            "footnote_count": len(tracker.first_occurrence_terms)  # One per term
        },
        "recurring_brief_terms": {
            "count": len(tracker.recurring_brief_terms),
            "terms": list(tracker.recurring_brief_terms.keys()),
            "footnote_count": sum(
                len(data["current_chapter_occurrences"])
                for data in tracker.recurring_brief_terms.values()
            )
        },
        "every_occurrence_terms": {
            "count": len(tracker.every_occurrence_terms),
            "terms": list(tracker.every_occurrence_terms.keys()),
            "footnote_count": sum(
                len(data["occurrences"])
                for data in tracker.every_occurrence_terms.values()
            )
        },
        "total_footnotes_generated": (
            len(tracker.first_occurrence_terms) +
            sum(len(data["current_chapter_occurrences"])
                for data in tracker.recurring_brief_terms.values()) +
            sum(len(data["occurrences"])
                for data in tracker.every_occurrence_terms.values())
        ),
        "estimated_footnotes_without_deduplication": "N/A"  # Calculate based on raw translations
    }
```

## Benefits of This Approach

1. **Reader Experience**: Readers learn wuxia vocabulary naturally through repetition, not through redundant footnotes
2. **Scholarly Quality**: Maintains thorough explanations on first occurrence, respecting PhD-level audience
3. **Contextual Intelligence**: RECURRING_BRIEF strategy provides reminders when readers might forget
4. **Flexibility**: EVERY_OCCURRENCE ensures rare terms are always explained
5. **Deterministic**: Same book translated twice will have identical footnote pattern
6. **Trackable**: State files allow resumption and auditing

## Future Enhancements

### Cross-Book Deduplication

For series or multiple books by same author, consider:

```python
class SeriesFootnoteTracker(FootnoteTracker):
    def __init__(self, series_id: str):
        super().__init__()
        self.series_id = series_id
        self.load_series_glossary()  # Terms explained in previous books

    def should_generate_footnote(self, term, strategy, chapter, content_id, book_number):
        # If term explained in previous book, treat as RECURRING_BRIEF
        if term in self.series_glossary and book_number > 1:
            # Provide brief reminder in footnote
            return {"generate_footnote": True, "footnote_type": "brief_series_reminder"}

        # Otherwise use normal logic
        return super().should_generate_footnote(term, strategy, chapter, content_id)
```

### Reader Preference Settings

Allow readers to customize deduplication:

```python
class ReaderPreferences:
    MINIMAL_FOOTNOTES = "minimal"  # FIRST_OCCURRENCE_ONLY for everything
    BALANCED = "balanced"          # Default strategy from glossary
    VERBOSE = "verbose"            # More frequent reminders

    def adjust_strategy(self, base_strategy: str, preference: str) -> str:
        if preference == self.MINIMAL_FOOTNOTES:
            return "FIRST_OCCURRENCE_ONLY"
        elif preference == self.VERBOSE:
            if base_strategy == "FIRST_OCCURRENCE_ONLY":
                return "RECURRING_BRIEF"
        return base_strategy
```

## Conclusion

This deduplication strategy balances scholarly rigor with readability, teaching readers wuxia vocabulary through intelligent repetition rather than footnote fatigue. The implementation is deterministic, trackable, and respects the sophistication of the target audience.
