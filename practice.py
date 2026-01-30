import streamlit as st
import json
import os
from datetime import datetime, date
from PIL import Image

st.set_page_config(page_title="Math & Thinking Skills Engine", page_icon="⭐", layout="wide")

# OC Test Countdown
OC_TEST_DATE = date(2026, 5, 8)  # 8 May 2026
days_left = (OC_TEST_DATE - date.today()).days

st.markdown("<h1 style='text-align: center;'>✨ Math and Thinking Skills Engine</h1>", unsafe_allow_html=True)
if days_left > 0:
    st.markdown(f"<h3 style='text-align: center;'>⏰ <b>{days_left} days</b> until OC Test (8 May 2026)</h3>", unsafe_allow_html=True)
elif days_left == 0:
    st.markdown("<h3 style='text-align: center;'>🎯 <b>OC Test is TODAY! Good luck!</b></h3>", unsafe_allow_html=True)
else:
    st.markdown(f"<h3 style='text-align: center;'>✅ OC Test was {-days_left} days ago</h3>", unsafe_allow_html=True)

st.divider()

# Load database once
@st.cache_data
def load_db():
    with open("mistakes_db.json", 'r') as f:
        return json.load(f)

def save_answer(item_id, answer):
    with open("mistakes_db.json", 'r') as f:
        db = json.load(f)
    for item in db:
        if item['id'] == item_id:
            item['answer'] = answer
            break
    with open("mistakes_db.json", 'w') as f:
        json.dump(db, f, indent=2)
    load_db.clear()

db = load_db()

# Filter questions
mode = st.sidebar.radio("Mode", ["Learning (no answer)", "Practice (has answer)"])
if mode == "Learning (no answer)":
    questions = [x for x in db if not x.get('answer')]
else:
    questions = [x for x in db if x.get('answer')]

# Topic filter
topics = sorted(set(x.get('topic', '') for x in questions if x.get('topic')))
if topics:
    selected = st.sidebar.selectbox("Topic", ["All"] + topics)
    if selected != "All":
        questions = [x for x in questions if x.get('topic') == selected]

st.sidebar.write(f"**{len(questions)} questions**")

if not questions:
    st.info("No questions in this mode/topic")
    st.stop()

# Question selector
q_num = st.sidebar.number_input("Question #", 1, len(questions), 1) - 1
current = questions[q_num]

# Display
st.title(f"Q{q_num + 1}: {current.get('topic', 'No topic')}")

# Show image
if os.path.exists(current['file_path']):
    st.image(current['file_path'])

st.divider()

# Answer
kid_answer = st.text_input("Answer:")

if current.get('answer'):
    # Has answer - check mode
    if st.button("Check"):
        if kid_answer.lower().strip() == current['answer'].lower().strip():
            st.success(f"✅ Correct! ({current['answer']})")
        else:
            st.error(f"❌ Wrong. Answer: {current['answer']}")
else:
    # No answer - learning mode
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Correct"):
            if kid_answer:
                save_answer(current['id'], kid_answer)
                st.success(f"Saved: {kid_answer}")
            else:
                st.warning("Enter answer first")
    with col2:
        correct = st.text_input("Or enter correct answer:")
        if st.button("💾 Save"):
            if correct:
                save_answer(current['id'], correct)
                st.success(f"Saved: {correct}")
