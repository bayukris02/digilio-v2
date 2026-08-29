from core.fields import CharField
from core.model_meta import BaseModel


class ProductCategory(BaseModel):
    _model_name = 'inventory.product_category'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Kategori', required=True),
        'code': CharField(label='Kode Kategori'),
    }

    _list_view = {
        'columns': ['code', 'name'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'Umum',
                    'fields': ['name', 'code'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategori'

    def __str__(self):
        return self.name or ''
