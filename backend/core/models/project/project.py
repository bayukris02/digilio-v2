from core.fields import (
    CharField, DateField, MonetaryField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class Project(BaseModel):
    """Inisiasi dan pencatatan data dasar proyek baru."""

    _model_name = 'project.project'
    _display_name = 'name'

    _fields = {
        'name': CharField(label='Nama Proyek', required=True),
        'category': Many2OneField(
            label='Kategori',
            relation='project.project_category',
            required=False,
            help_text='Kategori proyek dari master Project Categories',
        ),
        'date_start': DateField(label='Tanggal Mulai'),
        'date_end': DateField(label='Tanggal Selesai'),
        'project_manager': Many2OneField(
            label='Manajer Proyek (PM)',
            relation='settings.user',
            required=False,
        ),
        'contract_value': MonetaryField(
            label='Nilai Kontrak',
            currency='IDR',
        ),
        'client': Many2OneField(
            label='Client / Owner',
            relation='sales.customer',
            required=False,
        ),
        'location': CharField(label='Lokasi'),
        'executing_entity': Many2OneField(
            label='Entitas Pelaksana',
            relation='settings.company',
            required=False,
        ),
        'lines': One2ManyField(
            label='Project Lines',
            relation='project.project_line',
            inverse_field='project_id',
        ),
        'units': One2ManyField(
            label='Project Units',
            relation='project.project_unit',
            inverse_field='project_id',
        ),
    }

    _list_view = {
        'columns': ['name', 'category', 'client', 'project_manager', 'date_start', 'date_end', 'contract_value', 'location'],
        'filters': ['category'],
        'default_sort': ['name'],
    }

    _form_view = {
        'header': {
            'tabs': [
                {
                    'key': 'general',
                    'label': 'General',
                    'fields': ['name', 'category', 'date_start', 'date_end'],
                },
                {
                    'key': 'details',
                    'label': 'Details',
                    'fields': ['project_manager', 'contract_value', 'client', 'location', 'executing_entity'],
                },
            ],
            'actions': [
                {
                    'label': 'Update Progress',
                    'icon': 'EditOutlined',
                    'color': 'primary',
                    'action': 'update_progress',
                    'wizard': {
                        'title': 'Update Progress',
                        'modes': [
                            {'value': 'update', 'label': '✅ Simpan Progress', 'icon': 'CheckCircleOutlined'},
                        ],
                        'line_selection': {
                            'relation': 'lines',
                            'columns': ['milestone_id', 'progress'],
                            'progress_columns': ['progress'],
                            'show_for_modes': ['update'],
                            'qty_label': 'Progress (%)',
                            'default_selected': False,
                        },
                    },
                },
                {
                    'label': 'Input Penjualan',
                    'icon': 'SendOutlined',
                    'color': 'primary',
                    'action': 'input_sales',
                    'wizard': {
                        'title': 'Input Penjualan',
                        'modes': [
                            {'value': 'save', 'label': '✅ Simpan Penjualan', 'icon': 'CheckCircleOutlined'},
                        ],
                        'line_selection': {
                            'relation': 'units',
                            'columns': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
                            'show_for_modes': ['save'],
                            'qty_label': 'Unit Terjual',
                        },
                    },
                },
            ],
            'smart_buttons': [],
        },
        'notebook': [
            {
                'key': 'lines',
                'label': 'Project Milestones',
                'relation': 'lines',
                'columns': ['milestone_id', 'progress'],
            },
            {
                'key': 'units',
                'label': 'Unit',
                'relation': 'units',
                'columns': ['unit_id', 'qty_available', 'qty_sold', 'sold_percentage'],
            },
        ],
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return self.name or ''

    # ── Actions ──

    def _action_update_progress(self, data=None):
        """Update progress milestone lines dari wizard (nilai input = progress baru)."""
        from core.model_meta import ErpModelBase

        selected_lines_raw = (data or {}).get('selected_lines')
        if not selected_lines_raw or not isinstance(selected_lines_raw, list):
            return {'error': 'Tidak ada baris yang dipilih.'}

        fd = self._field_descriptors.get('lines')
        if not fd:
            return {'error': 'Konfigurasi lines tidak ditemukan.'}
        line_model = ErpModelBase._model_registry.get(fd.relation)
        if not line_model:
            return {'error': 'Model project.project_line tidak ditemukan.'}

        updated = 0
        for item in selected_lines_raw:
            lid = item.get('id')
            if lid is None:
                continue
            value = float(item.get('qty', 0) or 0)
            line = line_model.objects.filter(
                pk=int(lid), project_id=self.pk, is_deleted=False
            ).first()
            if not line:
                continue
            line.progress = min(max(value, 0), 100)
            line.save(update_fields=['progress'])
            updated += 1

        return {'message': f'Progress diupdate untuk {updated} milestone.'}

    def _action_input_sales(self, data=None):
        """Input penjualan unit — set qty_sold (sold_percentage recompute otomatis)."""
        from core.model_meta import ErpModelBase

        selected_lines_raw = (data or {}).get('selected_lines')
        if not selected_lines_raw or not isinstance(selected_lines_raw, list):
            return {'error': 'Tidak ada baris yang dipilih.'}

        fd = self._field_descriptors.get('units')
        if not fd:
            return {'error': 'Konfigurasi units tidak ditemukan.'}
        unit_model = ErpModelBase._model_registry.get(fd.relation)
        if not unit_model:
            return {'error': 'Model project.project_unit tidak ditemukan.'}

        updated = 0
        for item in selected_lines_raw:
            lid = item.get('id')
            if lid is None:
                continue
            value = float(item.get('qty', 0) or 0)
            unit = unit_model.objects.filter(
                pk=int(lid), project_id=self.pk, is_deleted=False
            ).first()
            if not unit:
                continue
            unit.qty_sold = value
            unit.save()  # _run_compute → sold_percentage
            updated += 1

        return {'message': f'Penjualan diinput untuk {updated} unit.'}
