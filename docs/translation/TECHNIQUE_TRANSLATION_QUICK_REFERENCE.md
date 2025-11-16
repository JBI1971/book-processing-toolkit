# Technique Translation Quick Reference

## One-Page Guide for AI Translation Service

---

## PINYIN_ONLY (Technique Categories)

Use italicized pinyin with footnote on first occurrence only.

### Internal Arts & Energy
- *nèigōng* (內功) - internal cultivation
- *wàigōng* (外功) - external skill
- *nèilì* (內力) - internal force
- *qì* (氣) - vital energy
- *zhēnqì* (真氣) - true qi

### Movement Arts
- *qīnggōng* (輕功) - lightness skill
- *shēnfǎ* (身法) - body movement
- *bùfǎ* (步法) - footwork

### Unarmed Combat Categories
- *zhǎngfǎ* (掌法) - palm techniques
- *quánfǎ* (拳法) - fist techniques
- *tuǐfǎ* (腿法) - leg techniques
- *zhǐfǎ* (指法) - finger techniques
- *shuāifǎ* (摔法) - throwing techniques
- *qínná* (擒拿) - seizing and grappling
- *diǎnxué* (點穴) - acupoint sealing
- *jiěxué* (解穴) - unsealing points

### Weapon Arts Categories
- *jiànfǎ* (劍法) - swordsmanship
- *dāofǎ* (刀法) - sabre techniques
- *qiāngfǎ* (槍法) - spear techniques
- *gùnfǎ* (棍法) - staff techniques
- *biānfǎ* (鞭法) - whip techniques

### Energy Projection
- *ànqì* (暗器) - hidden weapons
- *jiànqì* (劍氣) - sword qi
- *dāoqì* (刀氣) - blade qi
- *zhǎngfēng* (掌風) - palm wind

---

## ENGLISH_ONLY (Named Techniques)

Use English translation with [footnote marker], include pinyin in footnote.

### Famous Palm Techniques
- "Eighteen Dragon-Subduing Palms"[1] (降龍十八掌 *Jiàng Lóng Shíbā Zhǎng*)

### Legendary Manuals/Texts
- "Nine Yin Manual"[1] (九陰真經 *Jiǔ Yīn Zhēnjīng*)
- "Muscle-Tendon Transformation Classic"[1] (易筋經 *Yìjīn Jīng*)
- "Sunflower Manual"[1] (葵花寶典 *Kuíhuā Bǎodiǎn*)

### Footwork/Movement Techniques
- "Wave-Striding Steps"[1] (凌波微步 *Língbō Wēibù*)

### Internal Skills
- "Northern Darkness Divine Skill"[1] (北冥神功 *Běimíng Shéngōng*)
- "Star-Absorbing Great Method"[1] (吸星大法 *Xī Xīng Dà Fǎ*)

### Sword Techniques
- "Nine Swords of Dugu"[1] (獨孤九劍 *Dúgū Jiǔ Jiàn*)
- "Six Meridians Divine Sword"[1] (六脈神劍 *Liù Mài Shén Jiàn*)

### Body Protection
- "Iron Cloth Shirt"[1] (鐵布衫 *Tiěbùshān*)
- "Golden Bell Cover"[1] (金鐘罩 *Jīnzhōngzhào*)

---

## Decision Tree

```
Is this term a martial arts technique?
│
├─ YES → Is it a category or a specific technique?
│        │
│        ├─ CATEGORY (abstract/general)
│        │   Examples: "palm techniques", "swordsmanship", "lightness skill"
│        │   → Use PINYIN: *zhǎngfǎ*, *jiànfǎ*, *qīnggōng*
│        │   → Footnote on first occurrence only
│        │
│        └─ SPECIFIC TECHNIQUE (proper noun)
│            Examples: "Eighteen Dragon-Subduing Palms", "Nine Yin Manual"
│            → Use ENGLISH: "Technique Name"[1]
│            → Include pinyin in footnote
│            → Footnote on first occurrence only
│
└─ NO → Follow general translation guidelines
```

---

## Footnote Templates

### For Technique Categories (Pinyin):
```
[Category name] ([characters] *pinyin*): [Definition and cultural context].
```

Example:
```
Swordsmanship (劍法 *jiànfǎ*): The scholarly and elegant weapon system associated with literati and nobility.
```

### For Named Techniques (English):
```
[English Name] ([characters] *Pinyin*): [Origin/source]. [Description]. [Historical/cultural context]. [Technical details].
```

Example:
```
Eighteen Dragon-Subduing Palms (降龍十八掌 *Jiàng Lóng Shíbā Zhǎng*): A legendary palm technique from Jin Yong's novels, consisting of eighteen powerful strikes each named after concepts from the *Yìjīng* (易經 Book of Changes). Associated with heroic characters, particularly in *The Legend of the Condor Heroes* and *Demi-Gods and Semi-Devils*. Each palm strike channels *nèilì* with devastating yang force.
```

---

## Usage in Sentences

### Good Balance:
> "He drew upon his *nèigōng* and executed the Eighteen Dragon-Subduing Palms, each strike channeling devastating *nèilì*."

**Why it works**:
- Abstract categories in pinyin (*nèigōng*, *nèilì*)
- Specific technique in English (Eighteen Dragon-Subduing Palms)
- Natural reading flow

### Too Much Pinyin:
> "He drew upon his *nèigōng* and executed *Jiàng Lóng Shíbā Zhǎng*, each strike channeling devastating *nèilì*."

**Problem**: Reader must mentally translate the technique name

### Too Much English:
> "He drew upon his internal cultivation and executed the Eighteen Dragon-Subduing Palms, each strike channeling devastating internal force."

**Problem**: Loses technical martial arts vocabulary

---

## Common Patterns

### Training Description:
- Categories in pinyin: "He practiced *zhǎngfǎ* and *jiànfǎ* daily."
- Named techniques in English: "He finally mastered the Golden Bell Cover."

### Combat Scene:
- Categories in pinyin: "His *jiànqì* flashed, his *qīnggōng* was supreme."
- Named techniques in English: "He countered with the Nine Swords of Dugu."

### Knowledge Transfer:
- Categories in pinyin: "This sect teaches *nèigōng* and *diǎnxué*."
- Named texts in English: "Their treasure is the Nine Yin Manual."

---

## Red Flags

### Wrong: Mixing strategies for same term
- "He studied *jiànfǎ* (swordsmanship) in chapter 1"
- "His swordsmanship (*jiànfǎ*) improved in chapter 2"

### Right: Consistent strategy per term
- "He studied *jiànfǎ* in chapter 1"
- "His *jiànfǎ* improved in chapter 2"

### Wrong: Translating technique categories
- "He practiced palm techniques and fist techniques"

### Right: Using pinyin for categories
- "He practiced *zhǎngfǎ* and *quánfǎ*"

---

## File Locations

- **Main Glossary**: `/wuxia_translation_glossary.csv`
- **Additional Named Techniques**: `/wuxia_translation_glossary_additions.csv`
- **Full Documentation**: `/WUXIA_GLOSSARY_UPDATE_SUMMARY.md`
- **Examples**: `/WUXIA_TRANSLATION_EXAMPLES.md`

---

## For AI Translation Service

1. Load both CSV files into memory
2. Create lookup tables:
   - `technique_categories` → PINYIN_ONLY
   - `technique_named` → ENGLISH_ONLY
3. Track footnote usage per `content_text_id`
4. Only footnote on first occurrence
5. Use consistent pinyin romanization for deduplication
6. Validate footnote format in editorial pass
