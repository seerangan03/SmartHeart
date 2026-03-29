"""
SmartHeart - OCR & Image Processing Utility
Extracts medical values from uploaded scan images using Tesseract OCR.
When values can't be extracted, uses safe clinical defaults so the result
is always generated without asking the user to re-enter data.
"""
import re
import os

try:
    import pytesseract
    from PIL import Image, ImageFilter, ImageEnhance
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Safe clinical defaults used when OCR cannot read a value
CLINICAL_DEFAULTS = {
    'age':        45,   # Middle-aged adult
    'gender':     1,    # Male (most common in cardiac datasets)
    'bp':         120,  # Normal systolic BP
    'cholesterol':185,  # Desirable range
    'heart_rate': 72,   # Normal resting HR
    'sugar':      0,    # Normal fasting glucose
    'chest_pain': 3,    # Asymptomatic (lowest risk default)
}


def preprocess_image(image_path):
    """Enhance image for best OCR accuracy."""
    img = cv2.imread(image_path)
    if img is None:
        # Try PIL as fallback
        from PIL import Image as PILImage
        pil_img = PILImage.open(image_path).convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Adaptive threshold works well for medical documents
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    # Scale up for better OCR
    h, w = denoised.shape
    if w < 1000:
        scale = 1200 / w
        denoised = cv2.resize(denoised, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_text(image_path):
    """Run Tesseract OCR on the image, trying multiple configs for best result."""
    if not OCR_AVAILABLE:
        return ""
    try:
        processed = preprocess_image(image_path)
        # Try multiple PSM modes and pick the one with most content
        best_text = ""
        for psm in [6, 4, 3, 11]:
            try:
                cfg = f'--oem 3 --psm {psm}'
                text = pytesseract.image_to_string(processed, config=cfg)
                if len(text.strip()) > len(best_text.strip()):
                    best_text = text
            except Exception:
                continue
        return best_text
    except Exception as e:
        return f"OCR processing error: {str(e)}"


def parse_medical_values(text):
    """
    Parse OCR text to find medical parameters.
    Returns dict of found values (may be partial).
    """
    tl = text.lower()
    found = {}

    # ── Age ──────────────────────────────────────────────────
    for pat in [
        r'age[:\s]+(\d{1,3})',
        r'(\d{1,3})\s*(?:year|yr)s?\s*(?:old)?',
        r'dob.*?(\d{1,3})\s*y',
    ]:
        m = re.search(pat, tl)
        if m:
            v = int(m.group(1))
            if 1 <= v <= 110:
                found['age'] = v
                break

    # ── Blood Pressure ───────────────────────────────────────
    for pat in [
        r'(?:systolic|s\.?b\.?p\.?|blood pressure)[:\s]+(\d{2,3})',
        r'(\d{2,3})\s*/\s*\d{2,3}\s*mm',
        r'b\.?p\.?[:\s]+(\d{2,3})',
        r'(\d{2,3})\s*mm\s*hg',
    ]:
        m = re.search(pat, tl)
        if m:
            v = int(m.group(1))
            if 50 <= v <= 250:
                found['bp'] = v
                break

    # ── Cholesterol ──────────────────────────────────────────
    for pat in [
        r'(?:total\s+)?cholesterol[:\s]+(\d{2,4})',
        r'chol(?:esterol)?[:\s]+(\d{2,4})',
        r'tc[:\s]+(\d{2,4})',
    ]:
        m = re.search(pat, tl)
        if m:
            v = int(m.group(1))
            if 50 <= v <= 600:
                found['cholesterol'] = v
                break

    # ── Heart Rate ───────────────────────────────────────────
    for pat in [
        r'(?:heart rate|pulse|hr|p\.?r\.?)[:\s]+(\d{2,3})',
        r'(\d{2,3})\s*b\.?p\.?m',
    ]:
        m = re.search(pat, tl)
        if m:
            v = int(m.group(1))
            if 20 <= v <= 250:
                found['heart_rate'] = v
                break

    # ── Blood Sugar ──────────────────────────────────────────
    for pat in [
        r'(?:fasting\s+)?(?:blood\s+)?(?:sugar|glucose)[:\s]+(\d{2,4})',
        r'(?:fbs|fbg|rbs)[:\s]+(\d{2,4})',
        r'glucose[:\s]+(\d{2,4})',
    ]:
        m = re.search(pat, tl)
        if m:
            v = int(m.group(1))
            found['sugar'] = 1 if v > 120 else 0
            break

    # ── Gender ───────────────────────────────────────────────
    if re.search(r'\b(?:male|m)\b', tl):
        found['gender'] = 1
    elif re.search(r'\b(?:female|f)\b', tl):
        found['gender'] = 0

    # ── Chest Pain ───────────────────────────────────────────
    if 'typical angina' in tl and 'atypical' not in tl:
        found['chest_pain'] = 0
    elif 'atypical' in tl:
        found['chest_pain'] = 1
    elif 'non-anginal' in tl or 'non anginal' in tl:
        found['chest_pain'] = 2
    elif 'asymptomatic' in tl or 'no chest' in tl:
        found['chest_pain'] = 3

    return found


def analyze_scan_report(image_path):
    """
    Full pipeline: image → OCR → parse → fill defaults.
    ALWAYS returns a complete set of 7 values (using defaults for unreadable fields).
    Returns: (complete_data: dict, raw_text: str, used_defaults: list)
    """
    raw_text = ""
    if OCR_AVAILABLE and os.path.exists(image_path):
        try:
            raw_text = extract_text(image_path)
        except Exception as e:
            raw_text = f"Error: {str(e)}"

    extracted = parse_medical_values(raw_text) if raw_text else {}

    required = ['age', 'gender', 'bp', 'cholesterol', 'heart_rate', 'sugar', 'chest_pain']
    used_defaults = []

    # Fill missing fields with clinical defaults
    complete_data = {}
    for field in required:
        if field in extracted:
            complete_data[field] = extracted[field]
        else:
            complete_data[field] = CLINICAL_DEFAULTS[field]
            used_defaults.append(field)

    # Return empty missing list — caller always gets complete data
    return complete_data, raw_text, used_defaults
