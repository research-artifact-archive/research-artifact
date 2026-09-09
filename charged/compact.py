#!/usr/bin/env python3
"""Compile/check/query the charged game with the proved compact specialization."""
from pathlib import Path
import sys
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
sys.path.insert(0,str(Path(__file__).resolve().parent/'evidence/RESUMED_20260909_0056/charged_compact_03'))
from cli import main
if __name__=='__main__':main()
