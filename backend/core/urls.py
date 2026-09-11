from django.urls import path, include
from core.model_api import model_list, model_config, model_compute, ModelRecordView, chatter_logs, model_action, model_create_child
from core.dashboard_api import dashboard_data
from core.report_api import report_data
from core.pivot_api import pivot_data
from core.stock_report_api import stock_balance, stock_card, stock_ledger
from core.tax_report_api import tax_report
from core.access_api import (
    access_roles, access_role_detail, access_role_permissions,
    access_me, access_users, access_user_role,
)
from core.purge_api import purge_preview, purge_run

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
    path('stock/ledger/', stock_ledger, name='stock-ledger'),
    # Tax report (rekap pajak per tag dari baris dokumen lintas modul)
    path('tax/report/', tax_report, name='tax-report'),
    # RBAC — role & checklist akses menu
    path('access/roles/', access_roles, name='access-roles'),
    path('access/me/', access_me, name='access-me'),
    path('access/roles/<int:role_id>/', access_role_detail, name='access-role-detail'),
    path('access/roles/<int:role_id>/permissions/', access_role_permissions, name='access-role-permissions'),
    path('access/users/', access_users, name='access-users'),
    path('access/users/<int:user_id>/role/', access_user_role, name='access-user-role'),
    # Pemeliharaan data — clear database (khusus admin/staff)
    path('maintenance/purge/preview/', purge_preview, name='purge-preview'),
    path('maintenance/purge/', purge_run, name='purge-run'),
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
