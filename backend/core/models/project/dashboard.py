"""Project dashboard config — meta-driven blocks (versi sederhana).

Engine + renderer 100% generic (core/dashboard_api.py + components/dashboard/*);
file ini hanya konfigurasi declarative yang menyebut model project.
"""
from core.dashboard_api import register_dashboard

PROJECT_DASHBOARD = {
    'key': 'project',
    'title': 'Dashboard Proyek',
    'blocks': [
        # ── KPI row ──
        {
            'key': 'total_projects',
            'title': 'Total Proyek',
            'type': 'kpi', 'span': 6,
            'model': 'project.project',
            'aggregate': {'field': 'id', 'func': 'count'},
        },
        {
            'key': 'total_contract',
            'title': 'Total Nilai Kontrak',
            'type': 'kpi', 'span': 6,
            'model': 'project.project',
            'aggregate': {'field': 'contract_value', 'func': 'sum'},
        },
        {
            'key': 'avg_progress',
            'title': 'Rata-rata Progress Milestone',
            'type': 'kpi', 'span': 6,
            'model': 'project.project_line',
            'aggregate': {'field': 'progress', 'func': 'avg'},
        },
        {
            'key': 'total_milestones',
            'title': 'Total Milestone',
            'type': 'kpi', 'span': 6,
            'model': 'project.project_line',
            'aggregate': {'field': 'id', 'func': 'count'},
        },
        # ── Charts ──
        {
            'key': 'projects_by_category',
            'title': 'Proyek per Kategori',
            'type': 'pie', 'span': 12,
            'model': 'project.project',
            'aggregate': {'field': 'id', 'func': 'count'},
            'group_by': 'category',
        },
        {
            'key': 'top_projects',
            'title': 'Proyek Teratas per Kontrak',
            'type': 'bar', 'span': 12,
            'model': 'project.project',
            'aggregate': {'field': 'contract_value', 'func': 'sum'},
            'group_by': 'name',
            'limit': 5, 'sort': '-value',
        },
        # ── Grid ──
        {
            'key': 'recent_projects',
            'title': 'Proyek',
            'type': 'grid', 'span': 24,
            'model': 'project.project',
            'columns': ['name', 'category', 'client', 'date_start', 'contract_value'],
            'order_by': ['-updated_at'],
        },
    ],
}

register_dashboard('project', PROJECT_DASHBOARD)
