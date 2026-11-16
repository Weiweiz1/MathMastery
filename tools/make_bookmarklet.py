"""Print the Pi-Lead export bookmarklet (a javascript: URL) built from pilead_export.js."""
import os
import re
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))


def bookmarklet():
    with open(os.path.join(HERE, "pilead_export.js")) as f:
        src = f.read()
    src = "\n".join(line for line in src.splitlines() if not line.strip().startswith("//"))
    src = re.sub(r"\s*\n\s*", " ", src).strip()
    return "javascript:" + quote(src, safe="")


if __name__ == "__main__":
    print(bookmarklet())
