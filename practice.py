import streamlit as st
import json
import os
import random
from datetime import datetime, date
from PIL import Image

st.set_page_config(page_title="Math & Thinking Skills Engine", page_icon="⭐", layout="wide")

# === CONFIG ===
DB_FILE = "mistakes_db.json"
OC_TEST_DATE = date(2026, 5, 8)

# === DATABASE ===
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def get_question_by_id(db, q_id):
    for item in db:
        if item['id'] == q_id:
            return item
    return None

# === HEADER ===
days_left = (OC_TEST_DATE - date.today()).days
st.markdown("<h1 style='text-align: center;'>✨ Math and Thinking Skills Engine</h1>", unsafe_allow_html=True)
if days_left > 0:
    st.markdown(f"<h3 style='text-align: center;'>⏰ <b>{days_left} days</b> until OC Test (8 May 2026)</h3>", unsafe_allow_html=True)
st.divider()

# === SESSION STATE INIT ===
if 'mode' not in st.session_state:
    st.session_state.mode = 'setup'  # setup, quiz, review, manage
if 'quiz_questions' not in st.session_state:
    st.session_state.quiz_questions = []
if 'quiz_index' not in st.session_state:
    st.session_state.quiz_index = 0
if 'quiz_answers' not in st.session_state:
    st.session_state.quiz_answers = {}  # {question_id: kid_answer}

# === LOAD DATA ===
db = load_db()

# Filter active questions (not archived/deleted)
active_questions = [q for q in db if q.get('status', 'active') == 'active']
mastered_questions = [q for q in db if q.get('status') == 'mastered']

# === SIDEBAR ===
st.sidebar.header("📊 Stats")
st.sidebar.metric("Active Questions", len(active_questions))
st.sidebar.metric("Mastered", len(mastered_questions))
st.sidebar.divider()

# Mode buttons in sidebar
st.sidebar.header("Menu")
if st.sidebar.button("🏠 New Quiz", use_container_width=True):
    st.session_state.mode = 'setup'
    st.session_state.quiz_questions = []
    st.session_state.quiz_index = 0
    st.session_state.quiz_answers = {}
    st.rerun()

if st.sidebar.button("📋 Manage Questions", use_container_width=True):
    st.session_state.mode = 'manage'
    st.rerun()

if st.sidebar.button("📦 View Mastered", use_container_width=True):
    st.session_state.mode = 'mastered'
    st.rerun()

# ==================== SETUP MODE ====================
if st.session_state.mode == 'setup':
    st.header("🎯 Setup Quiz")

    # Get topics
    topics = sorted(set(q.get('topic', 'No Topic') for q in active_questions))

    st.write("**Choose ONE option:**")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Option A: By Topic")
        selected_topic = st.selectbox("Select topic:", [""] + topics)
        if selected_topic and st.button("▶️ Start Topic Quiz", type="primary"):
            questions = [q for q in active_questions if q.get('topic', 'No Topic') == selected_topic]
            if questions:
                st.session_state.quiz_questions = questions
                st.session_state.quiz_index = 0
                st.session_state.quiz_answers = {}
                st.session_state.mode = 'quiz'
                st.rerun()
            else:
                st.warning("No questions in this topic")

    with col2:
        st.subheader("Option B: Random Questions")
        max_q = len(active_questions)
        num_questions = st.number_input("How many questions?", 1, max_q, min(10, max_q))
        if st.button("▶️ Start Random Quiz", type="primary"):
            questions = random.sample(active_questions, min(num_questions, len(active_questions)))
            st.session_state.quiz_questions = questions
            st.session_state.quiz_index = 0
            st.session_state.quiz_answers = {}
            st.session_state.mode = 'quiz'
            st.rerun()

    st.divider()
    st.caption(f"Total active questions: {len(active_questions)}")

# ==================== QUIZ MODE ====================
elif st.session_state.mode == 'quiz':
    questions = st.session_state.quiz_questions
    idx = st.session_state.quiz_index

    if not questions:
        st.warning("No questions selected. Go back to setup.")
        st.stop()

    current = questions[idx]
    q_id = current['id']

    # Progress
    st.progress((idx + 1) / len(questions))
    st.write(f"**Question {idx + 1} of {len(questions)}**")

    # Wrong count
    times_practiced = current.get('times_practiced', 0)
    times_correct = current.get('times_correct', 0)
    times_wrong = times_practiced - times_correct
    if times_wrong > 0:
        st.warning(f"⚠️ Previously wrong: {times_wrong} time(s)")

    # Show image
    if os.path.exists(current['file_path']):
        st.image(current['file_path'], use_container_width=True)
    else:
        st.error("Image not found")

    st.caption(f"Topic: {current.get('topic', 'No Topic')}")
    st.divider()

    # Answer input - use question ID as key to clear on navigation
    saved_answer = st.session_state.quiz_answers.get(q_id, "")
    kid_answer = st.text_input("Your answer:", value=saved_answer, key=f"answer_{q_id}")

    # Auto-save answer to session
    if kid_answer != saved_answer:
        st.session_state.quiz_answers[q_id] = kid_answer

    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if idx > 0:
            if st.button("⬅️ Previous"):
                st.session_state.quiz_index = idx - 1
                st.rerun()

    with col3:
        if idx < len(questions) - 1:
            if st.button("Next ➡️"):
                st.session_state.quiz_index = idx + 1
                st.rerun()
        else:
            if st.button("✅ Finish Quiz", type="primary"):
                st.session_state.mode = 'review'
                st.rerun()

# ==================== REVIEW MODE ====================
elif st.session_state.mode == 'review':
    st.header("👨‍👩‍👧 Parent Review")

    questions = st.session_state.quiz_questions
    answers = st.session_state.quiz_answers

    if not questions:
        st.warning("No quiz to review. Start a new quiz.")
        st.stop()

    st.write(f"**Reviewing {len(questions)} questions**")
    st.divider()

    # Reload DB for saving
    db = load_db()
    changes_made = False

    for i, q in enumerate(questions):
        q_id = q['id']
        kid_answer = answers.get(q_id, "")
        correct_answer = q.get('answer', '')

        # Get fresh data from db
        db_item = get_question_by_id(db, q_id)
        if not db_item:
            continue

        with st.expander(f"Q{i+1}: {q.get('topic', 'No Topic')} | Kid's answer: **{kid_answer or '(empty)'}**", expanded=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                if os.path.exists(q['file_path']):
                    st.image(q['file_path'], width=400)

                # Wrong count
                times_wrong = db_item.get('times_practiced', 0) - db_item.get('times_correct', 0)
                st.caption(f"Previously wrong: {times_wrong} time(s)")

            with col2:
                st.write(f"**Kid's answer:** {kid_answer or '(empty)'}")

                if correct_answer:
                    st.write(f"**Saved answer:** {correct_answer}")
                    # Check if correct
                    if kid_answer.lower().strip() == correct_answer.lower().strip():
                        st.success("✅ Correct!")
                        # Update stats
                        db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                        db_item['times_correct'] = db_item.get('times_correct', 0) + 1
                        changes_made = True
                    else:
                        st.error("❌ Wrong")
                        db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                        changes_made = True
                else:
                    st.info("No correct answer saved yet")

                    # Parent enters correct answer
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if kid_answer and st.button(f"✅ Kid is correct", key=f"correct_{q_id}"):
                            db_item['answer'] = kid_answer
                            db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                            db_item['times_correct'] = db_item.get('times_correct', 0) + 1
                            changes_made = True
                            st.success(f"Saved: {kid_answer}")

                    with col_b:
                        new_answer = st.text_input("Correct answer:", key=f"new_{q_id}")
                        if st.button("💾 Save", key=f"save_{q_id}"):
                            if new_answer:
                                db_item['answer'] = new_answer
                                db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                                changes_made = True
                                st.success(f"Saved: {new_answer}")

                st.divider()

                # Actions
                col_arch, col_del = st.columns(2)
                with col_arch:
                    if st.button("📦 Mark Mastered", key=f"master_{q_id}"):
                        db_item['status'] = 'mastered'
                        changes_made = True
                        st.success("Moved to Mastered")

                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{q_id}"):
                        db_item['status'] = 'deleted'
                        changes_made = True
                        st.success("Deleted")

    # Save all changes
    if changes_made:
        save_db(db)

    st.divider()
    if st.button("🏠 Back to Setup", type="primary"):
        st.session_state.mode = 'setup'
        st.session_state.quiz_questions = []
        st.session_state.quiz_answers = {}
        st.rerun()

# ==================== MANAGE MODE ====================
elif st.session_state.mode == 'manage':
    st.header("📋 Manage Questions")

    # Filter
    topics = sorted(set(q.get('topic', 'No Topic') for q in active_questions))
    selected_topic = st.selectbox("Filter by topic:", ["All"] + topics)

    if selected_topic == "All":
        filtered = active_questions
    else:
        filtered = [q for q in active_questions if q.get('topic', 'No Topic') == selected_topic]

    st.write(f"**{len(filtered)} questions**")

    db = load_db()

    for q in filtered:
        q_id = q['id']
        db_item = get_question_by_id(db, q_id)
        if not db_item:
            continue

        times_wrong = db_item.get('times_practiced', 0) - db_item.get('times_correct', 0)

        with st.expander(f"{q_id} | {q.get('topic', '')} | Wrong: {times_wrong}x"):
            col1, col2 = st.columns([1, 1])

            with col1:
                if os.path.exists(q['file_path']):
                    st.image(q['file_path'], width=350)

            with col2:
                st.write(f"**Answer:** {q.get('answer', 'Not set')}")
                st.write(f"**Practiced:** {db_item.get('times_practiced', 0)} times")
                st.write(f"**Correct:** {db_item.get('times_correct', 0)} times")
                st.write(f"**Wrong:** {times_wrong} times")

                # Edit answer
                new_ans = st.text_input("Edit answer:", value=q.get('answer', ''), key=f"edit_{q_id}")
                if new_ans != q.get('answer', ''):
                    if st.button("💾 Save", key=f"saveedit_{q_id}"):
                        db_item['answer'] = new_ans
                        save_db(db)
                        st.success("Saved!")
                        st.rerun()

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("📦 Mastered", key=f"m_{q_id}"):
                        db_item['status'] = 'mastered'
                        save_db(db)
                        st.success("Moved to Mastered")
                        st.rerun()
                with col_b:
                    if st.button("🗑️ Delete", key=f"d_{q_id}"):
                        db_item['status'] = 'deleted'
                        save_db(db)
                        st.success("Deleted")
                        st.rerun()

# ==================== MASTERED MODE ====================
elif st.session_state.mode == 'mastered':
    st.header("📦 Mastered Questions")

    if not mastered_questions:
        st.info("No mastered questions yet.")
    else:
        st.write(f"**{len(mastered_questions)} mastered questions**")

        db = load_db()

        for q in mastered_questions:
            q_id = q['id']
            db_item = get_question_by_id(db, q_id)

            with st.expander(f"{q_id} | {q.get('topic', '')}"):
                col1, col2 = st.columns([1, 1])

                with col1:
                    if os.path.exists(q['file_path']):
                        st.image(q['file_path'], width=350)

                with col2:
                    st.write(f"**Answer:** {q.get('answer', 'Not set')}")

                    if st.button("🔄 Move back to Active", key=f"reactivate_{q_id}"):
                        db_item['status'] = 'active'
                        save_db(db)
                        st.success("Moved back to Active")
                        st.rerun()
