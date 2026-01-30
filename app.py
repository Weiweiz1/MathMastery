import streamlit as st
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from PIL import Image

# --- CONFIGURATION ---
VAULT_DIR = "./vault"
DB_FILE = "./mistakes_db.json"

Path(VAULT_DIR).mkdir(exist_ok=True)

# --- DATABASE FUNCTIONS ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_file_hash(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def normalize_answer(ans):
    if not ans: return ""
    return str(ans).lower().strip()

def get_answer(item):
    """Get answer from either new or old format"""
    return item.get('answer') or item.get('data', {}).get('user_correct_key', '')

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Mistake Mastery Engine",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Mistake Mastery Engine")
st.caption("Help your child master math by learning from mistakes")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📥 Add Questions", "📋 Manage", "📝 Practice"])

# ==================== TAB 1: ADD QUESTIONS ====================
with tab1:
    st.header("Add New Questions")

    uploaded_files = st.file_uploader(
        "Drop math problem screenshots here",
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} files ready**")

        with st.form("add_form"):
            entries = []

            for i, file in enumerate(uploaded_files):
                st.divider()
                col_img, col_info = st.columns([1, 2])

                with col_img:
                    img = Image.open(file)
                    st.image(img, caption=file.name, width=400)

                with col_info:
                    answer = st.text_input(
                        f"Correct Answer *",
                        key=f"ans_{i}",
                        placeholder="e.g., 24, 1/2, C"
                    )
                    question = st.text_area(
                        f"Question Text (optional - for clean practice)",
                        key=f"q_{i}",
                        placeholder="Type the question here for text-only practice mode",
                        height=80
                    )
                    topic = st.text_input(
                        f"Topic (optional)",
                        key=f"topic_{i}",
                        placeholder="e.g., Fractions, Algebra, Geometry"
                    )

                entries.append({
                    'file': file,
                    'answer': answer,
                    'question': question,
                    'topic': topic
                })

            submitted = st.form_submit_button("💾 Save All", type="primary")

            if submitted:
                db = load_db()
                saved = 0

                for entry in entries:
                    if not entry['answer']:
                        st.warning(f"Skipping {entry['file'].name} - no answer provided")
                        continue

                    # Generate ID
                    today = datetime.now().strftime("%Y%m%d")
                    existing_today = [x for x in db if x['id'].startswith(today)]
                    next_num = len(existing_today) + 1
                    new_id = f"{today}_{next_num:02d}"

                    # Save file
                    ext = Path(entry['file'].name).suffix.lower()
                    new_filename = f"{new_id}{ext}"
                    vault_path = os.path.join(VAULT_DIR, new_filename)

                    with open(vault_path, 'wb') as f:
                        entry['file'].seek(0)
                        f.write(entry['file'].read())

                    # Check duplicates
                    file_hash = get_file_hash(vault_path)
                    if any(x.get('file_hash') == file_hash for x in db):
                        os.remove(vault_path)
                        st.warning(f"Duplicate: {entry['file'].name}")
                        continue

                    # Add record
                    record = {
                        "id": new_id,
                        "file_path": vault_path,
                        "original_filename": entry['file'].name,
                        "file_hash": file_hash,
                        "created": datetime.now().isoformat(),
                        "answer": entry['answer'],
                        "question_text": entry['question'],
                        "topic": entry['topic'],
                        "times_practiced": 0,
                        "times_correct": 0
                    }
                    db.append(record)
                    saved += 1

                save_db(db)
                st.success(f"✅ Saved {saved} questions!")
                st.rerun()

# ==================== TAB 2: MANAGE ====================
with tab2:
    st.header("Manage Questions")

    db = load_db()

    if not db:
        st.info("No questions yet. Add some in the first tab!")
    else:
        # Filter
        topics = list(set(x.get('topic', '') for x in db if x.get('topic')))
        topics.insert(0, "All")
        selected_topic = st.selectbox("Filter by topic:", topics)

        filtered = db if selected_topic == "All" else [x for x in db if x.get('topic') == selected_topic]

        st.write(f"**{len(filtered)} questions**")

        for item in filtered:
            with st.expander(f"📋 {item['id']} - {item.get('topic', 'No topic')}"):
                col1, col2 = st.columns([1, 2])

                with col1:
                    if os.path.exists(item['file_path']):
                        st.image(item['file_path'], use_container_width=True)

                with col2:
                    # Editable fields (handle old format)
                    current_answer = item.get('answer') or item.get('data', {}).get('user_correct_key', '')
                    new_answer = st.text_input("Answer:", value=current_answer, key=f"edit_ans_{item['id']}")
                    new_question = st.text_area("Question Text:", value=item.get('question_text', ''), key=f"edit_q_{item['id']}", height=80)
                    new_topic = st.text_input("Topic:", value=item.get('topic', ''), key=f"edit_topic_{item['id']}")

                    # Stats
                    practiced = item.get('times_practiced', 0)
                    correct = item.get('times_correct', 0)
                    if practiced > 0:
                        st.caption(f"Practiced: {practiced} times | Correct: {correct} ({correct/practiced*100:.0f}%)")

                    col_save, col_delete = st.columns(2)

                    with col_save:
                        if st.button("💾 Save", key=f"save_{item['id']}"):
                            item['answer'] = new_answer
                            item['question_text'] = new_question
                            item['topic'] = new_topic
                            save_db(db)
                            st.success("Saved!")
                            st.rerun()

                    with col_delete:
                        if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                            if os.path.exists(item['file_path']):
                                os.remove(item['file_path'])
                            db.remove(item)
                            save_db(db)
                            st.success("Deleted!")
                            st.rerun()

# ==================== TAB 3: PRACTICE ====================
with tab3:
    st.header("Practice Mode")

    db = load_db()

    # Mode selection
    mode = st.radio("Select Mode:", ["📝 Practice (has answers)", "🆕 Learning (no answers yet)"], horizontal=True)

    if mode == "📝 Practice (has answers)":
        practice_items = [x for x in db if get_answer(x)]
    else:
        practice_items = [x for x in db if not get_answer(x)]

    if not practice_items:
        if mode == "📝 Practice (has answers)":
            st.info("No questions with answers yet. Use Learning mode or add answers in Manage tab.")
        else:
            st.info("All questions have answers! Switch to Practice mode.")
    else:
        # Settings
        col_set1, col_set2 = st.columns(2)
        with col_set1:
            show_text_only = st.checkbox("Text-only mode (hide images)", value=True)
        with col_set2:
            shuffle = st.checkbox("Shuffle questions", value=False)

        if shuffle:
            import random
            if 'shuffled' not in st.session_state:
                st.session_state.shuffled = practice_items.copy()
                random.shuffle(st.session_state.shuffled)
            practice_items = st.session_state.shuffled

        # Session state
        if 'q_index' not in st.session_state:
            st.session_state.q_index = 0
        if 'revealed' not in st.session_state:
            st.session_state.revealed = False
        if 'score' not in st.session_state:
            st.session_state.score = {'correct': 0, 'total': 0}

        # Navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous"):
                st.session_state.q_index = max(0, st.session_state.q_index - 1)
                st.session_state.revealed = False
                st.rerun()
        with col2:
            st.write(f"**Question {st.session_state.q_index + 1} of {len(practice_items)}**")
        with col3:
            if st.button("Next ➡️"):
                st.session_state.q_index = min(len(practice_items) - 1, st.session_state.q_index + 1)
                st.session_state.revealed = False
                st.rerun()

        st.divider()

        # Current question
        current = practice_items[st.session_state.q_index]

        # Display question
        if show_text_only and current.get('question_text'):
            st.subheader("📝 Question")
            st.markdown(f"**{current['question_text']}**")
        else:
            if os.path.exists(current['file_path']):
                st.image(current['file_path'], use_container_width=True)
            else:
                st.error("Image not found")

        if current.get('topic'):
            st.caption(f"Topic: {current['topic']}")

        st.divider()

        # Answer section
        user_answer = st.text_input("Kid's answer:", placeholder="Type your answer", key=f"practice_ans_{st.session_state.q_index}")

        correct_answer = get_answer(current)

        if correct_answer:
            # PRACTICE MODE - answer exists
            col_check, col_show = st.columns(2)

            with col_check:
                if st.button("✔️ Check", type="primary"):
                    if normalize_answer(user_answer) == normalize_answer(correct_answer):
                        st.success(f"🎉 Correct! Answer: **{correct_answer}**")
                        st.session_state.score['correct'] += 1
                        current['times_correct'] = current.get('times_correct', 0) + 1
                    else:
                        st.error(f"❌ Wrong. Correct answer: **{correct_answer}**")
                    st.session_state.score['total'] += 1
                    current['times_practiced'] = current.get('times_practiced', 0) + 1
                    save_db(db)
                    st.session_state.revealed = True

            with col_show:
                if st.button("👁️ Show Answer"):
                    st.session_state.revealed = True

            if st.session_state.revealed:
                st.info(f"**Answer: {correct_answer}**")
        else:
            # LEARNING MODE - no answer yet, parent enters it
            st.divider()
            st.subheader("👨‍👩‍👧 Parent: Enter correct answer")

            col_correct, col_wrong = st.columns(2)

            with col_correct:
                if st.button("✅ Kid is CORRECT", type="primary"):
                    if user_answer:
                        current['answer'] = user_answer
                        current['times_practiced'] = current.get('times_practiced', 0) + 1
                        current['times_correct'] = current.get('times_correct', 0) + 1
                        save_db(db)
                        st.success(f"Saved! Answer: **{user_answer}**")
                        st.session_state.score['correct'] += 1
                        st.session_state.score['total'] += 1
                    else:
                        st.warning("Kid needs to type an answer first!")

            with col_wrong:
                if st.button("❌ Kid is WRONG"):
                    st.session_state.revealed = True
                    st.session_state.score['total'] += 1

            if st.session_state.revealed:
                correct_input = st.text_input("Enter the correct answer:", key=f"correct_{st.session_state.q_index}")
                if st.button("💾 Save Correct Answer"):
                    if correct_input:
                        current['answer'] = correct_input
                        current['times_practiced'] = current.get('times_practiced', 0) + 1
                        save_db(db)
                        st.success(f"Saved! Correct answer: **{correct_input}**")
                    else:
                        st.warning("Please enter the correct answer")

        if st.session_state.revealed and correct_answer:
            if show_text_only and current.get('question_text'):
                with st.expander("Show Image"):
                    if os.path.exists(current['file_path']):
                        st.image(current['file_path'], use_container_width=True)

        # Score
        st.divider()
        if st.session_state.score['total'] > 0:
            pct = st.session_state.score['correct'] / st.session_state.score['total'] * 100
            st.metric("Score", f"{st.session_state.score['correct']}/{st.session_state.score['total']}", f"{pct:.0f}%")

        if st.button("🔄 Reset Session"):
            st.session_state.score = {'correct': 0, 'total': 0}
            st.session_state.q_index = 0
            st.session_state.revealed = False
            if 'shuffled' in st.session_state:
                del st.session_state.shuffled
            st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📊 Stats")
    db = load_db()

    st.metric("Total Questions", len(db))

    with_text = len([x for x in db if x.get('question_text')])
    st.metric("With Question Text", with_text)

    total_practiced = sum(x.get('times_practiced', 0) for x in db)
    total_correct = sum(x.get('times_correct', 0) for x in db)
    st.metric("Total Attempts", total_practiced)
    if total_practiced > 0:
        st.metric("Overall Accuracy", f"{total_correct/total_practiced*100:.0f}%")
