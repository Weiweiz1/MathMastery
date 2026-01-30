import os
import shutil
import json
import re
import csv
import hashlib
from datetime import datetime

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
VAULT_DIR = os.path.join(BASE_DIR, "vault")
DB_FILE = os.path.join(BASE_DIR, "mistakes_db.json")

os.makedirs(VAULT_DIR, exist_ok=True)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_file_hash(filepath):
    # Prevents duplicate uploads
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def load_answer_key(folder_path):
    # Reads key.csv into a dictionary { "3.16.03 pm": "150" }
    key_map = {}
    csv_path = os.path.join(folder_path, "key.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['id'] and row['answer']:
                    key_map[row['id'].strip()] = row['answer'].strip()
    return key_map

def extract_timestamp_id(filename):
    match = re.search(r"at\s+(\d+\.\d+\.\d+\s?[ap]m)", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return filename

def generate_system_id(counter):
    # Creates 20260106_01
    today = datetime.now().strftime("%Y%m%d")
    return f"{today}_{counter:02d}"

def ingest():
    db = load_db()
    
    # Calculate next ID sequence
    today_prefix = datetime.now().strftime("%Y%m%d")
    todays_entries = [i for i in db if i['id'].startswith(today_prefix)]
    counter = len(todays_entries) + 1
    
    # Existing hashes to prevent duplicates
    existing_hashes = {item.get('file_hash') for item in db}
    
    new_entries = []
    
    print(f"🚀 Starting Ingestion from {INBOX_DIR}...")

    for root, dirs, files in os.walk(INBOX_DIR):
        # 1. Load the key.csv for this batch folder
        batch_answers = load_answer_key(root)
        
        # Determine Batch Name
        rel_path = os.path.relpath(root, INBOX_DIR)
        source_batch = rel_path if rel_path != "." else "General"

        for filename in files:
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            file_path = os.path.join(root, filename)
            
            # 2. Check Duplicate
            f_hash = get_file_hash(file_path)
            if f_hash in existing_hashes:
                print(f"⚠️  Duplicate skipped: {filename}")
                # Optional: os.remove(file_path) # Auto-delete duplicates?
                continue
            
            # 3. Match Answer Key
            # We look for the "3.16.03 pm" part in our loaded CSV map
            short_id = extract_timestamp_id(filename)
            correct_answer = batch_answers.get(short_id, None)
            
            if correct_answer is None:
                print(f"❌ No answer key found for {filename} (ID: {short_id}). Skipping.")
                continue # Skip processing if no answer provided
                
            # 4. Move & Rename
            new_id = generate_system_id(counter)
            counter += 1
            
            ext = os.path.splitext(filename)[1]
            new_filename = f"{new_id}{ext}"
            vault_path = os.path.join(VAULT_DIR, new_filename)
            
            shutil.move(file_path, vault_path)
            
            # 5. Create Record
            entry = {
                "id": new_id,
                "file_path": f"vault/{new_filename}",
                "original_filename": filename,
                "source_batch": source_batch,
                "file_hash": f_hash,
                "ingest_date": datetime.now().isoformat(),
                "status": "pending_ai_verification", # <--- Ready for Gemini
                "data": {
                    "user_correct_key": correct_answer,
                    "ai_calculated_answer": None,
                    "match_confidence": 0
                }
            }
            new_entries.append(entry)
            existing_hashes.add(f_hash)
            print(f"✅ Ingested: {filename} -> {new_id} [Ans: {correct_answer}]")

    # Save
    if new_entries:
        db.extend(new_entries)
        save_db(db)
        print(f"\n🎉 Successfully vaulted {len(new_entries)} items.")
    else:
        print("\n💤 No new items with answer keys found.")

if __name__ == "__main__":
    ingest()