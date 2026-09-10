"""
Role & akses menu (RBAC).

- Role            : daftar role / hak akses (nama, kode, keterangan, aktif).
- RoleMenuAccess  : checklist akses per role — satu baris per key yang dicentang.
                    `menu_type` membedakan level: 'module' | 'section' | 'menu'.
                    Hanya baris `allow=True` yang dianggap diberi akses.
"""
from core.fields import (
    CharField, TextField, BooleanField, Many2OneField, SelectionField,
)
from core.model_meta import BaseModel


class Role(BaseModel):
    """Role / hak akses yang bisa di-assign ke user."""

    _model_name = 'settings.role'
    _display_name = 'name'

    _fields = {
        'name': CharField(
            label='Nama Role',
            required=True,
            help_text='Contoh: Admin, Sales, Gudang',
        ),
        'code': CharField(
            label='Kode',
            help_text='Identifier singkat, mis. ADMIN, SALES, GUDANG',
        ),
        'description': TextField(label='Keterangan'),
        'active': BooleanField(label='Active', default=True),
    }

    _list_view = {
        'columns': ['name', 'code', 'description', 'active'],
        'filters': ['active'],
    }

    _form_view = {
        'header': {
            'fields': ['name', 'code', 'description', 'active'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name or f'#{self.pk}'


class RoleMenuAccess(BaseModel):
    """Checklist akses menu per role (tabel internal RBAC)."""

    _model_name = 'settings.role_menu_access'
    _display_name = 'menu_key'

    _fields = {
        'role_id': Many2OneField(
            label='Role',
            relation='settings.role',
            required=True,
        ),
        'menu_key': CharField(
            label='Menu Key',
            required=True,
            help_text='Key menu/section/modul, mis. /purchase.order',
        ),
        'menu_type': SelectionField(
            label='Tipe',
            options=[('module', 'Modul'), ('section', 'Section'), ('menu', 'Menu')],
            default='menu',
        ),
        'allow': BooleanField(label='Allow', default=True),
    }

    _list_view = {
        'columns': ['role_id', 'menu_key', 'menu_type', 'allow'],
        'filters': ['role_id', 'menu_type', 'allow'],
    }

    _form_view = {
        'header': {
            'fields': ['role_id', 'menu_key', 'menu_type', 'allow'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Role Menu Access'
        verbose_name_plural = 'Role Menu Access'

    def __str__(self):
        return self.menu_key or f'#{self.pk}'
