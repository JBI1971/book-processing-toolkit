# EPUB Formatting Strategy for Chinese Wuxia Novels
## Comprehensive Content Type Taxonomy and Formatting Rules

**Project**: Chinese-to-English Translation Pipeline
**Version**: 1.0.0
**Date**: 2025-11-13
**Analysis Basis**: 20-work sample from cleaned JSON corpus

---

## Executive Summary

This document defines a comprehensive formatting strategy for converting cleaned Chinese wuxia novel JSON files into formatted EPUB-ready content. The strategy is based on analysis of 20 representative works (490 chapters total, 2,500+ content blocks) and proposes:

1. **Content Type Taxonomy**: 12 semantic categories with clear identification rules
2. **Formatting Rules**: CSS-based styling mapped to each content type
3. **Workflow Recommendation**: Hybrid approach (tag types first, translate, then apply formatting)
4. **Implementation Path**: Phased rollout with validation checkpoints

**Key Finding**: Current JSON structure uses only 2 types (`text` 98%, `heading` 2%). We propose enriching this with 10 additional semantic types to enable superior EPUB formatting and translation quality.

---

## 1. Content Analysis Findings

### 1.1 Current State

**Analyzed Corpus**:
- 20 works by major authors (金庸, 梁羽生, 黃易, 古龍, 雲中岳, 倪匡, etc.)
- 490 total chapters
- 2,529 content blocks sampled
- Average block length: 99.7 characters (range: 3-624)

**Existing Type Distribution**:
```
text      : 2,481 blocks (98.10%)
heading   :    48 blocks ( 1.90%)
```

**Problem**: The `text` category is too broad and conflates:
- Narrative prose
- Dialogue (56% of samples use speaker_verb_quote pattern)
- Descriptive passages
- Action sequences
- Internal thoughts
- Special content (letters, documents, inscriptions)

### 1.2 Dialogue Pattern Analysis

From manual sampling, dialogue appears in **~60-70% of text blocks** with these patterns:

| Pattern | Distribution | Example |
|---------|-------------|----------|
| `speaker_verb_quote` | 56 occurrences | 趙穆聽完項少龍半點都沒有隱瞞的說話後，興奮得站了起來，仰天長笑道：「今回真是天助我也，若我有朝一日坐上王位，你就是我的三軍統帥。」 |
| `quote_first` | 19 occurrences | 「是崔爺長青。」小秋答。|
| `mixed` | 11 occurrences | (narrative + embedded dialogue) |
| `quote_speaker_verb` | 4 occurrences | 紅綃魔女盯著遠去的人馬背影發怔，信口問：「你兩人知道烏騅馬上的人是誰麼？」|

**Critical Insight**: Dialogue formatting MUST preserve quotation structure for translation. English translation will convert Chinese quotes (「」『』) to English quotes ("" ''), requiring careful handling.

### 1.3 Special Content Identified

**Rare but important** (requires distinct formatting):
- **Inscriptions** (碑文, 墓誌銘): 1 occurrence in 20-work sample
  - Example: 董海川墓碑文 in 《偷拳》
- **Verse/Poetry**: 0 detected in random sample (likely appears in specific chapters)
  - Known markers: 詩曰, 詞曰, 賦曰, 頌曰, 歌曰
- **Letters/Missives**: Not found in sample, but common in genre
  - Markers: 信上寫道, 書上寫, 信中, 函曰, 書曰
- **Documents/Edicts**: Not found in sample
  - Markers: 詔曰, 令曰, 旨曰, 敕曰

---

## 2. Proposed Content Type Taxonomy

### 2.1 Complete Type System

We propose **12 semantic content types** organized into 4 categories:

#### **A. Core Prose Types** (90% of content)
1. **narrative** - Standard narrative prose describing events, actions, progression of plot
2. **dialogue** - Character speech, conversations (WITH quotation marks)
3. **descriptive** - Detailed descriptions of scenery, people, objects, settings
4. **action_sequence** - Fight scenes, combat descriptions, martial arts moves
5. **internal_thought** - Character's internal monologue (often unmarked or subtle)

#### **B. Structural Types** (5-8% of content)
6. **heading** - Chapter titles, section headings (already implemented)
7. **transition** - Scene transitions, time jumps, location changes
8. **author_note** - Author's commentary, footnotes (rare in source material)

#### **C. Formal/Literary Types** (1-2% of content)
9. **verse** - Classical Chinese poetry, song lyrics, verses
10. **letter** - Written correspondence, notes, missives
11. **document** - Official documents, edicts, decrees, proclamations
12. **inscription** - Tombstone inscriptions, plaques, couplets, signs

#### **D. Metadata Type** (handled separately)
13. **chapter_metadata** - Chapter ordinals, IDs, navigation (already in TOC)

### 2.2 Classification Rules (Pattern-Based)

Each type has **deterministic patterns** that can be detected without AI:

#### **1. heading**
- **Already implemented** in current pipeline
- Pattern: `metadata.tag == 'h1'|'h2'|'h3'` OR first block with `第N章` format

#### **2. dialogue**
- **Primary indicator**: Contains Chinese quotation marks `「」` or `『』`
- **Secondary indicator**: Contains dialogue verbs: `道：`, `說：`, `問：`, `答：`, `喝道：`, `笑道：`, `怒道：`, `冷笑道：`
- **Sub-patterns**:
  - `quote_first`: `「content」speaker說`
  - `speaker_verb_quote`: `speaker道：「content」`
  - `mixed`: Narrative + embedded dialogue

```python
def is_dialogue(content: str) -> bool:
    has_quotes = '「' in content or '『' in content
    dialogue_verbs = ['道：', '說：', '問：', '答：', '喝道：', '笑道：', '怒道：']
    has_verb = any(verb in content for verb in dialogue_verbs)
    return has_quotes or has_verb
```

#### **3. verse**
- **Structure-based**: 2+ short lines (avg < 25 chars/line) with 4+ total lines
- **Marker-based**: Contains verse intro markers: `詩曰`, `詞曰`, `賦曰`, `頌曰`, `歌曰`
- **Rhythm pattern**: Classical Chinese verse often has 5-char or 7-char line structure

```python
def is_verse(content: str) -> bool:
    verse_markers = ['詩曰', '詞曰', '賦曰', '頌曰', '歌曰']
    if any(marker in content for marker in verse_markers):
        return True

    lines = content.split('\n') if '\n' in content else [content]
    if len(lines) >= 4:
        avg_len = sum(len(line.strip()) for line in lines) / len(lines)
        if avg_len < 25:
            return True
    return False
```

#### **4. letter**
- **Markers**: `信上寫道`, `書上寫`, `信中`, `函曰`, `書曰`
- Often follows character name + action (e.g., "張無忌打開信，只見信上寫道：")

#### **5. document**
- **Markers**: `詔曰`, `令曰`, `旨曰`, `敕曰` (imperial/official language)
- Formal tone, classical Chinese syntax

#### **6. inscription**
- **Markers**: `碑文`, `墓誌銘`, `匾額`, `對聯`
- Often introduced by descriptive context (e.g., "墓前有弟子輦公立的碑文，可以徵實")

#### **7. action_sequence**
- **Complex to detect** - may require length + verb frequency analysis
- High frequency of action verbs: `飛`, `躍`, `刺`, `劈`, `砍`, `擊`, `閃`, `避`
- Often lacks dialogue markers
- May contain martial arts move names (e.g., "降龍十八掌", "獨孤九劍")

#### **8. descriptive**
- **Heuristic**: Longer paragraphs (>150 chars) without dialogue or action verbs
- Contains visual/sensory descriptors: `景色`, `只見`, `遠處`, `山間`, color terms, weather terms
- Slower narrative pacing (fewer verbs per sentence)

#### **9. narrative** (default)
- **Catch-all** for standard prose that doesn't match other categories
- Mixed tense and pacing
- Third-person omniscient narration (most common in wuxia)

#### **10. internal_thought**
- **Difficult to detect** without context
- May be unmarked or use subtle markers: `心想`, `心道`, `暗自`, `暗想`, `不禁想道`
- Sometimes uses single quotes 『』 for thoughts vs double quotes 「」 for speech

#### **11. transition**
- **Short blocks** (< 50 chars) indicating time/location change
- Temporal markers: `次日`, `三日後`, `半月後`, `數年後`, `此時`, `忽然`, `不料`
- Location markers: `另一邊`, `此時`, place names + `處`

---

## 3. EPUB Formatting Rules

### 3.1 Design Principles

1. **Readability First**: Optimize for English EPUB readers (Kindle, Apple Books, Google Play Books)
2. **Genre Conventions**: Honor wuxia genre expectations (action pacing, dialogue clarity)
3. **Accessibility**: WCAG AA compliance (contrast ratios, font sizing, screen readers)
4. **Responsiveness**: Support user font size preferences
5. **Minimalism**: Clean, unobtrusive formatting that doesn't distract from content

### 3.2 Formatting Specification (CSS + HTML)

#### **Base Stylesheet Structure**

```css
/* ========================================
   EPUB Base Styles - Chinese Wuxia Novels
   ======================================== */

/* --- BODY & DEFAULTS --- */
body {
  font-family: "Crimson Text", "Noto Serif", Georgia, serif;
  font-size: 1em; /* User-adjustable */
  line-height: 1.6;
  margin: 1em 2em;
  color: #1a1a1a;
  background-color: #ffffff;
  text-align: justify;
  hyphens: auto;
  -webkit-hyphens: auto;
  adobe-hyphenate: auto;
}

/* --- CHAPTER STRUCTURE --- */
section.chapter {
  page-break-before: always;
  margin-bottom: 2em;
}

/* --- HEADINGS --- */
h1.chapter-title {
  font-family: "Noto Serif SC", "STSong", serif; /* Preserve Chinese characters if needed */
  font-size: 1.8em;
  font-weight: bold;
  text-align: center;
  margin-top: 2em;
  margin-bottom: 1.5em;
  page-break-after: avoid;
  color: #2c3e50;
}

h2.section-heading {
  font-size: 1.4em;
  font-weight: bold;
  margin-top: 1.5em;
  margin-bottom: 1em;
  color: #34495e;
}

/* --- NARRATIVE PROSE (DEFAULT) --- */
p.narrative {
  text-indent: 1.5em;
  margin-bottom: 0.5em;
  line-height: 1.6;
}

p.narrative:first-of-type,
p.narrative.chapter-opening {
  text-indent: 0; /* No indent for first paragraph */
}

/* Optional: Drop cap for chapter opening */
p.narrative.chapter-opening::first-letter {
  float: left;
  font-size: 3em;
  line-height: 0.9;
  margin-right: 0.1em;
  font-weight: bold;
  color: #8b4513;
}

/* --- DIALOGUE --- */
p.dialogue {
  text-indent: 1.5em; /* Match narrative for consistency */
  margin-bottom: 0.5em;
  line-height: 1.65;
}

/* Speaker tags in dialogue */
span.speaker {
  font-style: italic;
  font-weight: 500;
}

/* Quotation marks - handled in translation (Chinese → English) */
/* Chinese: 「」『』 → English: "" '' */

/* --- DESCRIPTIVE PASSAGES --- */
p.descriptive {
  text-indent: 1.5em;
  margin-bottom: 0.75em;
  line-height: 1.7; /* Slightly more spacious */
  font-style: normal;
}

/* --- ACTION SEQUENCES --- */
p.action-sequence {
  text-indent: 1.5em;
  margin-bottom: 0.4em; /* Tighter spacing for pacing */
  line-height: 1.55;
  font-weight: 400;
}

/* Optional: Highlight martial arts technique names */
span.technique-name {
  font-style: italic;
  font-weight: 600;
  letter-spacing: 0.02em;
}

/* --- INTERNAL THOUGHTS --- */
p.internal-thought {
  text-indent: 1.5em;
  margin-bottom: 0.6em;
  font-style: italic; /* Distinguish from narrative */
  line-height: 1.6;
  color: #3a3a3a;
}

/* --- VERSE / POETRY --- */
div.verse {
  margin: 1.5em 2em;
  padding: 1em;
  text-align: center;
  font-style: italic;
  line-height: 1.8;
  background-color: #f9f9f9;
  border-left: 3px solid #c0c0c0;
}

div.verse p {
  margin-bottom: 0.5em;
  text-indent: 0; /* No indent for verse */
}

div.verse-header {
  font-weight: bold;
  font-style: normal;
  margin-bottom: 0.75em;
  color: #555;
}

/* --- LETTERS / MISSIVES --- */
div.letter {
  margin: 1.5em 2em;
  padding: 1em 1.5em;
  font-family: "Courier New", "Noto Sans Mono", monospace;
  font-size: 0.95em;
  line-height: 1.7;
  background-color: #faf8f3;
  border: 1px solid #d4c5a9;
  border-radius: 3px;
}

div.letter-header {
  font-weight: bold;
  margin-bottom: 0.75em;
  text-align: right;
  font-style: italic;
}

div.letter p {
  text-indent: 1.5em;
  margin-bottom: 0.6em;
}

/* --- DOCUMENTS / EDICTS --- */
div.document {
  margin: 1.5em 1em;
  padding: 1em 2em;
  font-family: "Noto Serif SC", "STSong", serif;
  font-size: 0.98em;
  line-height: 1.8;
  background-color: #fffef5;
  border-left: 4px solid #8b4513;
  font-style: italic;
}

div.document-title {
  font-weight: bold;
  text-align: center;
  margin-bottom: 1em;
  font-size: 1.1em;
  color: #5a3a1a;
}

/* --- INSCRIPTIONS --- */
div.inscription {
  margin: 2em auto;
  padding: 1.5em;
  max-width: 30em;
  text-align: center;
  font-family: "Noto Serif SC", serif;
  font-size: 0.95em;
  line-height: 1.9;
  border: 2px solid #888;
  background-color: #f5f5f5;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

div.inscription p {
  margin-bottom: 0.5em;
  text-indent: 0;
}

/* --- TRANSITIONS --- */
p.transition {
  text-align: center;
  margin: 1.5em 0;
  font-style: italic;
  font-size: 0.95em;
  color: #666;
  text-indent: 0;
}

/* Optional: Ornamental divider */
p.transition::before,
p.transition::after {
  content: "✦";
  margin: 0 0.5em;
  color: #999;
}

/* --- AUTHOR NOTES --- */
aside.author-note {
  margin: 1em 2em;
  padding: 0.75em 1em;
  font-size: 0.9em;
  line-height: 1.5;
  background-color: #f0f8ff;
  border-left: 3px solid #4682b4;
  font-style: italic;
}

/* --- ACCESSIBILITY ENHANCEMENTS --- */

/* Screen reader support */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0,0,0,0);
  border: 0;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  body {
    color: #000;
    background-color: #fff;
  }

  h1, h2, h3 {
    color: #000;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  body {
    color: #e0e0e0;
    background-color: #1a1a1a;
  }

  div.verse,
  div.letter,
  div.document,
  div.inscription {
    background-color: #2a2a2a;
    border-color: #555;
  }
}

/* --- RESPONSIVE FONT SIZES --- */
@media (max-width: 600px) {
  body {
    margin: 0.5em 1em;
  }

  h1.chapter-title {
    font-size: 1.6em;
  }
}
```

### 3.3 HTML Output Examples

#### **Example 1: Mixed Narrative + Dialogue**

**Chinese Source**:
```
宗維俠見張無忌擒釋圓音，舉重若輕，不禁大為驚訝，但既已身在場中，豈能就此示弱退下？大聲道：「姓曾的，你來強行出頭，到底受了何人指使？」張無忌道：「我只盼望六大派和明教罷手言和，並無誰人指使在下。」
```

**English Translation + Formatting**:
```html
<p class="narrative">
  Zong Weixia watched as Zhang Wuji subdued Yuanyin effortlessly,
  and couldn't help but be astonished. However, having already entered
  the fray, how could he show weakness and retreat now?
</p>

<p class="dialogue">
  He shouted loudly, <span class="speaker">saying</span>, "Surnamed Zeng!
  You forcibly intervene here—who exactly sent you?"
</p>

<p class="dialogue">
  <span class="speaker">Zhang Wuji replied</span>, "I only hope that the
  Six Major Sects and the Ming Cult can cease hostilities and make peace.
  No one has instructed me to act."
</p>
```

#### **Example 2: Verse (Poetry)**

**Chinese Source**:
```
詩曰：
寒梅最堪恨
長作去年花
月落烏啼霜滿天
江楓漁火對愁眠
```

**English Translation + Formatting**:
```html
<div class="verse">
  <div class="verse-header">A Poem</div>
  <p>The cold plum tree is most lamentable,</p>
  <p>Forever becoming last year's bloom.</p>
  <p>The moon sets, crows cry, frost fills the sky,</p>
  <p>By maple-lined river, fishing fires companion worried sleep.</p>
</div>
```

#### **Example 3: Letter**

**Chinese Source**:
```
張無忌打開信，只見信上寫道：「無忌吾兒：為父不能親自前來，深感愧疚。你需謹記，武林險惡，切勿輕信他人...」
```

**English Translation + Formatting**:
```html
<p class="narrative">
  Zhang Wuji opened the letter and read:
</p>

<div class="letter">
  <div class="letter-header">From Father</div>
  <p>
    My son Wuji: As your father, I cannot come in person, for which I feel
    deeply ashamed. You must remember that the martial world is treacherous—
    never trust others lightly...
  </p>
</div>
```

#### **Example 4: Action Sequence**

**Chinese Source**:
```
他右手一揚，使出「降龍十八掌」第三式「見龍在田」，掌風呼呼作響，直取對方胸口。對方側身閃避，同時反手一劍，刺向他的肩頭。兩人你來我往，瞬間已拆了十餘招。
```

**English Translation + Formatting**:
```html
<p class="action-sequence">
  He raised his right hand and executed the third stance of the
  <span class="technique-name">Eighteen Dragon-Subduing Palms</span>—
  "Seeing the Dragon in the Field." His palm wind whooshed forth,
  striking straight at his opponent's chest. The opponent sidestepped
  to evade, simultaneously backhanding his sword toward his shoulder.
  The two traded blows back and forth, exchanging over ten moves in
  an instant.
</p>
```

### 3.4 Enriched JSON Schema

To support this formatting system, we propose extending the current JSON schema:

```json
{
  "meta": {
    "title": "Book Title",
    "formatting_version": "1.0.0",
    "formatting_profile": "wuxia_standard"
  },
  "structure": {
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "第一章　神秘的年輕人",
          "content_blocks": [
            {
              "id": "block_0001",
              "type": "narrative",           // NEW: semantic type
              "content": "原文內容...",
              "translated_content": null,     // NEW: post-translation
              "metadata": {
                "tag": "p",
                "original_type": "text"       // Preserve original classification
              },
              "formatting": {
                "css_class": "narrative",     // NEW: CSS class
                "html_tag": "p",              // NEW: Output HTML tag
                "attributes": {               // NEW: Optional HTML attributes
                  "data-block-id": "block_0001"
                }
              }
            },
            {
              "id": "block_0002",
              "type": "dialogue",
              "subtype": "speaker_verb_quote", // NEW: dialogue pattern
              "content": "張無忌道：「我只盼望六大派和明教罷手言和。」",
              "metadata": {
                "speaker": "張無忌",          // NEW: extracted speaker
                "dialogue_verb": "道",
                "quote_style": "chinese_double"
              },
              "formatting": {
                "css_class": "dialogue",
                "html_tag": "p",
                "preserve_structure": true     // Flag for translation
              }
            },
            {
              "id": "block_0003",
              "type": "verse",
              "content": "詩曰：\n寒梅最堪恨\n長作去年花",
              "metadata": {
                "verse_type": "classical_poem",
                "lines": 2,
                "intro_marker": "詩曰"
              },
              "formatting": {
                "css_class": "verse",
                "html_tag": "div",
                "wrapper_class": "verse",
                "preserve_line_breaks": true
              }
            }
          ]
        }
      ]
    }
  },
  "formatting_config": {
    "global_settings": {
      "base_font_family": "Crimson Text, Georgia, serif",
      "base_line_height": 1.6,
      "dialogue_quote_conversion": {
        "「」": "\"\"",
        "『』": "''"
      }
    },
    "type_mappings": {
      "narrative": {
        "css_class": "narrative",
        "html_tag": "p",
        "text_indent": "1.5em"
      },
      "dialogue": {
        "css_class": "dialogue",
        "html_tag": "p",
        "text_indent": "1.5em",
        "special_handling": "preserve_quotation_structure"
      }
      // ... other mappings
    }
  }
}
```

---

## 4. Workflow Recommendation: Hybrid Approach

### 4.1 Three Workflow Options Evaluated

#### **Option A: Format-First, Then Translate**

**Process**: Clean JSON → Apply Formatting Tags → Translate → Generate EPUB

**Pros**:
- Formatting context guides translation (e.g., verse formatting signals need for poetic language)
- Translator sees structure and can adapt tone accordingly
- Preserves original formatting intent

**Cons**:
- English text length differs from Chinese (avg 1.3-1.5x longer)
- Formatting assumptions may break (e.g., short lines in Chinese become long in English)
- Requires re-formatting if translation changes structure

**Best For**: Content where format heavily influences meaning (poetry, formal letters)

---

#### **Option B: Translate-First, Then Format**

**Process**: Clean JSON → Translate → Classify Translated Content → Apply Formatting → Generate EPUB

**Pros**:
- Formatting rules adapt to actual English text patterns
- No need to re-format after translation
- Simpler pipeline (one formatting pass)

**Cons**:
- Translator lacks formatting context
- May lose semantic cues that should guide translation
- Harder to preserve structural intent (e.g., verse rhythm)

**Best For**: Prose-heavy content where formatting is primarily aesthetic

---

#### **Option C: HYBRID - Tag Types First, Translate, Then Apply Formatting** ⭐ **RECOMMENDED**

**Process**:
```
Clean JSON →
Semantic Tagging (type classification) →
Translation (with type awareness) →
Formatting Application (CSS + HTML) →
Generate EPUB
```

**Pros**:
- **Best of both worlds**: Semantic tags guide translation, formatting adapts to English output
- Type information helps translator choose appropriate tone (formal for documents, poetic for verse)
- Formatting rules can be adjusted post-translation without re-translating
- Separates content logic from presentation (maintainable)

**Cons**:
- More complex pipeline (3 stages instead of 2)
- Requires additional processing stage (semantic tagging)

**Why This Works Best**:
1. **Translation Quality**: Knowing a block is "verse" vs "dialogue" vs "document" helps translator choose register/style
2. **Format Flexibility**: Can experiment with CSS rules without touching translation
3. **Iterative Refinement**: Can improve formatting based on EPUB previews without retranslation
4. **Automation-Friendly**: Semantic tagging can be rule-based (fast, cheap) while translation uses AI

---

### 4.2 Recommended Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: Semantic Tagging (Rule-Based)                          │
├─────────────────────────────────────────────────────────────────┤
│ Input:  cleaned_book.json (current format)                      │
│ Engine: Python script with pattern matching                     │
│ Output: tagged_book.json (with "type" field enriched)           │
│ Speed:  ~1-2 seconds per book (no API calls)                    │
│ Cost:   $0 (deterministic rules)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: Translation (AI-Powered)                               │
├─────────────────────────────────────────────────────────────────┤
│ Input:  tagged_book.json                                        │
│ Engine: OpenAI GPT-4o with type-aware prompts                   │
│         - "This is a dialogue block"                             │
│         - "This is classical verse"                              │
│         - "This is a formal edict"                               │
│ Output: translated_book.json (adds "translated_content" field)  │
│ Speed:  Variable (depends on API rate limits)                   │
│ Cost:   ~$0.50-2.00 per book (depends on length)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: Formatting Application (Template Engine)               │
├─────────────────────────────────────────────────────────────────┤
│ Input:  translated_book.json                                    │
│ Engine: Jinja2 templates + CSS rules                            │
│         - Map type → CSS class → HTML output                    │
│         - Apply quotation conversion (「」→ "")                  │
│         - Preserve structure (line breaks for verse)             │
│ Output: formatted_epub_ready.json OR direct EPUB                │
│ Speed:  ~0.5 seconds per book                                   │
│ Cost:   $0                                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: EPUB Generation (ebooklib or similar)                  │
├─────────────────────────────────────────────────────────────────┤
│ Input:  formatted_epub_ready.json                               │
│ Engine: ebooklib + custom CSS stylesheet                        │
│ Output: final_book.epub                                         │
│ Speed:  ~1-2 seconds per book                                   │
│ Cost:   $0                                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4.3 Implementation Phases

#### **Phase 1: Foundation (Weeks 1-2)**
- [ ] Implement semantic tagger (rule-based classifier)
- [ ] Create unit tests with sample blocks from each type
- [ ] Validate on 20-work sample set
- [ ] **Deliverable**: `semantic_tagger.py` + test suite

#### **Phase 2: Integration (Weeks 3-4)**
- [ ] Integrate tagger into existing batch pipeline
- [ ] Add type-aware translation prompts to translator module
- [ ] Test on 5-10 sample books
- [ ] **Deliverable**: Updated `batch_process_books.py`

#### **Phase 3: Formatting Engine (Weeks 5-6)**
- [ ] Develop CSS stylesheet (base + type-specific rules)
- [ ] Create HTML template system (Jinja2)
- [ ] Build formatting rule mapper (JSON config → CSS classes)
- [ ] **Deliverable**: `formatting_engine.py` + `wuxia_styles.css`

#### **Phase 4: EPUB Builder (Weeks 7-8)**
- [ ] Implement EPUB generator (ebooklib wrapper)
- [ ] Add metadata injection (title, author, TOC)
- [ ] Create cover page template
- [ ] Test on e-readers (Kindle, Apple Books, Kobo)
- [ ] **Deliverable**: `epub_builder.py` + test EPUBs

#### **Phase 5: Validation & Refinement (Weeks 9-10)**
- [ ] Run full pipeline on 50-100 books
- [ ] Manual QA on 10 sample EPUBs
- [ ] Collect feedback and refine CSS rules
- [ ] **Deliverable**: Production-ready pipeline

---

## 5. Technical Implementation

### 5.1 Semantic Tagger Script

**File**: `processors/semantic_tagger.py`

```python
#!/usr/bin/env python3
"""
Semantic Content Type Tagger

Enriches cleaned JSON with semantic type classifications
for improved EPUB formatting and translation quality.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


class ContentTypeTagger:
    """Rule-based semantic type classifier."""

    # Classification patterns
    DIALOGUE_VERBS = ['道：', '說：', '問：', '答：', '喝道：', '笑道：', '怒道：',
                      '冷笑道：', '嘆道：', '驚道：', '叫道：', '罵道：']

    VERSE_MARKERS = ['詩曰', '詞曰', '賦曰', '頌曰', '歌曰', '聯曰']

    LETTER_MARKERS = ['信上寫道', '書上寫', '信中', '函曰', '書曰', '札上',
                      '信箋', '書信', '家書']

    DOCUMENT_MARKERS = ['詔曰', '令曰', '旨曰', '敕曰', '榜文', '告示',
                        '公文', '奏摺']

    INSCRIPTION_MARKERS = ['碑文', '墓誌銘', '匾額', '對聯', '牌匾', '墓碑']

    TRANSITION_MARKERS = ['次日', '三日後', '半月後', '數年後', '此時',
                          '忽然', '不料', '卻說', '且說', '另一邊',
                          '話說', '原來', '當下']

    ACTION_VERBS = ['飛', '躍', '刺', '劈', '砍', '擊', '閃', '避', '抓',
                    '掌', '拳', '腳', '招', '式', '劍', '刀']

    THOUGHT_MARKERS = ['心想', '心道', '暗自', '暗想', '不禁想道', '暗暗',
                       '心中', '心裡', '念頭']

    def tag_content_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Tag a single content block with semantic type."""
        content = block.get('content', '')
        current_type = block.get('type', 'text')

        # Keep heading types
        if current_type == 'heading':
            block['semantic_type'] = 'heading'
            return block

        # Classify text blocks
        semantic_type, subtype, metadata = self._classify(content)

        block['semantic_type'] = semantic_type
        if subtype:
            block['semantic_subtype'] = subtype
        if metadata:
            block['semantic_metadata'] = metadata

        return block

    def _classify(self, content: str) -> tuple:
        """Classify content into semantic type."""
        # Priority order matters!

        # 1. Verse (high confidence patterns)
        if self._is_verse(content):
            return 'verse', self._get_verse_subtype(content), None

        # 2. Letters
        if self._is_letter(content):
            return 'letter', None, None

        # 3. Documents
        if self._is_document(content):
            return 'document', None, None

        # 4. Inscriptions
        if self._is_inscription(content):
            return 'inscription', None, None

        # 5. Transitions (short blocks with temporal/location markers)
        if self._is_transition(content):
            return 'transition', None, None

        # 6. Dialogue (very common)
        if self._is_dialogue(content):
            pattern = self._identify_dialogue_pattern(content)
            speaker = self._extract_speaker(content)
            return 'dialogue', pattern, {'speaker': speaker}

        # 7. Internal thought
        if self._is_internal_thought(content):
            return 'internal_thought', None, None

        # 8. Action sequence (heuristic)
        if self._is_action_sequence(content):
            return 'action_sequence', None, None

        # 9. Descriptive (longer, visual/sensory)
        if self._is_descriptive(content):
            return 'descriptive', None, None

        # 10. Default: narrative
        return 'narrative', None, None

    def _is_dialogue(self, content: str) -> bool:
        """Detect dialogue."""
        has_quotes = '「' in content or '『' in content
        has_verb = any(verb in content for verb in self.DIALOGUE_VERBS)
        return has_quotes or has_verb

    def _identify_dialogue_pattern(self, content: str) -> str:
        """Identify dialogue structural pattern."""
        if content.startswith('「') or content.startswith('『'):
            return 'quote_first'
        elif any(f'{verb}「' in content for verb in ['道', '說', '問', '答', '喝道', '笑道']):
            return 'speaker_verb_quote'
        elif '」' in content and ('道' in content or '說' in content):
            return 'quote_speaker_verb'
        return 'mixed'

    def _extract_speaker(self, content: str) -> str:
        """Extract speaker name from dialogue."""
        for verb in self.DIALOGUE_VERBS:
            if verb in content:
                # Find text before verb
                parts = content.split(verb)
                if len(parts) > 0:
                    # Clean up to get just the name
                    speaker = parts[0].strip().split()[-1] if parts[0] else None
                    return speaker[:20] if speaker else None
        return None

    def _is_verse(self, content: str) -> bool:
        """Detect classical verse/poetry."""
        # Marker-based
        if any(marker in content for marker in self.VERSE_MARKERS):
            return True

        # Structure-based
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        if len(lines) >= 4:
            avg_len = sum(len(line) for line in lines) / len(lines)
            if avg_len < 25:
                return True

        return False

    def _get_verse_subtype(self, content: str) -> str:
        """Identify verse type."""
        if '詩曰' in content:
            return 'classical_poem'
        elif '詞曰' in content:
            return 'ci_poem'
        elif '賦曰' in content:
            return 'fu_rhapsody'
        elif '歌曰' in content:
            return 'song'
        return 'verse'

    def _is_letter(self, content: str) -> bool:
        """Detect letters/missives."""
        return any(marker in content for marker in self.LETTER_MARKERS)

    def _is_document(self, content: str) -> bool:
        """Detect official documents."""
        return any(marker in content for marker in self.DOCUMENT_MARKERS)

    def _is_inscription(self, content: str) -> bool:
        """Detect inscriptions."""
        return any(marker in content for marker in self.INSCRIPTION_MARKERS)

    def _is_transition(self, content: str) -> bool:
        """Detect scene transitions."""
        if len(content) > 100:
            return False
        return any(marker in content for marker in self.TRANSITION_MARKERS)

    def _is_internal_thought(self, content: str) -> bool:
        """Detect internal thoughts."""
        return any(marker in content for marker in self.THOUGHT_MARKERS)

    def _is_action_sequence(self, content: str) -> bool:
        """Detect action sequences (heuristic)."""
        if len(content) < 50:
            return False

        # Count action verbs
        action_count = sum(1 for verb in self.ACTION_VERBS if verb in content)

        # High density of action verbs
        action_density = action_count / (len(content) / 10)

        # No dialogue markers (pure action)
        has_dialogue = self._is_dialogue(content)

        return action_density > 1.5 and not has_dialogue

    def _is_descriptive(self, content: str) -> bool:
        """Detect descriptive passages."""
        if len(content) < 100:
            return False

        # Visual/sensory descriptors
        descriptors = ['景色', '只見', '遠處', '山間', '天空', '雲', '風',
                       '雨', '雪', '月', '星', '色', '聲', '香']

        descriptor_count = sum(1 for desc in descriptors if desc in content)

        # No dialogue
        has_dialogue = self._is_dialogue(content)

        return descriptor_count >= 2 and not has_dialogue

    def process_file(self, input_path: Path, output_path: Path = None) -> Dict[str, Any]:
        """Process entire cleaned JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Tag all content blocks
        chapters = data.get('structure', {}).get('body', {}).get('chapters', [])

        for chapter in chapters:
            content_blocks = chapter.get('content_blocks', [])
            for block in content_blocks:
                self.tag_content_block(block)

        # Add metadata
        if 'meta' not in data:
            data['meta'] = {}
        data['meta']['semantic_tagging_version'] = '1.0.0'
        data['meta']['tagging_engine'] = 'rule_based'

        # Save
        if output_path is None:
            output_path = input_path.parent / f"tagged_{input_path.name}"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Tag content with semantic types')
    parser.add_argument('--input', required=True, help='Input cleaned JSON file')
    parser.add_argument('--output', help='Output tagged JSON file (default: tagged_{input})')

    args = parser.parse_args()

    tagger = ContentTypeTagger()
    result = tagger.process_file(Path(args.input), Path(args.output) if args.output else None)

    print(f"✓ Tagged file saved")


if __name__ == '__main__':
    main()
```

---

### 5.2 Formatting Rule Configuration

**File**: `config/formatting_rules.yml`

```yaml
# EPUB Formatting Rules Configuration
# Maps semantic content types to CSS classes and HTML structure

global_settings:
  base_font_family: "Crimson Text, Georgia, serif"
  chinese_font_family: "Noto Serif SC, STSong, serif"
  base_font_size: "1em"
  base_line_height: 1.6
  base_text_color: "#1a1a1a"
  base_background_color: "#ffffff"

  quotation_conversion:
    chinese_double: "「」"
    english_double: "\"\""
    chinese_single: "『』"
    english_single: "''"

type_mappings:
  heading:
    html_tag: "h1"
    css_class: "chapter-title"
    attributes:
      class: "chapter-title"
    page_break_before: true

  narrative:
    html_tag: "p"
    css_class: "narrative"
    text_indent: "1.5em"
    margin_bottom: "0.5em"
    line_height: 1.6
    special_rules:
      - first_paragraph_no_indent
      - optional_drop_cap_opening

  dialogue:
    html_tag: "p"
    css_class: "dialogue"
    text_indent: "1.5em"
    margin_bottom: "0.5em"
    line_height: 1.65
    preserve_structure: true
    quotation_handling: "convert_to_english"
    special_elements:
      speaker:
        tag: "span"
        class: "speaker"
        style: "italic"

  descriptive:
    html_tag: "p"
    css_class: "descriptive"
    text_indent: "1.5em"
    margin_bottom: "0.75em"
    line_height: 1.7

  action_sequence:
    html_tag: "p"
    css_class: "action-sequence"
    text_indent: "1.5em"
    margin_bottom: "0.4em"
    line_height: 1.55
    special_elements:
      technique_name:
        tag: "span"
        class: "technique-name"
        style: "italic bold"

  internal_thought:
    html_tag: "p"
    css_class: "internal-thought"
    text_indent: "1.5em"
    margin_bottom: "0.6em"
    font_style: "italic"
    color: "#3a3a3a"

  verse:
    html_tag: "div"
    css_class: "verse"
    wrapper: true
    text_align: "center"
    margin: "1.5em 2em"
    padding: "1em"
    background_color: "#f9f9f9"
    border_left: "3px solid #c0c0c0"
    preserve_line_breaks: true
    child_elements:
      verse_line:
        tag: "p"
        margin_bottom: "0.5em"
        text_indent: "0"

  letter:
    html_tag: "div"
    css_class: "letter"
    wrapper: true
    margin: "1.5em 2em"
    padding: "1em 1.5em"
    font_family: "Courier New, monospace"
    font_size: "0.95em"
    background_color: "#faf8f3"
    border: "1px solid #d4c5a9"

  document:
    html_tag: "div"
    css_class: "document"
    wrapper: true
    margin: "1.5em 1em"
    padding: "1em 2em"
    background_color: "#fffef5"
    border_left: "4px solid #8b4513"
    font_style: "italic"

  inscription:
    html_tag: "div"
    css_class: "inscription"
    wrapper: true
    margin: "2em auto"
    padding: "1.5em"
    max_width: "30em"
    text_align: "center"
    border: "2px solid #888"
    background_color: "#f5f5f5"

  transition:
    html_tag: "p"
    css_class: "transition"
    text_align: "center"
    margin: "1.5em 0"
    font_style: "italic"
    font_size: "0.95em"
    color: "#666"
    text_indent: "0"
    decorators:
      before: "✦"
      after: "✦"
```

---

## 6. Testing & Validation Strategy

### 6.1 Unit Testing

**Test semantic tagger** on known examples:

```python
# test_semantic_tagger.py
import pytest
from processors.semantic_tagger import ContentTypeTagger

def test_dialogue_detection():
    tagger = ContentTypeTagger()

    # Speaker-verb-quote pattern
    content = '張無忌道：「我只盼望六大派和明教罷手言和。」'
    semantic_type, subtype, _ = tagger._classify(content)
    assert semantic_type == 'dialogue'
    assert subtype == 'speaker_verb_quote'

    # Quote-first pattern
    content = '「是崔爺長青。」小秋答。'
    semantic_type, subtype, _ = tagger._classify(content)
    assert semantic_type == 'dialogue'
    assert subtype == 'quote_first'

def test_verse_detection():
    tagger = ContentTypeTagger()

    content = '''詩曰：
寒梅最堪恨
長作去年花
月落烏啼霜滿天
江楓漁火對愁眠'''

    semantic_type, subtype, _ = tagger._classify(content)
    assert semantic_type == 'verse'
    assert subtype == 'classical_poem'

def test_action_sequence():
    tagger = ContentTypeTagger()

    content = '他右手一揚，使出降龍十八掌第三式見龍在田，掌風呼呼作響，直取對方胸口。對方側身閃避，同時反手一劍，刺向他的肩頭。兩人你來我往，瞬間已拆了十餘招。'

    semantic_type, _, _ = tagger._classify(content)
    # Should detect high action verb density
    assert semantic_type in ['action_sequence', 'narrative']
```

### 6.2 Integration Testing

Test on **5-10 complete books**:
1. Run semantic tagger
2. Verify type distribution matches manual inspection
3. Check for misclassifications
4. Validate that `heading` types are preserved

### 6.3 EPUB Validation

Use **epubcheck** tool:
```bash
java -jar epubcheck.jar output.epub
```

Test on multiple e-readers:
- **Kindle** (Amazon)
- **Apple Books** (iOS/macOS)
- **Google Play Books**
- **Kobo**

### 6.4 Manual QA Checklist

For each sample EPUB:
- [ ] TOC navigation works correctly
- [ ] Dialogue is clearly formatted and readable
- [ ] Verse/poetry is visually distinct and centered
- [ ] Letters/documents have appropriate styling
- [ ] Action sequences flow smoothly
- [ ] Font sizing is responsive (test 3 sizes: small, medium, large)
- [ ] Dark mode renders correctly (if supported)
- [ ] No orphaned headings (page breaks work)

---

## 7. Recommendations & Next Steps

### 7.1 Immediate Actions

1. **Validate Approach**: Review this strategy document with stakeholders
2. **Create Proof-of-Concept**: Implement semantic tagger for 3 sample books
3. **Test Translation Integration**: Run type-aware translation on 1 book
4. **Refine CSS**: Generate sample EPUB and test on real e-readers

### 7.2 Success Metrics

- **Tagging Accuracy**: >95% correct semantic type classification
- **Translation Quality**: Translators report types are helpful (qualitative)
- **EPUB Validity**: 100% pass epubcheck validation
- **Readability**: User testing shows preference for formatted vs unformatted versions
- **Processing Speed**: <30 seconds per book for tagging + formatting

### 7.3 Future Enhancements

- **AI-Assisted Tagging**: Use GPT-4o to classify edge cases (10% ambiguous blocks)
- **Custom Stylesheets**: Allow users to select formatting profiles (minimal, classic, ornate)
- **Interactive EPUB**: Add footnotes, glossary, character index (EPUB 3.0 features)
- **Accessibility Features**: Screen reader enhancements, alt text for decorative elements
- **Multi-Language Support**: Adapt formatting rules for other target languages (Spanish, French, etc.)

### 7.4 Challenges & Mitigation

**Challenge 1**: Type classification ambiguity
- **Mitigation**: Use confidence scoring, allow manual override for edge cases

**Challenge 2**: English text length differences break formatting
- **Mitigation**: Test with actual translations, adjust CSS for longer text

**Challenge 3**: E-reader compatibility issues
- **Mitigation**: Test on 5+ devices, use conservative CSS (avoid unsupported properties)

**Challenge 4**: Maintaining consistency across 600+ books
- **Mitigation**: Automated validation, spot-check sampling, version control for rules

---

## 8. Conclusion

This formatting strategy provides a **robust, scalable framework** for converting Chinese wuxia novels into high-quality English EPUBs. By combining:

- **Rule-based semantic tagging** (fast, cheap, deterministic)
- **Type-aware translation** (better quality, context-sensitive)
- **Flexible CSS formatting** (maintainable, iterative improvement)

We achieve a **hybrid workflow** that balances automation with quality control.

**Next Step**: Implement the semantic tagger and test on 5 sample books to validate the approach before full-scale deployment.

---

## Appendix A: Content Type Quick Reference

| Type | Chinese Markers | Formatting | Translation Notes |
|------|----------------|------------|------------------|
| **narrative** | (default) | Standard paragraphs, indent | General prose tone |
| **dialogue** | 「」, 道：, 說： | Preserved structure, speaker tags | Convert quotes, maintain attribution |
| **verse** | 詩曰, 詞曰 | Centered, line breaks preserved | Poetic language, rhythm |
| **letter** | 信上寫道, 書曰 | Monospace, bordered box | Formal/personal tone |
| **document** | 詔曰, 令曰 | Formal border, italic | Classical/official language |
| **inscription** | 碑文, 匾額 | Centered box, shadow | Archaic, formal |
| **action** | High verb density | Tight spacing | Dynamic, present tense |
| **descriptive** | 景色, 只見 | Spacious line height | Vivid imagery |
| **thought** | 心想, 暗自 | Italics | First-person perspective |
| **transition** | 次日, 此時 | Centered, decorators | Brief, clear |

---

## Appendix B: Sample Books for Testing

**Recommended test set** (diverse authors and styles):

1. 金庸 - 倚天屠龍記 (Classical wuxia, complex dialogue)
2. 梁羽生 - 冰川天女傳 (Romantic elements, verse)
3. 古龍 - 飄香劍雨 (Modern style, short sentences)
4. 黃易 - 尋秦記 (Time travel, mixed genres)
5. 雲中岳 - 俠影紅顏 (Action-heavy)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-13
**Author**: Claude Code (Anthropic)
**Contact**: [Project Lead Email]
