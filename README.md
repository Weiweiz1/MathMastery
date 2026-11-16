# ⭐ MathMastery Hub

A simple practice app that helps a child prepare for the NSW Selective School test by learning from their mistakes. Wrong questions come back at growing intervals until they stick.

## Features

- **Today's practice**: one button. The app picks the questions: overdue reviews first, then reviews due today, then new questions, up to a daily amount.
- **Answer all, check at the end**: the child answers every question, submits, then sees ✓/✗, the correct answer and an optional explanation.
- **Review schedule**: a correct answer brings the question back after 1 → 3 → 7 → 14 → 30 days, then it's Mastered. A wrong answer brings it back tomorrow.
- **Questions to explain**: questions answered wrong 2+ times after review are flagged for a parent to explain.
- **Add Questions page**: drag in screenshots and set the topic, answer and explanation in the app.
- **Parent Report**: % mastered, days practised, reviews due, top 3 weak topics by miss rate, "what to do next" advice, and the full question list for editing.
- **Selective test countdown** (7 May 2028).

## Quick Start

```bash
git clone https://github.com/Weiweiz1/MathMastery.git
cd MathMastery
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run practice.py
```

Then open **http://localhost:8501**.

## Daily Start

```bash
cd /Users/WZ/Documents/Projects/MathMastery
source venv/bin/activate
streamlit run practice.py
```

## How to Use

1. **Add questions** (parent): open **➕ Add Questions**, drop in screenshots, choose a topic, type the answer, and press **Save**. Questions without an answer can still be saved; you'll be asked to check the child's answer after practice.
2. **Practise** (child): on **🏠 Today**, press **Start today's practice**, answer every question, then **Submit answers**.
3. **Check progress** (parent): open **📊 Parent Report**. The daily question count is set at the bottom of that page.

Settings such as the student name, test date and review intervals are at the top of `practice.py`.

Bulk import from folders is still possible with `python import_new.py`.

## File Structure

```
/MathMastery
├── practice.py         # The Streamlit app
├── import_new.py       # Optional bulk import from folders
├── requirements.txt    # Python dependencies
├── mistakes_db.json    # Questions and review schedule (gitignored)
├── practice_log.json   # Every answer: date, question, right/wrong (gitignored)
├── settings.json       # Questions per day (gitignored)
├── vault/              # Stored question images (gitignored)
└── inbox/              # Imported source images (gitignored)
```

## Tech Stack

- **UI**: Streamlit
- **Database**: Local JSON
- **Language**: Python 3

## License

MIT
