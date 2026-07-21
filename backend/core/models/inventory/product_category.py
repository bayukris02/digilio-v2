from core.fields import CharField
from core.model_meta import BaseModel


class ProductCategory(BaseModel):
    _model_name = 'inventory.product_category'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Category Name', required=True),
        'code': CharField(label='Category Code'),
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
                    'label': 'General',
                    'fields': ['name', 'code'],
                },
            ],
        },
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name or ''
