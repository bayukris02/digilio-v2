"""
Import views — preview, template download, execute.

Endpoints:
    POST /api/import/{model_name}/preview/
    GET  /api/import/{model_name}/template/
    POST /api/import/{model_name}/execute/
"""
import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.model_api import get_model_class
from core.model_meta import ErpModelBase
from .parser import parse_file
from .validator import validate_file_data, _should_skip
from .importer import execute_import


BASE_SKIP_FIELDS = {'id', 'created_at', 'updated_at', 'created_by', 'is_deleted'}


def _get_importable_fields(model_cls):
    """Return fields that can be imported (not compute, virtual, one2many, base)."""
    result = []
    for fname, fd in model_cls._field_descriptors.items():
        if _should_skip(fd, fname):
            continue
        label = getattr(fd, 'label', None) or fname.replace('_', ' ').title()
        result.append((fname, label))
    return result


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_template(request, model_name):
    """
    Download CSV template with header columns for importable fields.

    GET /api/import/{model_name}/template/
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    fields = _get_importable_fields(model_cls)
    headers = [label for _, label in fields]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_template.csv"'

    writer = csv.writer(response)
    writer.writerow(headers)

    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_import(request, model_name):
    """
    Upload file → parse → validate → return preview.

    POST /api/import/{model_name}/preview/
    Body: multipart/form-data with 'file' field
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'No file uploaded'}, status=400)

    sheet_name = request.data.get('sheet_name', None)

    try:
        parsed = parse_file(file_obj, sheet_name)
    except Exception as e:
        return Response({'error': f'Failed to parse file: {str(e)}'}, status=400)

    validation = validate_file_data(parsed, model_name)

    return Response({
        'sheets': parsed.get('sheets', []),
        'selected_sheet': sheet_name or (parsed['sheets'][0] if parsed.get('sheets') else None),
        'total_rows': validation.get('total_rows', 0),
        'valid_count': validation.get('valid_count', 0),
        'error_count': validation.get('error_count', 0),
        'field_mapping': validation.get('field_mapping', {}),
        'unmapped_headers': validation.get('unmapped_headers', []),
        'preview_rows': validation.get('preview_rows', []),
        'valid_rows': validation.get('valid_rows', []),
        'error_rows': validation.get('error_rows', []),
        'has_child_data': validation.get('has_child_data', False),
        'child_groups': validation.get('child_groups', {}),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_import_view(request, model_name):
    """
    Execute import with validated data.

    POST /api/import/{model_name}/execute/
    Body: JSON with validation results from preview
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    valid_rows = request.data.get('valid_rows', [])
    error_rows = request.data.get('error_rows', [])
    field_mapping = request.data.get('field_mapping', {})
    unmapped_headers = request.data.get('unmapped_headers', [])
    child_groups = request.data.get('child_groups', {})

    total = len(valid_rows) + len(error_rows)

    if total == 0:
        return Response({'error': 'No data to import'}, status=400)

    if total > 100:
        return Response({
            'error': f'File terlalu besar ({total} rows). Maks 100 rows untuk import synchronous.',
        }, status=400)

    result = execute_import(model_name, valid_rows, error_rows, field_mapping, unmapped_headers, child_groups)

    return Response(result)
