from django.urls import path
from .views import download_template, preview_import, execute_import_view

urlpatterns = [
    path(
        'import/<str:model_name>/template/',
        download_template,
        name='import-template',
    ),
    path(
        'import/<str:model_name>/preview/',
        preview_import,
        name='import-preview',
    ),
    path(
        'import/<str:model_name>/execute/',
        execute_import_view,
        name='import-execute',
    ),
]
