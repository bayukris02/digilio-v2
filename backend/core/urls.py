from django.urls import path, include
from core.model_api import model_list, model_config, model_compute, ModelRecordView, chatter_logs, model_action, model_create_child
from core.dashboard_api import dashboard_data
from core.report_api import report_data
from core.pivot_api import pivot_data
from core.stock_report_api import stock_balance, stock_card
from core.tax_report_api import tax_report

urlpatterns = [
    # Dashboard (meta-driven, generic)
    path('dashboards/<str:key>/', dashboard_data, name='dashboard-data'),
    # Financial reports (meta-driven, generic)
    path('reports/<str:key>/', report_data, name='report-data'),
    # Pivots (meta-driven, generic — AG Grid pivot mode)
    path('pivots/<str:key>/', pivot_data, name='pivot-data'),
    # Stock reports (agregasi via StockEngine dari row stock ledger)
    path('stock/balance/', stock_balance, name='stock-balance'),
    path('stock/card/', stock_card, name='stock-card'),
    # Tax report (rekap pajak per tag dari baris dokumen lintas modul)
    path('tax/report/', tax_report, name='tax-report'),
    # Model registry
    path('models/', model_list, name='model-list'),
    path('models/<str:model_name>/config/', model_config, name='model-config'),
    path('models/<str:model_name>/records/', ModelRecordView.as_view(), name='model-records'),
    path('models/<str:model_name>/records/<int:record_id>/', ModelRecordView.as_view(), name='model-record-detail'),
    path('models/<str:model_name>/compute/', model_compute, name='model-compute'),
    path('chatter/<str:model_name>/<int:record_id>/', chatter_logs, name='chatter-logs'),
    path('models/<str:model_name>/records/<int:record_id>/action/', model_action, name='model-action'),
    path('models/<str:model_name>/records/<int:record_id>/create_child/',
         model_create_child, name='model-create-child'),
]
