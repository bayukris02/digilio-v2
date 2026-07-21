import { Typography, Card, Table, Tag, Anchor } from 'antd';
import {
  BookOutlined,
  CodeOutlined,
  InfoCircleOutlined,
  ArrowRightOutlined,
  LinkOutlined,
  UnorderedListOutlined,
  FormOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  CalculatorOutlined,
  AppstoreOutlined,
  NumberOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

// ── Inline Code Block Component ──

function CodeBlock({ code, lang = 'python' }: { code: string; lang?: string }) {
  return (
    <pre
      style={{
        background: '#1e1e2e',
        color: '#cdd6f4',
        padding: '16px 20px',
        borderRadius: 8,
        fontSize: 14,
        lineHeight: 1.6,
        overflow: 'auto',
        maxHeight: 500,
        border: '1px solid #313244',
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
      }}
    >
      <code>{code}</code>
    </pre>
  );
}

function NoteBox({ children }: { children: React.ReactNode }) {
  return (
    <Card
      size="small"
      style={{
        background: '#f6ffed',
        border: '1px solid #b7eb8f',
        margin: '16px 0',
      }}
    >
      <Text type="secondary">
        <InfoCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
        {children}
      </Text>
    </Card>
  );
}

function TipBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card
      size="small"
      style={{ marginBottom: 8, borderLeft: '3px solid #1677ff' }}
    >
      <Text strong>{title}</Text>
      <br />
      <Text type="secondary">{children}</Text>
    </Card>
  );
}

// ── Section 1: Model Definition ──

function Section1ModelDefinition() {
  return (
    <div id="model-definition">
      <Title level={2}>
        <BookOutlined style={{ marginRight: 12 }} />
        1. Model Definition
      </Title>
      <Paragraph>
        Setiap model ERP di Digilio adalah class Python yang mewarisi{' '}
        <Text code>BaseModel</Text>. Metaclass (<Text code>ErpModelBase</Text>)
        otomatis mengkonversi definisi Python ke Django model fields + REST API endpoints.
      </Paragraph>

      <Title level={3}>Atribut Wajib</Title>

      <Table
        dataSource={[
          { key: '1', attr: '_model_name', type: 'string', required: '✅ Wajib', desc: 'Nama unik model dalam format dot-notation, e.g. purchase.order' },
          { key: '2', attr: '_fields', type: 'dict', required: '✅ Wajib', desc: 'Dictionary field_name → FieldDescriptor' },
        ]}
        columns={[
          { title: 'Atribut', dataIndex: 'attr', key: 'attr', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Deskripsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Atribut Opsional</Title>

      <Table
        dataSource={[
          { key: '1', attr: '_display_name', desc: 'Nama field yang dipakai sebagai display label (e.g. "reference")' },
          { key: '2', attr: '_states', desc: 'Definisi state machine (status & rules)' },
          { key: '3', attr: '_transitions', desc: 'Transisi antar state (tombol aksi)' },
          { key: '4', attr: '_document_flow', desc: 'Relasi parent→child document creation' },
          { key: '5', attr: '_list_view', desc: 'Konfigurasi tampilan list/table' },
          { key: '6', attr: '_form_view', desc: 'Konfigurasi tampilan form' },
          { key: '7', attr: 'class Meta', desc: 'Django Meta: app_label, verbose_name, dll' },
          { key: '8', attr: 'get_model_config()', desc: 'Override classmethod untuk inject config rules & defaults' },
        ]}
        columns={[
          { title: 'Atribut', dataIndex: 'attr', key: 'attr', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Deskripsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>_display_name</Title>
      <Paragraph>
        Set ke <Text code>'reference'</Text> untuk dokumen (PO, SO, Bill, Invoice, GR, DO).
        Digunakan untuk breadcrumbs, smart buttons label, dan display di dropdown Many2One.
      </Paragraph>

      <Title level={4}>get_model_config()</Title>
      <Paragraph>
        Override classmethod untuk inject default values dan config rules ke frontend:
      </Paragraph>
      <CodeBlock code={`@classmethod
def get_model_config(cls):
    config = super().get_model_config()

    # Inject default sequence
    active_seq = Sequence.objects.filter(
        model_ref=cls._model_name, active=True, is_deleted=False
    ).first()
    if active_seq:
        config['fields']['sequence_id']['default'] = active_seq.pk

    # Column config rules untuk AG Grid
    config['column_config_rules'] = {
        'order_lines': {
            'discount_percentage': {
                'hide_when': {'discount_method': 'nominal', 'discount_type': 'global'},
            },
            'discount_amount': {
                'readonly_when': {'discount_type': 'global'},
                'editable_when': {'discount_method': 'nominal'},
            },
        },
    }

    # Field config rules untuk form fields
    config['field_config_rules'] = {
        'global_discount': {
            'hide_when': {'discount_type': 'per_product'},
            'field_props': {
                'max': {
                    'depends_on': 'discount_method',
                    'percentage': 100,
                    'nominal': None,
                },
                'currency': {
                    'depends_on': 'discount_method',
                    'percentage': '%',
                    'nominal': 'IDR',
                },
            },
        },
    }

    return config`} />

      <Title level={3}>Template Model Baru</Title>
      <Paragraph>
        Copy-paste template ini untuk membuat model baru:
      </Paragraph>
      <CodeBlock code={`from core.fields import (
    CharField, TextField, DateField, MonetaryField,
    SelectionField, BooleanField, Many2OneField, One2ManyField,
)
from core.model_meta import BaseModel


class PurchaseOrder(BaseModel):
    _model_name = 'purchase.order'
    _display_name = 'reference'

    _fields = {
        'reference': CharField(label='Reference', required=True),
        'vendor': Many2OneField(label='Vendor', relation='purchase.vendor'),
        'order_date': DateField(label='Order Date'),
        'total': MonetaryField(label='Total', currency='IDR'),
    }

    class Meta(BaseModel.Meta):
        app_label = 'core'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'`} />
    </div>
  );
}

// ── Section 2: Fields ──

function Section2Fields() {
  return (
    <div id="fields" style={{ marginTop: 48 }}>
      <Title level={2}>
        <CodeOutlined style={{ marginRight: 12 }} />
        2. Fields
      </Title>
      <Paragraph>
        Field descriptors adalah object Python yang mendefinisikan tipe data,
        validasi, label, dan perilaku setiap field. Semua field dideklarasikan
        dalam dictionary <Text code>_fields</Text>.
      </Paragraph>

      <Title level={3}>Field Types</Title>

      <Table
        dataSource={[
          { key: '1', type: 'CharField', import: 'CharField', desc: 'Text pendek (max 255 chars)', contoh: "'name': CharField(label='Name', required=True)" },
          { key: '2', type: 'TextField', import: 'TextField', desc: 'Text panjang (unlimited)', contoh: "'notes': TextField(label='Notes')" },
          { key: '3', type: 'IntegerField', import: 'IntegerField', desc: 'Angka bulat', contoh: "'qty': IntegerField(label='Quantity')" },
          { key: '4', type: 'FloatField', import: 'FloatField', desc: 'Angka desimal', contoh: "'rate': FloatField(label='Rate', default=0)" },
          { key: '5', type: 'MonetaryField', import: 'MonetaryField', desc: 'Nilai uang (decimal 18,2)', contoh: "'total': MonetaryField(label='Total', currency='IDR')" },
          { key: '6', type: 'PercentageField', import: 'PercentageField', desc: 'Persentase (0-100, decorator % di UI)', contoh: "'discount': PercentageField(label='Disc %', default=0)" },
          { key: '7', type: 'BooleanField', import: 'BooleanField', desc: 'Checkbox (true/false)', contoh: "'is_active': BooleanField(label='Active', default=True)" },
          { key: '8', type: 'DateField', import: 'DateField', desc: 'Tanggal (YYYY-MM-DD)', contoh: "'order_date': DateField(label='Order Date')" },
          { key: '9', type: 'DateTimeField', import: 'DateTimeField', desc: 'Timestamp', contoh: "'confirmed_at': DateTimeField(label='Confirmed At')" },
          { key: '10', type: 'SelectionField', import: 'SelectionField', desc: 'Dropdown pilihan', contoh: "'status': SelectionField(label='Status', options=['draft', 'done'])" },
          { key: '11', type: 'Many2OneField', import: 'Many2OneField', desc: 'ForeignKey ke model lain, support autofill', contoh: "'vendor': Many2OneField(label='Vendor', relation='purchase.vendor', autofill={'address': 'address'})" },
          { key: '12', type: 'One2ManyField', import: 'One2ManyField', desc: 'Inverse relation (list anak)', contoh: "'lines': One2ManyField(label='Lines', relation='purchase.line', inverse_field='order_id')" },
        ]}
        columns={[
          { title: 'Field Type', dataIndex: 'type', key: 'type', render: (v: string) => <Text strong>{v}</Text> },
          { title: 'Import', dataIndex: 'import', key: 'import', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Deskripsi', dataIndex: 'desc', key: 'desc' },
          { title: 'Contoh', dataIndex: 'contoh', key: 'contoh', render: (v: string) => <Text code style={{ fontSize: 12 }}>{v}</Text> },
        ]}
        pagination={false}
        size="small"
        bordered
      />

      <Title level={3} style={{ marginTop: 24 }}>Parameter Umum (semua field)</Title>

      <Table
        dataSource={[
          { key: '1', param: 'label', type: 'string', required: 'Opsional', desc: 'Label tampilan di form' },
          { key: '2', param: 'required', type: 'bool', required: 'Opsional', desc: 'Harus diisi? Default: False' },
          { key: '3', param: 'default', type: 'any', required: 'Opsional', desc: 'Nilai default' },
          { key: '4', param: 'virtual', type: 'bool', required: 'Opsional', desc: 'True = frontend-only, tidak ada kolom di DB' },
          { key: '5', param: 'compute', type: 'string', required: 'Opsional', desc: "Nama method compute, e.g. '_compute_total'" },
          { key: '6', param: 'depends', type: 'list', required: 'Opsional', desc: "Field dependencies untuk compute, e.g. ['qty', 'price']" },
          { key: '7', param: 'editable_statuses', type: 'list', required: 'Opsional', desc: "[...] Field hanya editable di status ini. [] = auto-field (tidak bisa diedit user)" },
          { key: '8', param: 'hidden_statuses', type: 'list', required: 'Opsional', desc: "['draft'] — Sembunyikan field di status tertentu" },
          { key: '9', param: 'onchange', type: 'dict', required: 'Opsional', desc: "{'target_field': value} — Reset target field saat source field berubah" },
          { key: '10', param: 'placeholder', type: 'string', required: 'Opsional', desc: 'Custom placeholder text di input' },
          { key: '11', param: 'chatter_show', type: 'bool', required: 'Opsional', desc: 'Tampil di chatter log? Default: True' },
          { key: '12', param: 'unique', type: 'bool', required: 'Opsional', desc: 'Nilai harus unik? Default: False' },
        ]}
        columns={[
          { title: 'Parameter', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Deskripsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
      />

      <Title level={4}>editable_statuses</Title>
      <Paragraph>
        Field-level control untuk menentukan status apa saja yang boleh mengedit field ini.
        Berguna untuk auto-generated fields seperti <Text code>reference</Text> yang diisi
        oleh backend (Draft# → sequence number) — set <Text code>editable_statuses=[]</Text>
        agar field readonly selamanya.
      </Paragraph>
      <CodeBlock code={`# Auto-filled reference — tidak bisa diedit user
'reference': CharField(
    label='Reference',
    required=True,
    editable_statuses=[],
    placeholder='Automatic',
),

# Field hanya bisa diedit di status draft & waiting
'received_qty': FloatField(
    label='Received Qty',
    editable_statuses=['draft', 'waiting'],
),`} />

      <Title level={3}>Many2OneField: autofill</Title>
      <Paragraph>
        Saat user memilih relasi, field-field tertentu bisa otomatis terisi dari record
        yang dipilih:
      </Paragraph>
      <CodeBlock code={`'vendor': Many2OneField(
    label='Vendor',
    relation='purchase.vendor',
    required=True,
    autofill={
        'address': 'address',   # vendor.address → po.address
        'code': 'code',
        'bill_method': 'bill_method',
    },
),`} />
    </div>
  );
}

// ── Section 3: State Machine ──

function Section3StateMachine() {
  const stateColorOptions = [
    { key: '1', value: 'default', color: '#d9d9d9', text: 'Abu-abu (neutral)' },
    { key: '2', value: 'processing', color: '#1677ff', text: 'Biru (in progress)' },
    { key: '3', value: 'success', color: '#52c41a', text: 'Hijau (completed)' },
    { key: '4', value: 'error', color: '#ff4d4f', text: 'Merah (cancelled/error)' },
    { key: '5', value: 'warning', color: '#faad14', text: 'Kuning (warning)' },
    { key: '6', value: 'blue', color: '#1677ff', text: 'Biru' },
    { key: '7', value: 'purple', color: '#722ed1', text: 'Ungu' },
    { key: '8', value: 'cyan', color: '#13c2c2', text: 'Cyan' },
    { key: '9', value: 'orange', color: '#fa8c16', text: 'Oranye' },
    { key: '10', value: 'gold', color: '#faad14', text: 'Emas' },
    { key: '11', value: 'lime', color: '#a0d911', text: 'Lime' },
    { key: '12', value: 'green', color: '#52c41a', text: 'Hijau' },
    { key: '13', value: 'magenta', color: '#eb2f96', text: 'Magenta' },
    { key: '14', value: 'geekblue', color: '#2f54eb', text: 'Geek Blue' },
    { key: '15', value: 'volcano', color: '#fa541c', text: 'Volcano (merah bata)' },
  ];

  return (
    <div id="state-machine" style={{ marginTop: 48 }}>
      <Title level={2}>
        <InfoCircleOutlined style={{ marginRight: 12 }} />
        3. State Machine (<Text code>_states</Text>)
      </Title>
      <Paragraph>
        State machine mendefinisikan <strong>status</strong> apa saja yang dimiliki
        sebuah dokumen dan aturan main untuk setiap status. Core otomatis membuat
        field <Text code>status</Text> (SelectionField) dari definisi ini,
        dan meng-enforce aturan <Text code>allow_edit</Text> /{' '}
        <Text code>allow_delete</Text> di setiap request PUT / DELETE.
      </Paragraph>

      <Title level={3}>Opsi per State</Title>

      <Table
        dataSource={[
          { key: '1', key_name: 'allow_edit', type: 'boolean', default: 'True', desc: 'Boleh diedit? False = PUT ditolak oleh core' },
          { key: '2', key_name: 'allow_delete', type: 'boolean', default: 'True', desc: 'Boleh dihapus? False = DELETE ditolak oleh core' },
          { key: '3', key_name: 'label', type: 'string', default: 'Key name (title case)', desc: 'Label yang tampil di badge status' },
          { key: '4', key_name: 'color', type: 'string', default: 'default', desc: 'Warna badge status (lihat daftar warna di bawah)' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'key_name', key: 'key_name', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Default', dataIndex: 'default', key: 'default' },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Daftar Warna yang Valid</Title>
      <Paragraph>Parameter <Text code>color</Text> menggunakan warna dari Ant Design Tag:</Paragraph>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {stateColorOptions.map((opt) => (
          <Tag key={opt.key} color={opt.value}>{opt.value}</Tag>
        ))}
      </div>

      <NoteBox>
        Parameter <Text code>color</Text> hanya optional. Jika tidak diisi,
        badge akan menggunakan warna default Ant Design.
      </NoteBox>

      <Title level={3}>Contoh Penggunaan</Title>
      <Paragraph>
        Purchase Order memiliki 4 state dengan konfigurasi berikut:
      </Paragraph>
      <CodeBlock code={`_states = {
    'draft': {
        'allow_edit': True,
        'allow_delete': True,
        'label': 'Draft',
        'color': 'default',
    },
    'confirmed': {
        'allow_edit': False,
        'allow_delete': False,
        'label': 'Confirmed',
        'color': 'processing',
    },
    'done': {
        'allow_edit': False,
        'allow_delete': False,
        'label': 'Done',
        'color': 'success',
    },
    'cancelled': {
        'allow_edit': False,
        'allow_delete': False,
        'label': 'Cancelled',
        'color': 'error',
    },
}`} />

      <Title level={4}>Efek allow_edit = False</Title>
      <Paragraph>
        Saat user mengirim PUT request ke record yang statusnya <Text code>confirmed</Text>,
        core otomatis menolak dengan response:
      </Paragraph>
      <CodeBlock code={`HTTP 400 Bad Request
{
    "error": "Cannot edit record with status \\"confirmed\\"."
}`} />

      <Title level={4}>Hidden Statuses (field-level)</Title>
      <Paragraph>
        Selain state-level allow_edit, ada field-level <Text code>hidden_statuses</Text>:
      </Paragraph>
      <CodeBlock code={`'done_qty': FloatField(
    label='Done Qty',
    default=0,
    virtual=True,
    hidden_statuses=['draft'],  # Sembunyi saat status draft
),`} />

      <Title level={3} style={{ marginTop: 24 }}>Tips & Best Practice</Title>

      <TipBox title="State pertama = default">
        State pertama dalam dictionary akan menjadi nilai default saat record baru dibuat.
        Biasanya <Text code>draft</Text>.
      </TipBox>

      <TipBox title="Set allow_edit jadi False untuk non-draft">
        Setelah dokumen dikonfirmasi, seharusnya tidak bisa diedit lagi.
        Core otomatis enforce ini — jadi tidak perlu nulis validasi manual di PUT.
      </TipBox>

      <TipBox title="Model master data tidak perlu _states">
        Jika model tidak punya lifecycle dokumen (create → confirm → done),
        cukup jangan define <Text code>_states</Text>. Core tidak akan generate status field.
      </TipBox>
    </div>
  );
}

// ── Section 4: Transitions ──

function Section4Transitions() {
  return (
    <div id="transitions" style={{ marginTop: 48 }}>
      <Title level={2}>
        <ArrowRightOutlined style={{ marginRight: 12 }} />
        4. Transitions (<Text code>_transitions</Text>)
      </Title>
      <Paragraph>
        Transitions mendefinisikan <strong>tombol aksi</strong> yang mengubah status
        dokumen. Core otomatis menjalankan transisi saat user memanggil endpoint{' '}
        <Text code>.../action/</Text> dengan nama action yang cocok.
      </Paragraph>

      <Paragraph>
        Sebelum ada <Text code>_transitions</Text>, setiap action harus ditulis manual
        sebagai method <Text code>_action_confirm()</Text>,{' '}
        <Text code>_action_cancel()</Text>, dll. Sekarang cukup deklarasi 1 baris —
        core yang handle sisanya.
      </Paragraph>

      <Title level={3}>Opsi per Transition</Title>

      <Table
        dataSource={[
          { key: '1', param: 'name', type: 'string', required: '✅ Wajib', desc: 'Nama action (dikirim dari frontend). Core panggil endpoint action/ dengan name ini' },
          { key: '2', param: 'from', type: 'string[]', required: '✅ Wajib', desc: 'Daftar status yang diizinkan untuk menjalankan transisi ini' },
          { key: '3', param: 'to', type: 'string', required: '✅ Wajib', desc: 'Status tujuan setelah transisi berhasil' },
          { key: '4', param: 'label', type: 'string', required: 'Opsional', desc: 'Label tombol (jika tidak diisi, pakai name)' },
          { key: '5', param: 'icon', type: 'string', required: 'Opsional', desc: 'Nama icon Ant Design (e.g. CheckOutlined)' },
          { key: '6', param: 'guard', type: 'string', required: 'Opsional', desc: 'Nama method penjaga. Core panggil method ini SEBELUM transisi' },
          { key: '7', param: 'effect', type: 'string', required: 'Opsional', desc: 'Nama method efek. Core panggil method ini SETELAH status berubah' },
        ]}
        columns={[
          { title: 'Parameter', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Alur Eksekusi Transisi</Title>
      <Paragraph>Ketika user menekan tombol Confirm, core menjalankan urutan berikut:</Paragraph>

      <CodeBlock code={`1. Frontend: POST .../action/  { "action": "confirm" }
2. Core:   Cari transisi dengan name = "confirm" di _transitions[]
3. Core:   Validasi status sekarang ada di "from"?
4. Core:   Panggil method guard (jika ada)  ← cek apakah boleh jalan
5. Core:   Set status = "confirmed"          ← ubah status
6. Core:   Panggil method effect (jika ada)  ← efek setelah transisi
7. Core:   Save ke database
8. Core:   Return record terbaru ke frontend`} />

      <Title level={3}>Contoh dari Purchase Order</Title>
      <CodeBlock code={`_transitions = [
    {
        'name': 'confirm',
        'from': ['draft'],
        'to': 'confirmed',
        'label': 'Confirm',
        'icon': 'CheckOutlined',
        'guard': '_guard_confirm',
        'effect': '_effect_confirm',
    },
    {
        'name': 'mark_done',
        'from': ['confirmed'],
        'to': 'done',
        'label': 'Mark Done',
        'icon': 'CheckCircleOutlined',
    },
    {
        'name': 'cancel',
        'from': ['draft', 'confirmed'],
        'to': 'cancelled',
        'label': 'Cancel',
        'icon': 'StopOutlined',
        'guard': '_guard_cancel',
    },
]`} />

      <NoteBox>
        Action yang TIDAK mengubah status (Print, Email) tetap menggunakan method
        <Text code>_action_print()</Text> — itu legacy actions, bukan transisi.
        Lihat <a href="#legacy-actions">Section 9: Legacy Actions</a>.
      </NoteBox>
    </div>
  );
}

// ── Section 5: Document Flow ──

function Section5DocumentFlow() {
  return (
    <div id="document-flow" style={{ marginTop: 48 }}>
      <Title level={2}>
        <LinkOutlined style={{ marginRight: 12 }} />
        5. Document Flow (<Text code>_document_flow</Text>)
      </Title>
      <Paragraph>
        Document flow mendefinisikan <strong>dokumen anak</strong> yang bisa dibuat
        dari dokumen ini. Contoh: dari Purchase Order bisa dibuat Goods Receipt.
        Core mengatur validasi, pembuatan, dan enforcement constraint dengan
        guard cancel otomatis — tidak perlu nulis <Text code>if GR.objects.filter(...)</Text> manual.
      </Paragraph>

      <Title level={3}>Opsi per Child</Title>

      <Table
        dataSource={[
          { key: '1', param: 'model', type: 'string', required: '✅ Wajib', desc: 'Nama model anak (e.g. purchase.goods_receipt)' },
          { key: '2', param: 'label', type: 'string', required: '✅ Wajib', desc: 'Label yang tampil di tombol "Buat ..."' },
          { key: '3', param: 'icon', type: 'string', required: 'Opsional', desc: 'Icon untuk tombol (Ant Design)' },
          { key: '4', param: 'source_field_in_child', type: 'string', required: '✅ Wajib', desc: 'Field di child yang nyimpen reference ke parent (e.g. purchase_order)' },
          { key: '5', param: 'state_conditions', type: 'dict', required: '✅ Wajib', desc: 'Aturan state: allowed_parent_states + blocked_child_states_for_parent_cancel' },
          { key: '6', param: 'mapping', type: 'dict', required: 'Opsional', desc: 'Mapping field parent → child (template & copy)' },
          { key: '7', param: 'constraints', type: 'dict', required: 'Opsional', desc: 'max_per_parent, unique_per_parent' },
        ]}
        columns={[
          { title: 'Parameter', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Detail state_conditions</Title>

      <Table
        dataSource={[
          { key: '1', param: 'allowed_parent_states', type: 'string[]', desc: "Parent harus dalam status ini untuk bisa bikin child. Contoh: ['confirmed', 'done']" },
          { key: '2', param: 'blocked_child_states_for_parent_cancel', type: 'string[]', desc: "Parent gak bisa dicancel kalau child masih punya status ini. Contoh: ['draft', 'done'] — child harus cancelled dulu" },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Detail constraints</Title>

      <Table
        dataSource={[
          { key: '1', param: 'max_per_parent', type: 'int', desc: 'Maksimal jumlah child per parent. 0 = unlimited, 1 = max 1 child' },
          { key: '2', param: 'unique_per_parent', type: 'bool', desc: 'True = cuma boleh 1 child per parent' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Contoh dari Purchase Order</Title>
      <CodeBlock code={`_document_flow = {
    'children': [
        {
            'model': 'purchase.goods_receipt',
            'label': 'Goods Receipt',
            'icon': 'InboxOutlined',
            'source_field_in_child': 'purchase_order',
            'state_conditions': {
                'allowed_parent_states': ['confirmed', 'done'],
                'blocked_child_states_for_parent_cancel': ['draft', 'waiting', 'done'],
            },
            'mapping': {
                'purchase_order': 'id',  # Set parent PK
            },
            'constraints': {
                'max_per_parent': 0,       # 0 = unlimited GR per PO
                'unique_per_parent': False,
            },
        },
        {
            'model': 'accounting.vendor_bill',
            'label': 'Tagihan',
            'icon': 'FileTextOutlined',
            'source_field_in_child': 'purchase_order',
            'state_conditions': {
                'allowed_parent_states': ['confirmed', 'done'],
                'blocked_child_states_for_parent_cancel': ['draft', 'confirmed', 'done'],
            },
            'mapping': {
                'vendor': 'vendor',
                'purchase_order': 'id',
            },
            'constraints': {
                'max_per_parent': 0,
                'unique_per_parent': False,
            },
        },
    ],
}`} />

      <Title level={3}>Guard Cancel Otomatis</Title>
      <Paragraph>
        Core otomatis memeriksa <Text code>blocked_child_states_for_parent_cancel</Text>
        saat user mencoba cancel parent. Guard manual (<Text code>_guard_cancel</Text>)
        tinggal panggil method bawaan:
      </Paragraph>
      <CodeBlock code={`def _guard_cancel(self):
    can_cancel, msg = self._can_cancel()
    if not can_cancel:
        raise ValueError(msg)`} />

      <Title level={3} style={{ marginTop: 24 }}>Multi-level Chain</Title>
      <Paragraph>
        Setiap model punya <Text code>_document_flow</Text> sendiri, jadi chain bisa
        multi-level tanpa inheritance:
      </Paragraph>

      <CodeBlock code={`SalesOrder._document_flow → child: stock.delivery
DeliveryOrder._document_flow → child: account.invoice
AccountInvoice._document_flow → child: account.journal.entry`} />

      <TipBox title="Mapping bisa template string atau callable">
        <Text code>{`'reference': 'GR/{parent.reference}'`}</Text> = template string.
        Bisa juga pakai Python function callable untuk logic yang kompleks.
      </TipBox>
    </div>
  );
}

// ── Section 6: List View ──

function Section6ListView() {
  return (
    <div id="list-view" style={{ marginTop: 48 }}>
      <Title level={2}>
        <UnorderedListOutlined style={{ marginRight: 12 }} />
        6. List View (<Text code>_list_view</Text>)
      </Title>
      <Paragraph>
        Mengkonfigurasi tampilan halaman daftar (table/AG Grid).
        Semua kolom, filter, dan grouping didefinisikan di sini.
      </Paragraph>

      <Title level={3}>Opsi</Title>

      <Table
        dataSource={[
          { key: '1', param: 'columns', type: 'string[]', required: 'Opsional', desc: 'Daftar field yang tampil sebagai kolom table' },
          { key: '2', param: 'filters', type: 'string[]', required: 'Opsional', desc: 'Daftar field yang bisa difilter' },
          { key: '3', param: 'group_by', type: 'string[]', required: 'Opsional', desc: 'Daftar field untuk grouping row' },
          { key: '4', param: 'default_sort', type: 'string[]', required: 'Opsional', desc: "Sort default. Prefix - untuk descending, e.g. ['-updated_at']" },
        ]}
        columns={[
          { title: 'Parameter', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Contoh</Title>
      <CodeBlock code={`_list_view = {
    'columns': ['reference', 'vendor', 'order_date', 'status', 'total'],
    'filters': ['status', 'order_date'],
    'group_by': ['status', 'category'],
    'default_sort': ['-updated_at'],
}`} />
    </div>
  );
}

// ── Section 7: Form View ──

function Section7FormView() {
  return (
    <div id="form-view" style={{ marginTop: 48 }}>
      <Title level={2}>
        <FormOutlined style={{ marginRight: 12 }} />
        7. Form View (<Text code>_form_view</Text>)
      </Title>
      <Paragraph>
        Mengkonfigurasi tampilan form detail — termasuk tab, tombol aksi, smart buttons,
        wizard actions, dan notebook (table baris anak + summary).
      </Paragraph>

      <Title level={3}>Struktur</Title>
      <CodeBlock code={`_form_view = {
    'header': {
        'tabs': [
            {
                'key': 'general',
                'label': 'General',
                'fields': ['reference', 'vendor', 'order_date'],
            },
            {
                'key': 'details',
                'label': 'Details',
                'fields': ['notes', 'description'],
            },
        ],
        'actions': [
            {'label': 'Print', 'icon': 'FileTextOutlined', 'color': 'green', 'action': 'print'},
            {'label': 'Confirm', 'icon': 'CheckOutlined', 'color': 'primary', 'action': 'confirm', 'states': ['draft']},
        ],
        'smart_buttons': [
            {'label': 'Receipt', 'model': 'purchase.goods_receipt', 'icon': 'InboxOutlined'},
            {'label': 'Bill', 'model': 'accounting.vendor_bill', 'icon': 'FileTextOutlined'},
        ],
    },
    'notebook': [
        {
            'key': 'lines',
            'label': 'Order Lines',
            'relation': 'order_lines',
            'columns': ['product', 'qty', 'price', 'total'],
            'summary': {
                'columns': {'qty': 'sum', 'total': 'sum'},
                'subtotal': 'subtotal',
                'lines': ['discount', 'tax'],
                'compute_deps': ['discount_type', 'discount_method', 'global_discount'],
                'grand_total': 'grand_total',
                'after_grand_total': ['due_amount'],
            },
        },
    ],
}`} />

      <Title level={3}>Opsi header.tabs</Title>
      <Table
        dataSource={[
          { key: '1', param: 'key', type: 'string', desc: 'Key unik tab' },
          { key: '2', param: 'label', type: 'string', desc: 'Label tab' },
          { key: '3', param: 'fields', type: 'string[]', desc: 'Daftar field yang tampil di tab ini' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Opsi header.actions</Title>
      <Table
        dataSource={[
          { key: '1', param: 'label', type: 'string', desc: 'Label tombol' },
          { key: '2', param: 'icon', type: 'string', desc: 'Nama icon Ant Design' },
          { key: '3', param: 'color', type: 'string', desc: 'Warna tombol (primary, green, danger, dll)' },
          { key: '4', param: 'action', type: 'string', desc: "Nama action (cocok dengan _transitions.name atau _action_{name})" },
          { key: '5', param: 'states', type: 'string[]', desc: 'Filter: tombol hanya muncul di status tertentu' },
          { key: '6', param: 'wizard', type: 'dict', desc: 'Konfigurasi wizard modal (lihat Section 11)' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>states filter</Title>
      <Paragraph>
        Setiap action bisa filter visibility berdasarkan status dokumen. Contoh:
        tombol Cancel hanya muncul saat status draft/confirmed.
      </Paragraph>
      <CodeBlock code={`{'label': 'Cancel', 'icon': 'StopOutlined', 'color': 'red',
 'action': 'cancel', 'states': ['draft', 'confirmed']}`} />

      <Title level={3}>Opsi header.smart_buttons</Title>
      <Table
        dataSource={[
          { key: '1', param: 'label', type: 'string', desc: 'Label tombol' },
          { key: '2', param: 'model', type: 'string', desc: 'Nama model child yang ditampilkan' },
          { key: '3', param: 'icon', type: 'string', desc: 'Nama icon Ant Design' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />
      <Paragraph>
        Smart buttons menampilkan jumlah record child di badge. Saat diklik, navigasi
        ke halaman form child. Jumlah dihitung otomatis dari <Text code>_document_flow.children</Text>.
      </Paragraph>

      <Title level={3}>Opsi notebook</Title>
      <Table
        dataSource={[
          { key: '1', param: 'key', type: 'string', desc: 'Key tab notebook' },
          { key: '2', param: 'label', type: 'string', desc: 'Label tab' },
          { key: '3', param: 'relation', type: 'string', desc: 'Nama field one2many yang ditampilkan sebagai table' },
          { key: '4', param: 'columns', type: 'string[]', desc: 'Kolom yang tampil di AG Grid (default: semua field)' },
          { key: '5', param: 'read_only', type: 'bool', desc: 'True = table tidak bisa diedit (view-only tab)' },
          { key: '6', param: 'summary', type: 'dict', desc: 'Konfigurasi summary footer (lihat detail di bawah)' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Detail summary config</Title>
      <Table
        dataSource={[
          { key: '1', param: 'columns', type: 'dict', desc: "{'qty': 'sum', 'total': 'sum'} — Sigma row di AG Grid footer" },
          { key: '2', param: 'subtotal', type: 'string', desc: 'Field name untuk nilai subtotal di SummaryCard' },
          { key: '3', param: 'lines', type: 'string[]', desc: "Field name array untuk baris diskon/pajak di SummaryCard — ['discount', 'tax']" },
          { key: '4', param: 'grand_total', type: 'string', desc: 'Field name untuk grand total di SummaryCard' },
          { key: '5', param: 'compute_deps', type: 'string[]', desc: "Header field dependencies untuk trigger compute API — ['discount_type', 'global_discount']" },
          { key: '6', param: 'after_grand_total', type: 'string[]', desc: "Field yang tampil setelah grand total — ['due_amount', 'dp_amount']" },
          { key: '7', param: 'child_details', type: 'dict', desc: "Konfigurasi daftar child document di bawah summary" },
          { key: '8', param: 'inputs', type: 'array', desc: "[DEPRECATED] Gunakan compute_deps untuk trigger compute" },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Contoh Summary dengan child_details</Title>
      <CodeBlock code={`'summary': {
    'columns': {'qty': 'sum', 'discount_amount': 'sum',
                'tax_amount': 'sum', 'total': 'sum'},
    'subtotal': 'subtotal',
    'lines': ['discount', 'tax'],
    'compute_deps': ['discount_type', 'discount_method', 'global_discount'],
    'grand_total': 'grand_total',
    'after_grand_total': ['due_amount'],
    'child_details': {
        'label': 'Down Payments & Bills',
        'data_key': '_bill_details',
        'model': 'accounting.vendor_bill',
    },
}`} />
    </div>
  );
}

// ── Section 8: Guards & Effects ──

function Section8GuardsEffects() {
  return (
    <div id="guards-effects" style={{ marginTop: 48 }}>
      <Title level={2}>
        <SafetyOutlined style={{ marginRight: 12 }} />
        8. Guards & Effects
      </Title>
      <Paragraph>
        <Text code>guard</Text> dan <Text code>effect</Text> adalah method opsional
        yang dipanggil core sebelum/sesudah transisi status. Keduanya dideklarasikan
        di <Text code>_transitions</Text> sebagai string nama method.
      </Paragraph>

      <Title level={3}>Guard (Penjaga Pintu)</Title>
      <Paragraph>
        Dipanggil <strong>sebelum</strong> status berubah. Gunakan untuk validasi
        tambahan. Jika method melempar <Text code>ValueError</Text>, transisi
        dibatalkan dan frontend mendapat error 400.
      </Paragraph>

      <CodeBlock code={`def _guard_confirm(self):
    """Wajib pilih sequence sebelum konfirmasi."""
    if not self.sequence_id:
        raise ValueError('Silakan pilih Sequence terlebih dahulu.')

    # Validasi minimal 1 order line
    from core.model_meta import ErpModelBase
    fd = self._field_descriptors.get('order_lines')
    if fd:
        child_model = ErpModelBase._model_registry.get(fd.relation)
        if child_model:
            count = child_model.objects.filter(
                **{fd.inverse_field: self.pk, 'is_deleted': False}
            ).count()
            if count == 0:
                raise ValueError('Minimal harus ada 1 Order Line.')`} />

      <Title level={3}>Effect (Efek Samping)</Title>
      <Paragraph>
        Dipanggil <strong>setelah</strong> status diubah, tapi{' '}
        <strong>sebelum</strong> disave ke database. Gunakan untuk mengubah field
        lain bersamaan dengan transisi.
      </Paragraph>

      <CodeBlock code={`def _effect_confirm(self):
    """Generate reference dari sequence setelah confirm."""
    from core.sequence_engine import SequenceEngine
    if (self.reference or '').startswith('Draft#'):
        self.reference = SequenceEngine.next_by_id(self.sequence_id.pk)`} />

      <Title level={3}>Guard Cancel dengan _can_cancel()</Title>
      <Paragraph>
        Untuk cancel protection dengan child documents, gunakan method bawaan:
      </Paragraph>
      <CodeBlock code={`def _guard_cancel(self):
    can_cancel, msg = self._can_cancel()
    if not can_cancel:
        raise ValueError(msg)`} />
    </div>
  );
}

// ── Section 9: Legacy Actions ──

function Section9LegacyActions() {
  return (
    <div id="legacy-actions" style={{ marginTop: 48 }}>
      <Title level={2}>
        <ThunderboltOutlined style={{ marginRight: 12 }} />
        9. Legacy Actions
      </Title>
      <Paragraph>
        Action yang <strong>tidak mengubah status</strong> (Print, Email, Export)
        tetap menggunakan method <Text code>_action{'{name}'}()</Text>.
        Core akan fallback ke method ini jika tidak menemukan transisi yang cocok.
      </Paragraph>

      <Title level={3}>Kapan Pakai Legacy vs Transition?</Title>

      <Table
        dataSource={[
          { key: '1', situasi: 'User klik Confirm → status berubah', pakai: '_transitions' },
          { key: '2', situasi: 'User klik Cancel → status berubah', pakai: '_transitions' },
          { key: '3', situasi: 'User klik Print → tampilkan PDF', pakai: '_action_print()' },
          { key: '4', situasi: 'User klik Email → kirim email', pakai: '_action_email()' },
          { key: '5', situasi: 'User klik create_child → buat child doc', pakai: 'Wizard action + _action_{name}()' },
        ]}
        columns={[
          { title: 'Situasi', dataIndex: 'situasi', key: 'situasi' },
          { title: 'Pakai', dataIndex: 'pakai', key: 'pakai', render: (v: string) => <Text code>{v}</Text> },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={3}>Contoh Legacy Action: Print</Title>
      <CodeBlock code={`def _action_print(self):
    """Print PO — tampilkan print preview di halaman yang sama."""
    return {
        '_action_type': 'print_preview',
        'url': f'/api/print/purchase.order/{self.pk}/preview/',
        'pdf_url': f'/api/print/purchase.order/{self.pk}/download/',
    }`} />

      <NoteBox>
        Legacy actions harus return dict dengan setidaknya{' '}
        <Text code>_action_type</Text> — biasanya 'refresh' atau 'print_preview'.
      </NoteBox>
    </div>
  );
}

// ── Section 10: Compute Methods ──

function Section10ComputeMethods() {
  return (
    <div id="compute-methods" style={{ marginTop: 48 }}>
      <Title level={2}>
        <CalculatorOutlined style={{ marginRight: 12 }} />
        10. Compute Methods
      </Title>
      <Paragraph>
        Compute method adalah method yang otomatis dipanggil setiap kali record
        disimpan. Gunakan untuk menghitung field yang nilainya berasal dari field lain
        (total = qty × price, grand_total = subtotal - discount + tax).
        Juga dipanggil real-time oleh frontend via endpoint <Text code>.../compute/</Text>.
      </Paragraph>

      <Title level={3}>Cara Kerja</Title>
      <Paragraph>
        Field dideklarasikan dengan parameter <Text code>compute</Text> dan{' '}
        <Text code>depends</Text>. Core akan memanggil method compute setiap{' '}
        <Text code>save()</Text>.
      </Paragraph>

      <CodeBlock code={`# Field definition (parent model header)
'discount': MonetaryField(
    label='Discount',
    currency='IDR',
    compute='_compute_summary',
    depends=['order_lines', 'discount_type', 'discount_method', 'global_discount'],
),
'grand_total': MonetaryField(
    label='Grand Total',
    currency='IDR',
    compute='_compute_summary',
    depends=['order_lines', 'discount_type', 'discount_method', 'global_discount'],
),`} />

      <Title level={3}>Single-Formula _compute_summary</Title>
      <Paragraph>
        Semua mode diskon (per-product dan global) menggunakan satu formula yang sama.
        Global discount diprorata langsung ke <Text code>discount_amount</Text> per line:
      </Paragraph>
      <CodeBlock code={`def _compute_summary(self):
    # 1. Load lines dari tmp (in-memory) atau DB
    lines_data = getattr(self, '_tmp_one2many', {}).get('order_lines', [])
    if not lines_data and self.pk:
        # Fallback: load from DB
        ...

    # 2. Recompute per-line values
    computed_lines = []
    for line in lines_data:
        qty = float(line.get('qty', 0) or 0)
        price = float(line.get('price', 0) or 0)
        subtotal = qty * price
        disc_pct = float(line.get('discount_percentage', 0) or 0)
        disc_amt = subtotal * (disc_pct / 100) if disc_pct > 0 \
            else float(line.get('discount_amount', 0) or 0)
        computed_lines.append({
            '_key': line.get('_key'),
            'subtotal_raw': subtotal,
            'discount_amount': round(disc_amt, 2),
            'discount_percentage': disc_pct,
            'tax_percentage': float(line.get('tax_percentage', 0) or 0),
        })

    # 3. Global mode: prorata header discount
    if discount_type == 'global':
        global_val = float(getattr(self, 'global_discount', 0) or 0)
        disc_method = getattr(self, 'discount_method', 'percentage') or 'percentage'
        raw_all = sum(cl['subtotal_raw'] for cl in computed_lines)
        total_disc = global_val if disc_method == 'nominal' \
            else raw_all * (global_val / 100)
        for cl in computed_lines:
            cl['discount_percentage'] = 0
            cl['discount_amount'] = round(
                (cl['subtotal_raw'] / raw_all) * total_disc, 2
            ) if raw_all > 0 else 0

    # 4. Per-product: cleanup stale values (mode switch handling)
    if discount_type == 'per_product':
        self.global_discount = 0
        ...

    # 5. Tax & total — 1 formula
    for cl in computed_lines:
        taxable = cl['subtotal_raw'] - cl['discount_amount']
        tax_amt = round(taxable * (cl['tax_percentage'] / 100), 2)
        cl['tax_amount'] = tax_amt
        cl['total'] = round(
            cl['subtotal_raw'] - cl['discount_amount'] + tax_amt, 2
        )

    # 6. Summary totals
    self.subtotal = sum(cl['subtotal_raw'] for cl in computed_lines)
    self.discount = sum(cl['discount_amount'] for cl in computed_lines)
    self.tax = sum(cl['tax_amount'] for cl in computed_lines)
    self.grand_total = sum(cl['total'] for cl in computed_lines)

    # 7. Kirim per-line values ke frontend
    self._computed_o2m_lines = {
        'order_lines': [
            {k: cl[k] for k in ('_key', 'discount_amount',
             'discount_percentage', 'tax_amount', 'total')}
            for cl in computed_lines if cl.get('_key')
        ],
    }`} />

      <Title level={3}>Line-level compute</Title>
      <Paragraph>
        Setiap line model juga punya compute method sendiri untuk menghitung
        nilai per baris:
      </Paragraph>
      <CodeBlock code={`# Line model fields
'total': MonetaryField(
    label='Total',
    currency='IDR',
    compute='_compute_total',
    depends=['qty', 'price', 'discount_amount', 'tax_amount'],
),

# Implementation
def _compute_total(self):
    qty = float(self.qty or 0)
    price = float(self.price or 0)
    subtotal = qty * price
    disc_pct = float(self.discount_percentage or 0)
    if disc_pct > 0:
        self.discount_amount = round(subtotal * (disc_pct / 100), 2)
    disc_amt = float(self.discount_amount or 0)
    taxable = subtotal - disc_amt
    tax_pct = float(self.tax_percentage or 0)
    self.tax_amount = round(taxable * (tax_pct / 100), 2)
    self.total = round(subtotal - disc_amt + float(self.tax_amount or 0), 2)`} />

      <Title level={3}>_computed_o2m_lines (Per-Line Response)</Title>
      <Paragraph>
        Compute API endpoint mengembalikan <Text code>_computed_o2m_lines</Text> —
        dict keyed by O2M relation name, masing-masing berisi array per-line
        computed values. Frontend secara generik merge nilai-nilai ini ke
        state line items.
      </Paragraph>
      <CodeBlock code={`# Response dari POST .../compute/
{
    "subtotal": 1000000,
    "discount": 50000,
    "tax": 104500,
    "grand_total": 1054500,
    "_computed_o2m_lines": {
        "order_lines": [
            {
                "_key": "__key1",
                "discount_amount": 50000,
                "discount_percentage": 0,
                "tax_amount": 50000,
                "total": 500000
            }
        ]
    }
}`} />

      <Title level={3}>Compute API (Real-time Preview)</Title>
      <Paragraph>
        Frontend bisa memanggil endpoint <Text code>.../compute/</Text> untuk preview
        tanpa menyimpan. Core membuat instance in-memory, set field, jalankan compute,
        dan return hasil termasuk <Text code>_computed_o2m_lines</Text>.
      </Paragraph>

      <CodeBlock code={`POST /api/models/purchase.order/compute/
Body: {
    "discount_type": "global",
    "global_discount": 10,
    "discount_method": "percentage",
    "order_lines": [{"qty": 10, "price": 100000, ...}]
}
Response: {
    "subtotal": 1000000,
    "discount": 100000,
    "grand_total": 999000,
    "_computed_o2m_lines": { ... }
}`} />

      <TipBox title="depends harus diisi">
        Parameter <Text code>depends</Text> memberitahu frontend field mana yang
        perlu di-refresh saat field lain berubah. Jika lupa, frontend tidak akan
        otomatis memicu recompute.
      </TipBox>

      <TipBox title="compute_deps di summary config">
        Summary notebook punya <Text code>compute_deps</Text> — daftar header field
        yang dikirim ke compute API saat nilai field tersebut berubah.
        <Text code>{`'compute_deps': ['discount_type', 'discount_method', 'global_discount']`}</Text>
      </TipBox>

      <TipBox title="Akses child records via model registry">
        One2ManyField tidak punya Django reverse manager. Gunakan{' '}
        <Text code>ErpModelBase._model_registry</Text> untuk akses child model.
      </TipBox>
    </div>
  );
}

// ── Section 11: Wizards ──

function Section11Wizards() {
  return (
    <div id="wizards" style={{ marginTop: 48 }}>
      <Title level={2}>
        <AppstoreOutlined style={{ marginRight: 12 }} />
        11. Wizard Actions
      </Title>
      <Paragraph>
        Wizard adalah modal dialog yang muncul saat user mengklik action button.
        Berguna untuk action yang membutuhkan input tambahan sebelum dieksekusi,
        seperti membuat Goods Receipt (pilih mode + pilih qty) atau membuat
        Down Payment (input nominal DP).
      </Paragraph>

      <Title level={3}>Struktur Wizard</Title>
      <CodeBlock code={`{
    'label': 'Terima Barang',
    'icon': 'InboxOutlined',
    'color': 'primary',
    'action': 'receive_goods',
    'states': ['confirmed'],
    'wizard': {
        'title': 'Penerimaan Barang',
        'modes': [
            {
                'value': 'save_draft',
                'label': '📄 Buat Draft Dokumen',
                'icon': 'FileAddOutlined',
            },
            {
                'value': 'confirm',
                'label': '✅ Konfirm Penerimaan',
                'icon': 'CheckCircleOutlined',
            },
        ],
        'line_selection': {
            'relation': 'order_lines',
            'columns': ['product', 'qty', 'done_qty',
                        'in_receipt_qty', 'remaining_qty'],
            'show_for_modes': ['save_draft', 'confirm'],
            'qty_label': 'Receive Qty',
        },
    },
}`} />

      <Title level={3}>Opsi Wizard</Title>

      <Table
        dataSource={[
          { key: '1', param: 'title', type: 'string', required: '✅ Wajib', desc: 'Judul modal dialog' },
          { key: '2', param: 'modes', type: 'array', required: '✅ Wajib', desc: 'Daftar mode/opsi yang bisa dipilih user (radio buttons)' },
          { key: '3', param: 'line_selection', type: 'dict', required: 'Opsional', desc: 'Tampilkan grid baris anak dengan checkbox untuk seleksi + input qty' },
          { key: '4', param: 'inputs', type: 'array', required: 'Opsional', desc: 'Custom input fields (number, text, selection) di luar line_selection' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Required', dataIndex: 'required', key: 'required' },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Opsi modes</Title>
      <Table
        dataSource={[
          { key: '1', param: 'value', type: 'string', desc: 'Value mode yang dikirim ke backend' },
          { key: '2', param: 'label', type: 'string', desc: 'Label radio button' },
          { key: '3', param: 'icon', type: 'string', desc: 'Icon Ant Design untuk radio button' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Opsi line_selection</Title>
      <Table
        dataSource={[
          { key: '1', param: 'relation', type: 'string', desc: 'Nama O2M relation yang ditampilkan' },
          { key: '2', param: 'columns', type: 'string[]', desc: 'Kolom yang ditampilkan di grid' },
          { key: '3', param: 'show_for_modes', type: 'string[]', desc: 'Mode mana saja yang menampilkan grid ini' },
          { key: '4', param: 'qty_label', type: 'string', desc: 'Label kolom input qty (default: Qty)' },
        ]}
        columns={[
          { title: 'Key', dataIndex: 'param', key: 'param', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Type', dataIndex: 'type', key: 'type', render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Fungsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <Title level={4}>Opsi inputs (custom input fields)</Title>
      <Paragraph>
        Untuk wizard yang butuh input tambahan (contoh: Down Payment):
      </Paragraph>
      <CodeBlock code={`'inputs': [
    {
        'key': 'dp_value',
        'label': 'DP',
        'type': 'number',
        'default': 0,
        'min': 0,
    },
    {
        'key': 'dp_mode',
        'label': 'Mode',
        'type': 'selection',
        'options': [
            {'value': 'percentage', 'label': '%'},
            {'value': 'nominal', 'label': 'Rp'},
        ],
        'default': 'percentage',
    },
],`} />

      <Title level={3}>Backend Handler</Title>
      <Paragraph>
        Backend menerima data wizard sebagai parameter method:
      </Paragraph>
      <CodeBlock code={`def _action_receive_goods(self, data=None):
    mode = (data or {}).get('mode', 'save_draft')
    selected_lines = (data or {}).get('selected_lines', [])
    # selected_lines: [{'id': 1, 'qty': 5}, {'id': 2, 'qty': 10}]

    if mode == 'save_draft':
        gr_status = 'waiting'
    elif mode == 'confirm':
        gr_status = 'done'

    # Gunakan child_cfg dari _document_flow
    child_cfg = self._get_child_flow('purchase.goods_receipt')
    # Buat GR record + copy lines dengan qty sesuai
    ...

    return {
        '_action_type': 'open_record',
        'model': 'purchase.goods_receipt',
        'record_id': gr.pk,
        'from': self._model_name,
        'fromId': self.pk,
    }`} />

      <TipBox title="Return _action_type: open_record untuk breadcrumb">
        Wizard action yang membuat child document harus return{' '}
        <Text code>{`'_action_type': 'open_record'`}</Text> dengan parameter{' '}
        <Text code>from</Text> dan <Text code>fromId</Text> agar breadcrumb
        terhubung ke parent.
      </TipBox>
    </div>
  );
}

// ── Section 12: Sequence & Auto-numbering ──

function Section12Sequence() {
  return (
    <div id="sequence" style={{ marginTop: 48 }}>
      <Title level={2}>
        <NumberOutlined style={{ marginRight: 12 }} />
        12. Sequence & Auto-numbering
      </Title>
      <Paragraph>
        Setiap dokumen ERP membutuhkan nomor referensi yang unik dan berurutan.
        Digilio menyediakan sistem sequence berbasis engine sendiri yang
        memisahkan format nomor dari logika model.
      </Paragraph>

      <Title level={3}>Cara Kerja</Title>
      <Paragraph>
        Sequence diatur melalui model <Text code>settings.sequence</Text> —
        record yang mendefinisikan prefix, padding, dan format nomor.
        Model dokumen (PO, SO, dll) memiliki field <Text code>sequence_id</Text>
        yang merupakan Many2One ke sequence record.
      </Paragraph>

      <CodeBlock code={`# Di model definition
'sequence_id': Many2OneField(
    label='Order Type',
    relation='settings.sequence',
    help_text='Pilih format nomor dokumen (PO Local / PO Import, dll)',
),
'reference': CharField(
    label='Reference',
    required=True,
    editable_statuses=[],
    placeholder='Automatic',
),`} />

      <Title level={3}>Alur Generate Reference</Title>
      <Paragraph>
        Reference digenerate dalam 2 tahap:
      </Paragraph>
      <CodeBlock code={`1. Saat create: reference = "Draft#{pk}" (auto dari backend)
2. Saat confirm → _effect_confirm():
   - SequenceEngine.next_by_id(sequence_id.pk)
   - Hasil: "PO-2026-00001" (format sesuai sequence record)
   - reference berubah dari "Draft#5" → "PO-2026-00001"

def _effect_confirm(self):
    from core.sequence_engine import SequenceEngine
    if (self.reference or '').startswith('Draft#'):
        self.reference = SequenceEngine.next_by_id(
            self.sequence_id.pk
        )`} />

      <Title level={3}>Default Sequence via get_model_config</Title>
      <Paragraph>
        Agar sequence_id otomatis terisi saat buat baru:
      </Paragraph>
      <CodeBlock code={`@classmethod
def get_model_config(cls):
    config = super().get_model_config()
    from core.models.settings.sequence import Sequence
    active_seq = Sequence.objects.filter(
        model_ref=cls._model_name, active=True, is_deleted=False
    ).first()
    if active_seq:
        config['fields']['sequence_id']['default'] = active_seq.pk
    return config`} />

      <Title level={3}>Sequence Engine</Title>
      <Paragraph>
        <Text code>SequenceEngine</Text> adalah class utility yang mengelola
        increment counter per sequence record. Method utama:
      </Paragraph>

      <Table
        dataSource={[
          { key: '1', method: 'SequenceEngine.next_by_id(id)', desc: 'Generate nomor berikutnya berdasarkan sequence ID. Handle concurrency dengan select_for_update().' },
          { key: '2', method: 'SequenceEngine.next_by_ref(ref)', desc: 'Generate berdasarkan reference string sequence' },
        ]}
        columns={[
          { title: 'Method', dataIndex: 'method', key: 'method', render: (v: string) => <Text code>{v}</Text> },
          { title: 'Deskripsi', dataIndex: 'desc', key: 'desc' },
        ]}
        pagination={false}
        size="small"
        bordered
        style={{ marginBottom: 16 }}
      />

      <TipBox title="editable_statuses=[] untuk reference">
        Field <Text code>reference</Text> harus diset{' '}
        <Text code>editable_statuses=[]</Text> agar tidak bisa diedit user.
        Nilai digenerate otomatis oleh backend.
      </TipBox>

      <TipBox title="Sequence records di settings">
        Sequence records bisa dibuat via menu Settings → Sequences.
        Atur prefix (PO, SO, INV), padding length, dan tahun.
      </TipBox>
    </div>
  );
}

// ── Main Page ──

export default function DocumentationPage() {
  const tocItems = [
    { key: 'model-definition', href: '#model-definition', title: '1. Model Definition' },
    { key: 'fields', href: '#fields', title: '2. Fields' },
    { key: 'state-machine', href: '#state-machine', title: '3. State Machine (_states)' },
    { key: 'transitions', href: '#transitions', title: '4. Transitions (_transitions)' },
    { key: 'document-flow', href: '#document-flow', title: '5. Document Flow (_document_flow)' },
    { key: 'list-view', href: '#list-view', title: '6. List View (_list_view)' },
    { key: 'form-view', href: '#form-view', title: '7. Form View (_form_view)' },
    { key: 'guards-effects', href: '#guards-effects', title: '8. Guards & Effects' },
    { key: 'legacy-actions', href: '#legacy-actions', title: '9. Legacy Actions' },
    { key: 'compute-methods', href: '#compute-methods', title: '10. Compute Methods' },
    { key: 'wizards', href: '#wizards', title: '11. Wizard Actions' },
    { key: 'sequence', href: '#sequence', title: '12. Sequence & Auto-numbering' },
  ];

  return (
    <div style={{ display: 'flex', gap: 24, padding: 16 }}>
      {/* Table of Contents — Sidebar */}
      <div style={{ width: 240, flexShrink: 0 }}>
        <Anchor
          affix
          offsetTop={80}
          items={tocItems}
          replace
        />
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, maxWidth: 900 }}>
        <Title level={2}>📘 Model Development Guide</Title>
        <Paragraph type="secondary" style={{ fontSize: 16 }}>
          Panduan untuk developer yang ingin membuat model ERP baru di Digilio v2.
          Setiap bagian menjelaskan atribut class, opsi yang tersedia,
          dan contoh kode dari model yang sudah ada.
        </Paragraph>

        <Section1ModelDefinition />
        <Section2Fields />
        <Section3StateMachine />
        <Section4Transitions />
        <Section5DocumentFlow />
        <Section6ListView />
        <Section7FormView />
        <Section8GuardsEffects />
        <Section9LegacyActions />
        <Section10ComputeMethods />
        <Section11Wizards />
        <Section12Sequence />
      </div>
    </div>
  );
}
