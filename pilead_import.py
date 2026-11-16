"""Import a Pi-Lead notebook export (from tools/pilead_export.js) into mistakes_db.json.

- New Pi-Lead questions are added as New questions.
- Questions imported before get their text / answer / explanation / topic refreshed,
  but keep their MathMastery practice history and review schedule.
- Pictures (embedded or referenced) are saved into vault/ so the app works offline.

Command line:  python pilead_import.py ~/Downloads/pilead_export_2026-11-16.json
"""
import base64
import json
import os
import re
import sys
from datetime import datetime

DB_FILE = "mistakes_db.json"
VAULT_DIR = "vault"
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
EXT = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg"}


def _save_data_url(data_url, path_no_ext):
    m = re.match(r"data:([^;,]+)(;base64)?,(.*)", data_url, re.S)
    if not m:
        return None
    mime, is_b64, payload = m.groups()
    if not mime.lower().startswith("image/"):
        return None  # e.g. a "not found" page instead of a picture
    path = path_no_ext + EXT.get(mime.lower(), ".png")
    data = base64.b64decode(payload) if is_b64 else payload.encode()
    with open(path, "wb") as f:
        f.write(data)
    return path


def _localise_images(text, prefix, images):
    """Replace every markdown picture with a local vault file path."""
    n = 0

    def repl(m):
        nonlocal n
        url = m.group(1)
        data_url = url if url.startswith("data:") else images.get(url)
        if not data_url:
            return ""  # picture couldn't be exported
        n += 1
        path = _save_data_url(data_url, f"{prefix}_{n}")
        return f"![]({path})" if path else ""

    return IMG_RE.sub(repl, text or "")


def _answer_key(answer_text):
    """'B. 5' -> 'B';  'E' -> 'E';  '48' -> '48'."""
    a = (answer_text or "").strip()
    m = re.match(r"^([A-Ea-e])(?:[.)]\s|\s*$)", a)
    return m.group(1).upper() if m else a


def _topic(item):
    if item.get("errorType"):
        return item["errorType"].strip()
    try:
        kps = json.loads(item.get("knowledgePoints") or "[]")
    except ValueError:
        kps = []
    return (kps[0].strip() if kps else "") or item.get("subject", "")


def import_export(export, db):
    """Merge a Pi-Lead export dict into db (list). Returns (added, updated)."""
    if export.get("source") != "pilead" or "items" not in export:
        raise ValueError("This isn't a Pi-Lead export file.")
    os.makedirs(VAULT_DIR, exist_ok=True)
    images = export.get("images", {})
    by_id = {q.get("pilead_id"): q for q in db if q.get("pilead_id")}
    added = updated = 0

    for it in export["items"]:
        prefix = os.path.join(VAULT_DIR, f"pl_{it['id']}")
        content = {
            "subject": it.get("subject", ""),
            "topic": _topic(it),
            "question_md": _localise_images(it.get("questionText", ""), prefix + "_q", images),
            "answer": _answer_key(it.get("answerText")),
            "answer_display": (it.get("answerText") or "").strip(),
            "explanation": _localise_images(it.get("analysis", ""), prefix + "_e", images).strip(),
            "source": it.get("source", "") or "Pi-Lead",
            "difficulty": it.get("difficultyLevel"),
        }
        if it.get("originalImageUrl", "").startswith("data:"):
            content["file_path"] = _save_data_url(it["originalImageUrl"], prefix + "_orig")

        q = by_id.get(it["id"])
        if q:
            q.update(content)  # keep stage / next_review / counts
            updated += 1
        else:
            db.append({
                "id": f"pl_{it['id']}", "pilead_id": it["id"], "origin": "pilead",
                "status": "active", "times_practiced": 0, "times_correct": 0,
                "created": it.get("createdAt") or datetime.now().isoformat(),
                "file_path": "", **content,
            })
            added += 1
    return added, updated


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python pilead_import.py <pilead_export.json>")
    with open(sys.argv[1]) as f:
        export = json.load(f)
    db = json.load(open(DB_FILE)) if os.path.exists(DB_FILE) else []
    added, updated = import_export(export, db)
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)
    print(f"Added {added} new question(s), updated {updated}. Total in database: {len(db)}")
