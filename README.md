# ⭐ MathMastery Hub

A simple practice app that helps a child prepare for the NSW Selective School test by learning from their mistakes. Wrong questions come back at growing intervals until they stick.

## Features

- **Today's practice**: one button. The app picks the questions: overdue reviews first, then reviews due today, then new questions, up to a daily amount.
- **Answer all, check at the end**: the child answers every question, submits, then sees ✓/✗, the correct answer and an optional explanation.
- **Review schedule**: a correct answer brings the question back after 1 → 3 → 7 → 14 → 30 days, then it's Mastered. A wrong answer brings it back tomorrow.
- **Questions to explain**: questions answered wrong 2+ times after review are flagged for a parent to explain.
- **Pi-Lead import**: pull wrong questions (text, pictures, answers, explanations, topics) from Pi-Lead's notebook.
- **Add Questions page**: drag in screenshots and set the topic, answer and explanation in the app.
- **Free on-device OCR** (macOS): read a screenshot's text so practice shows easy-to-read text, with fractions like 2/5 drawn stacked and a cropped graph placed where `[graph]` is typed.
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

0. **Import from Pi-Lead** (parent): Pi-Lead's notebook does the OCR and AI explanations; MathMastery does the practice.
   - One time: on **➕ Add Questions → Import from Pi-Lead → First time?**, copy the code into a new Chrome bookmark called `Export to MathMastery`.
   - Each time: open your Pi-Lead Notebook in Chrome, click the bookmark, then drop the downloaded `pilead_export_<date>.json` into **Import from Pi-Lead**.
   - Questions already imported keep their practice progress; their text, answer and explanation are refreshed.
   - Command-line alternative: `python pilead_import.py ~/Downloads/pilead_export_<date>.json`
1. **Add questions** (parent): open **➕ Add Questions**, drop in screenshots, choose a topic, type the answer, and press **Save**. Questions without an answer can still be saved; you'll be asked to check the child's answer after practice.
   - Optional: press **🔤 Extract text** to read the question text (free, offline, macOS Vision via `ocrmac`). Fix mistakes before saving: it is what the child reads. OCR can't read stacked fractions or diagrams, so type fractions as `2/5` and, for a graph, attach a cropped screenshot of it and type `[graph]` on its own line where it belongs. Check with **👀 Preview**, and press ⌘+Enter (or click outside the box) to apply your typing.
   - Or tick **Show the full photo in practice** to show the whole photo under the text.
   - A topic that isn't in the list can be added with **➕ New topic** (saved in `categories.json`).
   - Text and graphs can be changed later in **📊 Parent Report → All questions**, which also has a search box.
2. **Practise** (child): on **🏠 Today**, press **Start today's practice**, answer every question, then **Submit answers**.
3. **Check progress** (parent): open **📊 Parent Report**. The daily question count is set at the bottom of that page.

Settings such as the student name, test date and review intervals are at the top of `practice.py`.

Bulk import from folders is still possible with `python import_new.py`.

## File Structure

```
/MathMastery
├── practice.py         # The Streamlit app
├── import_new.py       # Optional bulk import from folders
├── pilead_import.py    # Imports a Pi-Lead notebook export
├── ocr.py              # Free on-device text recognition (macOS)
├── tools/
│   ├── pilead_export.js      # Export script run in the Pi-Lead tab (bookmark)
│   └── make_bookmarklet.py   # Builds the bookmark code from it
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
