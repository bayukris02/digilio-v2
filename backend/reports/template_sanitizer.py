"""
Sanitasi output HTML dari GrapesJS sebelum disimpan ke database.
WeasyPrint tidak execute JS, jadi XSS tidak berbahaya saat render.
Tapi tetap filter untuk keamanan berlapis.
"""

import re


def sanitize_template_html(html: str) -> str:
    """
    Hapus elemen berbahaya dari output GrapesJS:
    - <script>, <iframe>, <object>, <embed>
    - Event handler inline (onclick, onload, onerror)
    - javascript: URLs
    """
    # Hapus tag beserta isinya
    html = re.sub(
        r'<(script|iframe|object|embed)[^>]*>.*?</\1>',
        '',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Hapus event handler — cukup yang standalone
    html = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r"\s+on\w+\s*=\s*'[^']*'", '', html, flags=re.IGNORECASE)
    # Hapus javascript: URLs di href
    html = re.sub(r'href\s*=\s*"javascript:[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r"href\s*=\s*'javascript:[^']*'", '', html, flags=re.IGNORECASE)

    return html.strip()
