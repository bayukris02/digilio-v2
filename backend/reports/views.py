"""
Print API views — render HTML preview (same page) and PDF download.
"""
from io import BytesIO

from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.model_api import get_model_class
from reports.renderer import render_pdf


def _resolve_printout(model_cls, template_key=None):
    """Printout yang diminta (meta-driven dari `model.get_printouts()`).

    `template_key` kosong → printout pertama. Key tidak dikenal → None (ditolak;
    template hanya boleh yang terdaftar di model, bukan sembarang path).
    """
    getter = getattr(model_cls, 'get_printouts', None)
    printouts = getter() if getter else []
    if not printouts:
        return None
    if not template_key:
        return printouts[0]
    for item in printouts:
        if item.get('key') == template_key:
            return item
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_preview(request, model_name, record_id, template_key=None):
    """
    Render print preview as HTML (with print CSS).
    Dipanggil via fetch dari halaman yang sama — JWT via Authorization header.

    GET /api/print/{model_name}/{record_id}/preview/
    GET /api/print/{model_name}/{record_id}/{printout_key}/preview/
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    printout = _resolve_printout(model_cls, template_key)
    if not printout:
        return Response(
            {'error': f'Printout "{template_key}" tidak tersedia untuk {model_name}'},
            status=404,
        )

    record = get_object_or_404(
        model_cls.objects.filter(is_deleted=False), pk=record_id
    )

    if not hasattr(record, '_print_context'):
        return Response(
            {'error': f'Model "{model_name}" does not support printing'},
            status=400,
        )

    context = record._print_context()
    suffix = f'/{template_key}' if template_key else ''
    context['pdf_download_url'] = f'/api/print/{model_name}/{record_id}{suffix}/download/'
    context['model_name'] = model_name
    context['record_id'] = record_id
    context['printout'] = printout
    context['model_label'] = str(getattr(model_cls._meta, 'verbose_name', '') or model_name)

    return render(request, printout['template'], context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_download(request, model_name, record_id, template_key=None):
    """
    Generate PDF dan download sebagai file attachment.
    Dipanggil dari tombol "Download PDF" di toolbar preview.

    GET /api/print/{model_name}/{record_id}/download/
    GET /api/print/{model_name}/{record_id}/{printout_key}/download/
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    printout = _resolve_printout(model_cls, template_key)
    if not printout:
        return Response(
            {'error': f'Printout "{template_key}" tidak tersedia untuk {model_name}'},
            status=404,
        )

    record = get_object_or_404(
        model_cls.objects.filter(is_deleted=False), pk=record_id
    )

    if not hasattr(record, '_print_context'):
        return Response(
            {'error': f'Model "{model_name}" does not support printing'},
            status=400,
        )
    context = record._print_context()
    context['printout'] = printout
    context['model_label'] = str(getattr(model_cls._meta, 'verbose_name', '') or model_name)

    pdf_bytes = render_pdf(printout['template'], context)

    key_suffix = f'_{template_key}' if template_key else ''
    filename = f'{model_name.replace(".", "_")}{key_suffix}_{record_id}.pdf'
    return FileResponse(
        BytesIO(pdf_bytes),
        as_attachment=True,
        filename=filename,
        content_type='application/pdf',
    )
