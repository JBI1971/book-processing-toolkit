# Wuxia Translation Glossary Update Changelog

## Date: 2025-11-13

---

## Summary

Updated wuxia translation glossary to implement a clear distinction between **technique classes** (abstract categories → PINYIN_ONLY) and **named techniques** (specific proper nouns → ENGLISH_ONLY).

---

## Files Modified

### 1. `wuxia_translation_glossary.csv`

**Changes**: 27 entries updated

#### Category Changes (technique → technique_category):
Updated these entries to use `technique_category` category and maintain PINYIN_ONLY:

1. 內功 (nèigōng) - internal cultivation
2. 外功 (wàigōng) - external skill
3. 輕功 (qīnggōng) - lightness skill
4. 身法 (shēnfǎ) - body movement
5. 步法 (bùfǎ) - footwork
6. 掌法 (zhǎngfǎ) - palm techniques
7. 拳法 (quánfǎ) - fist techniques
8. 腿法 (tuǐfǎ) - leg techniques
9. 指法 (zhǐfǎ) - finger techniques
10. 擒拿 (qínná) - seizing and grappling
11. 點穴 (diǎnxué) - acupoint sealing
12. 解穴 (jiěxué) - unsealing points
13. 摔法 (shuāifǎ) - throwing techniques
14. 劍法 (jiànfǎ) - swordsmanship
15. 刀法 (dāofǎ) - sabre techniques
16. 槍法 (qiāngfǎ) - spear techniques
17. 棍法 (gùnfǎ) - staff techniques
18. 鞭法 (biānfǎ) - whip techniques
19. 暗器 (ànqì) - hidden weapons
20. 劍氣 (jiànqì) - sword qi
21. 刀氣 (dāoqì) - blade qi
22. 掌風 (zhǎngfēng) - palm wind

#### Translation Strategy Changes (PINYIN_ONLY → ENGLISH_ONLY):
Converted these named techniques to use English translations:

23. **凌波微步** (língbō wēibù)
    - OLD: PINYIN_ONLY, *Língbō Wēibù*
    - NEW: ENGLISH_ONLY, "Wave-Striding Steps"[1]
    - Enhanced footnote with literary origin (Cao Zhi's ode)

24. **鐵布衫** (tiěbùshān)
    - OLD: PINYIN_ONLY, *Tiěbùshān*
    - NEW: ENGLISH_ONLY, "Iron Cloth Shirt"[1]
    - Enhanced footnote with technical details

25. **金鐘罩** (jīnzhōngzhào)
    - OLD: PINYIN_ONLY, *Jīnzhōngzhào*
    - NEW: ENGLISH_ONLY, "Golden Bell Cover"[1]
    - Enhanced footnote with defensive characteristics

---

## Files Created

### 2. `wuxia_translation_glossary_additions.csv`

**New entries**: 8 famous named techniques from Jin Yong novels

All entries use ENGLISH_ONLY strategy with comprehensive footnotes:

1. **降龍十八掌** → "Eighteen Dragon-Subduing Palms"[1]
2. **九陰真經** → "Nine Yin Manual"[1]
3. **北冥神功** → "Northern Darkness Divine Skill"[1]
4. **獨孤九劍** → "Nine Swords of Dugu"[1]
5. **易筋經** → "Muscle-Tendon Transformation Classic"[1]
6. **六脈神劍** → "Six Meridians Divine Sword"[1]
7. **葵花寶典** → "Sunflower Manual"[1]
8. **吸星大法** → "Star-Absorbing Great Method"[1]

### 3. Documentation Files

- **WUXIA_GLOSSARY_UPDATE_SUMMARY.md** - Comprehensive documentation of changes
- **WUXIA_TRANSLATION_EXAMPLES.md** - Six detailed translation examples
- **TECHNIQUE_TRANSLATION_QUICK_REFERENCE.md** - One-page quick reference guide

---

## Impact on Translation

### Before Update:
- All techniques treated uniformly (mostly PINYIN_ONLY)
- Named techniques buried in pinyin
- Example: "He executed *Jiàng Lóng Shíbā Zhǎng* with his *zhǎngfǎ*"

### After Update:
- Clear distinction between categories and proper nouns
- Named techniques have narrative weight in English
- Example: "He executed the Eighteen Dragon-Subduing Palms with his *zhǎngfǎ*"

---

## Translation Philosophy

### Technique Categories (PINYIN):
- Abstract concepts (*nèigōng*, *qīnggōng*, *jiànfǎ*)
- Build consistent technical vocabulary
- Reader learns martial arts terminology through repetition

### Named Techniques (ENGLISH):
- Specific proper nouns with poetic names
- "Eighteen Dragon-Subduing Palms" more readable than "*Jiàng Lóng Shíbā Zhǎng*"
- Footnotes preserve cultural context with pinyin and historical details

---

## Editorial Validation

AI Editor now checks:
1. Technique categories use pinyin (*zhǎngfǎ*, *jiànfǎ*)
2. Named techniques use English ("Eighteen Dragon-Subduing Palms")
3. Pinyin standardization matches glossary
4. Footnotes follow template format

---

## Version History

- **v1.0** (2025-11-13): Initial implementation of technique class vs. named technique distinction
