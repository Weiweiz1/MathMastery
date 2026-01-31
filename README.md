# ✨ Math and Thinking Skills Engine

A simple, fast practice app to help children prepare for NSW OC and Selective School tests by learning from their mistakes.

## Features

- **OC Test Countdown** - Shows days remaining until test day
- **Image-based questions** - Upload screenshots of wrong answers
- **Learning Mode** - Kid answers first, parent verifies and saves correct answer
- **Practice Mode** - Quiz against saved answers
- **Topic filtering** - Organize by test/source
- **Fast navigation** - Jump to any question instantly

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Weiweiz1/MathMastery.git
cd MathMastery

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run practice.py
```

Then open **http://localhost:8501**

## How to Use

### Adding Questions
Drop screenshot images into the `inbox/` folder, then run:
```python
# Quick import script (run in Python)
import json, os, shutil, hashlib
from datetime import datetime

# ... (see repo for full import script)
```

Or contact me for the import helper.

### Learning Mode (New Questions)
1. Select **"Learning (no answer)"** in sidebar
2. Kid types their answer
3. Parent clicks:
   - **✅ Correct** - saves kid's answer as correct
   - **💾 Save** - enter and save the correct answer

### Practice Mode
1. Select **"Practice (has answer)"** in sidebar
2. Kid answers questions
3. Click **Check** to verify

## File Structure

```
/MathMastery
├── practice.py         # Main Streamlit app
├── requirements.txt    # Python dependencies
├── mistakes_db.json    # Question database (gitignored)
├── vault/              # Stored images (gitignored)
└── inbox/              # Drop new images here (gitignored)
```

## Tech Stack

- **UI**: Streamlit
- **Database**: Local JSON
- **Language**: Python 3

## License

MIT
