@echo off
cd c:\VARTAPRAVAH
git add .
git commit -m "Fix YouTube streaming and FFmpeg promo generation issues

- Fixed root Dockerfile: replaced Alpine placeholder with proper Python backend build
  - Now builds FastAPI app from backend/ with all dependencies (ffmpeg, fonts, etc)
  - Ensures Uvicorn runs on 0.0.0.0:8000 by default

- Fixed FFmpeg filter expressions in create_premium_promo.py:
  - Added eval=frame for animated scale expressions in filter_complex
  - Allows frame-by-frame evaluation of sin() functions for breathing logo effect
  - Fixed both normal and emergency mode filter chains

- Standardized Marathi language to professional terminology:
  - Replaced informal transliterations: लोकल→स्थानिक, टेस्टिंग→चाचणी
  - Updated anchor/correspondent terminology: संवाददाता with proper gender forms
    - Female: तुमची संवाददाता (तुम्ची = your, feminine)
    - Male: तुमचा संवाददाता (तुम्चा = your, masculine)
  - Fixed brand name spacing: वार्ताप्रवाह → वार्ता प्रवाह throughout codebase
  
- Enhanced streamer.py for YouTube stability:
  - Added stderr logging threads for FFmpeg processes (MAIN-STREAM, PUMPER)
  - Fixed Marathi ticker text capitalization
  - Improved FFmpeg process supervision and error visibility

- Updated streaming_engine/activities.py:
  - Corrected Marathi brand name spacing in all text strings
  - Maintained professional news terminology"
git push origin main
echo Push completed!
