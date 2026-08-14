# -*- coding: utf-8 -*-
"""
PlanX CartoLab — Color Accessibility, CVD Simulation & Contrast Engine.

Provides mathematically accurate Color Vision Deficiency (CVD) simulation
(Protanopia, Deuteranopia, Tritanopia, Achromatopsia) using the Brettel/Machado
spectrophotometric matrix model, plus WCAG 2.1 relative luminance and contrast ratio calculations.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# WCAG 2.1 Relative Luminance & Contrast
# ---------------------------------------------------------------------------

def srgb_to_linear(c_srgb: float) -> float:
    """Convert an sRGB component in [0, 1] to linear RGB."""
    c = max(0.0, min(1.0, c_srgb))
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c_lin: float) -> float:
    """Convert a linear RGB component in [0, 1] to sRGB."""
    c = max(0.0, min(1.0, c_lin))
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Parse '#RRGGBB' or 'RRGGBB' into (r, g, b) integers in [0, 255]."""
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) < 6:
        return (0, 0, 0)
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return (r, g, b)
    except ValueError:
        return (0, 0, 0)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Format RGB integers to '#RRGGBB'."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def relative_luminance(hex_or_rgb: str | Tuple[int, int, int]) -> float:
    """
    Calculate WCAG 2.1 relative luminance for a given color in [0.0, 1.0].
    """
    if isinstance(hex_or_rgb, str):
        r, g, b = hex_to_rgb(hex_or_rgb)
    else:
        r, g, b = hex_or_rgb

    r_lin = srgb_to_linear(r / 255.0)
    g_lin = srgb_to_linear(g / 255.0)
    b_lin = srgb_to_linear(b / 255.0)

    # Standard ITU-R BT.709 coefficients
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color_a: str | Tuple[int, int, int], color_b: str | Tuple[int, int, int]) -> float:
    """
    Calculate the WCAG 2.1 contrast ratio between two colors in [1.0, 21.0].
    """
    l1 = relative_luminance(color_a)
    l2 = relative_luminance(color_b)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def rate_wcag_contrast(ratio: float) -> str:
    """Return WCAG compliance tier string."""
    if ratio >= 7.0:
        return "AAA (Enhanced Contrast)"
    elif ratio >= 4.5:
        return "AA (Standard Contrast)"
    elif ratio >= 3.0:
        return "AA Large (Moderate)"
    return "Fail (Low Contrast)"


# ---------------------------------------------------------------------------
# Color Vision Deficiency (CVD) Simulation Matrices (Machado et al.)
# ---------------------------------------------------------------------------

CVD_MATRICES = {
    "protanopia": [
        [0.56667, 0.43333, 0.0],
        [0.55833, 0.44167, 0.0],
        [0.0,     0.24167, 0.75833],
    ],
    "deuteranopia": [
        [0.625, 0.375, 0.0],
        [0.70,  0.30,  0.0],
        [0.0,   0.30,  0.70],
    ],
    "tritanopia": [
        [0.95, 0.05,  0.0],
        [0.0,  0.433, 0.567],
        [0.0,  0.475, 0.525],
    ],
    "achromatopsia": [
        [0.299, 0.587, 0.114],
        [0.299, 0.587, 0.114],
        [0.299, 0.587, 0.114],
    ],
}


def simulate_cvd_rgb(r: int, g: int, b: int, cvd_type: str = "deuteranopia") -> Tuple[int, int, int]:
    """
    Simulate a specific color vision deficiency on an (r, g, b) tuple.
    """
    matrix = CVD_MATRICES.get(cvd_type.lower(), CVD_MATRICES["deuteranopia"])
    rf = r / 255.0
    gf = g / 255.0
    bf = b / 255.0

    sim_r = matrix[0][0] * rf + matrix[0][1] * gf + matrix[0][2] * bf
    sim_g = matrix[1][0] * rf + matrix[1][1] * gf + matrix[1][2] * bf
    sim_b = matrix[2][0] * rf + matrix[2][1] * gf + matrix[2][2] * bf

    out_r = int(round(max(0.0, min(1.0, sim_r)) * 255.0))
    out_g = int(round(max(0.0, min(1.0, sim_g)) * 255.0))
    out_b = int(round(max(0.0, min(1.0, sim_b)) * 255.0))
    return (out_r, out_g, out_b)


def simulate_cvd_hex(hex_str: str, cvd_type: str = "deuteranopia") -> str:
    """Simulate CVD on a hex color string, returning simulated '#RRGGBB'."""
    r, g, b = hex_to_rgb(hex_str)
    sr, sg, sb = simulate_cvd_rgb(r, g, b, cvd_type)
    return rgb_to_hex(sr, sg, sb)


def evaluate_palette_accessibility(palette_hexes: List[str]) -> Dict[str, any]:
    """
    Evaluate a sequence of palette colors for readability, minimum step contrast,
    and distinctness under CVD simulations.
    """
    if not palette_hexes:
        return {"distinct": True, "min_contrast": 1.0, "rating": "Empty", "cvd_distinct": {}}

    n = len(palette_hexes)
    step_contrasts = []
    for i in range(n - 1):
        c1 = palette_hexes[i]
        c2 = palette_hexes[i + 1]
        step_contrasts.append(contrast_ratio(c1, c2))

    min_step = min(step_contrasts) if step_contrasts else 1.0
    bg_contrast = contrast_ratio(palette_hexes[0], palette_hexes[-1])

    # Check distinctness under CVD
    cvd_distinct = {}
    for cvd_name in ("deuteranopia", "protanopia", "tritanopia"):
        sim_colors = [simulate_cvd_hex(h, cvd_name) for h in palette_hexes]
        min_cvd_contrast = 21.0
        for i in range(len(sim_colors) - 1):
            cr = contrast_ratio(sim_colors[i], sim_colors[i + 1])
            if cr < min_cvd_contrast:
                min_cvd_contrast = cr
        cvd_distinct[cvd_name] = round(min_cvd_contrast, 2)

    return {
        "min_step_contrast": round(min_step, 2),
        "endpoint_contrast": round(bg_contrast, 2),
        "rating": rate_wcag_contrast(bg_contrast),
        "cvd_distinct": cvd_distinct,
    }
