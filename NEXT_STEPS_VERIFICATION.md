# Next Steps: Verifying the Footnote Classifier Fix

## Current Status

✅ **Fixed**: The OpenAI response parsing bug in `utils/cleanup_character_footnotes_standalone.py`

⚠️ **Blocked**: Cannot test due to invalid OPENAI_API_KEY

## What Was Fixed

The script was defaulting ALL footnotes to `CULTURAL` classification because:
- It only checked 2 possible JSON keys in the OpenAI response
- When neither key existed, it returned an empty list
- This caused all footnotes to fall through to the fallback handler

**Fix applied**: Enhanced parsing to check 5+ possible keys and added comprehensive debug logging.

See `FOOTNOTE_FIX_CODE_DIFF.md` for detailed code changes.

## Before You Can Test

### 1. Update OpenAI API Key

The current key is invalid:
```
Error code: 401 - Incorrect API key provided: sk-90vP7***************************************FwLZ
```

**Options:**

**Option A: Update env_creds.yml**
```bash
# Edit the file
nano ~/Dev/pycharm/env.yml
# or wherever your env_creds.yml is located

# Update the OPENAI_API_KEY line with a valid key
OPENAI_API_KEY: sk-proj-XXXXXXXXXXXXX
```

**Option B: Set environment variable**
```bash
export OPENAI_API_KEY="sk-proj-XXXXXXXXXXXXX"
```

**Option C: Create project-local env_creds.yml**
```bash
cd /Users/jacki/PycharmProjects/agentic_test_project

cat > env_creds.yml << 'EOF'
OPENAI_API_KEY: sk-proj-XXXXXXXXXXXXX
EOF
```

### 2. Verify API Key Works

```bash
python utils/load_env_creds.py
# Should output:
# ✓ Loaded N credentials
# ✓ OpenAI API key verified successfully
```

## Testing the Fix

### Phase 1: Small Sample Test (10 footnotes)

This verifies the parsing fix works correctly.

```bash
# Run on test file
python utils/cleanup_character_footnotes_standalone.py \
  --input test_footnotes_sample.json \
  --output test_footnotes_cleaned.json \
  --dry-run
```

**Expected Output:**
```
Total footnotes:           10
Internal refs stripped:    0
Fictional characters:      2    ← Should be 2 (張三, 李四)
Historical figures:        1    ← Should be 1 (孔子)
Legendary personages:      2    ← Should be 2 (關羽, 玉皇大帝)
Cultural notes:            5    ← Should be 5 (chapter markers, concepts)
Removed:                   2    ← Only fictional characters removed
Preserved:                 8
```

**What to Look For:**

1. **Response key detection** (should appear in logs):
   ```
   OpenAI response keys: ['classifications']
   Found results array under key 'classifications' with 10 items
   ```

2. **Per-footnote classification** (first 5 logged):
   ```
   Footnote 1/10: '第一回' -> CULTURAL (confidence: 0.95)
   Footnote 2/10: '古怪離奇的考試' -> CULTURAL (confidence: 0.90)
   Footnote 3/10: '死' -> CULTURAL (confidence: 0.93)
   Footnote 4/10: '償命' -> CULTURAL (confidence: 0.92)
   Footnote 5/10: '劍戟' -> CULTURAL (confidence: 0.94)
   ```

3. **Debug file created**:
   ```bash
   ls -la debug_openai_response.json
   cat debug_openai_response.json | head -20
   ```

4. **No fallback warnings**:
   ```
   # Should NOT see this:
   Missing classification for footnote N, defaulting to CULTURAL
   ```

### Phase 2: Inspect Classifications

```bash
# Check the debug response file
cat debug_openai_response.json

# Should look like:
# {
#   "classifications": [
#     {
#       "type": "CULTURAL",
#       "confidence": 0.95,
#       "reasoning": "Chapter marker..."
#     },
#     {
#       "type": "FICTIONAL_CHARACTER",
#       "confidence": 0.90,
#       "reasoning": "Story protagonist..."
#     },
#     ...
#   ]
# }
```

### Phase 3: Run on Real Data (First 20 Footnotes)

After verifying the test file works:

```bash
# Create a small subset of the real data
python << 'EOF'
import json
from pathlib import Path

# Load the real file
input_file = Path("/Users/jacki/project_files/translation_project/羅剎夫人/I0929_english_translated.json")
with open(input_file) as f:
    data = json.load(f)

# Extract only first chapter
chapters = data['structure']['body']['chapters']
data['structure']['body']['chapters'] = chapters[:1]

# Save subset
output_file = Path("real_data_subset.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Created {output_file}")
EOF

# Run on subset
python utils/cleanup_character_footnotes_standalone.py \
  --input real_data_subset.json \
  --output real_data_subset_cleaned.json \
  --dry-run
```

**Look for:**
- Classification diversity (not all CULTURAL)
- Reasonable confidence scores (0.7+)
- Sensible reasoning in debug file

### Phase 4: Full Processing

Only after phases 1-3 succeed:

```bash
# Process the full file
python utils/cleanup_character_footnotes_standalone.py \
  --input /Users/jacki/project_files/translation_project/羅剎夫人/I0929_english_translated.json \
  --output /Users/jacki/project_files/translation_project/羅剎夫人/I0929_character_footnotes_cleaned.json \
  --log-dir ./logs

# Check results
cat logs/I0929_english_translated_character_cleanup_log.json | jq '.summary'
```

**Expected Results** (based on the original 3,876 footnotes):
- Some FICTIONAL_CHARACTER classifications (not 0)
- Some HISTORICAL_FIGURE classifications (not 0)
- Some LEGENDARY_PERSONAGE classifications (not 0)
- CULTURAL should be the majority, but NOT 100%

## Troubleshooting

### Issue: Still All CULTURAL

**Check:**
1. `debug_openai_response.json` exists and has data
2. Response has expected structure
3. Log shows "Found results array under key 'X'"

**If response structure is different than expected:**
```bash
# Inspect the response file
cat debug_openai_response.json | jq '.'

# Look for where the array actually is
# Update the key list in the script if needed
```

### Issue: Count Mismatch Warning

```
Result count mismatch: expected 25 classifications, got 20
```

**This means:**
- OpenAI returned fewer results than requested
- Possible rate limiting or token limits
- Try reducing `--batch-size` to 10 or 15

### Issue: JSON Decode Error

```
Failed to parse OpenAI response: Expecting value: line 1 column 1 (char 0)
```

**This means:**
- OpenAI returned non-JSON response
- Possible API error or rate limit
- Check `result_text` in debug output

## Success Criteria

✅ Test file shows diverse classifications (not all CULTURAL)
✅ Fictional characters identified and removed
✅ Historical figures preserved
✅ Cultural notes preserved
✅ Debug file shows proper response structure
✅ No fallback warnings in logs
✅ Classification reasoning makes sense

## Files to Review

1. **debug_openai_response.json** - First API response structure
2. **logs/{filename}_character_cleanup_log.json** - Detailed results
3. **test_footnotes_cleaned.json** - Output file (if not dry-run)

## Contact/Support

If issues persist after following these steps:
1. Share `debug_openai_response.json` for response structure analysis
2. Share relevant log excerpts showing the error
3. Confirm OpenAI API key is valid and has credits

## Files Created for Testing

- `test_footnotes_sample.json` - 10 diverse test footnotes
- `test_openai_response.py` - Diagnostic script
- `FOOTNOTE_CLASSIFIER_FIX_REPORT.md` - Detailed fix report
- `FOOTNOTE_FIX_CODE_DIFF.md` - Code changes
- `NEXT_STEPS_VERIFICATION.md` - This file
