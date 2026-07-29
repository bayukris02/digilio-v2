import { useState } from 'react';
import { Layout, Menu, Button, theme } from 'antd';
import {
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  FormOutlined,
  AppstoreOutlined,
  ShoppingCartOutlined,
  ImportOutlined,
  DollarOutlined,
  TeamOutlined,
  SettingOutlined,
  NumberOutlined,
  BankOutlined,
  ApartmentOutlined,
  BookOutlined,
  CarOutlined,
  TagOutlined,
  FileTextOutlined,
  PieChartOutlined,
  UnorderedListOutlined,
  FileAddOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  {
    key: 'purchase',
    icon: <ShoppingCartOutlined />,
    label: 'Purchase',
    children: [
      { key: '/purchase/dashboard', label: 'Dashboard' },
      { key: '/purchase/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/purchase.request', label: 'Purchase Request' },
        { key: '/purchase.order', label: 'Purchase Order' },
        { key: '/purchase.goods_receipt', label: 'Goods Receipt' },
        { key: '/purchase.quick_purchase', label: 'Quick Purchase' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/purchase.vendor', label: 'Vendor' },
        { key: '/inventory.product', label: 'Product' },
        { key: '/purchase.order_template', label: 'Order Template' },
        { key: '/purchase.vendor_pricelist', label: 'Vendor Pricelist' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/purchase/pivot', label: 'Purchase Pivot' },
        { key: '/purchase/detail', label: 'Purchase Detail' },
      ]},
    ],
  },
  {
    key: 'sales',
    icon: <DollarOutlined />,
    label: 'Sales',
    children: [
      { key: '/sales.order', label: 'Sales Order' },
      { key: '/sales.delivery_order', label: 'Delivery Order' },
      { key: '/sales.customer', label: 'Customers' },
    ],
  },
  {
    key: 'inventory',
    icon: <AppstoreOutlined />,
    label: 'Inventory',
    children: [
      { key: '/inventory.product', label: 'Products' },
      { key: '/inventory.product_category', label: 'Categories' },
      { key: '/inventory.warehouse', label: 'Warehouses' },
    ],
  },
  {
    key: 'accounting',
    icon: <BookOutlined />,
    label: 'Accounting',
    children: [
      { key: '/accounting.jurnal', label: 'Jurnal' },
      { key: '/accounting.chart_of_account', label: 'Chart of Account' },
      { key: '/accounting.vendor_bill', label: 'Tagihan' },
      { key: '/accounting.vendor_payment', label: 'Pembayaran' },
      { key: '/accounting.customer_invoice', label: 'Faktur' },
      { key: '/accounting.customer_receipt', label: 'Penerimaan' },
      { key: '/accounting.payment_method', label: 'Payment Methods' },
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Settings',
    children: [
      { key: '/settings.sequence', label: 'Sequences' },
      { key: '/settings.company', label: 'Companies' },
      { key: '/settings.branch', label: 'Branches' },
      { key: '/settings.user', label: 'Users' },
    ],
  },
];

// Top-level items for sidebar 1 (icon-only when collapsed)
const topLevelItems = menuItems.map(({ key, icon, label }) => ({ key, icon, label }));

function getModuleKey(pathname: string): string {
  if (pathname === '/') return '/';
  if (pathname.startsWith('/purchase.') || pathname.startsWith('/purchase/')) return 'purchase';
  if (pathname.startsWith('/sales.')) return 'sales';
  if (pathname.startsWith('/inventory.')) return 'inventory';
  if (pathname.startsWith('/accounting.')) return 'accounting';
  if (pathname.startsWith('/settings.')) return 'settings';
  return '/';
}

export default function MainLayout() {
  const [sidebar1Collapsed, setSidebar1Collapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { token } = theme.useToken();

  const currentModule = getModuleKey(location.pathname);
  const selectedItem = menuItems.find((m) => m.key === currentModule);
  const subItems = selectedItem?.children || [];
  const selectedModuleLabel = selectedItem?.label;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout style={{ height: '100vh' }}>
      {/* Sidebar 1: Main module icons — default collapsed */}
      <Sider
        collapsible
        collapsed={sidebar1Collapsed}
        onCollapse={setSidebar1Collapsed}
        collapsedWidth={56}
        width={180}
        theme="dark"
        style={{ overflow: 'auto', height: '100vh' }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: sidebar1Collapsed ? 16 : 20,
          }}
        >
          {sidebar1Collapsed ? 'DE' : 'Digilio ERP'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentModule]}
          inlineCollapsed={sidebar1Collapsed}
          items={topLevelItems}
          onClick={({ key }) => {
            if (key === '/') {
              navigate('/');
            } else {
              // Navigate to first child of selected module
              const module = menuItems.find((m) => m.key === key);
              if (module?.children?.[0]) {
                navigate(module.children[0].key);
              }
            }
          }}
        />
      </Sider>

      {/* Sidebar 2: Submenu items for selected module */}
      {subItems.length > 0 && (
        <Sider
          width={160}
          theme="dark"
          style={{
            overflow: 'auto',
            height: '100vh',
            borderLeft: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              paddingLeft: 20,
              color: 'rgba(255,255,255,0.45)',
              fontWeight: 600,
              fontSize: 12,
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
            }}
          >
            {selectedModuleLabel}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={subItems.map(item => ({
              ...item,
              label: <span style={{ whiteSpace: 'normal', lineHeight: 1.4, wordBreak: 'break-word' }}>{item.label}</span>,
            }))}
            style={{ fontSize: 12 }}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
      )}

      {/* Main content area */}
      <Layout style={{ height: '100vh' }}>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Button
            type="text"
            icon={sidebar1Collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setSidebar1Collapsed(!sidebar1Collapsed)}
          />
          <Button type="text" icon={<LogoutOutlined />} onClick={logout}>
            Logout
          </Button>
        </Header>
        <Content style={{ margin: 12, overflow: 'auto', height: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
