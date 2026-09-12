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

from .fields import BaseField, Many2OneField, Many2ManyField, One2ManyField, MonetaryField, DateField, DateTimeField, BooleanField


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
        m2m_fields = {}
        virtual_fields = {}

        for field_name, fd in field_descriptors.items():
            if isinstance(fd, One2ManyField) or getattr(fd, 'virtual', False):
                virtual_fields[field_name] = fd
                continue

            if isinstance(fd, Many2ManyField):
                # M2M — buat setelah class jadi (butuh model relasi ter-resolve)
                m2m_fields[field_name] = fd
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

        # Add M2M fields (ManyToMany) setelah class creation — butuh class
        # model relasi sudah ter-registrasi (pastikan import model relasi
        # lebih dulu di core/models/__init__.py).
        for field_name, fd in m2m_fields.items():
            relation = fd.relation
            to_model = mcs._model_registry.get(relation) if isinstance(relation, str) else relation
            if to_model is None:
                raise RuntimeError(
                    f'Many2ManyField "{name}.{field_name}": model relasi '
                    f'"{relation}" belum ter-registrasi (import model relasi lebih dulu).'
                )
            df = dj_models.ManyToManyField(
                to_model,
                blank=True,
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

    _preview_view = None  # Optional: dict config untuk drawer preview (klik 1x baris list)
    #   {
    #     'title': 'reference',      # field judul drawer (default: display_field)
    #     'subtitle': 'vendor',      # opsional
    #     'status': 'status',        # opsional (default: 'status' bila ada)
    #     'fields': ['vendor', ...], # daftar field penting (flat)
    #     # atau 'sections': [{'title': 'Nilai', 'fields': ['grand_total']}]
    #     'lines': 'order_lines',    # opsional: field one2many → tabel ringkas
    #   }
    # Bila kosong, config diisi otomatis (fallback) dari _form_view/_list_view.

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
            'allow_create': getattr(cls, '_allow_create', True),
        }

        # Include state machine config (frontend uses for auto-generating actions + status badge)
        if cls._states:
            result['states'] = cls._states
        if cls._transitions:
            result['transitions'] = cls._transitions
        if cls._document_flow:
            result['document_flow'] = cls._document_flow

        result['preview_view'] = cls._build_preview_view()

        return result

    # ── Meta-driven preview (drawer klik 1x pada baris list) ──
    @classmethod
    def _preview_fallback_fields(cls):
        """Field penting otomatis bila `_preview_view` tidak didefinisikan.

        Urutan sumber: `_form_view.header.fields` → seluruh `header.tabs[].fields`
        → `_list_view.columns`. Field relasi (one2many/many2many) & teks panjang
        dibuang; maksimal 10 field.
        """
        header = (cls._form_view or {}).get('header', {}) or {}
        raw = list(header.get('fields') or [])
        if not raw:
            for tab in header.get('tabs') or []:
                raw.extend(tab.get('fields') or [])
        if not raw:
            raw = list((cls._list_view or {}).get('columns') or [])

        out = []
        for item in raw:
            fname = item.get('key') or item.get('field') if isinstance(item, dict) else item
            if not fname or fname in out:
                continue
            fd = cls._field_descriptors.get(fname)
            if not fd:
                continue
            if getattr(fd, 'field_type', None) in ('one2many', 'many2many'):
                continue
            out.append(fname)
        return out[:10]

    @classmethod
    def _build_preview_view(cls):
        """Bangun config drawer preview — generik, semua spesifik ada di model.

        Mengembalikan dict: {title, subtitle, status, fields|sections, lines}.
        `lines` di-resolve ke model anak (kolom + label) supaya frontend bisa
        merender tabel ringkas tanpa hardcode per model.
        """
        cfg = dict(getattr(cls, '_preview_view', None) or {})
        # Judul: config → display_field → 'reference' → 'name' → 'code' (yang ada saja)
        title = cfg.get('title') or cls._display_name
        if not title or title not in cls._field_descriptors:
            title = next((f for f in ('reference', 'name', 'code') if f in cls._field_descriptors), None)
        status = cfg.get('status') or ('status' if 'status' in cls._field_descriptors else None)

        sections = []
        for sec in cfg.get('sections') or []:
            sec_fields = [f for f in (sec.get('fields') or []) if f in cls._field_descriptors]
            if sec_fields:
                sections.append({'title': sec.get('title') or '', 'fields': sec_fields})

        fields = [f for f in (cfg.get('fields') or []) if f in cls._field_descriptors]
        if not fields and not sections:
            fields = cls._preview_fallback_fields()
        if not fields and not sections:
            return {}

        # ── Baris anak (tabel ringkas) — opsional ──
        lines = cfg.get('lines')
        if isinstance(lines, str):
            lines = {'field': lines}
        if isinstance(lines, dict) and lines.get('field'):
            fd = cls._field_descriptors.get(lines['field'])
            child_name = getattr(fd, 'relation', None) if fd else None
            child = ErpModelBase._model_registry.get(child_name) if child_name else None
            if child:
                cols = lines.get('columns') or list((getattr(child, '_list_view', {}) or {}).get('columns') or [])
                cols = [c for c in cols if c in child._field_descriptors][:6]
                lines = {
                    'field': lines['field'],
                    'model': child_name,
                    'title': lines.get('title') or (getattr(fd, 'label', '') or 'Baris'),
                    'columns': cols,
                    'labels': {c: getattr(child._field_descriptors[c], 'label', c) for c in cols},
                    # Config field anak (type/options/colors) → frontend render generik
                    'fields': {c: child._field_descriptors[c].to_config() for c in cols},
                }
            else:
                lines = None
        else:
            lines = None

        preview = {
            'title': title,
            'subtitle': cfg.get('subtitle') or None,
            'status': status,
            'fields': fields,
            'sections': sections,
            'lines': lines,
        }
        return preview

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
            columns_meta = {}
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
                                parent_cls = ErpModelBase._model_registry.get(btn_model)
                                cols = self._smart_button_columns(btn, parent_cls)
                                rec = {'id': parent_obj.pk}
                                for col in cols:
                                    rec[col['key']] = self._preview_cell(parent_obj, col['key'])
                                columns_meta[btn_model] = cols
                                previews[btn_model] = [rec]
                            break

                if children_qs is not None:
                    child_cls = ErpModelBase._model_registry.get(btn_model) or children_qs.model
                    cols, records = self._build_smart_button_preview(btn, child_cls, children_qs)
                    columns_meta[btn_model] = cols
                    previews[btn_model] = records

            if previews:
                data['_smart_button_previews'] = previews
            if columns_meta:
                data['_smart_button_columns'] = columns_meta

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

    # ── Preview smart button (generik, meta-driven) ──────────────────────────
    # Kolom preview ditentukan per smart button di config model:
    #   {'label': 'Purchase Order', 'model': 'purchase.order', 'icon': '...',
    #    'preview_columns': ['reference', 'vendor', 'order_date', 'status']}
    # Bila `preview_columns` tidak diisi → default ['display_name', 'status']
    # (kompatibel dengan perilaku lama: referensi + status).
    PREVIEW_DEFAULT_COLUMNS = ['display_name', 'status']

    @staticmethod
    def _preview_scalar(val):
        """Konversi nilai field apa pun → tipe primitif yang aman dikirim ke frontend."""
        from decimal import Decimal

        if val is None or isinstance(val, (str, int, float, bool)):
            return val
        if isinstance(val, Decimal):
            return float(val)
        if hasattr(val, 'pk') and hasattr(val, '_meta'):        # relasi many2one
            for attr in ('reference', 'name', 'code', 'username'):
                disp = getattr(val, attr, None)
                if disp:
                    return disp
            return f'#{val.pk}'
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        return str(val)

    @classmethod
    def _preview_cell(cls, obj, key):
        """Nilai satu kolom preview untuk sebuah record anak."""
        if key == 'display_name':
            for attr in ('reference', 'name', 'code'):
                val = getattr(obj, attr, None)
                if val:
                    return val
            return f'#{obj.pk}'
        return cls._preview_scalar(getattr(obj, key, None))

    @classmethod
    def _smart_button_columns(cls, btn, child_cls):
        """Metadata kolom preview (label + tipe) untuk satu smart button.

        Diambil dari config model (`preview_columns`); field yang tidak ada di model
        anak diabaikan supaya config yang salah tidak memecahkan halaman.
        """
        keys = list(btn.get('preview_columns') or cls.PREVIEW_DEFAULT_COLUMNS)
        cols = []
        for key in keys:
            if key == 'display_name':
                cols.append({
                    'key': 'display_name',
                    'label': btn.get('display_label') or 'Referensi',
                    'type': 'text',
                })
                continue
            fd = (child_cls._field_descriptors or {}).get(key) if child_cls else None
            if fd is None:
                continue                     # field tidak dikenal → dilewati
            ftype = getattr(fd, 'field_type', None)
            col = {
                'key': key,
                'label': getattr(fd, 'label', None) or key.replace('_', ' ').title(),
                'type': {
                    'date': 'date',
                    'datetime': 'date',
                    'monetary': 'number',
                    'float': 'number',
                    'integer': 'number',
                    'many2one': 'text',
                    'selection': 'text',
                }.get(ftype, 'text'),
            }
            # Kolom `status` → sertakan label & warna state model anak (dari _states)
            if key == 'status':
                states = getattr(child_cls, '_states', None) or {}
                col['type'] = 'status'
                col['options'] = [
                    {'value': k, 'label': v.get('label', k), 'color': v.get('color', 'default')}
                    for k, v in states.items()
                ]
            cols.append(col)
        return cols or [{'key': 'display_name', 'label': 'Referensi', 'type': 'text'}]

    def _build_smart_button_preview(self, btn, child_cls, children_qs):
        """Susun daftar preview + metadata kolom untuk satu smart button."""
        cols = self._smart_button_columns(btn, child_cls)
        # Hindari N+1: ambil sekaligus relasi many2one yang dipakai sebagai kolom
        m2o = [
            c['key'] for c in cols
            if c['key'] != 'display_name'
            and child_cls
            and getattr((child_cls._field_descriptors or {}).get(c['key']), 'field_type', None) == 'many2one'
        ]
        qs = children_qs.select_related(*m2o) if m2o else children_qs
        records = []
        for child in qs:
            rec = {'id': child.pk}
            for col in cols:
                rec[col['key']] = self._preview_cell(child, col['key'])
            records.append(rec)
        return cols, records

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
        if not hasattr(self, '_m2m_override'):
            self._m2m_override = {}
        for fname, fd in self._field_descriptors.items():
            compute_method = getattr(fd, 'compute', None)
            if compute_method and isinstance(compute_method, str):
                method_name = compute_method if compute_method.startswith('_') else f'_compute_{compute_method}'
                compute_fn = getattr(self, method_name, None)
                if compute_fn:
                    compute_fn()

    def _m2m_ids(self, field_name):
        """Daftar pk relasi many2many — memakai override dari payload compute
        bila ada (record belum disimpan), selain itu query dari DB."""
        if field_name in getattr(self, '_m2m_override', {}):
            return self._m2m_override[field_name]
        try:
            return [o.pk for o in getattr(self, field_name).all()]
        except Exception:
            return []

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

    # ── Duplikat dokumen (generik) ──────────────────────────────────────────
    # Dipakai fitur "Batal & Buat Baru" (dan bisa dipakai aksi duplikat lain).
    # Kolom sistem tidak disalin; nomor dokumen dikosongkan (jadi Draft#<id> baru);
    # status kembali ke state awal model (umumnya 'draft').
    DUPLICATE_EXCLUDE = {
        'id', 'pk', 'created_at', 'updated_at', 'is_deleted',
        'created_by', 'updated_by', 'reference', 'status',
    }

    @classmethod
    def _has_field(cls, name: str) -> bool:
        """True bila `name` benar-benar field DB pada model ini (bukan sekadar atribut)."""
        return any(f.name == name or f.attname == name for f in cls._meta.concrete_fields)

    def duplicate_record(self, include_children: bool = True):
        """Salin record ini menjadi dokumen BARU (status awal model, nomor kosong).

        Generik untuk semua model:
          * field scalar/FK disalin, kecuali kolom sistem (pk, audit, reference, status);
          * status di-set ke state pertama `_states` (biasanya draft);
          * baris one2many ikut disalin dan diarahkan ke record baru (1 level);
          * reference dibiarkan kosong → BaseModel.save() mengisi `Draft#<id>`.
        """
        cls = self.__class__
        values = {}
        for field in cls._meta.concrete_fields:
            if field.primary_key or field.name in self.DUPLICATE_EXCLUDE or field.attname in self.DUPLICATE_EXCLUDE:
                continue
            values[field.attname] = field.value_from_object(self)

        new_obj = cls(**values)
        states = getattr(cls, '_states', None) or {}
        if states and self._has_field('status'):
            new_obj.status = next(iter(states))          # state awal (draft)
        if self._has_field('reference'):
            new_obj.reference = ''
        for audit in ('created_by_id', 'updated_by_id'):
            if self._has_field(audit):
                setattr(new_obj, audit, None)
        new_obj.is_deleted = False
        new_obj.save()

        if include_children:
            for _fname, fd in (cls._field_descriptors or {}).items():
                if getattr(fd, 'field_type', None) != 'one2many':
                    continue
                child_cls = ErpModelBase._model_registry.get(fd.relation)
                if child_cls is None:
                    continue
                children = child_cls.objects.filter(
                    **{fd.inverse_field: self.pk, 'is_deleted': False}
                )
                for child in children:
                    child_copy = child.duplicate_record(include_children=False)
                    setattr(child_copy, f'{fd.inverse_field}_id', new_obj.pk)
                    child_copy.save()

        return new_obj

    # ── Konfirmasi transisi (generik) ───────────────────────────────────────
    # Konvensi: transisi yang berakhir di state 'cancelled' TIDAK BISA dikembalikan
    # ke draft → wajib dikonfirmasi user dulu. Bisa dioverride per transisi:
    #   {'name': 'cancel', ..., 'confirm': False}                 # matikan
    #   {'name': 'x', 'confirm': True, 'confirm_message': '...'}  # transisi lain
    #   {'name': 'x', 'confirm_options': [...]}                   # tombol custom
    @classmethod
    def _transition_needs_confirm(cls, transition: dict) -> bool:
        if 'confirm' in transition:
            return bool(transition['confirm'])
        return transition.get('to') == 'cancelled'

    @classmethod
    def _build_confirm_payload(cls, obj, transition: dict) -> dict:
        """Payload konfirmasi yang dikirim ke frontend (_action_type 'confirm')."""
        label = transition.get('label') or transition.get('name') or 'Lanjutkan'
        target = transition.get('to')
        # Kata kerja untuk tombol: 'Batalkan' bila transisi menuju state cancelled
        verb = 'Batalkan' if target == 'cancelled' else label
        entity = getattr(cls._meta, 'verbose_name', None) or cls.__name__
        reference = ''
        try:
            reference = obj.to_record().get('display_name') or ''
        except Exception:
            reference = getattr(obj, 'reference', '') or f'#{obj.pk}'

        default_message = (
            f'Yakin ingin {verb.lower()} {entity} {reference}? '
            'Dokumen yang dibatalkan tidak bisa dikembalikan ke Draft atau diedit ulang — '
            'harus membuat dokumen baru.'
        ) if target == 'cancelled' else f'Yakin ingin melanjutkan {label} pada {entity} {reference}?'

        # Nilai opsi ('value') dipakai apa adanya oleh frontend sebagai `confirm_mode`
        # saat request dikirim ulang — jadi kontraknya harus sama dengan yang dibaca
        # backend: 'back' (batal), 'yes' (jalankan), 'new' (jalankan + buat dokumen baru).
        options = transition.get('confirm_options') or [
            {'value': 'back', 'label': 'Kembali', 'type': 'default'},
            {'value': 'yes', 'label': f'Ya, {verb}', 'type': 'danger'},
            *([{'value': 'new', 'label': f'Ya, {verb} & Buat Baru', 'type': 'primary'}]
              if target == 'cancelled' or transition.get('confirm_new') else []),
        ]
        return {
            '_action_type': 'confirm',
            'confirm_message': transition.get('confirm_message') or default_message,
            'confirm_options': options,
        }
