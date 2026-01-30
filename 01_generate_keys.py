import os
import re
import csv

# CONFIG
INBOX_DIR = "./inbox"

def extract_timestamp_id(filename):
    # Regex to capture the time part of macOS screenshots
    # Matches: "3.16.03 pm" from "Screenshot 2026-01-06 at 3.16.03 pm.png"
    match = re.search(r"at\s+(\d+\.\d+\.\d+\s?[ap]m)", filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return filename # Fallback if naming is weird

def generate_keys():
    print(f"🕵️  Scanning {INBOX_DIR} for missing key files...")
    
    for root, dirs, files in os.walk(INBOX_DIR):
        png_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not png_files:
            continue
            
        csv_path = os.path.join(root, "key.csv")
        
        # 1. Read existing keys (to avoid overwriting work)
        existing_ids = set()
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id']:
                        existing_ids.add(row['id'].strip())
        
        # 2. Identify new files
        new_rows = []
        for png in sorted(png_files):
            file_id = extract_timestamp_id(png)
            if file_id not in existing_ids:
                new_rows.append({"id": file_id, "answer": ""})
                print(f"   [+] Found new image: {file_id}")

        # 3. Append to CSV
        if new_rows:
            mode = 'a' if os.path.exists(csv_path) else 'w'
            with open(csv_path, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=["id", "answer"])
                if mode == 'w':
                    writer.writeheader()
                writer.writerows(new_rows)
            print(f"✅ Updated: {csv_path}")
        else:
            print(f"   (Skipping {os.path.basename(root)} - up to date)")

if __name__ == "__main__":
    generate_keys()