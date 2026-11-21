"""Free, on-device text recognition using macOS's built-in Vision framework.

No AI service, API key or internet connection is used. Math notation
(fractions, powers, diagrams) is often misread, so the result is meant to be
checked and edited by a person, with the screenshot kept as the real question.
"""
import io

from PIL import Image

try:
    from ocrmac import ocrmac
    OCR_AVAILABLE = True
except ImportError:  # not on macOS, or ocrmac not installed
    OCR_AVAILABLE = False


def extract_text(data: bytes) -> str:
    """Return the text found in an image, in reading order (top to bottom)."""
    if not OCR_AVAILABLE:
        raise RuntimeError("Text recognition needs macOS and the 'ocrmac' package.")

    image = Image.open(io.BytesIO(data))
    results = ocrmac.OCR(image, recognition_level="accurate",
                         language_preference=["en-US"]).recognize()

    # Each result is (text, confidence, (x, y, w, h)) with y measured from the
    # bottom of the image, so a larger top edge means higher up on the page.
    items = sorted(results, key=lambda r: (-(r[2][1] + r[2][3]), r[2][0]))

    lines = []
    current_top = None
    for text, _conf, (x, y, w, h) in items:
        top = y + h
        if current_top is not None and abs(top - current_top) < h * 0.5:
            lines[-1].append((x, text))  # same visual line
        else:
            lines.append([(x, text)])
            current_top = top
    return "\n".join(" ".join(t for _x, t in sorted(parts)) for parts in lines)
