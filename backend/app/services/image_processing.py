"""
Image Processing Service (Phase 4)

Preprocessing and quality assessment for scanned banking documents.

- Keeps ORIGINAL and PROCESSED images separate.
- Never destroys the original: a processed copy is produced for OCR.
- Quality uses measurable indicators (Laplacian variance, dimensions,
  brightness statistics, document boundary detection).

This module is a Horizon prototype component used for demonstration only.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import math


# ---------------------------------------------------------------------------
# Loading / validation
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

MIN_DIMENSION = 200          # px, anything smaller is unusable
MAX_DIMENSION = 2400         # px, downscale target for the long edge
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def load_image(path: str) -> Optional[np.ndarray]:
    """Load an image from disk as a BGR numpy array, or None on failure."""
    data = np.fromfile(path, dtype=np.uint8)  # unicode-safe on Windows
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def encode_jpeg(image: np.ndarray, quality: int = 90) -> bytes:
    ok, buf = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""


# ---------------------------------------------------------------------------
# Preprocessing pipeline
# ---------------------------------------------------------------------------

def detect_document_boundary(gray: np.ndarray) -> Optional[np.ndarray]:
    """
    Attempt to find the document quad (4 corner points) in a grayscale image.
    Returns corners ordered [tl, tr, br, bl] or None when no clear boundary.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)
    edged = cv2.dilate(edged, np.ones((3, 3), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # Largest contour area heuristic
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    h, w = gray.shape[:2]
    img_area = h * w
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.15 * img_area:
            continue  # too small to be the document
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            pts = approx.reshape(4, 2).astype(np.float32)
            return _order_corners(pts)
        # Approximation failed: use min-area rect of the contour as fallback
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect).astype(np.float32)
        if cv2.contourArea(box) >= 0.15 * img_area:
            return _order_corners(box)
    return None


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order points as tl, tr, br, bl."""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _rotation_angle(corners: np.ndarray) -> float:
    """Estimate skew angle (degrees) from the top edge of the ordered quad."""
    tl, tr = corners[0], corners[1]
    dx, dy = float(tr[0] - tl[0]), float(tr[1] - tl[1])
    angle = math.degrees(math.atan2(dy, dx))
    return angle


def perspective_correct(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Warp a perspective quad into an upright rectangle."""
    tl, tr, br, bl = corners
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_w = int(max(width_a, width_b))
    max_h = int(max(height_a, height_b))
    if max_w < MIN_DIMENSION or max_h < MIN_DIMENSION:
        return image
    dst = np.array(
        [[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]],
        dtype=np.float32,
    )
    m = cv2.getPerspectiveTransform(corners, dst)
    return cv2.warpPerspective(image, m, (max_w, max_h))


def preprocess(image: np.ndarray, apply_threshold: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run the preprocessing pipeline. Returns (processed_bgr, info).

    Pipeline: resize -> boundary detect -> perspective correct -> rotate
    -> grayscale -> denoise -> contrast (CLAHE) -> sharpen
    -> (optional) adaptive threshold.
    """
    info: Dict[str, Any] = {
        "boundary_detected": False,
        "perspective_corrected": False,
        "rotation_corrected": False,
        "estimated_rotation_deg": 0.0,
        "original_size": None,
        "processed_size": None,
    }

    orig = image
    info["original_size"] = [int(orig.shape[1]), int(orig.shape[0])]

    # 1. Resize to a sane working resolution
    h, w = orig.shape[:2]
    scale = 1.0
    long_edge = max(h, w)
    if long_edge > MAX_DIMENSION:
        scale = MAX_DIMENSION / long_edge
    elif long_edge < 800:
        # mildly upscale small photos for better OCR
        scale = min(2.0, 800.0 / long_edge)
    if scale != 1.0:
        orig = cv2.resize(orig, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)

    # 2/3. Document boundary + perspective correction
    gray_full = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    corners = detect_document_boundary(gray_full)
    if corners is not None:
        info["boundary_detected"] = True
        angle = _rotation_angle(corners)
        info["estimated_rotation_deg"] = round(angle, 2)
        orig = perspective_correct(orig, corners)
        info["perspective_corrected"] = True
        # 4. Rotation correction for any remaining skew
        if abs(angle) > 1.5:
            orig = _rotate_bound(orig, -angle)
            info["rotation_corrected"] = True

    # 5. Grayscale
    gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)

    # 6. Noise reduction
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 7. Contrast enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    # 8. Sharpening (light unsharp mask)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 3)
    sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)

    if apply_threshold:
        # 9. Adaptive threshold as final binarisation for OCR
        bw = cv2.adaptiveThreshold(
            sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
        )
        processed = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
    else:
        processed = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    info["processed_size"] = [int(processed.shape[1]), int(processed.shape[0])]
    return processed, info


def _rotate_bound(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by angle with expanded bounds (no corner cropping)."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    n_w = int(h * sin + w * cos)
    n_h = int(h * cos + w * sin)
    m[0, 2] += n_w / 2 - center[0]
    m[1, 2] += n_h / 2 - center[1]
    return cv2.warpAffine(image, m, (n_w, n_h), borderValue=(255, 255, 255))


# ---------------------------------------------------------------------------
# Quality assessment
# ---------------------------------------------------------------------------

def assess_quality(image: np.ndarray, preprocess_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Assess image quality with measurable indicators.

    Returns metrics + per-issue flags + overall status:
      GOOD    - ready for OCR
      WARNING - quality could affect extraction
      POOR    - please scan again
    """
    metrics: Dict[str, Any] = {}
    issues: List[str] = []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    # Blur: Laplacian variance (higher = sharper). Reference ~ 100+ okay for docs.
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    metrics["sharpness_laplacian_variance"] = round(lap_var, 2)
    if lap_var < 18.0:
        issues.append("blurry")
    elif lap_var < 45.0:
        issues.append("slightly_blurry")

    # Resolution
    metrics["width"] = int(w)
    metrics["height"] = int(h)
    if min(h, w) < 320:
        issues.append("low_resolution")

    # Lighting: brightness stats
    mean_lum = float(gray.mean())
    dark_ratio = float((gray < 40).mean())
    bright_ratio = float((gray > 235).mean())
    metrics["mean_brightness"] = round(mean_lum, 1)
    metrics["dark_pixel_ratio"] = round(dark_ratio, 3)
    metrics["bright_pixel_ratio"] = round(bright_ratio, 3)
    if mean_lum < 60:
        issues.append("underexposed")
    elif mean_lum > 200 and bright_ratio > 0.60:
        issues.append("overexposed")
    if dark_ratio > 0.45:
        issues.append("poor_lighting")

    # Contrast
    std_lum = float(gray.std())
    metrics["contrast_std"] = round(std_lum, 1)
    if std_lum < 25:
        issues.append("low_contrast")

    # Document boundary / cropping / rotation
    corners = detect_document_boundary(gray)
    if corners is not None:
        metrics["document_boundary_detected"] = True
        angle = _rotation_angle(corners)
        metrics["estimated_rotation_deg"] = round(angle, 2)
        area = cv2.contourArea(corners)
        metrics["document_area_ratio"] = round(float(area / (h * w)), 3)
        if area < 0.15 * h * w:
            issues.append("document_cropped")
        if abs(angle) > 20:
            issues.append("excessive_rotation")
    else:
        metrics["document_boundary_detected"] = False
        # Not automatically an issue (plain background scans) - only warn
        issues.append("document_boundary_not_detected")

    # Overall status: do NOT reject on a single weak metric.
    hard_issues = {"blurry", "low_resolution", "poor_lighting"}
    if len(hard_issues & set(issues)) >= 2 or (min(h, w) < 200):
        status = "POOR"
    elif lap_var < 18.0 or "overexposed" in issues or "underexposed" in issues:
        status = "WARNING" if lap_var >= 18.0 else "POOR"
    elif issues:
        status = "WARNING"
    else:
        status = "GOOD"

    return {
        "status": status,
        "issues": issues,
        "metrics": metrics,
    }


# Issue explanations for the customer (English; i18n handled on frontend keys)
ISSUE_EXPLANATIONS_EN = {
    "blurry": "The image is too blurry. Hold the camera steady and tap to focus.",
    "slightly_blurry": "The image is a little soft. Keep the camera still.",
    "low_resolution": "The image resolution is too low. Move closer or use a better camera.",
    "underexposed": "The image is too dark. Scan in a brighter place and avoid shadows.",
    "overexposed": "The image is too bright / washed out. Avoid direct light on the document.",
    "poor_lighting": "Lighting is poor. Use even lighting and avoid shadows.",
    "low_contrast": "The document appears faded due to low contrast.",
    "document_cropped": "Part of the document may be cut off. Show all four corners inside the frame.",
    "excessive_rotation": "The document is very tilted. Place it straight inside the frame.",
    "document_boundary_not_detected": "Document edges were not clear. Place the document on a plain dark surface.",
}


def quality_summary(quality: Dict[str, Any]) -> Dict[str, Any]:
    """Attach short English explanations for detected issues."""
    out = dict(quality)
    out["explanations"] = [
        ISSUE_EXPLANATIONS_EN[i] for i in quality.get("issues", []) if i in ISSUE_EXPLANATIONS_EN
    ]
    return out
