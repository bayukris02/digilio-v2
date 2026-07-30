from django.db import models
from core.fields import (
    CharField, TextField, DateField, MonetaryField, FloatField,
    Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class PurchaseRequest(BaseModel):
    _model_name = 'purchase.request'
    _display_name = 'reference'

    _states = {
        'draft': {'allow_edit': True, 'allow_delete': True, 'label': 'Draft', 'color': 'default'},
        'confirmed': {'allow_edit': False, 'allow_delete': False, 'label': 'Confirmed', 'color': 'processing'},
        'cancelled': {'allow_edit': False, 'allow_delete': False, 'label': 'Cancelled', 'color': 'error'},
    }

    _transitions = [
        {
            'name': 'confirm',
            'from': ['draft'],
            'to': 'confirmed',
            'label': 'Confirm',
            'icon': 'CheckOutlined',
        },
        {
            'name': 'cancel',
            'from': ['draft', 'confirmed'],
            'to': 'cancelled',
            'label': 'Cancel',
            'icon': 'StopOutlined',
        },
    ]

    _fields = {
        'reference': CharField(
            label='Reference', required=True, editable_statuses=[],
            placeholder='Automatic',
        ),
        'requested_by': CharField(label='Requested By', required=True),
        'request_date': DateField(label='Request Date'),
        'estimated_receipt_date': DateField(label='Estimated Receipt Date'),
        'notes': TextField(label='Notes'),
        'request_lines': One2ManyField(
            label='Request Lines',
            relation='purchase.request.line',
            inverse_field='request_id',
        ),
    }

    _list_view = {
        'columns': ['reference', 'requested_by', 'request_date', 'estimated_receipt_date', 'status'],
        'filters': ['status', 'request_date'],
        'default_sort': ['-updated_at'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['reference', 'requested_by', 'request_date',
                               'estimated_receipt_date', 'notes'],
                },
            ],
            'actions': [
                {
                    'label': 'Confirm',
                    'icon': 'CheckOutlined',
                    'color': 'primary',
                    'action': 'confirm',
                    'states': ['draft'],
                },
                {
                    'label': 'Cancel',
                    'icon': 'StopOutlined',
                    'color': 'red',
                    'action': 'cancel',
                    'states': ['draft', 'confirmed'],
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Request Lines',
                'relation': 'request_lines',
                'columns': ['product', 'description', 'qty', 'estimated_cost', 'total', 'vendor'],
                'summary': {
                    'columns': {'qty': 'sum', 'estimated_cost': 'sum', 'total': 'sum'},
                },
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Request'
        verbose_name_plural = 'Purchase Requests'

    def __str__(self):
        return self.reference or f'PR#{self.pk}'
