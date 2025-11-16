#!/usr/bin/env python3
"""
CLI for JSON Cleaner

Clean raw book JSON into structured format with discrete content blocks.
"""

import sys

from processors.json_cleaner import main

if __name__ == "__main__":
    sys.exit(main())
