"""
User model — wraps django.contrib.auth.models.User (auth_user table).
Read-only: list, detail. No CRUD from ERP UI.
"""
from django.db import models
from core.fields import CharField, BooleanField, DateTimeField, One2ManyField
from core.model_meta import ErpModelBase


class AuthUserQuerySet(models.QuerySet):
    """Custom QuerySet that ignores is_deleted filter (auth_user doesn't have it)."""

    def filter(self, *args, **kwargs):
        kwargs.pop('is_deleted', None)
        return super().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        kwargs.pop('is_deleted', None)
        return super().exclude(*args, **kwargs)


class AuthUserManager(models.Manager):
    """Custom manager that strips is_deleted from generic ERP queries."""

    def get_queryset(self):
        return AuthUserQuerySet(self.model, using=self._db)

    def filter(self, *args, **kwargs):
        kwargs.pop('is_deleted', None)
        return self.get_queryset().filter(*args, **kwargs)


class User(models.Model, metaclass=ErpModelBase):
    """ERP wrapper around auth_user table."""

    _model_name = 'settings.user'
    _display_name = 'username'

    _fields = {
        'username': CharField(label='Username', max_length=150, required=True),
        'email': CharField(label='Email', max_length=254),
        'first_name': CharField(label='First Name', max_length=150),
        'last_name': CharField(label='Last Name', max_length=150),
        'is_active': BooleanField(label='Active', default=True),
        'is_staff': BooleanField(label='Staff', default=False),
        'is_superuser': BooleanField(label='Superuser', default=False),
        'date_joined': DateTimeField(label='Date Joined'),
        'last_login': DateTimeField(label='Last Login'),
        # Relasi role (RBAC) — disimpan di tabel settings.user_role karena
        # auth_user (managed=False) tak bisa ditambah kolom. Satu baris per user.
        'role_lines': One2ManyField(
            label='Role',
            relation='settings.user_role',
            inverse_field='user_id',
        ),
    }

    _list_view = {
        'columns': ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff'],
        'filters': ['is_active', 'is_staff'],
        'default_sort': ['-date_joined'],
    }

    _form_view = {
        'header': {
            'fields': ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login'],
        },
        # Tabel Role (RBAC) — pilih role dari settings.role; tersimpan ke
        # settings.user_role lewat engine child-line generik.
        'notebook': [
            {
                'key': 'role',
                'label': 'Role',
                'relation': 'role_lines',
                'columns': ['role_id'],
            },
        ],
    }

    _states = None
    _transitions = None
    _document_flow = None

    objects = AuthUserManager()

    class Meta:
        managed = False
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        app_label = 'core'

    # ── ERP interface methods ──

    @classmethod
    def get_model_name(cls):
        return cls._model_name or cls.__name__.lower()

    @classmethod
    def get_model_config(cls):
        """Generate config dict compatible with generic ERP frontend."""
        from core.model_meta import BaseModel
        # Borrow the implementation from BaseModel's get_model_config
        return BaseModel.get_model_config.__func__(cls)

    # ── Kontrak BaseModel (dipakai core API generik) ──
    # User tidak mewarisi BaseModel (tabel auth_user, managed=False), jadi
    # method yang dipanggil core/model_api.py & core/model_meta.py diteruskan
    # manual ke BaseModel — sekali di sini, bukan patch di dalam core.
    @classmethod
    def _preview_fallback_fields(cls):
        from core.model_meta import BaseModel
        return BaseModel._preview_fallback_fields.__func__(cls)

    @classmethod
    def _build_preview_view(cls):
        from core.model_meta import BaseModel
        return BaseModel._build_preview_view.__func__(cls)

    def _run_compute(self):
        """Detail/create/update: isi virtual computed field (User tidak punya)."""
        from core.model_meta import BaseModel
        return BaseModel._run_compute(self)

    def _m2m_ids(self, field_name):
        from core.model_meta import BaseModel
        return BaseModel._m2m_ids(self, field_name)

    def _can_delete(self):
        """User tanpa _document_flow → selalu boleh dihapus."""
        from core.model_meta import BaseModel
        return BaseModel._can_delete(self)

    def _run_child_mapping(self, child_cfg):
        from core.model_meta import BaseModel
        return BaseModel._run_child_mapping(self, child_cfg)

    @classmethod
    def _get_state_config(cls, status):
        """No state machine for users."""
        return {}

    def to_record(self):
        """Serialize to dict for API response."""
        data = {'id': self.pk}
        for fname, fd in self._field_descriptors.items():
            val = getattr(self, fname, None)
            if hasattr(fd, 'to_representation'):
                val = fd.to_representation(val)
            data[fname] = val
        # Sertakan child one2many (role_lines) — pola sama dengan BaseModel.to_record.
        for fname, fd in self._field_descriptors.items():
            if getattr(fd, 'field_type', None) == 'one2many':
                child_model = ErpModelBase._model_registry.get(fd.relation)
                data[fname] = (
                    [
                        child.to_record()
                        for child in child_model.objects.filter(
                            **{fd.inverse_field: self.pk, 'is_deleted': False}
                        )
                    ]
                    if child_model
                    else []
                )
        data['display_name'] = self.get_display_name()
        return data

    def to_list_record(self, batch_counts=None):
        """Lightweight serialization for list views."""
        columns = getattr(self, '_list_view', {}).get('columns', [])
        data = {}
        for fname in columns:
            val = getattr(self, fname, None)
            fd = self._field_descriptors.get(fname)
            if fd and hasattr(fd, 'to_representation'):
                val = fd.to_representation(val)
            data[fname] = val
        data['id'] = self.pk
        data['display_name'] = self.get_display_name()
        return data

    def get_display_name(self):
        """Return a human-readable label for this record."""
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name} ({self.username})'
        return self.username or f'#{self.pk}'

    def __str__(self):
        return self.get_display_name()

    def soft_delete(self):
        """auth_user doesn't support soft-delete; hard-delete instead."""
        from django.contrib.auth.models import User as DjangoUser
        DjangoUser.objects.filter(pk=self.pk).delete()

    @classmethod
    def get_computed_fields(cls):
        return []

    @classmethod
    def batch_compute_smart_button_counts(cls, records):
        """No smart buttons on User model."""
        return {}
