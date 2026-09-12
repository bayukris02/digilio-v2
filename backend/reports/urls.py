from django.urls import path
from reports.views import print_preview, print_download

urlpatterns = [
    path(
        'print/<str:model_name>/<int:record_id>/preview/',
        print_preview,
        name='print-preview',
    ),
    path(
        'print/<str:model_name>/<int:record_id>/<str:template_key>/preview/',
        print_preview,
        name='print-preview-printout',
    ),
    path(
        'print/<str:model_name>/<int:record_id>/download/',
        print_download,
        name='print-download',
    ),
    path(
        'print/<str:model_name>/<int:record_id>/<str:template_key>/download/',
        print_download,
        name='print-download-printout',
    ),
]
