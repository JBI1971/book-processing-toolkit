#!/bin/bash

# Test script to verify translation API is working correctly

echo "Testing Translation API..."
echo ""

# Test 1: Book title translation
echo "Test 1: Translating book title '射鵰英雄傳'"
curl -s -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "射鵰英雄傳", "source_lang": "zh", "target_lang": "en"}' | python3 -m json.tool

echo ""
echo "---"
echo ""

# Test 2: Author name translation
echo "Test 2: Translating author name '金庸'"
curl -s -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "金庸", "source_lang": "zh", "target_lang": "en"}' | python3 -m json.tool

echo ""
echo "---"
echo ""

# Test 3: Chapter title translation
echo "Test 3: Translating chapter title '第一回　風雪驚變'"
curl -s -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "第一回　風雪驚變", "source_lang": "zh", "target_lang": "en"}' | python3 -m json.tool

echo ""
echo "---"
echo ""

echo "Translation tests complete!"
echo ""
echo "To run these tests, the backend must be running on http://localhost:8000"
