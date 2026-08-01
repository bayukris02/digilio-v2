"""
Auto-generating REST API for metadata-driven ERP models.

Endpoints:
  GET  /api/models/                          → List all registered models
  GET  /api/models/{model_name}/config/      → Get model config (fields + views)
  GET  /api/models/{model_name}/records/     → List records
  POST /api/models/{model_name}/records/     → Create record
  GET  /api/models/{model_name}/records/{id}/ → Get record detail
  PUT  /api/models/{model_name}/records/{id}/ → Update record
  DELETE /api/models/{model_name}/records/{id}/ → Soft-delete record
"""

from django.apps import apps
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import OuterRef, Subquery, Value
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from core.models.chatter_log import ChatterLog
from core.model_meta import ErpModelBase, BaseModel


def get_model_class(model_name):
    """Find ERP model class by _model_name."""
    for model in apps.get_models():
        if hasattr(model, '_field_descriptors') and model._field_descriptors:
            if model.get_model_name() == model_name:
                return model
    return None


def get_all_erp_models():
    """Return list of all registered ERP models."""
    result = []
    for model in apps.get_models():
        if hasattr(model, '_field_descriptors') and model._field_descriptors:
            result.append({
                'model_name': model.get_model_name(),
                'verbose_name': getattr(model._meta, 'verbose_name', model.__name__),
                'verbose_name_plural': getattr(model._meta, 'verbose_name_plural', f'{model.__name__}s'),
            })
    return result


def _recompute_child_lines(child_model, inverse_field, parent_pk):
    """After bulk_create, trigger compute pada child lines yang punya computed fields.
    
    bulk_create tidak trigger save() → computed fields (total, discount, tax, dll)
    tidak pernah terisi. Method ini loop & save ulang child lines agar compute jalan.
    """
    computed = child_model.get_computed_fields()
    if not computed:
        return
    for child in child_model.objects.filter(**{inverse_field: parent_pk, 'is_deleted': False}):
        child.save(update_fields=computed)


# ─── Models list endpoint ────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_list(request):
    """List all registered ERP models."""
    return Response(get_all_erp_models())


# ─── Model config endpoint ───────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_config(request, model_name):
    """Get model field definitions and view config."""
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)
    config = model_cls.get_model_config()
    config['_current_user_id'] = request.user.pk if request.user.is_authenticated else None
    return Response(config)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def model_compute(request, model_name):
    """Compute endpoint: partial data → run compute methods → return computed fields."""
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    data = request.data or {}

    # Optional: jika ada id di payload, load record dari DB
    # (agar computed fields seperti dp_amount bisa query cross-model)
    record_id = data.pop('id', None)
    if record_id is not None:
        try:
            obj = model_cls.objects.get(pk=record_id, is_deleted=False)
        except model_cls.DoesNotExist:
            return Response({'error': f'Record {record_id} not found'}, status=404)
    else:
        # Create in-memory instance (not saved), set provided fields
        try:
            obj = model_cls()
        except Exception:
            return Response({'error': f'Cannot instantiate {model_name}'}, status=400)

    for key, value in data.items():
        # Non-virtual fields: set normally via hasattr
        if hasattr(obj, key):
            fd = model_cls._field_descriptors.get(key)
            if fd and hasattr(fd, 'to_python'):
                value = fd.to_python(value)
            # FK fields (many2one) need _id suffix, not the relation name
            target_attr = f'{key}_id' if (fd and getattr(fd, 'field_type', None) == 'many2one') else key
            setattr(obj, target_attr, value)
        # Virtual fields: hasattr returns False, but set via _field_descriptors
        elif key in model_cls._field_descriptors:
            fd = model_cls._field_descriptors[key]
            if getattr(fd, 'virtual', False):
                setattr(obj, key, fd.to_python(value) if hasattr(fd, 'to_python') else value)
            elif getattr(fd, 'field_type', None) == 'one2many':
                if not hasattr(obj, '_tmp_one2many'):
                    obj._tmp_one2many = {}
                obj._tmp_one2many[key] = value

    try:
        obj._run_compute()
    except Exception as e:
        return Response({'error': f'Compute failed: {str(e)}'}, status=400)

    result = {}
    for fname in model_cls.get_computed_fields():
        val = getattr(obj, fname)
        fd = model_cls._field_descriptors.get(fname)
        if fd and hasattr(fd, 'to_representation'):
            val = fd.to_representation(val)
        result[fname] = val

    # Include per-line computed data jika ada (set oleh _compute_summary dkk)
    computed_lines = getattr(obj, '_computed_o2m_lines', None)
    if computed_lines:
        result['_computed_o2m_lines'] = computed_lines

    return Response(result)


# ─── Model records endpoint ──────────────────

def _log_field_changes(model_cls, obj, old_data=None, user=None):
    """Log all field changes (old → new) for a saved record.
    
    Args:
        model_cls: The ERP model class
        obj: The saved Django model instance
        old_data: Dict of old field values (None for create)
        user: The user who made the change (pk or None)
    """
    model_name = model_cls.get_model_name()
    pk = obj.pk
    user_pk = user.pk if hasattr(user, 'pk') else user

    for field_name, fd in model_cls._field_descriptors.items():
        # Skip virtual/system fields
        if field_name in ('id', 'is_deleted', 'created_at', 'updated_at', 'deleted_at', 'created_by'):
            continue
        if getattr(fd, 'field_type', None) == 'one2many':
            continue

        new_val = getattr(obj, field_name, None)
        old_val = old_data.get(field_name) if old_data else None

        # Normalize many2one: store pk not object
        if hasattr(new_val, 'pk'):
            new_val = new_val.pk
        if hasattr(old_val, 'pk'):
            old_val = old_val.pk

        # Convert to string for storage
        new_str = str(new_val) if new_val is not None else None
        old_str = str(old_val) if old_val is not None else None

        if old_str != new_str:
            ChatterLog.objects.create(
                model_name=model_name,
                record_id=pk,
                field_name=field_name,
                old_value=old_str,
                new_value=new_str,
                created_by=user_pk,
            )


def _log_child_changes(child_model, child_objs, old_child_data=None, inverse_field=None, user=None):
    """Log changes for child records (create only for now — put uses soft-delete+recreate)."""
    if not child_objs:
        return
    model_name = child_model.get_model_name()
    user_pk = user.pk if hasattr(user, 'pk') else user

    for i, obj in enumerate(child_objs):
        pk = obj.pk
        old = old_child_data[i] if old_child_data and i < len(old_child_data) else {}

        for field_name, fd in child_model._field_descriptors.items():
            if field_name in ('id', 'is_deleted', 'created_at', 'updated_at', 'deleted_at', 'created_by'):
                continue
            if getattr(fd, 'field_type', None) in ('one2many', 'many2one') and field_name == inverse_field:
                continue

            new_val = getattr(obj, field_name, None)
            old_val = old.get(field_name) if old else None

            if hasattr(new_val, 'pk'):
                new_val = new_val.pk
            if hasattr(old_val, 'pk'):
                old_val = old_val.pk

            new_str = str(new_val) if new_val is not None else None
            old_str = str(old_val) if old_val is not None else None

            if old_str != new_str:
                ChatterLog.objects.create(
                    model_name=model_name,
                    record_id=pk,
                    field_name=field_name,
                    old_value=old_str,
                    new_value=new_str,
                    created_by=user_pk,
                )


class ModelRecordView(APIView):
    permission_classes = [IsAuthenticated]

    def get_model(self, model_name):
        model_cls = get_model_class(model_name)
        if not model_cls:
            return None
        return model_cls

    def get(self, request, model_name, record_id=None):
        model_cls = self.get_model(model_name)
        if not model_cls:
            return Response({'error': f'Model "{model_name}" not found'}, status=404)

        if record_id:
            try:
                obj = model_cls.objects.get(pk=record_id, is_deleted=False)
                obj._run_compute()  # ensure virtual computed fields (due_amount, _bill_details etc.) are populated
                return Response(obj.to_record())
            except model_cls.DoesNotExist:
                return Response({'error': 'Record not found'}, status=404)
        else:
            # List records — use lightweight to_list_record() for performance
            objs = model_cls.objects.filter(is_deleted=False)
            # Generic eager-loading: select_related semua Many2One di list_view.columns
            # (1 query per relasi, bukan N+1 per record) — berlaku untuk SEMUA model
            list_columns = getattr(model_cls, '_list_view', {}).get('columns', [])
            m2o_select = []
            for col in list_columns:
                if not isinstance(col, str):
                    continue
                fd = model_cls._field_descriptors.get(col)
                if (
                    fd
                    and getattr(fd, 'field_type', None) == 'many2one'
                    and not getattr(fd, 'virtual', False)
                ):
                    m2o_select.append(col)
            if m2o_select:
                objs = objs.select_related(*m2o_select)
            # Support query param filtering: ?model_ref=purchase.order
            model_ref = request.query_params.get('model_ref')
            if model_ref and hasattr(model_cls, 'model_ref'):
                objs = objs.filter(**{'model_ref': model_ref})

            # ── Generic field filtering from query params ──
            # Model apa pun bisa difilter via: ?vendor=5&status=draft&payment_status=unpaid
            # Many2One fields otomatis pakai _id suffix.
            skip_params = {'page', 'page_size', 'model_ref', 'search'}

            # ── Global text search via ?search= ──
            # Cari di semua CharField/TextField dengan icontains (OR).
            search = request.query_params.get('search', '').strip()
            if search:
                from django.db.models import Q
                from core.fields import CharField as CoreCharField, TextField as CoreTextField
                search_q = Q()
                for key, fd in model_cls._field_descriptors.items():
                    if getattr(fd, 'virtual', False):
                        continue
                    if isinstance(fd, (CoreCharField, CoreTextField)):
                        search_q |= Q(**{f'{key}__icontains': search})
                if search_q:
                    objs = objs.filter(search_q)
            for param_key, param_val in request.query_params.items():
                if param_key in skip_params or not param_val:
                    continue
                fd = model_cls._field_descriptors.get(param_key)
                if fd:
                    if fd.field_type == 'many2one':
                        objs = objs.filter(**{f'{param_key}_id': param_val})
                    else:
                        objs = objs.filter(**{param_key: param_val})
                elif hasattr(model_cls, param_key):
                    objs = objs.filter(**{param_key: param_val})

            # Pagination: page_size=0 means "all records"
            page = int(request.query_params.get('page', 1))
            total = objs.count()
            page_size = request.query_params.get('page_size', None)
            if page_size is not None:
                page_size = int(page_size)
                if page_size == 0:
                    page_size = total
            else:
                # Default: 50
                page_size = 50

            offset = (page - 1) * page_size
            page_objs = list(objs[offset:offset + page_size])

            # Batch smart button counts — 1 query per smart button instead of N×M
            batch_counts = model_cls.batch_compute_smart_button_counts(page_objs)

            data = [
                obj.to_list_record(batch_counts=batch_counts.get(obj.pk, {}))
                for obj in page_objs
            ]

            return Response({
                'count': total,
                'results': data,
                'page': page,
                'page_size': page_size,
            })

    def post(self, request, model_name, record_id=None):
        model_cls = self.get_model(model_name)
        if not model_cls:
            return Response({'error': f'Model "{model_name}" not found'}, status=404)

        data = request.data
        # Remove read-only base fields
        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)
        data.pop('is_deleted', None)
        data.pop('created_by', None)
        data.pop('updated_by', None)

        # Remove virtual fields (frontend-only, no DB column)
        for key, fd in model_cls._field_descriptors.items():
            if getattr(fd, 'virtual', False) and key in data:
                data.pop(key)

        # Set created_by
        data['created_by'] = request.user if request.user.is_authenticated else None
        data['updated_by'] = request.user if request.user.is_authenticated else None

        # Normalize field values via field descriptors
        for key, fd in model_cls._field_descriptors.items():
            if key in data and hasattr(fd, 'to_python'):
                data[key] = fd.to_python(data[key])
            # Many2One: ubah jadi field_name_id untuk Django FK
            if fd.field_type == 'many2one' and key in data:
                if not isinstance(data[key], dict) and not hasattr(data[key], 'pk'):
                    data[f'{key}_id'] = data.pop(key)

        # Extract one2many nested data (pop from data so create() doesn't fail)
        one2many_data = {}
        for key, fd in model_cls._field_descriptors.items():
            if getattr(fd, 'field_type', None) == 'one2many' and key in data:
                one2many_data[key] = data.pop(key)

        try:
            obj = model_cls.objects.create(**data)
            # Handle one2many child records
            for field_name, lines in one2many_data.items():
                fd = model_cls._field_descriptors[field_name]
                child_model = get_model_class(fd.relation)
                if child_model and lines:
                    child_objs = []
                    child_field_names = set(child_model._field_descriptors.keys())
                    for line in lines:
                        # Remove keys not defined on the child model
                        # (e.g. display_name, _smart_button_previews from to_record())
                        for key in list(line.keys()):
                            if key not in child_field_names:
                                line.pop(key, None)
                            # Remove virtual fields (frontend-only, no DB column)
                            _vfd = child_model._field_descriptors.get(key)
                            if _vfd and getattr(_vfd, 'virtual', False):
                                line.pop(key, None)
                        line.pop('id', None)
                        line.pop('_key', None)  # frontend temp key
                        line.pop('created_at', None)
                        line.pop('updated_at', None)
                        line['is_deleted'] = False
                        line[fd.inverse_field] = obj
                        # Validate required fields BEFORE normalizing many2one
                        # (normalization pops the key, making required check fail)
                        for child_key, child_fd in child_model._field_descriptors.items():
                            if getattr(child_fd, 'required', False):
                                val = line.get(child_key)
                                if val is None or (isinstance(val, str) and not val.strip()):
                                    verbose = child_model._meta.verbose_name or child_model.__name__
                                    label = getattr(child_fd, 'label', None) or child_key
                                    return Response(
                                        {'error': f'{verbose}: {label} wajib diisi.'},
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                        # Normalize FK fields in child line (product: {id:5} → product_id:5)
                        for child_key, child_fd in child_model._field_descriptors.items():
                            if child_key in line and hasattr(child_fd, 'to_python'):
                                line[child_key] = child_fd.to_python(line[child_key])
                            if getattr(child_fd, 'field_type', None) == 'many2one' and child_key in line:
                                if not isinstance(line[child_key], dict) and not hasattr(line[child_key], 'pk'):
                                    line[f'{child_key}_id'] = line.pop(child_key)
                        child_objs.append(child_model(**line))
                    child_model.objects.bulk_create(child_objs)
                    _recompute_child_lines(child_model, fd.inverse_field, obj.pk)

            # Recompute parent summary setelah child lines diperbaiki
            if one2many_data:
                obj._run_compute()
                obj.save(update_fields=model_cls.get_computed_fields())

            # Log field changes
            _log_field_changes(model_cls, obj, user=getattr(request, 'user', None))
            if one2many_data:
                for field_name, lines in one2many_data.items():
                    fd = model_cls._field_descriptors[field_name]
                    child_model = get_model_class(fd.relation)
                    child_objs = list(child_model.objects.filter(**{fd.inverse_field: obj.pk, 'is_deleted': False}))
                    _log_child_changes(child_model, child_objs, inverse_field=fd.inverse_field, user=getattr(request, 'user', None))
            return Response(obj.to_record(), status=status.HTTP_201_CREATED)
        except ValidationError as e:
            msg = e.messages[0] if e.messages else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            # Unique constraint violation → clean message
            err_msg = str(e)
            if 'unique constraint' in err_msg.lower():
                # Extract field name from error like: 'Key (phone)=(...) already exists.'
                field_hint = err_msg.split('Key (')[-1].split(')')[0] if 'Key (' in err_msg else 'field'
                return Response({'error': f'Field \"{field_hint}\" must be unique'}, status=status.HTTP_409_CONFLICT)
            return Response({'error': 'Database integrity error'}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, model_name, record_id=None):
        if not record_id:
            return Response({'error': 'ID required'}, status=400)

        model_cls = self.get_model(model_name)
        if not model_cls:
            return Response({'error': f'Model "{model_name}" not found'}, status=404)

        try:
            obj = model_cls.objects.get(pk=record_id, is_deleted=False)
        except model_cls.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        # ── Enforce state allow_edit ──
        status_str = getattr(obj, 'status', None)
        state_config = model_cls._get_state_config(status_str) if hasattr(model_cls, '_get_state_config') else {}
        if state_config and not state_config.get('allow_edit', True):
            return Response(
                {'error': f'Cannot edit record with status "{status_str}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data
        # Remove read-only fields
        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)
        data.pop('is_deleted', None)
        data.pop('created_by', None)
        data.pop('updated_by', None)

        # Remove virtual fields (frontend-only, no DB column)
        for key, fd in model_cls._field_descriptors.items():
            if getattr(fd, 'virtual', False) and key in data:
                data.pop(key)

        # Normalize field values via field descriptors
        for key, fd in model_cls._field_descriptors.items():
            if key in data and hasattr(fd, 'to_python'):
                data[key] = fd.to_python(data[key])
            # Many2One: ubah jadi field_name_id untuk Django FK
            if fd.field_type == 'many2one' and key in data:
                if not isinstance(data[key], dict) and not hasattr(data[key], 'pk'):
                    data[f'{key}_id'] = data.pop(key)

        # Extract one2many nested data
        one2many_data = {}
        for key, fd in model_cls._field_descriptors.items():
            if getattr(fd, 'field_type', None) == 'one2many' and key in data:
                one2many_data[key] = data.pop(key)

        try:
            # Snapshot old field values before update (for chatter diff)
            old_data = {}
            for field_name, fd in model_cls._field_descriptors.items():
                if field_name in ('id', 'is_deleted', 'created_at', 'updated_at', 'deleted_at', 'created_by'):
                    continue
                if getattr(fd, 'field_type', None) == 'one2many':
                    continue
                val = getattr(obj, field_name, None)
                if hasattr(val, 'pk'):
                    val = val.pk
                old_data[field_name] = val

            # Snapshot old child records too
            old_child_objs = {}
            for key, fd in model_cls._field_descriptors.items():
                if getattr(fd, 'field_type', None) == 'one2many' and key in one2many_data:
                    child_model_cls = get_model_class(fd.relation)
                    if child_model_cls:
                        old_children = list(child_model_cls.objects.filter(
                            **{fd.inverse_field: obj.pk, 'is_deleted': False}
                        ))
                        if old_children:
                            old_child_objs[key] = [(c.to_record() if hasattr(c, 'to_record') else {f: getattr(c, f) for f in child_model_cls._field_descriptors if not hasattr(getattr(child_model_cls._field_descriptors[f], 'field_type', ''), 'one2many')}) for c in old_children]

            for key, value in data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            if request.user.is_authenticated:
                obj.updated_by = request.user
            obj.save()
            # Handle one2many: update existing children + soft-delete removed + create new
            for field_name, lines in one2many_data.items():
                fd = model_cls._field_descriptors[field_name]
                child_model = get_model_class(fd.relation)
                if child_model:
                    # 1. Get existing non-deleted children
                    existing_qs = child_model.objects.filter(
                        **{fd.inverse_field: obj.pk, 'is_deleted': False}
                    )
                    existing_map = {c.pk: c for c in existing_qs}
                    submitted_ids = set()
                    for line in (lines or []):
                        lid = line.get('id')
                        if lid is not None:
                            submitted_ids.add(int(lid))

                    # 2. Soft-delete children that user removed (not in submitted)
                    removed_ids = set(existing_map.keys()) - submitted_ids
                    if removed_ids:
                        child_model.objects.filter(pk__in=removed_ids).update(is_deleted=True)

                    # 3. Update existing / create new from payload
                    if lines:
                        child_objs = []
                        child_field_names = set(child_model._field_descriptors.keys())
                        for line in lines:
                            # Simpan id SEBELUM di-pop oleh cleanup di bawah
                            line_id = line.get('id')
                            # Remove keys not defined on the child model
                            # (e.g. display_name, _smart_button_previews from to_record())
                            for key in list(line.keys()):
                                if key not in child_field_names:
                                    line.pop(key, None)
                                # Remove virtual fields (frontend-only, no DB column)
                                _vfd = child_model._field_descriptors.get(key)
                                if _vfd and getattr(_vfd, 'virtual', False):
                                    line.pop(key, None)
                            line.pop('_key', None)
                            line.pop('created_at', None)
                            line.pop('updated_at', None)
                            line['is_deleted'] = False
                            line[fd.inverse_field] = obj
                            # Validate required fields BEFORE normalizing many2one
                            # (normalization pops the key, making required check fail)
                            for child_key, child_fd in child_model._field_descriptors.items():
                                if getattr(child_fd, 'required', False):
                                    val = line.get(child_key)
                                    if val is None or (isinstance(val, str) and not val.strip()):
                                        verbose = child_model._meta.verbose_name or child_model.__name__
                                        label = getattr(child_fd, 'label', None) or child_key
                                        return Response(
                                            {'error': f'{verbose}: {label} wajib diisi.'},
                                            status=status.HTTP_400_BAD_REQUEST,
                                        )
                            # Normalize FK fields in child line
                            for child_key, child_fd in child_model._field_descriptors.items():
                                if child_key in line and hasattr(child_fd, 'to_python'):
                                    line[child_key] = child_fd.to_python(line[child_key])
                                if getattr(child_fd, 'field_type', None) == 'many2one' and child_key in line:
                                    if not isinstance(line[child_key], dict) and not hasattr(line[child_key], 'pk'):
                                        line[f'{child_key}_id'] = line.pop(child_key)

                            lid = line.pop('id', None) if 'id' in line else line_id
                            if lid is not None and int(lid) in existing_map:
                                # UPDATE existing record (not touched by soft-delete)
                                child_model.objects.filter(pk=int(lid)).update(**line)
                                # Re-fetch the updated record for compute
                                child_objs.append(child_model.objects.get(pk=int(lid)))
                            else:
                                # CREATE new record
                                child_objs.append(child_model(**line))

                        if child_objs:
                            child_model.objects.bulk_create(
                                [c for c in child_objs if c.pk is None]
                            )
                        _recompute_child_lines(child_model, fd.inverse_field, obj.pk)

            # Recompute parent summary setelah child lines diperbaiki
            if one2many_data:
                obj._run_compute()
                obj.save(update_fields=model_cls.get_computed_fields())

            # Log field changes for parent
            _log_field_changes(model_cls, obj, old_data=old_data, user=getattr(request, 'user', None))
            # Log child changes (new children created after soft-delete)
            for field_name, lines in one2many_data.items():
                fd = model_cls._field_descriptors[field_name]
                child_model = get_model_class(fd.relation)
                if child_model and lines:
                    new_children = list(child_model.objects.filter(
                        **{fd.inverse_field: obj.pk, 'is_deleted': False}
                    ).order_by('pk'))
                    _log_child_changes(child_model, new_children,
                        old_child_data=old_child_objs.get(field_name),
                        inverse_field=fd.inverse_field,
                        user=getattr(request, 'user', None))
            return Response(obj.to_record())
        except ValidationError as e:
            msg = e.messages[0] if e.messages else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            err_msg = str(e)
            if 'unique constraint' in err_msg.lower():
                field_hint = err_msg.split('Key (')[-1].split(')')[0] if 'Key (' in err_msg else 'field'
                return Response({'error': f'Field \"{field_hint}\" must be unique'}, status=status.HTTP_409_CONFLICT)
            return Response({'error': 'Database integrity error'}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, model_name, record_id=None):
        if not record_id:
            return Response({'error': 'ID required'}, status=400)

        model_cls = self.get_model(model_name)
        if not model_cls:
            return Response({'error': f'Model "{model_name}" not found'}, status=404)

        try:
            obj = model_cls.objects.get(pk=record_id, is_deleted=False)
        except model_cls.DoesNotExist:
            return Response({'error': 'Record not found'}, status=404)

        # ── Enforce state allow_delete ──
        status_str = getattr(obj, 'status', None)
        state_config = model_cls._get_state_config(status_str) if hasattr(model_cls, '_get_state_config') else {}
        if state_config and not state_config.get('allow_delete', True):
            return Response(
                {'error': f'Cannot delete record with status "{status_str}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Enforce document flow: children block delete ──
        can_del, del_msg = obj._can_delete()
        if not can_del:
            return Response({'error': del_msg}, status=status.HTTP_400_BAD_REQUEST)

        obj.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Chatter Logs Endpoint ──────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatter_logs(request, model_name, record_id):
    """Get all chatter logs for a record."""
    logs = ChatterLog.objects.filter(
        model_name=model_name,
        record_id=record_id,
    ).annotate(
        created_by_name=Subquery(
            User.objects.filter(pk=OuterRef('created_by')).values('username')[:1]
        )
    ).values(
        'id', 'field_name', 'old_value', 'new_value', 'created_by', 'created_by_name', 'created_at'
    ).order_by('-created_at')[:100]
    return Response(list(logs))


# ─── Model Action Endpoint ──────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def model_action(request, model_name, record_id):
    """Execute a named action on a record.

    Two modes:
    1. State transition (via _transitions config) — core handles status change
    2. Legacy action (via _action_{name} method) — for print, email, etc.

    POST body: {"action": "confirm"}
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    action_name = request.data.get('action', '')
    if not action_name:
        return Response({'error': 'action name required'}, status=400)

    try:
        obj = model_cls.objects.get(pk=record_id, is_deleted=False)
    except model_cls.DoesNotExist:
        return Response({'error': 'Record not found'}, status=404)

    # ── Mode 1: Try state transition via _transitions ──
    transition = model_cls._find_transition(action_name) if hasattr(model_cls, '_find_transition') else None
    if transition:
        current_status = getattr(obj, 'status', None)
        allowed_from = transition.get('from', [])

        # Validate current status
        if allowed_from and current_status not in allowed_from:
            return Response({
                'error': f'Cannot {action_name}: current status is "{current_status}". '
                         f'Allowed states: {", ".join(allowed_from)}'
            }, status=400)

        # Run guard method (if defined)
        guard_name = transition.get('guard')
        if guard_name:
            guard_method = getattr(obj, guard_name, None)
            if guard_method:
                try:
                    guard_result = guard_method()
                    if guard_result is not None:
                        # guard returned dict → merge into response (like redirect info)
                        if isinstance(guard_result, dict) and guard_result.get('_action_type'):
                            pass  # let it pass through
                except Exception as e:
                    return Response({'error': str(e)}, status=400)

        # Apply the transition: change status
        target_state = transition.get('to', current_status)
        setattr(obj, 'status', target_state)

        # Run effect method (if defined) — before save, so it can modify other fields
        effect_name = transition.get('effect')
        effect_result = None
        if effect_name:
            effect_method = getattr(obj, effect_name, None)
            if effect_method:
                try:
                    effect_result = effect_method()
                except Exception as e:
                    return Response({'error': str(e)}, status=400)

        if request.user.is_authenticated:
            obj.updated_by = request.user
        obj.save()

        # Refresh from DB and return
        obj.refresh_from_db()
        response_data = obj.to_record()
        if effect_result and isinstance(effect_result, dict):
            for k, v in effect_result.items():
                response_data[k] = v
        if '_action_type' not in response_data:
            response_data['_action_type'] = 'refresh'

        return Response(response_data)

    # ── Mode 2: Legacy _action_{name} method (print, email, etc.) ──
    method_name = f'_action_{action_name}'
    action_method = getattr(obj, method_name, None)
    if not action_method:
        return Response({'error': f'Action "{action_name}" not found on {model_name}'}, status=404)

    try:
        # Pass request data (minus 'action' key) to action method
        # Methods that don't need it can accept *args, **kwargs
        extra_data = {k: v for k, v in request.data.items() if k != 'action'}
        result = action_method(extra_data)
        # Refresh obj from DB (action may have changed fields)
        obj.refresh_from_db()
        # Return updated record + action metadata
        response_data = obj.to_record()
        if result:
            for k, v in result.items():
                response_data[k] = v
        if '_action_type' not in response_data:
            response_data['_action_type'] = 'refresh'
        return Response(response_data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def model_create_child(request, model_name, record_id):
    """
    Create a child document from a parent record.

    POST /api/models/{parent_model}/records/{id}/create_child/
    body: {"child_model": "purchase.goods_receipt"}

    Uses _document_flow config on the parent model to:
    - Validate parent state
    - Enforce constraints (max_per_parent, unique)
    - Apply field mapping from parent → child
    - Set source field on child
    - Create the child record (default status = first state)
    """
    model_cls = get_model_class(model_name)
    if not model_cls:
        return Response({'error': f'Model "{model_name}" not found'}, status=404)

    child_model_name = request.data.get('child_model', '')
    if not child_model_name:
        return Response({'error': 'child_model required'}, status=400)

    child_cfg = model_cls._get_child_flow(child_model_name) if hasattr(model_cls, '_get_child_flow') else None
    if not child_cfg:
        return Response({'error': f'Model "{model_name}" has no child flow for "{child_model_name}"'}, status=400)

    child_model_cls = get_model_class(child_model_name)
    if not child_model_cls:
        return Response({'error': f'Child model "{child_model_name}" not found'}, status=404)

    try:
        obj = model_cls.objects.get(pk=record_id, is_deleted=False)
    except model_cls.DoesNotExist:
        return Response({'error': 'Parent record not found'}, status=404)

    # ── Validate parent state ──
    allowed_states = child_cfg.get('state_conditions', {}).get('allowed_parent_states', [])
    parent_status = getattr(obj, 'status', None)
    if allowed_states and parent_status not in allowed_states:
        allowed_labels = ', '.join(allowed_states)
        return Response({
            'error': f'Cannot create {child_cfg["label"]}: parent status is '
                     f'"{parent_status}". Allowed states: {allowed_labels}'
        }, status=400)

    # ── Enforce constraints ──
    source_field = child_cfg.get('source_field_in_child', 'source_document_id')
    constraints = child_cfg.get('constraints', {})

    if constraints.get('unique_per_parent'):
        existing = child_model_cls.objects.filter(
            **{source_field: obj.pk, 'is_deleted': False}
        ).exists()
        if existing:
            return Response({
                'error': f'A {child_cfg["label"]} already exists for this document. '
                         f'Only one is allowed.'
            }, status=400)

    max_children = constraints.get('max_per_parent')
    if max_children is not None:
        existing_count = child_model_cls.objects.filter(
            **{source_field: obj.pk, 'is_deleted': False}
        ).count()
        if existing_count >= max_children:
            return Response({
                'error': f'Maximum {max_children} {child_cfg["label"]}(s) allowed per parent.'
            }, status=400)

    # ── Apply mapping ──
    child_data = obj._run_child_mapping(child_cfg)

    # ── Set source field ──
    child_data[source_field] = obj.pk

    # ── Set default status (first state from child model) ──
    if child_model_cls._states:
        first_state = list(child_model_cls._states.keys())[0]
        if 'status' not in child_data:
            child_data['status'] = first_state

    # ── Set created_by ──
    child_data['created_by'] = request.user if request.user.is_authenticated else None

    # ── Create child ──
    try:
        # Remove virtual fields (frontend-only, no DB column)
        for key, fd in child_model_cls._field_descriptors.items():
            if getattr(fd, 'virtual', False) and key in child_data:
                child_data.pop(key)

        # Normalize field values
        for key, fd in child_model_cls._field_descriptors.items():
            if key in child_data and hasattr(fd, 'to_python'):
                child_data[key] = fd.to_python(child_data[key])
            # Many2One: ubah jadi field_name_id untuk Django FK
            if getattr(fd, 'field_type', None) == 'many2one' and key in child_data:
                if not isinstance(child_data[key], dict) and not hasattr(child_data[key], 'pk'):
                    child_data[f'{key}_id'] = child_data.pop(key)

        child_obj = child_model_cls.objects.create(**child_data)

        # Log creation
        _log_field_changes(child_model_cls, child_obj, user=getattr(request, 'user', None))

        # Return with redirect info for frontend
        response_data = child_obj.to_record()
        response_data['_action_type'] = 'redirect'
        response_data['_redirect_model'] = child_model_name
        response_data['_redirect_id'] = child_obj.pk
        return Response(response_data, status=status.HTTP_201_CREATED)

    except ValidationError as e:
        msg = e.messages[0] if e.messages else str(e)
        return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
    except IntegrityError as e:
        err_msg = str(e)
        if 'unique constraint' in err_msg.lower():
            field_hint = err_msg.split('Key (')[-1].split(')')[0] if 'Key (' in err_msg else 'field'
            return Response({'error': f'Field "{field_hint}" must be unique'}, status=status.HTTP_409_CONFLICT)
        return Response({'error': 'Database integrity error'}, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)