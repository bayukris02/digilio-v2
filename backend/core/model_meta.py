"""
Metaclass and base model for metadata-driven ERP models.

Usage:
    class PurchaseOrder(BaseModel):
        _model_name = 'purchase.order'
        _fields = {
            'reference': CharField(label='Reference', required=True),
            'vendor': CharField(label='Vendor'),
            ...
        }
        
    → Auto-creates Django model fields
    → Auto-generates API config endpoint
    → Auto-creates CRUD viewset
"""

import json
from django.db import models as dj_models
from django.db.models.base import ModelBase
from django.db.models import Count
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from .fields import BaseField, Many2OneField, One2ManyField, MonetaryField, DateField, DateTimeField, BooleanField


class ErpModelBase(ModelBase):
    """Metaclass that converts `_fields` descriptors into real Django model fields."""

    # Registry: _model_name → Django model class (populated as classes are created)
    _model_registry: dict = {}
    # Pending FK fields: [(model_class, field_name, erp_relation_str), ...]
    _pending_fk: list = []

    def __new__(mcs, name, bases, attrs):
        # Only process classes that define _fields
        field_descriptors = attrs.get('_fields', {})
        if not field_descriptors and any(hasattr(b, '_fields') for b in bases):
            # Inherit _fields from parent
            pass

        # ── Auto-generate 'status' field from _states ──
        states = attrs.get('_states', {})
        if states:
            status_options = [
                (state, info.get('label', state.title()))
                for state, info in states.items()
            ]
            status_colors = {
                state: info.get('color', 'default')
                for state, info in states.items()
            }
            first_state = list(states.keys())[0]
            # Only inject if _fields doesn't already define 'status'
            if 'status' not in field_descriptors:
                from .fields import SelectionField
                field_descriptors['status'] = SelectionField(
                    label='Status',
                    default=first_state,
                    options=status_options,
                    colors=status_colors,
                )
                attrs['_fields'] = field_descriptors

        django_fields = {}
        m2o_fields = {}
        virtual_fields = {}

        for field_name, fd in field_descriptors.items():
            if isinstance(fd, One2ManyField) or getattr(fd, 'virtual', False):
                virtual_fields[field_name] = fd
                continue

            df = fd.to_django_field()

            if isinstance(fd, Many2OneField):
                # FK field — store descriptor for post-processing
                m2o_fields[field_name] = (fd, df)
            else:
                django_fields[field_name] = df

        # Add Django fields to attrs
        attrs.update(django_fields)

        # Create the class
        new_class = super().__new__(mcs, name, bases, attrs)

        # Register this model in the global registry
        if hasattr(new_class, '_model_name') and new_class._model_name:
            mcs._model_registry[new_class._model_name] = new_class

        # Add M2O fields (FK) after class creation
        for field_name, (fd, df) in m2o_fields.items():
            # Resolve relation
            relation = fd.relation
            if relation and isinstance(relation, str):
                to_model = mcs._model_registry.get(relation)
                if to_model is not None:
                    # Related model already registered → create FK directly
                    df = dj_models.ForeignKey(
                        to_model,
                        on_delete=dj_models.SET_NULL,
                        blank=not fd.required,
                        null=True,
                        verbose_name=fd.label,
                        help_text=fd.help_text,
                        related_name='+',
                    )
                else:
                    # Related model not yet loaded → queue for resolution
                    mcs._pending_fk.append((new_class, field_name, relation))
                    df = dj_models.ForeignKey(
                        'self',
                        on_delete=dj_models.SET_NULL,
                        blank=not fd.required,
                        null=True,
                        verbose_name=fd.label,
                        help_text=fd.help_text,
                        related_name='+',
                    )
            elif relation:
                df = dj_models.ForeignKey(
                    relation,
                    on_delete=dj_models.SET_NULL,
                    blank=not fd.required,
                    null=True,
                    verbose_name=fd.label,
                    help_text=fd.help_text,
                    related_name='+',
                )

            df.contribute_to_class(new_class, field_name)

        # Try to resolve any pending FK fields now that this model registered
        mcs._resolve_pending_fk()

        # Store field descriptors and virtual fields
        new_class._field_descriptors = field_descriptors
        new_class._virtual_fields = virtual_fields

        return new_class

    @classmethod
    def _resolve_pending_fk(mcs):
        """Resolve FK fields whose related model has now been registered."""
        still_pending = []
        for model_cls, field_name, erp_relation in mcs._pending_fk:
            to_model = mcs._model_registry.get(erp_relation)
            if to_model is None:
                still_pending.append((model_cls, field_name, erp_relation))
                continue

            # Get the existing FK field and fix its remote model
            field = model_cls._meta.get_field(field_name)
            if isinstance(field, dj_models.ForeignKey):
                field.remote_field.model = to_model
        mcs._pending_fk = still_pending


class BaseModel(dj_models.Model, metaclass=ErpModelBase):
    """
    Abstract base for all ERP models.
    Inherit this to get: audit trail, soft-delete, metadata API, auto CRUD,
    state machine, and document flow.
    """
    _model_name = None  # e.g., 'purchase.order'
    _fields = {}  # { 'field_name': FieldDescriptor(...), ... }
    _display_name = None  # Field to use for display in breadcrumbs, e.g. 'reference', 'code', 'name'

    # ── State Machine (optional) ──
    # Defines valid statuses and their config.
    # Auto-generates 'status' field, allow_edit/allow_delete enforcement.
    # Example:
    #   _states = {
    #       'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
    #       'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
    #       'done': {'allow_edit': False, 'allow_delete': False, 'label': 'Done', 'color': 'success'},
    #       'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    #   }
    _states = None

    # ── Transitions (optional, requires _states) ──
    # Each transition: name, from states, to state, guard/effect methods.
    # Core executes the transition when model_action(name) is called.
    # Example:
    #   _transitions = [
    #       {'name': 'confirm', 'from': ['draft'], 'to': 'confirmed', 'label': 'Confirm'},
    #       {'name': 'cancel', 'from': ['draft', 'confirmed'], 'to': 'cancelled',
    #        'guard': '_guard_cancel', 'effect': '_effect_cancel'},
    #   ]
    _transitions = None

    # ── Document Flow (optional) ──
    # Defines child documents that can be created from this model.
    # Core enforces constraints (cancel/delete block, max children).
    # Example:
    #   _document_flow = {
    #       'children': [
    #           {
    #               'model': 'purchase.goods_receipt',
    #               'label': 'Goods Receipt',
    #               'icon': 'InboxOutlined',
    #               'source_field_in_child': 'purchase_order',
    #               'state_conditions': {
    #                   'allowed_parent_states': ['confirmed', 'done'],
    #                   'blocked_child_states_for_parent_cancel': ['draft', 'waiting', 'done'],
    #               },
    #               'mapping': {
    #                   'reference': 'GR/{parent.reference}',
    #                   'purchase_order': 'id',
    #               },
    #               'constraints': {
    #                   'max_per_parent': 1,
    #                   'unique_per_parent': True,
    #               },
    #           },
    #       ],
    #   }
    _document_flow = None

    _form_view = None  # Optional: dict config for form layout
    #   {
    #       'header': {
    #           'fields': [...],
    #           'actions': [...],
    #           'smart_buttons': [...],
    #       },
    #       'notebook': [...],
    #   }
    _list_view = None  # Optional: dict config for list view

    # Audit fields — added here but are part of _fields for API
    created_at = dj_models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = dj_models.DateTimeField(auto_now=True, verbose_name='Updated At')
    created_by = dj_models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=dj_models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Created By',
        related_name='+',
    )
    updated_by = dj_models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=dj_models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Updated By',
        related_name='+',
    )
    is_deleted = dj_models.BooleanField(default=False, verbose_name='Deleted')

    class Meta:
        abstract = True
        ordering = ['-updated_at']

    @classmethod
    def get_model_name(cls):
        """Return ERP model name, e.g. 'purchase.order'."""
        return cls._model_name or cls.__name__.lower()

    @classmethod
    def get_model_config(cls):
        """
        Auto-generate field and view configuration for the frontend.
        Returns dict: { fields: {...}, list_view: {...}, form_view: {...} }
        """
        fields_config = {}
        for fname, fd in cls._field_descriptors.items():
            config = fd.to_config()

            # Add relation metadata for Many2One
            if isinstance(fd, Many2OneField) and fd.relation:
                config['relation'] = fd.relation if isinstance(fd.relation, str) else fd.relation._model_name

            fields_config[fname] = config

        result = {
            'model_name': cls.get_model_name(),
            'verbose_name': getattr(cls._meta, 'verbose_name', cls.__name__),
            'verbose_name_plural': getattr(cls._meta, 'verbose_name_plural', f'{cls.__name__}s'),
            'fields': fields_config,
            'list_view': cls._list_view or {},
            'form_view': cls._form_view or {},
            'display_field': cls._display_name,
        }

        # Include state machine config (frontend uses for auto-generating actions + status badge)
        if cls._states:
            result['states'] = cls._states
        if cls._transitions:
            result['transitions'] = cls._transitions
        if cls._document_flow:
            result['document_flow'] = cls._document_flow

        return result

    # ── State Machine Helpers ──

    @classmethod
    def _find_transition(cls, name):
        """Find a transition config by action name."""
        if not cls._transitions:
            return None
        for t in cls._transitions:
            if t['name'] == name:
                return t
        return None

    @classmethod
    def _get_state_config(cls, status):
        """Get config dict for a state key."""
        if not cls._states:
            return {}
        return cls._states.get(status, {})

    def _get_state_label(self):
        """Return label for current status."""
        cfg = self._get_state_config(self.status)
        return cfg.get('label', self.status)

    # ── Document Flow Helpers ──

    @classmethod
    def _get_child_flow(cls, child_model_name):
        """Get child flow config by child model name."""
        if not cls._document_flow:
            return None
        for child in cls._document_flow.get('children', []):
            if child['model'] == child_model_name:
                return child
        return None

    def _get_active_children(self, child_model_name=None):
        """Get active (non-deleted) child records for this parent."""
        if not self._document_flow or not self.pk:
            return []
        from django.contrib.contenttypes.models import ContentType

        results = []
        for child_cfg in self._document_flow.get('children', []):
            if child_model_name and child_cfg['model'] != child_model_name:
                continue
            child_model = ErpModelBase._model_registry.get(child_cfg['model'])
            if not child_model:
                continue
            source_field = child_cfg.get('source_field_in_child', 'source_document_id')
            children = list(child_model.objects.filter(
                **{source_field: self.pk, 'is_deleted': False}
            ))
            results.append({
                'model': child_cfg['model'],
                'label': child_cfg['label'],
                'children': children,
            })
        return results

    def _can_cancel(self):
        """
        Check if parent can be cancelled based on active children.
        Returns (True, None) or (False, error_message).
        """
        if not self._document_flow:
            return True, None

        for child_cfg in self._document_flow.get('children', []):
            blocked_states = child_cfg.get('state_conditions', {}).get(
                'blocked_child_states_for_parent_cancel', []
            )
            if not blocked_states:
                continue
            child_model = ErpModelBase._model_registry.get(child_cfg['model'])
            if not child_model:
                continue
            source_field = child_cfg.get('source_field_in_child', 'source_document_id')
            blocking = child_model.objects.filter(
                **{source_field: self.pk, 'is_deleted': False, 'status__in': blocked_states}
            ).exists()
            if blocking:
                return False, (
                    f'Tidak bisa cancel: masih ada {child_cfg["label"]} yang aktif. '
                    f'Cancel atau selesaikan terlebih dahulu.'
                )

        return True, None

    def _can_delete(self):
        """
        Check if parent can be soft-deleted based on active children.
        Returns (True, None) or (False, error_message).
        """
        if not self._document_flow:
            return True, None

        for child_cfg in self._document_flow.get('children', []):
            child_model = ErpModelBase._model_registry.get(child_cfg['model'])
            if not child_model:
                continue
            source_field = child_cfg.get('source_field_in_child', 'source_document_id')
            # Any active (non-deleted) child blocks parent delete
            has_active = child_model.objects.filter(
                **{source_field: self.pk, 'is_deleted': False}
            ).exists()
            if has_active:
                return False, (
                    f'Cannot delete: there is a related {child_cfg["label"]}. '
                    f'Delete it first.'
                )

        return True, True

    def _run_child_mapping(self, child_cfg):
        """
        Apply field mapping from child config using current instance as parent.
        Returns dict of field values for the new child record.
        """
        mapping = child_cfg.get('mapping', {})
        result = {}
        for child_field, source_expr in mapping.items():
            if source_expr is None:
                continue
            if callable(source_expr):
                result[child_field] = source_expr(self)
            elif isinstance(source_expr, str) and '{parent.' in source_expr:
                # Template like 'GR/{parent.reference}'
                template = source_expr
                for field_name in self._field_descriptors:
                    placeholder = f'{{parent.{field_name}}}'
                    if placeholder in template:
                        val = getattr(self, field_name, '')
                        template = template.replace(placeholder, str(val or ''))
                result[child_field] = template
            elif isinstance(source_expr, str):
                # Direct field copy
                val = getattr(self, source_expr, None)
                result[child_field] = val
            else:
                result[child_field] = source_expr
        return result

    def to_record(self):
        """Return dict of field values for API response."""
        data = {}
        for fname, fd in self._field_descriptors.items():
            val = getattr(self, fname, None)
            if hasattr(fd, 'to_representation'):
                val = fd.to_representation(val)
            data[fname] = val

        # Add base fields
        data['id'] = self.pk
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        data['is_deleted'] = self.is_deleted
        data['updated_by'] = {
            'id': self.updated_by.pk,
            'name': str(self.updated_by),
            'username': getattr(self.updated_by, 'username', ''),
        } if self.updated_by else None

        # Display name for breadcrumb
        display_field = self._display_name
        if display_field:
            data['display_name'] = getattr(self, display_field, None) or f'#{self.pk}'
        else:
            # Fallback: same logic as __str__
            data['display_name'] = str(self) or f'#{self.pk}'

        # Include one2many child records (one level deep)
        for fname, fd in self._field_descriptors.items():
            if getattr(fd, 'field_type', None) == 'one2many':
                child_model = ErpModelBase._model_registry.get(fd.relation)
                if child_model:
                    children = child_model.objects.filter(
                        **{fd.inverse_field: self.pk, 'is_deleted': False}
                    )
                    data[fname] = [child.to_record() for child in children]
                else:
                    data[fname] = []

        # ── Auto-count smart buttons ──
        counts = self._compute_smart_button_counts()
        if counts:
            data['_smart_button_counts'] = counts

        # ── Smart button previews (list of child records for click navigation) ──
        smart_buttons = (getattr(self, '_form_view', {}) or {}).get('header', {}).get('smart_buttons', [])
        if smart_buttons:
            previews = {}
            for btn in smart_buttons:
                btn_model = btn.get('model')
                if not btn_model:
                    continue
                children_qs = None

                # 1. Cari One2ManyField yang relation-nya cocok
                for fname, fd in self._field_descriptors.items():
                    if getattr(fd, 'field_type', None) == 'one2many' and fd.relation == btn_model:
                        child_model = ErpModelBase._model_registry.get(fd.relation)
                        if child_model:
                            children_qs = child_model.objects.filter(
                                **{fd.inverse_field: self.pk, 'is_deleted': False}
                            )
                        break

                # 2. Fallback ke _document_flow
                if children_qs is None:
                    doc_flow = getattr(self, '_document_flow', None) or {}
                    for child_cfg in doc_flow.get('children', []):
                        if child_cfg.get('model') == btn_model:
                            source_field = child_cfg.get('source_field_in_child', 'source_document_id')
                            child_model_cls = ErpModelBase._model_registry.get(btn_model)
                            if child_model_cls:
                                children_qs = child_model_cls.objects.filter(
                                    **{source_field: self.pk, 'is_deleted': False}
                                )
                            break

                # 3. Fallback ke Many2One (parent)
                if children_qs is None:
                    for fname, fd in self._field_descriptors.items():
                        if getattr(fd, 'field_type', None) == 'many2one' and getattr(fd, 'relation', None) == btn_model:
                            parent_obj = getattr(self, fname, None)
                            if parent_obj is not None:
                                display_name = (
                                    getattr(parent_obj, 'reference', None)
                                    or getattr(parent_obj, 'name', None)
                                    or getattr(parent_obj, 'code', None)
                                    or f'#{parent_obj.pk}'
                                )
                                previews[btn_model] = [{
                                    'id': parent_obj.pk,
                                    'display_name': display_name,
                                    'status': getattr(parent_obj, 'status', None),
                                }]
                            break

                if children_qs is not None:
                    # Build preview list — query minimal fields that actually exist on the model
                    db_fields = {f.name for f in children_qs.model._meta.get_fields()}
                    display_field = next(
                        (f for f in ('reference', 'name', 'code') if f in db_fields),
                        None,
                    )
                    has_status = 'status' in db_fields

                    records = []
                    for child in children_qs.only('id', *(f for f in ('reference', 'name', 'code', 'status') if f in db_fields)):
                        display_name = (
                            child.reference if hasattr(child, 'reference') and child.reference
                            else child.name if hasattr(child, 'name') and child.name
                            else child.code if hasattr(child, 'code') and child.code
                            else f'#{child.pk}'
                        )
                        rec = {
                            'id': child.pk,
                            'display_name': display_name,
                        }
                        if has_status:
                            rec['status'] = child.status
                        records.append(rec)

                    previews[btn_model] = records

            if previews:
                data['_smart_button_previews'] = previews

        return data

    def _compute_smart_button_counts(self):
        """Compute smart button counts for this record.
        Returns dict of {model_name: count} or empty dict.
        Reused by both to_record() and to_list_record()."""
        smart_buttons = (getattr(self, '_form_view', {}) or {}).get('header', {}).get('smart_buttons', [])
        if not smart_buttons:
            return {}

        counts = {}
        for btn in smart_buttons:
            btn_model = btn.get('model')
            if not btn_model:
                continue
            count = None

            # 1. Cari One2ManyField yang relation-nya cocok
            for fname, fd in self._field_descriptors.items():
                if getattr(fd, 'field_type', None) == 'one2many' and fd.relation == btn_model:
                    child_model = ErpModelBase._model_registry.get(fd.relation)
                    if child_model:
                        count = child_model.objects.filter(
                            **{fd.inverse_field: self.pk, 'is_deleted': False}
                        ).count()
                    break

            # 2. Fallback ke _document_flow
            if count is None:
                doc_flow = getattr(self, '_document_flow', None) or {}
                for child_cfg in doc_flow.get('children', []):
                    if child_cfg.get('model') == btn_model:
                        source_field = child_cfg.get('source_field_in_child', 'source_document_id')
                        try:
                            child_model_cls = ErpModelBase._model_registry.get(btn_model)
                            if child_model_cls:
                                count = child_model_cls.objects.filter(
                                    **{source_field: self.pk, 'is_deleted': False}
                                ).count()
                        except Exception:
                            count = 0
                        break

            # 3. Fallback ke Many2One (parent)
            if count is None:
                for fname, fd in self._field_descriptors.items():
                    if getattr(fd, 'field_type', None) == 'many2one' and getattr(fd, 'relation', None) == btn_model:
                        parent_val = getattr(self, fname, None)
                        count = 1 if parent_val is not None else 0
                        break

            if count is not None:
                counts[btn_model] = count

        return counts

    @classmethod
    def batch_compute_smart_button_counts(cls, records):
        """Compute smart button counts for multiple records in batch.
        Uses GROUP BY — 1 query per smart button instead of N×M queries.
        Returns {record_pk: {model_name: count}}
        """
        if not records:
            return {}

        smart_buttons = (getattr(cls, '_form_view', {}) or {}).get('header', {}).get('smart_buttons', [])
        if not smart_buttons:
            return {}

        record_ids = [r.pk for r in records]
        result = {pk: {} for pk in record_ids}

        for btn in smart_buttons:
            btn_model = btn.get('model')
            if not btn_model:
                continue

            found = False

            # 1. Cari One2ManyField yang relation-nya cocok
            for fname, fd in cls._field_descriptors.items():
                if getattr(fd, 'field_type', None) == 'one2many' and fd.relation == btn_model:
                    found = True
                    child_model = ErpModelBase._model_registry.get(fd.relation)
                    if child_model:
                        counts_qs = child_model.objects.filter(
                            **{fd.inverse_field + '__in': record_ids, 'is_deleted': False}
                        ).values(fd.inverse_field).annotate(count=Count('id'))
                        for row in counts_qs:
                            pk = row[fd.inverse_field]
                            result.setdefault(pk, {})[btn_model] = row['count']
                    break

            if not found:
                # 2. Fallback ke _document_flow
                doc_flow = getattr(cls, '_document_flow', None) or {}
                for child_cfg in doc_flow.get('children', []):
                    if child_cfg.get('model') == btn_model:
                        found = True
                        source_field = child_cfg.get('source_field_in_child', 'source_document_id')
                        try:
                            child_model_cls = ErpModelBase._model_registry.get(btn_model)
                            if child_model_cls:
                                counts_qs = child_model_cls.objects.filter(
                                    **{source_field + '__in': record_ids, 'is_deleted': False}
                                ).values(source_field).annotate(count=Count('id'))
                                for row in counts_qs:
                                    pk = row[source_field]
                                    result.setdefault(pk, {})[btn_model] = row['count']
                        except Exception:
                            pass
                        break

            if not found:
                # 3. Fallback ke Many2One (parent) — batch fetch parent field
                for fname, fd in cls._field_descriptors.items():
                    if getattr(fd, 'field_type', None) == 'many2one' and getattr(fd, 'relation', None) == btn_model:
                        m2o_field = fname + '_id'
                        qs = cls.objects.filter(pk__in=record_ids).values('pk', m2o_field)
                        for row in qs:
                            pk = row['pk']
                            result.setdefault(pk, {})[btn_model] = 1 if row[m2o_field] is not None else 0
                        break

        return result

    def to_list_record(self, batch_counts=None):
        """Lightweight serialization for list views. No compute, no children, no previews."""
        columns = getattr(self, '_list_view', {}).get('columns', [])
        data = {}

        # 1. Only serialize fields in list_view.columns
        for fname in columns:
            val = getattr(self, fname, None)
            fd = self._field_descriptors.get(fname)
            if fd and hasattr(fd, 'to_representation'):
                val = fd.to_representation(val)
            data[fname] = val

        # 2. Minimal base fields
        data['id'] = self.pk

        # 3. Display name
        display_field = self._display_name
        if display_field:
            data['display_name'] = getattr(self, display_field, None) or f'#{self.pk}'
        else:
            data['display_name'] = str(self) or f'#{self.pk}'

        # 4. Smart button counts — use batch if provided, else per-record query
        if batch_counts is not None:
            counts = batch_counts.get(self.pk, {})
        else:
            counts = self._compute_smart_button_counts()
        if counts:
            data['_smart_button_counts'] = counts

        return data

    def _print_context(self):
        """
        Auto-generate print context from all model fields.

        Returns dict with:
            - All model field values (via to_record())
            - Many2One fields resolved to full related records
            - One2Many child records as full records
            - company: company info for kop surat
        """
        data = self.to_record()

        # Resolve Many2One fields to full records (not just {id, name})
        def _resolve_m2o(obj_data, obj_instance):
            """Replace Many2One {id, name} with full to_record() in-place."""
            for fname, fd in obj_instance._field_descriptors.items():
                if isinstance(fd, Many2OneField):
                    rel_obj = getattr(obj_instance, fname, None)
                    if rel_obj is not None and hasattr(rel_obj, 'to_record'):
                        obj_data[fname] = rel_obj.to_record()
                elif getattr(fd, 'field_type', None) == 'one2many':
                    # Resolve Many2One inside child records too
                    child_model = ErpModelBase._model_registry.get(fd.relation)
                    if child_model and fname in obj_data:
                        children = child_model.objects.filter(
                            **{fd.inverse_field: obj_instance.pk, 'is_deleted': False}
                        )
                        for child in children:
                            child_record = child.to_record()
                            _resolve_m2o(child_record, child)
                            # Replace in data
                            for i, c in enumerate(obj_data[fname]):
                                if c.get('id') == child.pk:
                                    obj_data[fname][i] = child_record
                                    break

        _resolve_m2o(data, self)

        # Company info (kop surat)
        data['company'] = {
            'name': 'PT. DIGILIO TEKNOLOGI',
            'address': 'Jl. Raya No. 123, Jakarta',
            'phone': '(021) 555-1234',
            'email': 'info@digilio.id',
        }

        return data

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def __str__(self):
        if self._display_name:
            return getattr(self, self._display_name, '') or f'#{self.pk}'
        return getattr(self, 'name', '') or getattr(self, 'reference', '') or f'#{self.pk}'

    def _run_compute(self):
        """Run all compute methods defined in _field_descriptors with compute attribute."""
        for fname, fd in self._field_descriptors.items():
            compute_method = getattr(fd, 'compute', None)
            if compute_method and isinstance(compute_method, str):
                method_name = compute_method if compute_method.startswith('_') else f'_compute_{compute_method}'
                compute_fn = getattr(self, method_name, None)
                if compute_fn:
                    compute_fn()

    @classmethod
    def get_computed_fields(cls):
        """Return list of field names that have compute methods (excludes virtual=True fields)."""
        result = []
        for fname, fd in cls._field_descriptors.items():
            if getattr(fd, 'compute', None) and not getattr(fd, 'virtual', False):
                result.append(fname)
        return result

    def save(self, *args, **kwargs):
        self._run_compute()

        # ── Set default reference BEFORE first save ──
        # Required untuk model dengan reference required=True (NOT NULL di DB)
        # karena Draft#id baru bisa diisi setelah pk tersedia dari INSERT
        if hasattr(self, 'reference') and self.reference is None:
            self.reference = ''

        super().save(*args, **kwargs)

        # ── Auto-fill Draft#id untuk model yang punya field 'reference' ──
        if hasattr(self, 'reference') and not self.reference:
            self.reference = f'Draft#{self.pk}'
            super().save(update_fields=['reference'])
