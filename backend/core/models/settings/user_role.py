"""
Penghubung User ↔ Role (RBAC).

Tabel `auth_user` (settings.user) tidak bisa ditambah kolom (managed=False),
jadi penugasan role disimpan di tabel terpisah ini: satu baris per user.
"""
from core.fields import Many2OneField
from core.model_meta import BaseModel


class UserRole(BaseModel):
    """Role yang diberikan ke seorang user."""

    _model_name = 'settings.user_role'

    _fields = {
        'user_id': Many2OneField(
            label='User',
            relation='settings.user',
            required=True,
        ),
        'role_id': Many2OneField(
            label='Role',
            relation='settings.role',
            required=True,
        ),
    }

    _list_view = {
        'columns': ['user_id', 'role_id'],
        'filters': ['role_id'],
    }

    _form_view = {
        'header': {
            'fields': ['user_id', 'role_id'],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f'{self.user_id} → {self.role_id}'
