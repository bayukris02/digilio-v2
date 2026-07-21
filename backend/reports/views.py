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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_preview(request, model_name, record_id):
    """
    Render print preview as HTML (with print CSS).
    Dipanggil via fetch dari halaman yang sama — JWT via Authorization header.

    GET /api/print/{model_name}/{record_id}/preview/
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    record = get_object_or_404(
        model_cls.objects.filter(is_deleted=False), pk=record_id
    )

    if not hasattr(record, '_print_context'):
        return Response(
            {'error': f'Model "{model_name}" does not support printing'},
            status=400,
        )

    context = record._print_context()
    context['pdf_download_url'] = f'/api/print/{model_name}/{record_id}/download/'
    context['model_name'] = model_name
    context['record_id'] = record_id

    template_name = f'print/{model_name.replace(".", "_")}.html'
    return render(request, template_name, context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_download(request, model_name, record_id, template_id=None):
    """
    Generate PDF dan download sebagai file attachment.
    Dipanggil dari tombol "Download PDF" di toolbar preview.

    GET /api/print/{model_name}/{record_id}/download/
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    record = get_object_or_404(
        model_cls.objects.filter(is_deleted=False), pk=record_id
    )

    if not hasattr(record, '_print_context'):
        return Response(
            {'error': f'Model "{model_name}" does not support printing'},
            status=400,
        )
    context = record._print_context()

    template_name = f'{model_name.replace(".", "_")}.html'
    pdf_bytes = render_pdf(template_name, context)

    filename = f'{model_name.replace(".", "_")}_{record_id}.pdf'
    return FileResponse(
        BytesIO(pdf_bytes),
        as_attachment=True,
        filename=filename,
        content_type='application/pdf',
    )
