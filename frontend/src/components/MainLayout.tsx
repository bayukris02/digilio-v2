import { useState } from 'react';
import { Layout, Menu, Button } from 'antd';
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
  ProjectOutlined,
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
        { key: '/purchase.product', label: 'Product' },
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
      { key: '/sales/dashboard', label: 'Dashboard' },
      { key: '/sales/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/sales.order', label: 'Sales Order' },
        { key: '/sales.delivery_order', label: 'Delivery Order' },
        { key: '/sales.quick_sales', label: 'Quick Sales' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/sales.customer', label: 'Customer' },
        { key: '/sales.product', label: 'Product' },
        { key: '/sales.pricelist', label: 'Pricelist' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/sales/pivot', label: 'Sales Pivot' },
        { key: '/sales/detail', label: 'Sales Detail' },
      ]},
    ],
  },
  {
    key: 'inventory',
    icon: <AppstoreOutlined />,
    label: 'Inventory',
    children: [
      { key: '/inventory/dashboard', label: 'Dashboard' },
      { key: '/inventory/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/inventory.stock_receipt', label: 'Stock Receipt' },
        { key: '/inventory.stock_delivery', label: 'Stock Delivery' },
        { key: '/inventory.stock_adjustment', label: 'Stock Adjustment' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/inventory.product', label: 'Product' },
        { key: '/inventory.product_category', label: 'Product Category' },
        { key: '/inventory.warehouse', label: 'Warehouse' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/inventory/pivot', label: 'Inventory Pivot' },
        { key: '/inventory/detail', label: 'Inventory Detail' },
      ]},
    ],
  },
  {
    key: 'project',
    icon: <ProjectOutlined />,
    label: 'Project',
    children: [
      { key: '/project/dashboard', label: 'Dashboard' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/project/progress', label: 'Project Update' },
        { key: '/project/wbs', label: 'WBS & Task Assignment' },
        { key: '/project/budgeting', label: 'Project Budgeting (RAB)' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/project.project', label: 'Project' },
        { key: '/project.project_category', label: 'Project Categories' },
        { key: '/project.unit', label: 'Units' },
        { key: '/project.dokumen', label: 'Dokumen' },
        { key: '/project.milestone', label: 'Milestone' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/project/pivot', label: 'Project Progress Pivot' },
        { key: '/project/pnl', label: 'Project P&L Detail' },
        { key: '/project/cashflow', label: 'Cash Flow Report' },
      ]},
    ],
  },
  {
    key: 'accounting',
    icon: <BookOutlined />,
    label: 'Accounting',
    children: [
      { key: '/accounting/dashboard', label: 'Dashboard' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/accounting.vendor_bill', label: 'Tagihan' },
        { key: '/accounting.customer_invoice', label: 'Faktur' },
        { key: '/accounting.expense', label: 'Input Biaya' },
        { key: '/accounting.vendor_payment', label: 'Pembayaran' },
        { key: '/accounting.customer_receipt', label: 'Penerimaan' },
        { key: '/accounting.jurnal', label: 'Jurnal' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/accounting.chart_of_account', label: 'COA' },
        { key: '/accounting.payment_method', label: 'Payment Method' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/accounting/laba_rugi', label: 'Laba Rugi' },
        { key: '/accounting/neraca', label: 'Neraca' },
        { key: '/accounting/cashflow', label: 'Cashflow' },
      ]},
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
  if (pathname.startsWith('/sales.') || pathname.startsWith('/sales/')) return 'sales';
  if (pathname.startsWith('/inventory.') || pathname.startsWith('/inventory/')) return 'inventory';
  if (pathname.startsWith('/project.') || pathname.startsWith('/project/')) return 'project';
  if (pathname.startsWith('/accounting.') || pathname.startsWith('/accounting/')) return 'accounting';
  if (pathname.startsWith('/settings.')) return 'settings';
  return '/';
}

export default function MainLayout() {
  const [sidebar1Collapsed, setSidebar1Collapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const currentModule = getModuleKey(location.pathname);
  const selectedItem = menuItems.find((m) => m.key === currentModule);
  const subItems = selectedItem?.children || [];
  const selectedModuleLabel = selectedItem?.label;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout style={{ height: '100vh' }}>
      {/* Custom CSS for sidebar styling */}
      <style>{`
        /* ── Sidebar 2: detail menu ── */
        .sidebar2-menu .ant-menu-item {
          height: 30px !important;
          line-height: 30px !important;
          margin: 0 !important;
          padding: 0 16px !important;
          width: 100% !important;
          border-radius: 0 !important;
          font-size: 10px !important;
        }
        .sidebar2-menu .ant-menu-item:hover {
          background: rgba(255,255,255,0.06) !important;
        }
        .sidebar2-menu .ant-menu-item-selected {
          background: rgba(24,144,255,0.12) !important;
        }
        .sidebar2-menu .ant-menu-item-selected::after {
          content: '';
          position: absolute;
          left: 0;
          top: 3px;
          bottom: 3px;
          width: 3px;
          background: #1677ff;
          border-radius: 0 2px 2px 0;
        }
        .sidebar2-menu .ant-menu-title-content {
          white-space: normal !important;
          word-break: break-word !important;
          line-height: 1.35 !important;
        }
        .sidebar2-menu .ant-menu-item-group-title {
          font-size: 9px !important;
          color: rgba(255,255,255,0.25) !important;
          letter-spacing: 0.6px !important;
          text-transform: uppercase !important;
          padding: 8px 16px 2px !important;
          margin-top: 4px !important;
          border-top: 1px solid rgba(255,255,255,0.06) !important;
          line-height: 1.2 !important;
        }
        .sidebar2-menu .ant-menu-item-group:first-of-type .ant-menu-item-group-title {
          border-top: none !important;
          margin-top: 0 !important;
        }
        .sidebar2-menu .ant-menu-item-group:first-of-type {
          margin-top: 4px;
        }

        /* ── Scrollbar minimalis ── */
        .sidebar-scroll::-webkit-scrollbar {
          width: 3px;
        }
        .sidebar-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
        .sidebar-scroll::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.08);
          border-radius: 3px;
        }
        .sidebar-scroll::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.18);
        }
      `}</style>

      {/* Sidebar 1: Main module icons — default collapsed */}
      <Sider
        collapsible
        collapsed={sidebar1Collapsed}
        onCollapse={setSidebar1Collapsed}
        collapsedWidth={56}
        width={180}
        theme="dark"
        className="sidebar-scroll"
        style={{ overflow: 'auto', height: '100vh' }}
      >
        <div
          style={{
            height: 48,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            fontSize: sidebar1Collapsed ? 14 : 18,
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          {sidebar1Collapsed ? 'D' : 'Digilio'}
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
              // Navigate to first child of selected module (skip group headers)
              const module = menuItems.find((m) => m.key === key);
              const firstChild = module?.children?.find((c) => c && (c as { key?: string }).key);
              if (firstChild) {
                navigate((firstChild as { key: string }).key);
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
          className="sidebar-scroll"
          style={{
            overflow: 'auto',
            height: '100vh',
            borderLeft: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              height: 48,
              display: 'flex',
              alignItems: 'center',
              padding: '0 16px',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
              color: 'rgba(255,255,255,0.55)',
              fontWeight: 600,
              fontSize: 11,
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
            }}
          >
            {selectedModuleLabel}
          </div>
          <Menu
            className="sidebar2-menu"
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={subItems}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
      )}

      {/* Main content area */}
      <Layout style={{ height: '100vh' }}>
        <Header
          style={{
            height: 48,
            lineHeight: '48px',
            padding: '0 16px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
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
        <Content style={{ margin: 12, overflow: 'auto', height: 'calc(100vh - 48px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
