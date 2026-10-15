"""
Lightweight OpenCV (cv2) compatibility shim for AWS Lambda.
Eliminates the bulky 120MB opencv-python-headless binary dependency while providing
the exact constants and functions required by pdf2docx (findContours, boundingRect).
"""

RETR_TREE = 3
CHAIN_APPROX_SIMPLE = 2

def findContours(image, mode, method):
    """Fallback stub for contour detection."""
    return ([], None)

def boundingRect(contour):
    """Fallback stub for bounding box calculation."""
    return (0, 0, 0, 0)
