"""
Field validator for import — auto-skip compute/virtual/one2many, lookup Many2One, validate types.
Handles One2Many child fields (headers with `/` separator).
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.db import models as dj_models
from core.model_api import get_model_class
from core.model_meta import ErpModelBase
from .parser import separate_parent_child


# Fields that are never importable (base Django fields)
BASE_SKIP_FIELDS = {'id', 'created_at', 'updated_at', 'created_by', 'is_deleted'}


def validate_file_data(parsed, model_name):
    """
    Validate parsed file data against model field definitions.

    Handles both flat parent fields and One2Many child fields (with / separator).

    Returns:
        dict with:
            - field_mapping: {header_label: field_name}
            - valid_rows: validated parent rows (deduped by reference)
            - error_rows: error rows
            - preview_rows: first 5 valid rows
            - child_groups: {relation: { child_headers, child_field_names, valid_rows, error_rows }}
            - total_rows, valid_count, error_count
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return {'error': f'Model "{model_name}" not found'}

    fd_map = model_cls._field_descriptors

    # --- 1. Separate parent vs child headers ---
    sep = separate_parent_child(parsed['headers'], parsed['rows'], model_cls)
    parent_headers = sep['parent_headers']
    parent_rows = sep['parent_rows']
    child_groups_raw = sep['child_groups']

    # --- 2. Build parent field mapping ---
    label_to_fname = {}
    for fname, fd in fd_map.items():
        if _should_skip(fd, fname):
            continue
        label = getattr(fd, 'label', None) or fname.replace('_', ' ').title()
        label_to_fname[fname] = fname
        label_to_fname[label.lower()] = fname
        label_to_fname[fname.replace('_', ' ').lower()] = fname

    parent_field_mapping = {}
    unmapped_headers = []
    for header in parent_headers:
        key = header.strip().lower()
        matched = label_to_fname.get(key)
        if matched:
            parent_field_mapping[header] = matched
        else:
            unmapped_headers.append(header)

    # --- 3. Validate parent rows ---
    parent_valid_rows = []
    parent_error_rows = []
    seen_references = {}  # ref -> row_index of first occurrence

    for idx, row in enumerate(parent_rows):
        row_index = idx + 2
        values = {}
        errors = {}

        for header, cell_val in zip(parent_headers, row):
            fname = parent_field_mapping.get(header)
            if not fname:
                continue
            fd = fd_map.get(fname)
            if not fd:
                continue

            # Detect "Reference" field for dedup
            cell_val = cell_val.strip() if isinstance(cell_val, str) else cell_val
            if not cell_val or cell_val == '':
                values[fname] = None
                continue

            error = _validate_cell(fd, fname, cell_val, model_cls)
            if error:
                errors[fname] = error['message']
                if error.get('suggestions'):
                    errors[f'{fname}_suggestions'] = error['suggestions']
            else:
                values[fname] = _parse_cell(fd, fname, cell_val, model_cls)

        # Track reference for dedup
        ref = values.get('reference') or str(row_index)

        if errors:
            parent_error_rows.append({'row_index': row_index, 'values': values, 'errors': errors, 'ref': ref})
        elif ref in seen_references:
            # Duplicate reference — skip parent creation, attach children
            parent_valid_rows.append(None)
        else:
            seen_references[ref] = row_index
            parent_valid_rows.append({'row_index': row_index, 'values': values, 'ref': ref})

    # --- 4. Validate child groups ---
    child_validations = {}
    for relation, group in child_groups_raw.items():
        child_fd = fd_map.get(relation)
        if not child_fd:
            continue

        child_model_name = getattr(child_fd, 'relation', None)
        child_model = ErpModelBase._model_registry.get(child_model_name) if child_model_name else None
        if not child_model:
            continue

        child_fd_map = child_model._field_descriptors

        # Build child field mapping (child_field_name → field_descriptor)
        child_label_map = {}
        for fname, fd in child_fd_map.items():
            if _should_skip(fd, fname):
                continue
            label = getattr(fd, 'label', None) or fname.replace('_', ' ').title()
            child_label_map[fname] = fname
            child_label_map[label.lower()] = fname
            child_label_map[fname.replace('_', ' ').lower()] = fname

        child_field_mapping = {}
        for header, field_name in zip(group['child_headers'], group['child_field_names']):
            matched = child_label_map.get(field_name.lower())
            if matched:
                child_field_mapping[header] = matched
            else:
                child_field_mapping[header] = field_name  # fallback

        # Validate each child row
        child_valid = []
        child_errors = []
        for idx, row in enumerate(group['child_rows']):
            row_index = idx + 2
            values = {}
            errors = {}

            # Get parent reference from corresponding parent row
            parent_ref = None
            if idx < len(parent_rows):
                for h, ref_col in zip(parent_headers, parent_rows[idx]):
                    if h.lower() in ('reference', 'ref'):
                        parent_ref = ref_col
                        break

            # Skip child rows if parent_ref is empty (no way to link)
            if not parent_ref:
                errors['_parent'] = 'Parent reference tidak ditemukan'
                child_errors.append({'row_index': row_index, 'values': values, 'errors': errors, 'parent_ref': ''})
                continue

            for header, cell_val in zip(group['child_headers'], row):
                fname = child_field_mapping.get(header)
                if not fname:
                    continue
                fd = child_fd_map.get(fname)
                if not fd:
                    continue

                cell_val = cell_val.strip() if isinstance(cell_val, str) else cell_val
                if not cell_val or cell_val == '':
                    values[fname] = None
                    continue

                error = _validate_cell(fd, fname, cell_val, child_model)
                if error:
                    errors[fname] = error['message']
                    if error.get('suggestions'):
                        errors[f'{fname}_suggestions'] = error['suggestions']
                else:
                    values[fname] = _parse_cell(fd, fname, cell_val, child_model)

            if errors:
                child_errors.append({'row_index': row_index, 'values': values, 'errors': errors, 'parent_ref': parent_ref})
            else:
                child_valid.append({'row_index': row_index, 'values': values, 'parent_ref': parent_ref})

        child_validations[relation] = {
            'child_headers': group['child_headers'],
            'child_field_names': group['child_field_names'],
            'valid_rows': child_valid,
            'error_rows': child_errors,
            'valid_count': len(child_valid),
            'error_count': len(child_errors),
        }

    # --- 5. Compile results ---
    # Filter out None entries (duplicate references)
    final_valid = [r for r in parent_valid_rows if r is not None]

    preview_rows = [r['values'] for r in final_valid[:5]]

    return {
        'field_mapping': parent_field_mapping,
        'unmapped_headers': unmapped_headers,
        'valid_rows': final_valid,
        'error_rows': parent_error_rows,
        'preview_rows': preview_rows,
        'total_rows': len(parsed['rows']),
        'valid_count': len(final_valid),
        'error_count': len(parent_error_rows),
        'child_groups': child_validations,
        'has_child_data': bool(child_validations),
    }


def _should_skip(fd, fname):
    """Check if field should be skipped in import."""
    if fname in BASE_SKIP_FIELDS:
        return True
    if getattr(fd, 'compute', None):
        return True
    if getattr(fd, 'virtual', False):
        return True
    if getattr(fd, 'field_type', None) == 'one2many':
        return True
    return False


def _get_m2o_suggestions(fd, limit=10):
    """Return list of available records for a Many2One field (for error suggestions)."""
    relation = getattr(fd, 'relation', None)
    if not relation or not isinstance(relation, str):
        return []
    related_model = ErpModelBase._model_registry.get(relation)
    if not related_model:
        return []
    qs = related_model.objects.filter(is_deleted=False)[:limit]
    suggestions = []
    for obj in qs:
        label = getattr(obj, 'name', None) or getattr(obj, 'code', None) or f'#{obj.pk}'
        suggestions.append(label)
    return suggestions


def _validate_cell(fd, fname, value, model_cls):
    """Validate a single cell value. Returns None if valid, or dict with error info if invalid."""
    ftype = getattr(fd, 'field_type', None)

    if ftype == 'many2one':
        result = _lookup_m2o(fd, value)
        if result is None:
            suggestions = _get_m2o_suggestions(fd, limit=20)
            return {'message': f'"{value}" tidak ditemukan', 'suggestions': suggestions, 'total_suggestions': len(suggestions)}
        return None

    if ftype in ('date', 'datetime'):
        try:
            _parse_date(value)
        except ValueError:
            return {'message': f'Format tanggal salah (harus YYYY-MM-DD), got "{value}"', 'suggestions': [], 'total_suggestions': 0}
        return None

    if ftype in ('monetary', 'float'):
        try:
            Decimal(str(value).replace(',', ''))
        except InvalidOperation:
            return {'message': f'Harus angka, got "{value}"', 'suggestions': [], 'total_suggestions': 0}
        return None

    if ftype == 'integer':
        try:
            int(str(value).replace(',', ''))
        except ValueError:
            return {'message': f'Harus bilangan bulat, got "{value}"', 'suggestions': [], 'total_suggestions': 0}
        return None

    if ftype == 'boolean':
        normalized = str(value).strip().lower()
        if normalized not in ('true', 'false', 'yes', 'no', '1', '0', 'y', 'n'):
            return {'message': f'Harus Yes/No/True/False/1/0, got "{value}"', 'suggestions': [], 'total_suggestions': 0}
        return None

    if ftype == 'selection':
        options = getattr(fd, 'options', [])
        option_values = {o if isinstance(o, str) else o[0] for o in options}
        if value not in option_values:
            option_labels = ', '.join(sorted(option_values))
            return {'message': f'Pilihan tidak valid. Opsi: {option_labels}', 'suggestions': [], 'total_suggestions': 0}
        return None

    return None


def _parse_cell(fd, fname, value, model_cls):
    """Parse cell value to Python type."""
    if value is None or value == '':
        return None
    ftype = getattr(fd, 'field_type', None)

    if ftype == 'many2one':
        result = _lookup_m2o(fd, value)
        return result.id if result else None
    if ftype == 'date':
        try:
            return _parse_date(value).isoformat()
        except ValueError:
            return value
    if ftype == 'monetary':
        try:
            return float(str(value).replace(',', ''))
        except (ValueError, InvalidOperation):
            return value
    if ftype == 'float':
        try:
            return float(str(value).replace(',', ''))
        except (ValueError, InvalidOperation):
            return value
    if ftype == 'integer':
        try:
            return int(str(value).replace(',', ''))
        except (ValueError, InvalidOperation):
            return value
    if ftype == 'boolean':
        normalized = str(value).strip().lower()
        return normalized in ('true', 'yes', '1', 'y')
    return value


def _parse_date(value):
    """Parse date string to datetime.date."""
    if isinstance(value, str):
        value = value.strip()
    return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()


def _lookup_m2o(fd, value):
    """
    Lookup a Many2One record by value.
    Priority: name → code → id (numeric)
    """
    relation = getattr(fd, 'relation', None)
    if not relation or not isinstance(relation, str):
        return None
    related_model = ErpModelBase._model_registry.get(relation)
    if not related_model:
        return None
    qs = related_model.objects.filter(is_deleted=False)

    if hasattr(related_model, 'name'):
        obj = qs.filter(name__iexact=str(value)).first()
        if obj:
            return obj
    if hasattr(related_model, 'code'):
        obj = qs.filter(code__iexact=str(value)).first()
        if obj:
            return obj
    if str(value).isdigit():
        obj = qs.filter(pk=int(value)).first()
        if obj:
            return obj
    return None
