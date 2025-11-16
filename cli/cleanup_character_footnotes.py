#!/usr/bin/env python3
"""
CLI wrapper for character footnote cleanup utility.

Usage:
    python cli/cleanup_character_footnotes.py --input file.json
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.cleanup_character_footnotes import main

if __name__ == "__main__":
    sys.exit(main())
