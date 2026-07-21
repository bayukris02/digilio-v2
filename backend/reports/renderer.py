"""
WeasyPrint PDF renderer for Digilio ERP.

Usage:
    from reports.renderer import render_pdf

    pdf_bytes = render_pdf('purchase_order.html', {
        'record': record_data,
        'vendor': vendor_data,
        'order_lines': lines_data,
        'summary': summary_data,
        'company': company_data,
    })
"""

from pathlib import Path
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name: str, context: dict, **kwargs) -> bytes:
    """
    Render Django template + context → HTML → PDF via WeasyPrint.

    Args:
        template_name: Nama file di folder templates/print/ (e.g. 'purchase_order.html')
        context: Dictionary data untuk di-inject ke template
        **kwargs: Opsional — page_size, orientation, base_url

    Returns:
        bytes — file PDF
    """
    page_size = kwargs.get('page_size', 'A4')
    orientation = kwargs.get('orientation', 'portrait')

    # Build CSS @page rule
    page_css = f"@page {{ size: {page_size} {orientation}; margin: 2cm; }}"

    # Render Django template → HTML string
    html_str = render_to_string(f'print/{template_name}', context)

    # Gabung CSS page + HTML
    full_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<style>{page_css}</style>
</head>
<body>{html_str}</body>
</html>"""

    # Generate PDF
    base_url = kwargs.get('base_url', None)
    pdf_result = HTML(string=full_html, base_url=base_url).write_pdf()

    if pdf_result is None:
        raise RuntimeError('WeasyPrint failed to generate PDF — returned None')

    return pdf_result
