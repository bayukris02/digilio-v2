import { useState, useEffect } from 'react';
import { Layout, Menu, Button, theme } from 'antd';
import {
  DashboardOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  FormOutlined,
  UnorderedListOutlined,
  PieChartOutlined,
  TableOutlined,
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
      { key: '/purchase.order', icon: <FormOutlined />, label: 'Purchase Order' },
      { key: '/purchase.goods_receipt', icon: <ImportOutlined />, label: 'Goods Receipt' },
      { key: '/purchase.vendor', icon: <TeamOutlined />, label: 'Vendor' },
    ],
  },
  {
    key: 'sales',
    icon: <DollarOutlined />,
    label: 'Sales',
    children: [
      { key: '/sales.order', icon: <FormOutlined />, label: 'Sales Order' },
      { key: '/sales.delivery_order', icon: <CarOutlined />, label: 'Delivery Order' },
      { key: '/sales.customer', icon: <TeamOutlined />, label: 'Customers' },
    ],
  },
  {
    key: 'inventory',
    icon: <AppstoreOutlined />,
    label: 'Inventory',
    children: [
      { key: '/inventory.product', icon: <FormOutlined />, label: 'Products' },
      { key: '/inventory.product_category', icon: <TagOutlined />, label: 'Categories' },
      { key: '/inventory.warehouse', icon: <BankOutlined />, label: 'Warehouses' },
    ],
  },
  {
    key: 'accounting',
    icon: <BookOutlined />,
    label: 'Accounting',
    children: [
      { key: '/accounting.jurnal', icon: <FormOutlined />, label: 'Jurnal' },
      { key: '/accounting.chart_of_account', icon: <BankOutlined />, label: 'Chart of Account' },
      { key: '/accounting.vendor_bill', icon: <FormOutlined />, label: 'Tagihan' },
      { key: '/accounting.customer_invoice', icon: <FileTextOutlined />, label: 'Faktur' },
      { key: '/accounting.payment_method', icon: <DollarOutlined />, label: 'Payment Methods' },
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Settings',
    children: [
      { key: '/settings.sequence', icon: <NumberOutlined />, label: 'Sequences' },
      { key: '/settings.company', icon: <BankOutlined />, label: 'Companies' },
      { key: '/settings.branch', icon: <ApartmentOutlined />, label: 'Branches' },
      { key: '/settings.user', icon: <TeamOutlined />, label: 'Users' },
    ],
  },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { token } = theme.useToken();

  // Auto-open parent submenu based on current path
  const parentKey = location.pathname === '/' ? '' : location.pathname.startsWith('/docs') || location.pathname.startsWith('/form') || location.pathname.startsWith('/list') || location.pathname.startsWith('/report') ? 'base' : location.pathname.startsWith('/purchase.') ? 'purchase' : location.pathname.startsWith('/sales.') ? 'sales' : location.pathname.startsWith('/inventory.') ? 'inventory' : location.pathname.startsWith('/accounting.') ? 'accounting' : location.pathname.startsWith('/settings.') ? 'settings' : 'base';
  const [openKeys, setOpenKeys] = useState<string[]>(parentKey ? [parentKey] : []);

  // Sync openKeys when path changes
  useEffect(() => {
    setOpenKeys(parentKey ? [parentKey] : []);
  }, [location.pathname]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        theme="dark"
        style={{ overflow: 'auto', position: 'sticky', top: 0, height: '100vh' }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: collapsed ? 16 : 20,
          }}
        >
          {collapsed ? 'DE' : 'Digilio ERP'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          openKeys={openKeys}
          onOpenChange={setOpenKeys}
          items={menuItems}
          onClick={({ key }) => {
            // Only navigate for leaf menu items (not submenu groups)
            if (key !== 'base' && key !== 'purchase' && key !== 'sales' && key !== 'inventory' && key !== 'settings' && key !== 'accounting') navigate(key);
          }}
        />
      </Sider>
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
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
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
