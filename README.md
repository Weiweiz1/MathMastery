# Mistake Mastery Engine

A local Python application to help children practice primary school math by learning from their mistakes. Built for NSW OC and selective placement preparation.

## Features

- **Image-based questions**: Upload screenshots of math problems
- **Practice Mode**: Quiz with score tracking
- **Learning Mode**: Kid answers first, parent verifies and saves correct answers
- **Topic filtering**: Organize questions by topic/source
- **Progress tracking**: Track correct/incorrect attempts per question
- **Text-only mode**: Hide images for clean retakes (no spoilers)

## Screenshot

The app has 3 tabs:
1. **Add Questions** - Upload images and enter answers
2. **Manage** - Edit questions, answers, and topics
3. **Practice** - Quiz mode with score tracking

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/MathMastery.git
cd MathMastery

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Usage

### Adding Questions
1. Go to **Add Questions** tab
2. Drag & drop screenshot images
3. Enter correct answer (required)
4. Optionally add question text and topic
5. Click **Save All**

### Learning Mode (New Questions)
1. Go to **Practice** tab
2. Select **"Learning (no answers yet)"**
3. Kid types their answer
4. Parent clicks:
   - ✅ **Kid is CORRECT** - saves kid's answer
   - ❌ **Kid is WRONG** - parent enters correct answer

### Practice Mode
1. Go to **Practice** tab
2. Select **"Practice (has answers)"**
3. Kid answers questions
4. App checks against saved answers

## File Structure

```
/MathMastery
├── app.py              # Streamlit UI
├── mistakes_db.json    # Question database (gitignored)
├── vault/              # Stored images (gitignored)
├── inbox/              # Drop new images here (gitignored)
└── requirements.txt    # Python dependencies
```

## Tech Stack

- **UI**: Streamlit
- **Database**: Local JSON
- **Language**: Python 3

## License

MIT
