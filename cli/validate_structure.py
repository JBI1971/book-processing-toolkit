#!/usr/bin/env python3
"""
CLI wrapper for structure_validator.py
"""
import sys


from processors.structure_validator import main

if __name__ == "__main__":
    sys.exit(main())
