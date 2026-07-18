import streamlit as st
import json
import os
import random
from datetime import datetime, date
from PIL import Image

st.set_page_config(page_title="Math & Thinking Skills Engine", page_icon="⭐", layout="wide")

# === CONFIG ===
DB_FILE = "mistakes_db.json"
SELECTIVE_TEST_DATE = date(2028, 5, 7)

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
days_left = (SELECTIVE_TEST_DATE - date.today()).days
st.markdown("<h1 style='text-align: center;'>✨ Math and Thinking Skills Engine</h1>", unsafe_allow_html=True)
if days_left > 0:
    st.markdown(f"<h3 style='text-align: center;'>⏰ <b>{days_left} days</b> until Selective Test (7 May 2028)</h3>", unsafe_allow_html=True)
st.divider()

# === SESSION STATE INIT ===
if 'mode' not in st.session_state:
    st.session_state.mode = 'setup'
if 'quiz_questions' not in st.session_state:
    st.session_state.quiz_questions = []
if 'quiz_index' not in st.session_state:
    st.session_state.quiz_index = 0
if 'quiz_answers' not in st.session_state:
    st.session_state.quiz_answers = {}

# === LOAD DATA ===
db = load_db()

active_questions = [q for q in db if q.get('status', 'active') == 'active']
mastered_questions = [q for q in db if q.get('status') == 'mastered']

# === SIDEBAR ===
st.sidebar.header("📊 Stats")
st.sidebar.metric("Active Questions", len(active_questions))
st.sidebar.metric("Mastered", len(mastered_questions))
st.sidebar.divider()

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

    topics = sorted(set(q.get('topic', '') for q in active_questions if q.get('topic', '')))
    sources = sorted(set(q.get('source', '') for q in active_questions if q.get('source', '')))

    st.write("**Choose ONE option:**")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Option A: Filter & Play")

        selected_topic = st.selectbox("Filter by topic:", ["All"] + topics)
        selected_source = st.selectbox("Filter by source:", ["All"] + sources)

        filtered_qs = active_questions
        if selected_topic != "All":
            filtered_qs = [q for q in filtered_qs if q.get('topic', '') == selected_topic]
        if selected_source != "All":
            filtered_qs = [q for q in filtered_qs if q.get('source', '') == selected_source]

        undone_qs = [q for q in filtered_qs if q.get('times_practiced', 0) == 0]
        wrong_qs = [q for q in filtered_qs if q.get('times_practiced', 0) > q.get('times_correct', 0)]
        uncategorized_qs = [q for q in filtered_qs if not q.get('topic', '')]

        st.caption(f"{len(filtered_qs)} total, {len(undone_qs)} not done, {len(wrong_qs)} previously wrong, {len(uncategorized_qs)} uncategorized")

        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button("▶️ All Questions", type="primary"):
                if filtered_qs:
                    st.session_state.quiz_questions = filtered_qs
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_answers = {}
                    st.session_state.mode = 'quiz'
                    st.rerun()
        with bcol2:
            if undone_qs:
                if st.button("⏩ Continue Undone"):
                    st.session_state.quiz_questions = undone_qs
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_answers = {}
                    st.session_state.mode = 'quiz'
                    st.rerun()
            else:
                st.success("All done! ✅")
        with bcol3:
            if wrong_qs:
                if st.button(f"🔄 Redo Wrong ({len(wrong_qs)})"):
                    st.session_state.quiz_questions = wrong_qs
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_answers = {}
                    st.session_state.mode = 'quiz'
                    st.rerun()

    with col2:
        st.subheader("Option B: Random Questions")
        max_q = len(active_questions)
        if max_q > 0:
            num_questions = st.number_input("How many questions?", 1, max_q, min(10, max_q))
            if st.button("▶️ Start Random Quiz", type="primary"):
                questions = random.sample(active_questions, min(num_questions, len(active_questions)))
                st.session_state.quiz_questions = questions
                st.session_state.quiz_index = 0
                st.session_state.quiz_answers = {}
                st.session_state.mode = 'quiz'
                st.rerun()
        else:
            st.info("No active questions yet. Import some!")

    st.divider()

    # === TOPIC OVERVIEW ===
    st.header("📊 Topic Overview")
    topic_questions = {}
    for q in active_questions:
        t = q.get('topic', '') or '(Uncategorized)'
        if t not in topic_questions:
            topic_questions[t] = []
        topic_questions[t].append(q)

    for t in sorted(topic_questions.keys()):
        qs = topic_questions[t]
        practiced = [q for q in qs if q.get('times_practiced', 0) > 0]
        not_practiced = [q for q in qs if q.get('times_practiced', 0) == 0]
        wrong = [q for q in qs if q.get('times_practiced', 0) > q.get('times_correct', 0)]
        done = len(not_practiced) == 0
        icon = "✅" if done else "⬜"
        alert = " ❗" if wrong else ""

        with st.expander(f"{icon} **{t}**{alert} — {len(practiced)}/{len(qs)} done ({len(not_practiced)} remaining)"):
            for q in qs:
                q_icon = "✅" if q.get('times_practiced', 0) > 0 else "⬜"
                q_wrong = " ❗" if q.get('times_practiced', 0) > q.get('times_correct', 0) else ""
                source_label = f" [{q.get('source', '')}]" if q.get('source', '') else ""
                st.write(f"{q_icon} {q['id']}{q_wrong}{source_label}")

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

    st.progress((idx + 1) / len(questions))
    st.write(f"**Question {idx + 1} of {len(questions)}**")

    times_practiced = current.get('times_practiced', 0)
    times_correct = current.get('times_correct', 0)
    times_wrong = times_practiced - times_correct
    if times_wrong > 0:
        st.warning(f"⚠️ Previously wrong: {times_wrong} time(s)")

    if os.path.exists(current['file_path']):
        st.image(current['file_path'], use_container_width=True)
    else:
        st.error("Image not found")

    labels = []
    if current.get('topic', ''):
        labels.append(f"Topic: {current['topic']}")
    if current.get('source', ''):
        labels.append(f"Source: {current['source']}")
    if labels:
        st.caption(" | ".join(labels))
    st.divider()

    saved_answer = st.session_state.quiz_answers.get(q_id, "")
    kid_answer = st.text_input("Your answer:", value=saved_answer, key=f"answer_{q_id}")

    if kid_answer != saved_answer:
        st.session_state.quiz_answers[q_id] = kid_answer

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

    wrong_qs = []
    correct_qs = []
    no_answer_qs = []
    for q in questions:
        kid_answer = answers.get(q['id'], "")
        correct_answer = q.get('answer', '')
        if not correct_answer:
            no_answer_qs.append(q)
        elif kid_answer.lower().strip() == correct_answer.lower().strip():
            correct_qs.append(q)
        else:
            wrong_qs.append(q)

    st.write(f"**{len(questions)} questions: ✅ {len(correct_qs)} correct, ❌ {len(wrong_qs)} wrong, ❓ {len(no_answer_qs)} no answer saved**")

    review_filter = st.radio("Show:", ["All", "Wrong Only", "Correct Only", "No Answer Only"], horizontal=True)
    if review_filter == "Wrong Only":
        filtered_questions = wrong_qs
    elif review_filter == "Correct Only":
        filtered_questions = correct_qs
    elif review_filter == "No Answer Only":
        filtered_questions = no_answer_qs
    else:
        filtered_questions = questions

    st.divider()

    db = load_db()
    changes_made = False

    for i, q in enumerate(filtered_questions):
        q_id = q['id']
        kid_answer = answers.get(q_id, "")
        correct_answer = q.get('answer', '')

        db_item = get_question_by_id(db, q_id)
        if not db_item:
            continue

        with st.expander(f"Q{i+1}: {q.get('topic', '') or q.get('source', '')} | Kid's answer: **{kid_answer or '(empty)'}**", expanded=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                if os.path.exists(q['file_path']):
                    st.image(q['file_path'], width=400)

                times_wrong = db_item.get('times_practiced', 0) - db_item.get('times_correct', 0)
                st.caption(f"Previously wrong: {times_wrong} time(s)")

            with col2:
                st.write(f"**Kid's answer:** {kid_answer or '(empty)'}")

                if correct_answer:
                    st.write(f"**Saved answer:** {correct_answer}")
                    if kid_answer.lower().strip() == correct_answer.lower().strip():
                        st.success("✅ Correct!")
                        db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                        db_item['times_correct'] = db_item.get('times_correct', 0) + 1
                        changes_made = True
                    else:
                        st.error("❌ Wrong")
                        db_item['times_practiced'] = db_item.get('times_practiced', 0) + 1
                        changes_made = True
                else:
                    st.info("No correct answer saved yet")

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

                # Assign topic
                current_topic = db_item.get('topic', '')
                new_topic = st.selectbox(
                    "Topic:",
                    [""] + TOPIC_CATEGORIES,
                    index=(TOPIC_CATEGORIES.index(current_topic) + 1) if current_topic in TOPIC_CATEGORIES else 0,
                    key=f"topic_{q_id}"
                )
                if new_topic != current_topic:
                    db_item['topic'] = new_topic
                    changes_made = True

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

    if changes_made:
        save_db(db)

    st.divider()
    col_back, col_redo = st.columns(2)
    with col_back:
        if st.button("🏠 Back to Setup", type="primary"):
            st.session_state.mode = 'setup'
            st.session_state.quiz_questions = []
            st.session_state.quiz_answers = {}
            st.rerun()
    with col_redo:
        if wrong_qs and st.button(f"🔄 Redo {len(wrong_qs)} Wrong Questions"):
            st.session_state.quiz_questions = wrong_qs
            st.session_state.quiz_index = 0
            st.session_state.quiz_answers = {}
            st.session_state.mode = 'quiz'
            st.rerun()

# ==================== MANAGE MODE ====================
elif st.session_state.mode == 'manage':
    st.header("📋 Manage Questions")

    col_f1, col_f2 = st.columns(2)
    topics = sorted(set(q.get('topic', '') for q in active_questions if q.get('topic', '')))
    sources = sorted(set(q.get('source', '') for q in active_questions if q.get('source', '')))

    with col_f1:
        selected_topic = st.selectbox("Filter by topic:", ["All", "(Uncategorized)"] + topics)
    with col_f2:
        selected_source = st.selectbox("Filter by source:", ["All"] + sources)

    filtered = active_questions
    if selected_topic == "(Uncategorized)":
        filtered = [q for q in filtered if not q.get('topic', '')]
    elif selected_topic != "All":
        filtered = [q for q in filtered if q.get('topic', '') == selected_topic]
    if selected_source != "All":
        filtered = [q for q in filtered if q.get('source', '') == selected_source]

    st.write(f"**{len(filtered)} questions**")

    db = load_db()

    for q in filtered:
        q_id = q['id']
        db_item = get_question_by_id(db, q_id)
        if not db_item:
            continue

        times_wrong = db_item.get('times_practiced', 0) - db_item.get('times_correct', 0)
        topic_label = db_item.get('topic', '') or '(Uncategorized)'
        source_label = db_item.get('source', '')

        with st.expander(f"{q_id} | {topic_label} | Source: {source_label} | Wrong: {times_wrong}x"):
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
                    if st.button("💾 Save Answer", key=f"saveedit_{q_id}"):
                        db_item['answer'] = new_ans
                        save_db(db)
                        st.success("Saved!")
                        st.rerun()

                # Assign topic
                current_topic = db_item.get('topic', '')
                new_topic = st.selectbox(
                    "Topic:",
                    [""] + TOPIC_CATEGORIES,
                    index=(TOPIC_CATEGORIES.index(current_topic) + 1) if current_topic in TOPIC_CATEGORIES else 0,
                    key=f"topic_{q_id}"
                )
                if new_topic != current_topic:
                    if st.button("💾 Save Topic", key=f"savetopic_{q_id}"):
                        db_item['topic'] = new_topic
                        save_db(db)
                        st.success(f"Topic set to: {new_topic}")
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

            with st.expander(f"{q_id} | {q.get('topic', '') or q.get('source', '')}"):
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
