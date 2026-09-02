from django.db import models
from core.fields import (
    CharField, TextField, DateField, IntegerField, MonetaryField,
    SelectionField, Many2OneField,
)
from core.model_meta import BaseModel


class CustomerInvoiceInstallment(BaseModel):
    _model_name = 'accounting.customer_invoice_installment'

    _fields = {
        'invoice_id': Many2OneField(
            label='Faktur',
            relation='accounting.customer_invoice',
            required=True,
        ),
        'term_no': IntegerField(label='Cicilan Ke'),
        'due_date': DateField(label='Jatuh Tempo'),
        'amount': MonetaryField(label='Nominal', currency='IDR'),
        'note': TextField(label='Catatan'),
        'payment_status': SelectionField(
            label='Status Pembayaran',
            options=[('unpaid', 'Belum Dibayar'), ('partial', 'Sebagian'), ('paid', 'Lunas')],
            default='unpaid',
            colors={'unpaid': 'red', 'partial': 'orange', 'paid': 'green'},
        ),
    }

    _list_view = {
        'columns': ['term_no', 'due_date', 'amount', 'note', 'payment_status'],
        'default_sort': ['term_no'],
    }

    _form_view = {
        'header': {
            'fields': ['invoice_id', 'term_no', 'due_date', 'amount', 'note', 'payment_status'],
            'smart_buttons': [],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Cicilan'
        verbose_name_plural = 'Cicilan'
