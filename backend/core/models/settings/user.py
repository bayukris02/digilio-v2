"""
User model — wraps django.contrib.auth.models.User (auth_user table).
Read-only: list, detail. No CRUD from ERP UI.
"""
from django.db import models
from core.fields import CharField, BooleanField, DateTimeField
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
