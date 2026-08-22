import { useState } from 'react';
import {
  Breadcrumb,
  Steps,
  Button,
  Card,
  Row,
  Col,
  Form,
  Input,
  Select,
  DatePicker,
  Switch,
  InputNumber,
  Table,
  Tabs,
  Space,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  SaveOutlined,
  CloseOutlined,
  PlusOutlined,
  DeleteOutlined,
  ShoppingCartOutlined,
  FileTextOutlined,
  InboxOutlined,
  MailOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import Chatter from '../../components/Chatter';

const { TextArea } = Input;
const { Title } = Typography;

// ─── Options ───────────────────────────────
const productCategories = [
  { value: 'raw', label: 'Raw Material' },
  { value: 'finished', label: 'Finished Good' },
  { value: 'service', label: 'Service' },
  { value: 'asset', label: 'Asset' },
];

const suppliers = [
  { value: 'sup-1', label: 'PT. Sumber Berkah' },
  { value: 'sup-2', label: 'CV. Maju Jaya' },
  { value: 'sup-3', label: 'UD. Sentosa Abadi' },
];

// ─── Stepper steps ─────────────────────────
const stepperSteps = [
  { title: 'Draft' },
  { title: 'Confirmed' },
  { title: 'Done' },
  { title: 'Cancelled' },
];

// ─── Line item type ────────────────────────
interface LineItem {
  key: string;
  product: string;
  name: string;
  qty: number;
  uom: string;
  price: number;
  total: number;
}

// ─── Smart Button Component ────────────────
interface SmartBtnProps {
  icon: React.ReactNode;
  count: number | string;
  label: string;
  color: string;
  onClick?: () => void;
}

function SmartButton({ icon, count, label, color, onClick }: SmartBtnProps) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        background: hovered ? color : '#fff',
        border: `1px solid ${color}`,
        borderRadius: 5,
        padding: '3px 8px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
        minWidth: 78,
        userSelect: 'none',
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 4,
          background: hovered ? 'rgba(255,255,255,0.2)' : color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: hovered ? '#fff' : '#fff',
          fontSize: 14,
          flexShrink: 0,
          transition: 'background 0.15s',
        }}
      >
        {icon}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: hovered ? '#fff' : '#222',
            transition: 'color 0.15s',
          }}
        >
          {count}
        </span>
        <span
          style={{
            fontSize: 9,
            color: hovered ? 'rgba(255,255,255,0.85)' : '#888',
            transition: 'color 0.15s',
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
}

// ─── Columns ───────────────────────────────
const itemColumns = (onDelete: (key: string) => void) => [
  { title: 'Product', dataIndex: 'product', key: 'product', width: 100 },
  { title: 'Name', dataIndex: 'name', key: 'name', width: 160 },
  {
    title: 'Qty',
    dataIndex: 'qty',
    key: 'qty',
    width: 60,
    align: 'right' as const,
  },
  { title: 'UOM', dataIndex: 'uom', key: 'uom', width: 60 },
  {
    title: 'Price',
    dataIndex: 'price',
    key: 'price',
    width: 100,
    align: 'right' as const,
    render: (v: number) => v.toLocaleString('id-ID'),
  },
  {
    title: 'Total',
    dataIndex: 'total',
    key: 'total',
    width: 120,
    align: 'right' as const,
    render: (v: number) => v.toLocaleString('id-ID'),
  },
  {
    title: '',
    key: 'action',
    width: 40,
    render: (_: unknown, record: LineItem) => (
      <Button
        type="text"
        danger
        icon={<DeleteOutlined />}
        onClick={() => onDelete(record.key)}
      />
    ),
  },
];

export default function FormPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('items');
  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const isNew = true; // TODO: ganti false kalo data PO udah ada

  // ── Line item CRUD ──
  const addLine = () => {
    const newKey = String(Date.now());
    const newItem: LineItem = {
      key: newKey,
      product: '',
      name: '',
      qty: 1,
      uom: 'pcs',
      price: 0,
      total: 0,
    };
    setLineItems((prev) => [...prev, newItem]);
  };

  const deleteLine = (key: string) => {
    setLineItems((prev) => prev.filter((item) => item.key !== key));
  };

  const grandTotal = lineItems.reduce((sum, item) => sum + item.total, 0);

  // ── Tab content ──
  const tabItems = [
    {
      key: 'items',
      label: 'Items',
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            onClick={addLine}
            style={{ width: 120 }}
          >
            Add Line
          </Button>
          <Table
            columns={itemColumns(deleteLine)}
            dataSource={lineItems}
            pagination={false}
            bordered
            scroll={{ x: 'max-content' }}
            locale={{
              emptyText:
                'No lines yet. Click "Add Line" to add items.',
            }}
            summary={() =>
              lineItems.length > 0 ? (
                <Table.Summary fixed>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={4}>
                      <strong>Grand Total</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={4}>
                      <strong>
                        Rp {grandTotal.toLocaleString('id-ID')}
                      </strong>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              ) : null
            }
          />
        </div>
      ),
    },
    {
      key: 'details',
      label: 'Detail',
      children: (
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Delivery Date">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Warehouse">
                <Select
                  options={[
                    { value: 'wh-1', label: 'Warehouse A' },
                    { value: 'wh-2', label: 'Warehouse B' },
                    { value: 'wh-3', label: 'Warehouse C' },
                  ]}
                  placeholder="Select warehouse"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Incoterm">
                <Select
                  options={[
                    { value: 'fob', label: 'FOB' },
                    { value: 'cif', label: 'CIF' },
                    { value: 'exw', label: 'EXW' },
                  ]}
                  placeholder="Select incoterm"
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="Payment Term">
                <Select
                  options={[
                    { value: '30', label: 'Net 30' },
                    { value: '60', label: 'Net 60' },
                    { value: 'cod', label: 'COD' },
                  ]}
                  placeholder="Select term"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Currency">
                <Select
                  options={[
                    { value: 'idr', label: 'IDR - Rupiah' },
                    { value: 'usd', label: 'USD - Dollar' },
                  ]}
                  placeholder="Select currency"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Notes">
                <TextArea rows={1} placeholder="Additional notes..." />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* ═══ HEADER ═══ */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        {/* Row 1: Breadcrumb | Stepper */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Breadcrumb
            items={[
              {
                title: (
                  <a
                    href="/purchase/order"
                    style={{ fontSize: 11 }}
                    onClick={(e) => {
                      e.preventDefault();
                      // TODO: navigate ke list PO
                    }}
                  >
                    Purchase Order
                  </a>
                ),
              },
              {
                title: (
                  <span style={{ fontSize: 11, fontWeight: 500 }}>
                    {isNew ? 'Buat Purchase Order' : 'PO-2024-0001'}
                  </span>
                ),
              },
            ]}
            style={{ fontSize: 11 }}
          />
          <div style={{ flex: 1, maxWidth: 480 }}>
            <Steps
              current={currentStep}
              items={stepperSteps}
              size="small"
            />
          </div>
        </div>

        {/* Row 2: Title | ◀ ▶ */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Title level={4} style={{ margin: 0, lineHeight: 1.4 }}>
            Purchase Order - PO-2024-0001
          </Title>
          <Space size={2}>
            <Button
              variant="outlined"
              color="primary"
              icon={<ArrowLeftOutlined />}
              title="Previous record"
            />
            <span
              style={{
                fontSize: 11,
                color: '#666',
                padding: '0 4px',
                userSelect: 'none',
              }}
            >
              {1}/{5}
            </span>
            <Button
              variant="outlined"
              color="primary"
              icon={<ArrowRightOutlined />}
              title="Next record"
            />
          </Space>
        </div>

        {/* Row 3: All buttons sejajar (sticky on scroll) */}
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            background: '#f0f2f5',
            padding: '8px 0 0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Space size={4}>
            <Button
              variant="solid"
              color="green"
              icon={<FileTextOutlined />}
            >
              Print
            </Button>
            <Button
              variant="solid"
              color="primary"
              icon={<MailOutlined />}
            >
              Email
            </Button>
            <Button
              variant="solid"
              color="primary"
              icon={<MoreOutlined />}
            >
              Action
            </Button>
          </Space>
          <Space size={6}>
            <Button icon={<SaveOutlined />} type="primary">
              Simpan
            </Button>
            <Button
              variant="solid"
              color="danger"
              icon={<CloseOutlined />}
            >
              Batal
            </Button>
          </Space>
        </div>
      </div>
      {/* /sticky header */}

      {/* ═══ FORM CARD — Odoo Style ═══ */}
      <Card
        styles={{
          header: {
            borderBottom: '1px solid #e8e8e8',
            padding: '8px 12px',
            minHeight: 44,
          },
          body: { padding: 16 },
        }}
        title={
          <Space size={6}>
            <InboxOutlined style={{ fontSize: 13, color: '#666' }} />
            <span>Purchase Order Details</span>
          </Space>
        }
        extra={
          <Space size={6}>
            <SmartButton
              icon={<ShoppingCartOutlined />}
              count={2}
              label="Receipt"
              color="#17a2b8"
            />
            <SmartButton
              icon={<FileTextOutlined />}
              count={1}
              label="Bill"
              color="#6f42c1"
            />
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="Order Reference"
                name="reference"
                rules={[{ required: true }]}
              >
                <Input placeholder="PO-2024-0001" />
              </Form.Item>
              <Form.Item
                label="Supplier"
                name="supplier"
                rules={[{ required: true }]}
              >
                <Select
                  showSearch
                  placeholder="Search supplier..."
                  options={suppliers}
                  filterOption={(input, option) =>
                    (option?.label ?? '')
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item label="Order Date" name="orderDate">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>

            <Col span={8}>
              <Form.Item label="Category" name="category">
                <Select
                  showSearch
                  placeholder="Select category..."
                  options={productCategories}
                />
              </Form.Item>
              <Form.Item label="Description" name="description">
                <TextArea rows={3} placeholder="Enter description..." />
              </Form.Item>
            </Col>

            <Col span={8}>
              <Form.Item
                label="Active"
                name="active"
                valuePropName="checked"
              >
                <Space>
                  <Switch defaultChecked />
                  <span style={{ fontSize: 11, color: '#888' }}>
                    Yes
                  </span>
                </Space>
              </Form.Item>
              <Form.Item label="Expected Qty" name="expectedQty">
                <InputNumber
                  min={0}
                  style={{ width: '100%' }}
                  placeholder="0"
                  formatter={(value) =>
                    `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                  }
                />
              </Form.Item>
              <Form.Item label="Priority" name="priority">
                <Select
                  options={[
                    {
                      value: 'low',
                      label: <Tag color="green">Low</Tag>,
                    },
                    {
                      value: 'medium',
                      label: <Tag color="orange">Medium</Tag>,
                    },
                    {
                      value: 'high',
                      label: <Tag color="red">High</Tag>,
                    },
                  ]}
                  placeholder="Select priority"
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* ═══ NOTEBOOK CARD ═══ */}
      <Card
        styles={{
          header: {
            borderBottom: '1px solid #e8e8e8',
            padding: '8px 12px',
          },
          body: { padding: 16 },
        }}
        title={<span>Order Lines</span>}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* ═══ CHATTER ═══ */}
      <Chatter title="Activity Log" />
    </div>
  );
}
