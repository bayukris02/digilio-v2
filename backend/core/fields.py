"""
Field type descriptors for metadata-driven ERP models.
Each field class describes: type, label, validation, and how to convert to Django ORM field.
"""

from django.db import models as dj_models


class BaseField:
    """Base class for all field types."""
    field_type = None  # e.g., 'char', 'date', 'monetary'
    django_field_class = None

    def __init__(self, label='', required=False, default=None, help_text='', compute=None, depends=None, chatter_show=True, unique=False, virtual=False, editable_statuses=None, placeholder=None, hidden_statuses=None, onchange=None, line_onchange=None, confirm_onchange=None):
        self.label = label
        self.required = required
        self.default = default
        self.help_text = help_text
        self.compute = compute  # e.g., 'qty * price'
        self.depends = depends or []  # e.g., ['qty', 'price']
        self.chatter_show = chatter_show  # default visible in chatter
        self.unique = unique
        self.virtual = virtual  # True = frontend-only, no DB column
        self.editable_statuses = editable_statuses  # e.g., ['draft', 'waiting']
        self.placeholder = placeholder  # custom placeholder text
        self.hidden_statuses = hidden_statuses  # e.g., ['draft'] — hide field at these statuses
        self.onchange = onchange or {}  # {target_field: target_value} — reset field saat nilai berubah
        self.line_onchange = line_onchange or {}  # {target_field: target_value} — reset line field saat nilai berubah
        self.confirm_onchange = confirm_onchange  # {message, reset_relations} — konfirmasi + reset lines

    def to_config(self):
        """Return JSON-serialisable config for the frontend."""
        # If field is never editable (editable_statuses=[]), don't mark as required
        # because it's auto-filled by backend (Draft#{pk} / SequenceEngine)
        frontend_required = self.required if self.editable_statuses != [] else False
        cfg = {
            'type': self.field_type,
            'label': self.label,
            'required': frontend_required,
            'default': self.default,
            'help_text': self.help_text,
            'chatter_show': self.chatter_show,
        }
        if self.unique:
            cfg['unique'] = True
        if self.compute:
            cfg['compute'] = self.compute
            cfg['depends'] = self.depends
        if self.virtual:
            cfg['virtual'] = True
        if self.editable_statuses is not None:
            cfg['editable_statuses'] = self.editable_statuses
        if self.placeholder is not None:
            cfg['placeholder'] = self.placeholder
        if self.hidden_statuses is not None:
            cfg['hidden_statuses'] = self.hidden_statuses
        if self.onchange:
            cfg['onchange'] = self.onchange
        if self.line_onchange:
            cfg['line_onchange'] = self.line_onchange
        if self.confirm_onchange:
            cfg['confirm_onchange'] = self.confirm_onchange
        return cfg

    def to_python(self, value):
        """Normalize input value before passing to Django ORM."""
        return value

    def to_representation(self, value):
        """Serialize value for API response."""
        return value

    def to_django_field(self):
        """Convert to a Django model field instance. Returns None if virtual."""
        if self.virtual:
            return None
        raise NotImplementedError


class CharField(BaseField):
    field_type = 'char'
    django_field_class = dj_models.CharField

    def __init__(self, label='', required=False, default=None, max_length=255, min_length=None, help_text='', **kwargs):
        super().__init__(label, required, default, help_text, **kwargs)
        self.max_length = max_length
        self.min_length = min_length

    def to_config(self):
        cfg = super().to_config()
        cfg['max_length'] = self.max_length
        if self.min_length is not None:
            cfg['min_length'] = self.min_length
        return cfg

    def to_django_field(self):
        kwargs = dict(
            max_length=self.max_length,
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )
        return dj_models.CharField(**kwargs)


class TextField(BaseField):
    field_type = 'text'
    django_field_class = dj_models.TextField

    def to_django_field(self):
        return dj_models.TextField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class IntegerField(BaseField):
    field_type = 'integer'
    django_field_class = dj_models.IntegerField

    def to_django_field(self):
        return dj_models.IntegerField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class FloatField(BaseField):
    field_type = 'float'
    django_field_class = dj_models.FloatField

    def to_django_field(self):
        return dj_models.FloatField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class PercentageField(BaseField):
    field_type = 'percentage'
    django_field_class = dj_models.FloatField

    def __init__(self, label='', required=False, default=None, help_text='', progress=False, **kwargs):
        if default is None:
            default = 0  # pertahankan perilaku lama: default 0
        super().__init__(label, required, default, help_text, **kwargs)
        self.progress = progress

    def to_config(self):
        cfg = super().to_config()
        if self.progress:
            cfg['progress'] = True
        return cfg

    def to_django_field(self):
        return dj_models.FloatField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
        )


class MonetaryField(BaseField):
    field_type = 'monetary'
    django_field_class = dj_models.DecimalField

    def __init__(self, label='', required=False, default=None, currency='IDR', digits=None, **kwargs):
        super().__init__(label, required, default, **kwargs)
        self.currency = currency
        self.digits = digits or (18, 2)

    def to_config(self):
        cfg = super().to_config()
        cfg['currency'] = self.currency
        return cfg

    def to_django_field(self):
        return dj_models.DecimalField(
            max_digits=self.digits[0],
            decimal_places=self.digits[1],
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class BooleanField(BaseField):
    field_type = 'boolean'
    django_field_class = dj_models.BooleanField

    def __init__(self, label='', required=False, default=False, help_text='', **kwargs):
        super().__init__(label, required, default, help_text, **kwargs)

    def to_representation(self, value):
        return bool(value) if value is not None else None

    def to_django_field(self):
        return dj_models.BooleanField(
            default=self.default or False,
            verbose_name=self.label,
            help_text=self.help_text,
        )


class DateTimeField(BaseField):
    field_type = 'datetime'
    django_field_class = dj_models.DateTimeField

    def __init__(self, label='', required=False, default=None, help_text='', **kwargs):
        super().__init__(label, required, default, help_text, **kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    def to_django_field(self):
        return dj_models.DateTimeField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class DateField(BaseField):
    field_type = 'date'
    django_field_class = dj_models.DateField

    def __init__(self, label='', required=False, default=None, help_text='', **kwargs):
        super().__init__(label, required, default, help_text, **kwargs)

    def to_python(self, value):
        if value is None or isinstance(value, str) and len(value) <= 10:
            return value
        if isinstance(value, str):
            # ISO datetime → YYYY-MM-DD (dari dayjs.toJSON())
            return value[:10]
        if hasattr(value, 'strftime'):
            return value.strftime('%Y-%m-%d')
        return value

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    def to_django_field(self):
        return dj_models.DateField(
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class SelectionField(BaseField):
    field_type = 'selection'
    django_field_class = dj_models.CharField

    def __init__(self, label='', required=False, default=None, options=None, help_text='', colors=None, **kwargs):
        super().__init__(label, required, default, help_text, **kwargs)
        self.options = options or []
        self.colors = colors or {}

    def to_config(self):
        cfg = super().to_config()
        cfg['options'] = [
            {'value': v[0], 'label': v[1]} if isinstance(v, (list, tuple)) else {'value': v, 'label': v}
            for v in self.options
        ]
        if self.colors:
            cfg['colors'] = self.colors
        return cfg

    def _get_choices(self):
        choices = []
        for opt in self.options:
            if isinstance(opt, (list, tuple)):
                choices.append((opt[0], opt[1]))
            else:
                choices.append((opt, opt))
        return choices

    def to_django_field(self):
        return dj_models.CharField(
            max_length=100,
            choices=self._get_choices(),
            blank=not self.required,
            null=not self.required,
            default=self.default,
            verbose_name=self.label,
            help_text=self.help_text,
            unique=self.unique,
        )


class Many2OneField(BaseField):
    """ForeignKey to another model. relation = 'model.name' or Model class."""
    field_type = 'many2one'
    django_field_class = dj_models.ForeignKey

    def __init__(self, label='', required=False, relation=None, help_text='', autofill=None, domain=None, allow_duplicate=False, **kwargs):
        super().__init__(label, required, help_text=help_text, **kwargs)
        self.relation = relation  # e.g., 'res.partner' or PartnerModel class
        self.autofill = autofill or {}
        self.domain = domain or {}  # {related_field: header_field} — filter options by header field
        self.allow_duplicate = allow_duplicate  # True = boleh pilih nilai m2o yang sama di beberapa baris notebook

    def to_config(self):
        cfg = super().to_config()
        cfg['relation'] = self.relation
        if self.autofill:
            cfg['autofill'] = self.autofill
        if self.domain:
            cfg['domain'] = self.domain
        if self.allow_duplicate:
            cfg['allow_duplicate'] = True
        return cfg

    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get('id') or value.get('pk')
        return value

    def to_representation(self, value):
        if value is None:
            return None
        if hasattr(value, 'pk'):
            return {'id': value.pk, 'name': str(value)}
        return {'id': value, 'name': str(value)} if not isinstance(value, dict) else value

    def to_django_field(self, on_delete=dj_models.SET_NULL, **kwargs):
        """Convert to FK field. on_delete defaults to SET_NULL for audit safety."""
        # We use a placeholder; the actual model class is resolved by the metaclass
        return dj_models.ForeignKey(
            'self',  # Placeholder, replaced by metaclass
            on_delete=on_delete,
            blank=not self.required,
            null=True,
            verbose_name=self.label,
            help_text=self.help_text,
            related_name='+',
            **kwargs,
        )


class Many2ManyField(BaseField):
    """ManyToMany ke model lain — bisa pilih lebih dari satu (relation = 'model.name')."""
    field_type = 'many2many'
    django_field_class = dj_models.ManyToManyField

    def __init__(self, label='', required=False, relation=None, help_text='', **kwargs):
        super().__init__(label, required, help_text=help_text, **kwargs)
        self.relation = relation  # e.g., 'accounting.tax'

    def to_config(self):
        cfg = super().to_config()
        cfg['relation'] = self.relation
        return cfg

    def to_python(self, value):
        # value: list of ids / {id} / objects dari payload API
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]
        out = []
        for v in value:
            if isinstance(v, dict):
                out.append(v.get('id') or v.get('pk') or v.get('value'))
            elif hasattr(v, 'pk'):
                out.append(v.pk)
            else:
                out.append(v)
        return [x for x in out if x is not None]

    def to_representation(self, value):
        # value = ManyRelatedManager (belum di-query sampai .all())
        try:
            qs = value.all() if hasattr(value, 'all') else value
            return [{'id': o.pk, 'name': str(o)} for o in qs]
        except Exception:
            return []

    def to_django_field(self, **kwargs):
        # Placeholder — metaclass membuat ManyToManyField dengan class yang
        # sudah ter-resolve dari registry.
        return None


class One2ManyField(BaseField):
    """Inverse of Many2One — represents a list of child records."""
    field_type = 'one2many'

    def __init__(self, label='', relation=None, inverse_field='', help_text='', **kwargs):
        super().__init__(label, required=False, help_text=help_text, **kwargs)
        self.relation = relation  # e.g., 'purchase.order.line'
        self.inverse_field = inverse_field

    def to_config(self):
        cfg = super().to_config()
        cfg['relation'] = self.relation
        cfg['inverse_field'] = self.inverse_field
        return cfg

    def to_django_field(self):
        """One2Many has no database column — it's a virtual relation."""
        return None  # No Django field; handled as reverse relation
