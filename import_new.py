import json
import os
import shutil
import hashlib
from datetime import datetime

DB_FILE = "mistakes_db.json"
VAULT_DIR = "vault"
NEW_DIR = "New2"
INBOX_DIR = "inbox"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return []

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def import_new():
    db = load_db()

    # Get existing hashes to skip duplicates
    existing_hashes = set(q.get('file_hash', '') for q in db)

    # Find next ID number
    today = datetime.now().strftime("%Y%m%d")
    max_num = 0
    for q in db:
        parts = q['id'].split('_')
        if len(parts) == 2 and parts[1].isdigit():
            max_num = max(max_num, int(parts[1]))
    next_num = max_num + 1

    total_added = 0
    total_skipped = 0

    # Process each folder in New1
    folders = sorted(os.listdir(NEW_DIR))
    for folder in folders:
        folder_path = os.path.join(NEW_DIR, folder)
        if not os.path.isdir(folder_path):
            continue

        topic = folder
        added = 0
        skipped = 0

        # Get image files sorted by name
        files = sorted(f for f in os.listdir(folder_path)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg')))

        for filename in files:
            src = os.path.join(folder_path, filename)
            fhash = file_hash(src)

            # Skip duplicates
            if fhash in existing_hashes:
                skipped += 1
                continue

            # Generate ID and vault filename
            q_id = f"{today}_{next_num}"
            ext = os.path.splitext(filename)[1].lower()
            vault_name = f"{q_id}{ext}"
            vault_path = os.path.join(VAULT_DIR, vault_name)

            # Copy to vault
            shutil.copy2(src, vault_path)

            # Add to database
            db.append({
                "id": q_id,
                "file_path": vault_path,
                "original_filename": filename,
                "file_hash": fhash,
                "answer": "",
                "question_text": "",
                "source": topic,
                "topic": "",
                "tags": [],
                "times_practiced": 0,
                "times_correct": 0,
                "created": datetime.now().isoformat()
            })

            existing_hashes.add(fhash)
            next_num += 1
            added += 1

        total_added += added
        total_skipped += skipped
        print(f"  {topic}: {added} added, {skipped} duplicates skipped")

        # Move folder to inbox
        dest = os.path.join(INBOX_DIR, folder)
        if os.path.exists(dest):
            # Folder already exists in inbox, merge files
            for f in os.listdir(folder_path):
                shutil.move(os.path.join(folder_path, f), os.path.join(dest, f))
            os.rmdir(folder_path)
        else:
            shutil.move(folder_path, dest)
        print(f"  → Moved to inbox/{folder}")

    save_db(db)
    print(f"\nDone! {total_added} questions added, {total_skipped} duplicates skipped.")
    print(f"Total questions in database: {len(db)}")

if __name__ == "__main__":
    import_new()
