import streamlit as st
import json
import os
import html
import hashlib
import re
from datetime import datetime, date, timedelta
from pilead_import import import_export
from tools.make_bookmarklet import bookmarklet

st.set_page_config(page_title="MathMastery Hub", page_icon="⭐", layout="wide", initial_sidebar_state="expanded")

# === CONFIG ===
DB_FILE = "mistakes_db.json"
LOG_FILE = "practice_log.json"       # one row per answered question: date, id, correct
SETTINGS_FILE = "settings.json"
VAULT_DIR = "vault"
SELECTIVE_TEST_DATE = date(2028, 5, 7)
STUDENT_NAME = "Isabella"
DEFAULT_DAILY = 15
# Days until the next review after each correct answer. Correct after the last one = Mastered.
REVIEW_INTERVALS = [1, 3, 7, 14, 30]
EXPLAIN_AFTER = 2                    # wrong this many times after reviewing -> parent should explain

TOPIC_CATEGORIES = [
    "Numbers and Calculation",
    "Factors, Multiples and Remainders",
    "Patterns",
    "Areas and Volume",
    "Time, Distance and Speed",
    "Rate and Percentage",
    "Graph, Geometry and Spatial",
    "Temperature, Mass and Length",
    "Problem Solving",
]


# === STORAGE ===
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def find(db, q_id):
    return next((q for q in db if q['id'] == q_id), None)


# === REVIEW LOGIC ===
TODAY = date.today()


def norm(answer):
    return " ".join(str(answer).lower().strip().rstrip('.').split())


def state(q):
    """New -> Learning -> Mastered. The only states anyone sees."""
    if q.get('status') == 'mastered':
        return 'mastered'
    if q.get('times_practiced', 0) == 0:
        return 'new'
    return 'learning'


def due_date(q):
    if q.get('next_review'):
        return date.fromisoformat(q['next_review'])
    # Practised before review dates existed: review it now
    return TODAY if q.get('times_practiced', 0) > 0 else None


def is_due(q):
    """New questions, and learning questions whose review date has arrived."""
    if state(q) == 'new':
        return True
    d = due_date(q)
    return state(q) == 'learning' and d is not None and d <= TODAY


def needs_explaining(q):
    return state(q) == 'learning' and q.get('wrong_after_review', 0) >= EXPLAIN_AFTER


def record_answer(q, correct, log):
    """Log the attempt and move the review schedule.
    Right: next review further away (only if it was due, so extra practice can't skip ahead).
    Wrong: back to the start, comes back tomorrow."""
    log.append({"date": TODAY.isoformat(), "id": q['id'], "correct": correct})
    if correct and not is_due(q):
        return
    q['times_practiced'] = q.get('times_practiced', 0) + 1
    q['last_practiced'] = TODAY.isoformat()
    stage = q.get('stage', 0)
    if correct:
        q['times_correct'] = q.get('times_correct', 0) + 1
        if stage >= len(REVIEW_INTERVALS):
            q['status'] = 'mastered'
            q['mastered_on'] = TODAY.isoformat()
            q.pop('next_review', None)
        else:
            q['next_review'] = (TODAY + timedelta(days=REVIEW_INTERVALS[stage])).isoformat()
            q['stage'] = stage + 1
    else:
        if stage > 0:
            q['wrong_after_review'] = q.get('wrong_after_review', 0) + 1
        q['stage'] = 0
        q['next_review'] = (TODAY + timedelta(days=1)).isoformat()


def todays_queue(active):
    """Due reviews first (most overdue first), then new questions."""
    due = [q for q in active if state(q) == 'learning' and is_due(q)]
    due.sort(key=lambda q: (due_date(q), -q.get('wrong_after_review', 0)))
    new = sorted((q for q in active if state(q) == 'new'), key=lambda q: q.get('created', ''))
    return due, new


def streak(log):
    days = {r['date'] for r in log}
    d = TODAY if TODAY.isoformat() in days else TODAY - timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= timedelta(days=1)
    return n


def topic_miss_rates(db, log, days=30):
    """[(topic, miss_rate, wrong, attempts)] over the last `days`, worst first."""
    since = (TODAY - timedelta(days=days)).isoformat()
    topic_of = {q['id']: q.get('topic', '') or 'Uncategorized' for q in db}
    stats = {}
    for r in log:
        if r['date'] >= since and r['id'] in topic_of:
            s = stats.setdefault(topic_of[r['id']], [0, 0])
            s[0] += 1
            s[1] += 0 if r['correct'] else 1
    ranked = [(t, w / a, w, a) for t, (a, w) in stats.items() if w > 0]
    ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return ranked


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def start_practice(questions):
    st.session_state.quiz_ids = [q['id'] for q in questions if q]
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = {}
    st.session_state.quiz_token = datetime.now().strftime("%H%M%S%f")
    st.session_state.mode = 'quiz'
    st.rerun()


IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")


def md_math(text):
    """Pi-Lead writes maths with backslash-bracket or dollar delimiters, and '$' also means money.
    Convert maths to Streamlit's $...$ and escape dollar signs used for money."""
    text = re.sub(r"\\\[(.+?)\\\]", lambda m: "$$" + m.group(1) + "$$", text, flags=re.S)
    text = re.sub(r"\\\((.+?)\\\)", lambda m: "\x00" + m.group(1) + "\x00", text, flags=re.S)

    # Pair up single $ signs in order: a pair wrapping LaTeX is maths, anything else is money
    signs = [m.start() for m in re.finditer(r"(?<![\\$])\$(?!\$)", text)]
    money, i = set(), 0
    while i < len(signs):
        if i + 1 < len(signs) and re.search(r"[\\^_{}]", text[signs[i] + 1:signs[i + 1]]):
            i += 2
        else:
            money.add(signs[i])
            i += 1
    text = "".join("\\$" if k in money else c for k, c in enumerate(text))
    text = text.replace("\x00", "$")
    return re.sub(r"\\frac(?=\s*\{)", r"\\dfrac", text)  # full-size fractions are easier to read


TABLE_GAP_RE = re.compile(r"(^\s*\|[^\n]*\|\s*)\n\s*\n(?=\s*\|)", re.M)


def render_md(text):
    """Markdown with maths; pictures saved in vault/ are shown with st.image."""
    # Pi-Lead puts blank lines between table rows, which breaks markdown tables
    prev = None
    while prev != text:
        prev, text = text, TABLE_GAP_RE.sub(r"\1\n", text or "")
    pos = 0
    for m in IMG_RE.finditer(text or ""):
        chunk = text[pos:m.start()].strip()
        if chunk:
            st.markdown(md_math(chunk))
        if os.path.exists(m.group(1)):
            st.image(m.group(1))
        pos = m.end()
    rest = (text or "")[pos:].strip()
    if rest:
        st.markdown(md_math(rest))


def show_question(q):
    if q.get('file_path') and os.path.exists(q['file_path']):
        st.image(q['file_path'], width="stretch")
    elif q.get('question_md'):
        render_md(q['question_md'])
    else:
        st.error("Question not found")


def show_explanation(q):
    if q.get('explanation'):
        with st.container(border=True):
            st.markdown("**💡 Explanation**")
            render_md(q['explanation'])


def answer_text(q):
    return q.get('answer_display') or q.get('answer', '')


def topic_of(q):
    return q.get('topic', '') or 'Uncategorized'


def topics_in_use(questions):
    """Topics that have questions, most questions first."""
    counts = {}
    for q in questions:
        counts[topic_of(q)] = counts.get(topic_of(q), 0) + 1
    return sorted(counts, key=lambda t: (-counts[t], t)), counts


# === STYLE (modelled on the Pi-Lead hub) ===
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --green: #2f9e5f; --green-dark: #1d6b42; --green-soft: #f2faf5; --green-line: #bfe3cc;
  --blue: #2563eb; --blue-dark: #1e4fae; --blue-soft: #f4f7ff; --blue-line: #c9d8f5;
  --amber-soft: #fff8eb; --amber-line: #f3dcae; --amber: #b45309;
  --red: #dc2626; --ink: #111827; --muted: #6b7280; --line: #e5e7eb;
}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, select, textarea {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.stApp { background: #ffffff; }
#MainMenu, footer, [data-testid="stAppDeployButton"] { display: none; }
.block-container { padding-top: 2.2rem; max-width: 1180px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 10px; margin: 0 0 18px 4px; }
.brand-logo { width: 38px; height: 38px; border-radius: 50%; border: 2px solid var(--green-line);
  display: flex; align-items: center; justify-content: center; font-size: 20px; background: var(--green-soft); }
.brand-name { font-size: 21px; font-weight: 800; color: var(--green-dark); }
.nav-label { font-size: 11px; font-weight: 700; color: var(--muted); letter-spacing: .06em; margin: 14px 0 4px 8px; }
[class*="st-key-nav_"] button {
  justify-content: flex-start; border: none; background: transparent; color: #374151;
  font-weight: 600; padding: 8px 12px; border-radius: 10px; box-shadow: none;
}
[class*="st-key-nav_"] button > div, [class*="st-key-nav_"] button p {
  justify-content: flex-start; text-align: left; width: 100%; font-size: 15px; }
[class*="st-key-nav_"] button:hover { background: var(--green-soft); color: var(--green-dark); }
.st-key-topnav { gap: 8px; margin: -6px 0 14px; }
.st-key-topnav button { border-radius: 999px; padding: 4px 16px; font-weight: 600; border: 1px solid var(--line); }
.st-key-topnav button[kind="primary"] { background: var(--green); border-color: var(--green); color: #fff; }
.st-key-topnav button[kind="secondary"]:hover { border-color: var(--green); color: var(--green-dark); }
.week-card { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; margin-top: 24px; }
.week-title { font-weight: 700; color: var(--green-dark); font-size: 14px; margin-bottom: 8px; }
.week-row { display: flex; justify-content: space-between; font-size: 13px; color: #374151; margin: 6px 0; }
.week-row b { color: var(--green-dark); }
.week-bar { height: 6px; background: #edf0f2; border-radius: 4px; overflow: hidden; }
.week-bar > div { height: 100%; background: var(--green); border-radius: 4px; }

/* Header */
.hub-header { display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 18px; flex-wrap: wrap; gap: 10px; }
.hub-title { font-size: 24px; font-weight: 800; color: var(--ink); }
.hub-sub { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 13px; margin-top: 4px; flex-wrap: wrap; }
.pill { border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; color: #374151; font-weight: 600; font-size: 12px; }
.pill .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--green); margin-right: 6px; }
.head-right { display: flex; align-items: center; gap: 10px; }
.avatar { width: 40px; height: 40px; border-radius: 50%; background: #d9f2ea; color: var(--green-dark);
  display: flex; align-items: center; justify-content: center; font-weight: 700; }

/* Strip */
.strip { display: flex; align-items: center; gap: 22px; border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 16px; margin-bottom: 16px; flex-wrap: wrap; }
.strip-sec { display: flex; align-items: center; gap: 10px; }
.strip-sec.grow { flex: 1; border-left: 1px solid var(--line); padding-left: 18px; }
.strip-sec.end { border-left: 1px solid var(--line); padding-left: 18px; }
.ico { width: 34px; height: 34px; border-radius: 9px; background: #f3f4f6; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.ico.amber { background: #fdefd3; }
.strip-big { font-weight: 700; font-size: 16px; color: var(--ink); line-height: 1.2; }
.strip-small { font-size: 13px; color: var(--muted); }
.strip-label { font-size: 12px; font-weight: 700; color: #374151; margin-bottom: 4px; }
.tag { display: inline-block; border-radius: 6px; padding: 2px 8px; font-size: 12px; font-weight: 600; margin: 2px 4px 2px 0; border: 1px solid; }
.tag.g { background: var(--green-soft); border-color: var(--green-line); color: var(--green-dark); }
.tag.b { background: var(--blue-soft); border-color: var(--blue-line); color: var(--blue-dark); }
.tag.a { background: var(--amber-soft); border-color: var(--amber-line); color: var(--amber); }
.amber-title { color: var(--amber); font-weight: 700; }

/* Cards */
.st-key-card_today { background: linear-gradient(135deg, #ffffff 40%, var(--green-soft));
  border: 1px solid var(--green-line); border-radius: 14px; padding: 20px 22px 18px; }
.st-key-card_topic { background: linear-gradient(135deg, #ffffff 40%, var(--blue-soft));
  border: 1px solid var(--blue-line); border-radius: 14px; padding: 20px 22px 18px; }
.st-key-card_progress { border: 1px solid var(--line); border-radius: 14px; padding: 18px 22px; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card-title { font-size: 28px; font-weight: 800; margin: 0 0 6px; line-height: 1.15; }
.card-title.g { color: var(--green-dark); } .card-title.b { color: var(--blue-dark); }
.card-desc { color: #374151; font-size: 15px; }
.card-art { font-size: 54px; line-height: 1; opacity: .9; }
.chips { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; border-top: 1px solid var(--line);
  padding-top: 14px; margin: 16px 0 4px; }
.chip { border: 1px solid var(--line); border-radius: 9px; padding: 7px 10px; background: #fff; }
.chip.a { background: var(--amber-soft); border-color: var(--amber-line); }
.chip-top { font-weight: 700; font-size: 13px; color: var(--green-dark); }
.chip.a .chip-top { color: var(--amber); }
.chip-bot { font-size: 12px; color: var(--muted); }
.st-key-card_today button, [class*="st-key-primary_"] button {
  background: var(--green); color: #fff; border: none; font-weight: 700; border-radius: 9px; padding: 10px; }
.st-key-card_topic button {
  background: var(--blue); color: #fff; border: none; font-weight: 700; border-radius: 9px; padding: 10px; }
.st-key-card_today button:hover, [class*="st-key-primary_"] button:hover { background: var(--green-dark); color: #fff; }
.st-key-card_topic button:hover { background: var(--blue-dark); color: #fff; }
.st-key-card_today button:disabled, .st-key-card_topic button:disabled, [class*="st-key-primary_"] button:disabled {
  background: #d1d5db; color: #fff; }
.done-msg { font-size: 16px; font-weight: 700; color: var(--green-dark); margin: 6px 0 10px; }

/* Topic progress */
.tp-title { font-weight: 700; font-size: 16px; color: var(--ink); margin-bottom: 10px; }
.tp-row { display: grid; grid-template-columns: 1fr 120px 54px; align-items: center; gap: 10px; font-size: 13px; margin: 7px 0; color: #374151; }
.tp-row .bar { height: 6px; background: #edf0f2; border-radius: 4px; overflow: hidden; }
.tp-row .bar > div { height: 100%; background: var(--green); }
.tp-row .num { text-align: right; color: var(--muted); }

/* Report */
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px; }
.tile { border: 1px solid var(--line); border-radius: 12px; padding: 14px; text-align: center; }
.tile-label { font-size: 13px; color: var(--muted); }
.tile-num { font-size: 30px; font-weight: 800; color: var(--green-dark); line-height: 1.3; }
.tile-sub { font-size: 12px; color: var(--muted); }
.section-title { font-size: 18px; font-weight: 800; color: var(--ink); margin: 18px 0 8px; }
.focus-row { display: flex; justify-content: space-between; border: 1px solid var(--line); border-radius: 10px;
  padding: 10px 14px; margin-bottom: 8px; font-size: 14px; }
.focus-row .pct { font-weight: 800; color: var(--red); }
.advice { border-left: 4px solid var(--green); background: var(--green-soft); border-radius: 6px;
  padding: 10px 14px; margin-bottom: 8px; font-size: 14px; color: #1f2937; }
.advice.warn { border-color: #f59e0b; background: var(--amber-soft); }

/* Results */
.score { font-size: 30px; font-weight: 800; color: var(--green-dark); }
.res-ok { color: var(--green-dark); font-weight: 800; font-size: 18px; }
.res-bad { color: var(--red); font-weight: 800; font-size: 18px; }
.res-check { color: var(--amber); font-weight: 800; font-size: 18px; }
.explain { background: var(--blue-soft); border: 1px solid var(--blue-line); border-radius: 8px; padding: 8px 12px; font-size: 14px; }

.banner { border: 1px solid var(--green-line); border-radius: 10px; padding: 10px 16px; margin-top: 16px; color: #374151; }
.banner b { color: var(--green-dark); }
.page-title { font-size: 26px; font-weight: 800; color: var(--green-dark); margin: 0 0 4px; }
.page-sub { color: var(--muted); font-size: 14px; margin-bottom: 16px; }
@media (max-width: 800px) { .tiles { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)

# === SESSION STATE ===
for k, v in {'mode': 'today', 'quiz_ids': [], 'quiz_index': 0, 'quiz_answers': {},
             'quiz_token': '', 'results': [], 'uploader_key': 0}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# === DATA ===
db = load_json(DB_FILE, [])
log = load_json(LOG_FILE, [])
settings = load_json(SETTINGS_FILE, {})
daily_target = settings.get('daily', DEFAULT_DAILY)

active = [q for q in db if q.get('status', 'active') == 'active']
mastered = [q for q in db if q.get('status') == 'mastered']
due_reviews, new_qs = todays_queue(active)
done_today = len({r['id'] for r in log if r['date'] == TODAY.isoformat()})
today_set = (due_reviews + new_qs)[:max(0, daily_target - done_today)]
week_start = (TODAY - timedelta(days=TODAY.weekday())).isoformat()
days_this_week = len({r['date'] for r in log if r['date'] >= week_start})
current_streak = streak(log)

# === SIDEBAR ===
NAV = [("today", "🏠  Today", None),
       ("add", "➕  Add Questions", "FOR PARENTS"),
       ("report", "📊  Parent Report", None)]
active_nav = 'today' if st.session_state.mode in ('today', 'quiz', 'results') else st.session_state.mode
st.markdown(f"""<style>.st-key-nav_{active_nav} button {{ background: var(--green) !important; color: #fff !important;
  box-shadow: 0 2px 6px rgba(47,158,95,.3) !important; }}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div class='brand'><div class='brand-logo'>⭐</div><div class='brand-name'>MathMastery Hub</div></div>",
                unsafe_allow_html=True)
    for key, label, section in NAV:
        if section:
            st.markdown(f"<div class='nav-label'>{section}</div>", unsafe_allow_html=True)
        with st.container(key=f"nav_{key}"):
            if st.button(label, key=f"navbtn_{key}", width="stretch"):
                st.session_state.mode = key
                st.rerun()

    pct = min(100, int(done_today / daily_target * 100)) if daily_target else 0
    st.markdown(f"""
    <div class='week-card'>
      <div class='week-title'>This Week</div>
      <div class='week-row'><span>Done today</span><b>{done_today} / {daily_target}</b></div>
      <div class='week-bar'><div style='width:{pct}%'></div></div>
      <div class='week-row'><span>Days practised</span><b>{days_this_week} / 7</b></div>
      <div class='week-row'><span>Streak</span><b>🔥 {plural(current_streak, 'day')}</b></div>
    </div>""", unsafe_allow_html=True)

# === HEADER ===
days_left = (SELECTIVE_TEST_DATE - TODAY).days
countdown = f"<span class='pill'>⏰ <b>{days_left}</b> days to Selective Test</span>" if days_left > 0 else ""
st.markdown(f"""
<div class='hub-header'>
  <div>
    <div class='hub-title'>Welcome back, {html.escape(STUDENT_NAME)}</div>
    <div class='hub-sub'>{TODAY.strftime('%a, %b %-d, %Y')}
      <span class='pill'><span class='dot'></span>Keep going! You are building great habits.</span></div>
  </div>
  <div class='head-right'>{countdown}<div class='avatar'>{html.escape(STUDENT_NAME[:1])}</div></div>
</div>""", unsafe_allow_html=True)

# Same pages along the top, so navigation works even when the sidebar is closed
with st.container(key="topnav", horizontal=True):
    for key, label, _ in NAV:
        if st.button(label, key=f"top_{key}", type="primary" if key == active_nav else "secondary"):
            st.session_state.mode = key
            st.rerun()


# ==================== TODAY ====================
if st.session_state.mode == 'today':
    focus = [t for t, *_ in topic_miss_rates(db, log)[:3]]
    tag_cls = ['g', 'b', 'a']
    focus_html = "".join(f"<span class='tag {tag_cls[i]}'>{html.escape(t)}</span>" for i, t in enumerate(focus)) \
        or "<span class='strip-small'>Shows up after some practice</span>"
    explain_n = sum(1 for q in active if needs_explaining(q))
    st.markdown(f"""
    <div class='strip'>
      <div class='strip-sec'><div class='ico'>📅</div>
        <div><div class='strip-big'>Selective Test</div>
        <div class='strip-small'>{SELECTIVE_TEST_DATE.strftime('%-d %b %Y')} · {max(days_left, 0)} days</div></div></div>
      <div class='strip-sec grow'><div><div class='strip-label'>Focus Topics</div>{focus_html}</div></div>
      <div class='strip-sec end'><div class='ico amber'>🙋</div>
        <div><div class='amber-title'>Ask a parent</div>
        <div class='strip-small'>{plural(explain_n, 'question')} to explain</div></div></div>
    </div>""", unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(key="card_today"):
            n_rev = sum(1 for q in today_set if state(q) == 'learning')
            st.markdown(f"""
            <div class='card-head'><div>
              <div class='card-title g'>Today's Practice</div>
              <div class='card-desc'>Answer every question, then submit. They're all checked at the end.</div>
            </div><div class='card-art'>📚</div></div>
            <div class='chips'>
              <div class='chip'><div class='chip-top'>{plural(n_rev, 'review')}</div><div class='chip-bot'>Coming back today</div></div>
              <div class='chip'><div class='chip-top'>{len(today_set) - n_rev} new</div><div class='chip-bot'>First try</div></div>
              <div class='chip a'><div class='chip-top'>🔥 {plural(current_streak, 'day')}</div><div class='chip-bot'>Streak</div></div>
            </div>""", unsafe_allow_html=True)
            if today_set:
                if st.button(f"▶  Start today's practice ({plural(len(today_set), 'question')})",
                             key="start_today", width="stretch"):
                    start_practice(today_set)
            elif not active:
                st.button("No questions yet. Ask a parent to add some.", key="start_none",
                          width="stretch", disabled=True)
            else:
                st.markdown("<div class='done-msg'>🎉 All done for today!</div>", unsafe_allow_html=True)
                extra = (due_reviews + new_qs)[:5]
                if extra and st.button(f"Practise {len(extra)} more", key="start_extra", width="stretch"):
                    start_practice(extra)

    with right:
        with st.container(key="card_topic"):
            st.markdown("""
            <div class='card-head'><div>
              <div class='card-title b'>Practise a Topic</div>
              <div class='card-desc'>Want extra practice? Pick one topic.</div>
            </div><div class='card-art'>🎯</div></div>""", unsafe_allow_html=True)
            topic_options, topic_counts = topics_in_use(active)
            pick = st.selectbox("Topic", topic_options, label_visibility="collapsed",
                                format_func=lambda t: f"{t} ({topic_counts[t]})", placeholder="No topics yet")
            if st.button("Start topic practice", key="start_topic", width="stretch", disabled=not pick):
                qs = [q for q in active if topic_of(q) == pick]
                qs.sort(key=lambda q: (not is_due(q), q.get('created', '')))
                start_practice(qs[:daily_target])

        with st.container(key="card_progress"):
            rows = []
            for t in topics_in_use(active + mastered)[0][:10]:
                qs = [q for q in active + mastered if topic_of(q) == t]
                m = sum(1 for q in qs if state(q) == 'mastered')
                width = int(m / len(qs) * 100) if qs else 0
                rows.append(f"<div class='tp-row'><span>{html.escape(t)}</span>"
                            f"<div class='bar'><div style='width:{width}%'></div></div>"
                            f"<span class='num'>{m}/{len(qs)}</span></div>")
            st.markdown("<div class='tp-title'>🏆 Mastered by Topic</div>" + "".join(rows), unsafe_allow_html=True)

    if not active and not mastered:
        banner = "<b>Get started!</b> A parent can add question screenshots on the <b>Add Questions</b> page."
    elif today_set:
        banner = f"<b>Keep going!</b> {plural(len(today_set), 'question')} waiting for you today."
    else:
        banner = "<b>Great work!</b> Come back tomorrow for your next set."
    st.markdown(f"<div class='banner'>⭐ {banner}</div>", unsafe_allow_html=True)

# ==================== PRACTICE: answer all, then submit ====================
elif st.session_state.mode == 'quiz':
    questions = [q for q in (find(db, i) for i in st.session_state.quiz_ids) if q]
    if not questions:
        st.warning("Nothing to practise.")
        if st.button("Back to Today"):
            st.session_state.mode = 'today'
            st.rerun()
        st.stop()

    idx = min(st.session_state.quiz_index, len(questions) - 1)
    q = questions[idx]
    answers = st.session_state.quiz_answers

    st.progress((idx + 1) / len(questions))
    st.markdown(f"**Question {idx + 1} of {len(questions)}**")
    show_question(q)
    if q.get('topic'):
        st.caption(q['topic'])

    is_mc = bool(re.fullmatch(r"[A-E]", q.get('answer', '')))
    answers[q['id']] = st.text_input("Your answer" + (" (type the letter A–E)" if is_mc else ""),
                                     value=answers.get(q['id'], ""),
                                     key=f"ans_{st.session_state.quiz_token}_{q['id']}")

    c1, _, c3 = st.columns([1, 2, 1])
    with c1:
        if idx > 0 and st.button("⬅️  Previous", width="stretch"):
            st.session_state.quiz_index = idx - 1
            st.rerun()
    with c3:
        if idx < len(questions) - 1:
            if st.button("Next  ➡️", width="stretch"):
                st.session_state.quiz_index = idx + 1
                st.rerun()
        else:
            blank = sum(1 for x in questions if not answers.get(x['id'], '').strip())
            if blank:
                st.caption(f"⚠️ {plural(blank, 'question')} left blank (counted as wrong)")
            with st.container(key="primary_submit"):
                if st.button("✅  Submit answers", width="stretch"):
                    results = []
                    for x in questions:
                        given = answers.get(x['id'], '').strip()
                        if x.get('answer'):
                            ok = norm(given) == norm(x['answer'])
                            record_answer(x, ok, log)
                        else:
                            ok = None  # no saved answer: a parent decides on the results page
                        results.append({"id": x['id'], "given": given, "correct": ok})
                    save_json(DB_FILE, db)
                    save_json(LOG_FILE, log)
                    st.session_state.results = results
                    st.session_state.mode = 'results'
                    st.rerun()

# ==================== RESULTS ====================
elif st.session_state.mode == 'results':
    results = st.session_state.results
    right_n = sum(1 for r in results if r['correct'] is True)
    wrong = [r for r in results if r['correct'] is False]
    pending = [r for r in results if r['correct'] is None]

    st.markdown("<div class='page-title'>Your Results</div>", unsafe_allow_html=True)
    note = "Wrong answers will come back tomorrow."
    if pending:
        note += f" {plural(len(pending), 'question')} {'needs' if len(pending) == 1 else 'need'} a parent to check."
    st.markdown(f"<div class='score'>{right_n} / {len(results)} correct</div>"
                f"<div class='page-sub'>{note}</div>", unsafe_allow_html=True)

    only_wrong = st.toggle("Show only wrong answers", value=bool(wrong or pending))
    shown = [r for r in results if r['correct'] is not True] if only_wrong else results

    for r in shown:
        q = find(db, r['id'])
        if not q:
            continue
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                show_question(q)
            with c2:
                if r['correct'] is True:
                    st.markdown("<span class='res-ok'>✓ Correct</span>", unsafe_allow_html=True)
                elif r['correct'] is False:
                    st.markdown("<span class='res-bad'>✗ Wrong</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='res-check'>? Parent to check</span>", unsafe_allow_html=True)
                st.write(f"**Your answer:** {r['given'] or '(blank)'}")
                if q.get('answer'):
                    st.markdown(f"**Correct answer:** {md_math(answer_text(q))}")
                if r['correct'] is not None:
                    show_explanation(q)

                if r['correct'] is None:
                    st.caption("No answer was saved for this question.")
                    if r['given'] and st.button(f"✓ \"{r['given']}\" is correct", key=f"ok_{r['id']}"):
                        q['answer'] = r['given']
                        record_answer(q, True, log)
                        r['correct'] = True
                        save_json(DB_FILE, db)
                        save_json(LOG_FILE, log)
                        st.rerun()
                    real = st.text_input("Or type the correct answer", key=f"real_{r['id']}")
                    if st.button("Save correct answer", key=f"save_{r['id']}", disabled=not real.strip()):
                        q['answer'] = real.strip()
                        ok = norm(r['given']) == norm(real)
                        record_answer(q, ok, log)
                        r['correct'] = ok
                        save_json(DB_FILE, db)
                        save_json(LOG_FILE, log)
                        st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        with st.container(key="primary_home"):
            if st.button("🏠  Back to Today", width="stretch"):
                st.session_state.mode = 'today'
                st.rerun()
    with c2:
        if wrong and st.button(f"🔄  Try the wrong {'one' if len(wrong) == 1 else str(len(wrong))} again",
                               width="stretch"):
            start_practice([find(db, r['id']) for r in wrong])

# ==================== ADD QUESTIONS ====================
elif st.session_state.mode == 'add':
    st.markdown("<div class='page-title'>Add Questions</div>"
                "<div class='page-sub'>Bring in wrong questions from Pi-Lead, or add your own screenshots. "
                "Questions with a saved answer are marked automatically.</div>",
                unsafe_allow_html=True)

    if st.session_state.get('flash'):
        st.success(st.session_state.pop('flash'))

    # --- Import from Pi-Lead ---
    with st.container(border=True):
        st.markdown("#### 📥 Import from Pi-Lead")
        st.markdown(
            "1. In Chrome, open your **Pi-Lead Notebook** (Hub → Review Task).\n"
            "2. Click the **Export to MathMastery** bookmark. A file called `pilead_export_<date>.json` downloads.\n"
            "3. Drop that file below and press **Import**. Questions already imported keep their practice progress.")
        with st.expander("First time? Set up the bookmark"):
            st.markdown(
                "1. Show the bookmarks bar in Chrome: **⌘ + Shift + B**.\n"
                "2. Right-click the bookmarks bar → **Add page…**\n"
                "3. Name: `Export to MathMastery`. URL: paste the code below (use the copy button at its top-right).\n"
                "4. Press **Save**.")
            st.code(bookmarklet(), language=None, wrap_lines=True)
        export_file = st.file_uploader("Pi-Lead export file", type=["json"],
                                       key=f"pilead_{st.session_state.uploader_key}")
        with st.container(key="primary_import"):
            if st.button("📥  Import", width="stretch", disabled=export_file is None):
                try:
                    added, updated = import_export(json.loads(export_file.getvalue()), db)
                    save_json(DB_FILE, db)
                    st.session_state.uploader_key += 1
                    st.session_state.flash = (f"Imported from Pi-Lead: {plural(added, 'new question')}, "
                                              f"{updated} updated.")
                    st.rerun()
                except (ValueError, KeyError) as e:
                    st.error(f"Couldn't import that file: {e}")

    st.markdown("#### 📷 Add your own screenshots")
    c1, c2 = st.columns(2)
    with c1:
        source = st.text_input("Where are these from?", placeholder="e.g. Selective Trial Test 3")
    with c2:
        topic_opts = [""] + TOPIC_CATEGORIES
        default_topic = st.selectbox("Topic for all", topic_opts, format_func=lambda t: t or "(choose later)")

    files = st.file_uploader("Screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True,
                             key=f"uploader_{st.session_state.uploader_key}")

    entries = []
    for i, f in enumerate(files or []):
        with st.container(border=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.image(f, width="stretch")
            with c2:
                topic = st.selectbox("Topic", topic_opts, index=topic_opts.index(default_topic),
                                     key=f"new_topic_{st.session_state.uploader_key}_{i}",
                                     format_func=lambda t: t or "(choose later)")
                answer = st.text_input("Answer", placeholder="e.g. C",
                                       key=f"new_ans_{st.session_state.uploader_key}_{i}")
                explanation = st.text_area("Explanation (optional)", height=80,
                                           key=f"new_exp_{st.session_state.uploader_key}_{i}")
            entries.append((f, topic, answer, explanation))

    if entries:
        missing = sum(1 for e in entries if not e[2].strip())
        if missing:
            st.caption(f"{plural(missing, 'question')} without an answer. You can still save; "
                       "you'll be asked to check those after practice.")
        with st.container(key="primary_save_new"):
            if st.button(f"💾  Save {plural(len(entries), 'question')}", width="stretch"):
                os.makedirs(VAULT_DIR, exist_ok=True)
                hashes = {q.get('file_hash') for q in db}
                stamp = datetime.now().strftime("%Y%m%d")
                nums = [int(q['id'].split('_')[1]) for q in db
                        if len(q['id'].split('_')) == 2 and q['id'].split('_')[1].isdigit()]
                next_num = max(nums, default=0) + 1
                added = skipped = 0
                for f, topic, answer, explanation in entries:
                    data = f.getvalue()
                    fhash = hashlib.md5(data).hexdigest()
                    if fhash in hashes:
                        skipped += 1
                        continue
                    q_id = f"{stamp}_{next_num}"
                    path = os.path.join(VAULT_DIR, q_id + os.path.splitext(f.name)[1].lower())
                    with open(path, 'wb') as out:
                        out.write(data)
                    db.append({"id": q_id, "file_path": path, "original_filename": f.name, "file_hash": fhash,
                               "answer": answer.strip(), "explanation": explanation.strip(),
                               "source": source.strip(), "topic": topic, "status": "active",
                               "times_practiced": 0, "times_correct": 0,
                               "created": datetime.now().isoformat()})
                    hashes.add(fhash)
                    next_num += 1
                    added += 1
                save_json(DB_FILE, db)
                st.session_state.uploader_key += 1
                st.session_state.flash = f"Saved {plural(added, 'question')}." + (
                    f" Skipped {skipped} that were already added." if skipped else "")
                st.rerun()

# ==================== PARENT REPORT ====================
elif st.session_state.mode == 'report':
    st.markdown("<div class='page-title'>Parent Report</div>"
                "<div class='page-sub'>How things are going, what to focus on, and every question.</div>",
                unsafe_allow_html=True)

    total = len(active) + len(mastered)
    mastered_pct = int(len(mastered) / total * 100) if total else 0
    last14 = {r['date'] for r in log if r['date'] > (TODAY - timedelta(days=14)).isoformat()}
    overdue = [q for q in due_reviews if due_date(q) < TODAY]
    week_ago = (TODAY - timedelta(days=7)).isoformat()
    added_week = sum(1 for q in active + mastered if q.get('created', '')[:10] > week_ago)
    mastered_week = sum(1 for q in mastered if q.get('mastered_on', '') > week_ago)
    explain = [q for q in active if needs_explaining(q)]
    no_answer = [q for q in active if not q.get('answer')]

    st.markdown(f"""
    <div class='tiles'>
      <div class='tile'><div class='tile-label'>Mastered</div><div class='tile-num'>{mastered_pct}%</div>
        <div class='tile-sub'>{len(mastered)} of {total} questions</div></div>
      <div class='tile'><div class='tile-label'>Days practised</div><div class='tile-num'>{len(last14)}</div>
        <div class='tile-sub'>of the last 14 days</div></div>
      <div class='tile'><div class='tile-label'>Reviews due</div><div class='tile-num'>{len(due_reviews)}</div>
        <div class='tile-sub'>{len(overdue)} overdue</div></div>
      <div class='tile'><div class='tile-label'>Added this week</div><div class='tile-num'>{added_week}</div>
        <div class='tile-sub'>{mastered_week} mastered this week</div></div>
    </div>""", unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        st.markdown("<div class='section-title'>Topics to focus on</div>", unsafe_allow_html=True)
        ranked = topic_miss_rates(db, log)[:3]
        if ranked:
            for i, (t, rate, w, a) in enumerate(ranked, 1):
                st.markdown(f"<div class='focus-row'><span>{i}. {html.escape(t)}</span>"
                            f"<span><span class='pct'>{round(rate * 100)}%</span> missed ({w} of {a})</span></div>",
                            unsafe_allow_html=True)
        else:
            st.caption("Shows up after some practice: the topics missed most often in the last 30 days.")

    with col_r:
        st.markdown("<div class='section-title'>What to do next</div>", unsafe_allow_html=True)
        tips = []
        if explain:
            tips.append(("warn", f"{plural(len(explain), 'question')} keep{'s' if len(explain) == 1 else ''} going wrong after review. "
                                 "Sit down and explain these (listed below) rather than repeating them."))
        if overdue:
            tips.append(("warn", f"{plural(len(overdue), 'review')} {'is' if len(overdue) == 1 else 'are'} overdue. "
                                 "Today's practice puts them first."))
        if log and len(last14) < 10:
            tips.append(("warn", f"Practised on {len(last14)} of the last 14 days. "
                                 "A short session every day works better than a long one now and then."))
        if added_week > mastered_week + 10:
            tips.append(("", "New mistakes are coming in faster than old ones are mastered. "
                             "That's normal early on. Keep the daily practice going."))
        if no_answer:
            tips.append(("", f"{plural(len(no_answer), 'question')} with no saved answer. "
                             "Add answers in the list below so they're marked automatically."))
        if not tips:
            tips.append(("", "Everything is on track. Keep the daily habit going."))
        for cls, text in tips:
            st.markdown(f"<div class='advice {cls}'>{text}</div>", unsafe_allow_html=True)

    if explain:
        st.markdown("<div class='section-title'>🙋 Questions to explain</div>", unsafe_allow_html=True)
        for q in explain:
            with st.container(border=True):
                c1, c2 = st.columns([3, 2])
                with c1:
                    show_question(q)
                with c2:
                    st.markdown(f"**Answer:** {md_math(answer_text(q)) or '(not set)'}")
                    st.write(f"Wrong {q.get('wrong_after_review', 0)} times after review")
                    if st.button("✓ I've explained it", key=f"explained_{q['id']}"):
                        q['wrong_after_review'] = 0
                        save_json(DB_FILE, db)
                        st.rerun()

    # --- Question list ---
    st.markdown("<div class='section-title'>All questions</div>", unsafe_allow_html=True)
    STATUS_FILTERS = {"All": lambda q: True,
                      "New": lambda q: state(q) == 'new',
                      "Learning": lambda q: state(q) == 'learning',
                      "Mastered": lambda q: state(q) == 'mastered',
                      "No answer saved": lambda q: not q.get('answer')}
    c1, c2 = st.columns(2)
    with c1:
        f_topic = st.selectbox("Topic", ["All"] + topics_in_use(active + mastered)[0], key="list_topic")
    with c2:
        f_status = st.selectbox("Status", list(STATUS_FILTERS), key="list_status")

    listed = [q for q in active + mastered if STATUS_FILTERS[f_status](q)
              and (f_topic == "All" or topic_of(q) == f_topic)]
    st.caption(plural(len(listed), 'question'))

    STATE_LABEL = {'new': '⚪ New', 'learning': '🟡 Learning', 'mastered': '🟢 Mastered'}
    for q in listed:
        nxt = due_date(q)
        when = f" · next review {nxt.strftime('%-d %b')}" if state(q) == 'learning' and nxt else ""
        src = f" · {q['source']}" if q.get('source') else ""
        subj = f"{q['subject']} · " if q.get('subject') else ""
        with st.expander(f"{STATE_LABEL[state(q)]} · {subj}{topic_of(q)}{src}{when}"):
            c1, c2 = st.columns([3, 2])
            with c1:
                show_question(q)
            with c2:
                new_ans = st.text_input("Answer", value=q.get('answer', ''), key=f"e_ans_{q['id']}")
                new_exp = st.text_area("Explanation", value=q.get('explanation', ''),
                                       key=f"e_exp_{q['id']}", height=80)
                opts = [""] + sorted(set(TOPIC_CATEGORIES) | {q2.get('topic', '') for q2 in db} - {""})
                new_topic = st.selectbox("Topic", opts, key=f"e_top_{q['id']}",
                                         index=opts.index(q.get('topic', '')) if q.get('topic', '') in opts else 0,
                                         format_func=lambda t: t or "(none)")
                new_src = st.text_input("Source", value=q.get('source', ''), key=f"e_src_{q['id']}")
                st.caption(f"Tried {q.get('times_practiced', 0)}× · right {q.get('times_correct', 0)}×")

                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("Save", key=f"e_save_{q['id']}", type="primary"):
                        q.update(answer=new_ans.strip(), explanation=new_exp.strip(),
                                 topic=new_topic, source=new_src.strip())
                        save_json(DB_FILE, db)
                        st.rerun()
                with b2:
                    if state(q) == 'mastered':
                        if st.button("Back to learning", key=f"e_unm_{q['id']}"):
                            q.update(status='active', stage=0, next_review=TODAY.isoformat())
                            save_json(DB_FILE, db)
                            st.rerun()
                    elif st.button("Mark mastered", key=f"e_m_{q['id']}"):
                        q.update(status='mastered', mastered_on=TODAY.isoformat())
                        save_json(DB_FILE, db)
                        st.rerun()
                with b3:
                    if st.button("Delete", key=f"e_del_{q['id']}"):
                        q['status'] = 'deleted'
                        save_json(DB_FILE, db)
                        st.rerun()

    # --- The one setting ---
    st.markdown("<div class='section-title'>Setting</div>", unsafe_allow_html=True)
    new_daily = st.number_input("Questions per day", min_value=1, max_value=100, value=daily_target, step=1)
    if new_daily != daily_target:
        settings['daily'] = int(new_daily)
        save_json(SETTINGS_FILE, settings)
        st.rerun()
