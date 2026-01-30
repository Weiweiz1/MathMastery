import os
import json
import time
import base64
import requests

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2-vision"
DB_FILE = "./mistakes_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def normalize_answer(ans):
    if not ans: return ""
    clean = str(ans).lower().strip()
    clean = clean.replace(" units", "").replace(" sq m", "").replace(" cm", "").replace("m2", "")
    return clean

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_image_with_ollama(image_path):
    """Send image to Ollama for analysis"""

    prompt = """Analyze this math problem image. You must respond with ONLY valid JSON, no other text.

{
    "question_text": "The verbatim text of the question",
    "topic_tag": "NSW Curriculum topic (e.g., 'Stage 3 Fractions')",
    "calculated_answer": "The final numeric or short answer only (e.g., '24', '1/2', 'C')",
    "logic_template": "The problem rewritten with variables",
    "reasoning_steps": "Brief step-by-step logic"
}

Important: For multiple choice, put just the letter (A, B, C, or D) in calculated_answer."""

    image_data = encode_image(image_path)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "images": [image_data],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()
    response_text = result.get("response", "")

    # Try to extract JSON from response
    try:
        # Find JSON in response (handle cases where model adds extra text)
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Fallback: return raw response in a structure
    return {
        "question_text": response_text,
        "topic_tag": "Unknown",
        "calculated_answer": "",
        "logic_template": "",
        "reasoning_steps": response_text
    }

def process_batch():
    db = load_db()
    queue = [item for item in db if item.get('status') == "pending_ai_verification"]

    if not queue:
        print("✅ No pending items found in database.")
        return

    print(f"🧠 Starting AI Analysis for {len(queue)} items...")

    for item in queue:
        file_path = item['file_path']
        print(f"\nProcessing: {item['id']} ({item['original_filename']})...")

        try:
            if not os.path.exists(file_path):
                print(f"   ❌ File not found: {file_path}")
                continue

            # Call Ollama
            analysis = analyze_image_with_ollama(file_path)

            # Compare Answers
            user_key = normalize_answer(item['data']['user_correct_key'])
            ai_ans = normalize_answer(analysis['calculated_answer'])

            # Simple string match
            is_match = (user_key == ai_ans) or (user_key in ai_ans) or (ai_ans in user_key)

            # Update Record
            item['meta'] = analysis
            item['data']['ai_calculated_answer'] = analysis['calculated_answer']

            if is_match:
                item['status'] = "auto_verified"
                item['data']['match_confidence'] = 1.0
                print(f"   ✅ VERIFIED! AI: '{ai_ans}' == Key: '{user_key}'")
            else:
                item['status'] = "flagged_for_review"
                item['data']['match_confidence'] = 0.0
                print(f"   ⚠️  MISMATCH. AI: '{ai_ans}' vs Key: '{user_key}'")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            item['status'] = "error_processing"

    save_db(db)
    print("\n💾 Database updated.")

if __name__ == "__main__":
    process_batch()
