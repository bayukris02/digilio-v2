from django.db import models
from django.core.exceptions import ValidationError
from core.fields import (
    CharField, TextField, BooleanField,
)
from core.model_meta import BaseModel


class Customer(BaseModel):
    _model_name = 'sales.customer'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Customer Name', required=True),
        'phone': CharField(label='Phone', unique=True, min_length=10),
        'email': CharField(label='Email'),
        'address': TextField(label='Address'),
        'is_active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['name', 'phone', 'email', 'is_active'],
        'filters': ['is_active'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'phone', 'email', 'is_active'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['address'],
                },
            ],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def clean(self):
        """Business rules for Customer."""
        super().clean()
        if self.phone:
            self.phone = self.phone.strip()
            # Check min_length from field definition
            fd = self._field_descriptors.get('phone')
            min_len = getattr(fd, 'min_length', None)
            if min_len and len(self.phone) < min_len:
                raise ValidationError({'phone': f'Phone must be at minimal {min_len} characters'})
            if not self.phone.startswith('0'):
                raise ValidationError({'phone': 'Phone must start with 0'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or ''
