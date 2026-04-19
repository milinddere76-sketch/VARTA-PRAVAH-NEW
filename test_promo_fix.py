#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.create_premium_promo import create_premium_promo

# Test the promo generation with the fixed audio filter
result = create_premium_promo()
if result:
    print("\n✅ Promo generation successful! FFmpeg audio filter syntax is correct.")
else:
    print("\n❌ Promo generation failed. Check FFmpeg output above.")
