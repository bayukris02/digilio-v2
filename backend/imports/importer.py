"""
Execute validated import — create parent + child records with partial import support.
"""
from django.db import transaction
from core.model_api import get_model_class
from core.model_meta import ErpModelBase


def execute_import(model_name, valid_rows, error_rows, field_mapping, unmapped_headers, child_groups=None):
    """
    Execute import — create records from validated rows.

    If child_groups is provided, create parent record first, then children linked via FK.

    Returns:
        dict: { imported: int, skipped: int, errors: [{row, message}] }
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return {'imported': 0, 'skipped': 0, 'errors': [{'row': 0, 'message': f'Model "{model_name}" not found'}]}

    imported = 0
    errors = []
    fd_map = model_cls._field_descriptors

    # Report pre-validated errors
    for er in error_rows:
        for fname, msg in er.get('errors', {}).items():
            if fname.endswith('_suggestions'):
                continue
            errors.append({'row': er['row_index'], 'message': f'Field "{fname}": {msg}'})

    # Build parent_ref -> child_rows mapping from child_groups
    parent_children = {}
    if child_groups:
        for relation, group in child_groups.items():
            for row in group.get('valid_rows', []):
                child_values = dict(row['values'])
                parent_children.setdefault(row.get('parent_ref'), []).append({
                    'relation': relation,
                    'values': child_values,
                    'child_model_name': getattr(fd_map.get(relation), 'relation', None),
                    'inverse_field': getattr(fd_map.get(relation), 'inverse_field', None),
                })

    # Process valid parent rows
    for row in valid_rows:
        try:
            values = dict(row['values'])
            clean = {}

            for fname, val in values.items():
                if val is None:
                    continue
                fd = fd_map.get(fname)
                if not fd:
                    clean[fname] = val
                    continue

                # Resolve Many2One FK
                if getattr(fd, 'field_type', None) == 'many2one':
                    relation = getattr(fd, 'relation', None)
                    if relation and isinstance(relation, str):
                        related_model = ErpModelBase._model_registry.get(relation)
                        if related_model:
                            instance = related_model.objects.filter(pk=int(val)).first()
                            if instance:
                                clean[fname] = instance
                                continue

                clean[fname] = val

            with transaction.atomic():
                parent = model_cls.objects.create(**clean)
                imported += 1

                # Create child records
                ref = row.get('ref')
                children = parent_children.get(ref, [])
                for cdata in children:
                    child_model = ErpModelBase._model_registry.get(cdata['child_model_name'])
                    if not child_model:
                        continue

                    child_clean = {}
                    inverse_field = cdata['inverse_field']
                    child_fd_map = child_model._field_descriptors if hasattr(child_model, '_field_descriptors') else {}

                    for fname, val in cdata['values'].items():
                        if val is None:
                            continue
                        fd = child_fd_map.get(fname)
                        if not fd:
                            child_clean[fname] = val
                            continue

                        # Resolve Many2One FK in children
                        if getattr(fd, 'field_type', None) == 'many2one':
                            relation = getattr(fd, 'relation', None)
                            if relation and isinstance(relation, str):
                                related_model = ErpModelBase._model_registry.get(relation)
                                if related_model:
                                    instance = related_model.objects.filter(pk=int(val)).first()
                                    if instance:
                                        child_clean[fname] = instance
                                        continue
                        child_clean[fname] = val

                    # Link child to parent via inverse field
                    if inverse_field:
                        child_clean[inverse_field] = parent

                    child_model.objects.create(**child_clean)

        except Exception as e:
            errors.append({'row': row.get('row_index', '?'), 'message': str(e)})

    return {
        'imported': imported,
        'skipped': len(error_rows),
        'errors': errors,
    }
