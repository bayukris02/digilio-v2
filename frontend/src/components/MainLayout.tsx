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
    label: 'Pembelian',
    children: [
      { key: '/purchase/dashboard', label: 'Dashboard' },
      { key: '/purchase/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/purchase.request', label: 'Permintaan Pembelian' },
        { key: '/purchase.order', label: 'Purchase Order' },
        { key: '/purchase.goods_receipt', label: 'Penerimaan Barang' },
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
    label: 'Penjualan',
    children: [
      { key: '/sales/dashboard', label: 'Dashboard' },
      { key: '/sales/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/sales.order', label: 'Penjualan' },
        { key: '/sales.delivery_order', label: 'Pengiriman Barang' },
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
    label: 'Stock',
    children: [
      { key: '/inventory/dashboard', label: 'Dashboard' },
      { key: '/inventory/insight', label: 'Insight' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/inventory.stock_receipt', label: 'Penerimaan Barang' },
        { key: '/inventory.stock_delivery', label: 'Pengiriman Barang' },
        { key: '/inventory.stock_adjustment', label: 'Stock Adjustment' },
      ]},
      { type: 'group', label: 'TRANSFER STOCK', children: [
        { key: '/inventory.stock_request', label: 'Request Stock' },
        { key: '/inventory.stock_out', label: 'Stock Keluar' },
        { key: '/inventory.stock_in', label: 'Terima Stock' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/inventory.product', label: 'Produk' },
        { key: '/inventory.product_category', label: 'Kategori Produk' },
        { key: '/inventory.uom', label: 'Satuan' },
        { key: '/inventory.warehouse', label: 'Warehouse' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/inventory.stock_ledger', label: 'Stock Ledger' },
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
        { key: '/project/progress', label: 'Update Proyek' },
        { key: '/project.project_unit_detail', label: 'Update Unit' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/project.project', label: 'Project' },
        { key: '/project.project_category', label: 'Project Kategori' },
        { key: '/project.unit', label: 'Unit' },
        { key: '/project.dokumen', label: 'Dokumen' },
        { key: '/project.milestone', label: 'Milestone' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        { key: '/project/pivot', label: 'Pivot Progress Proyek' },
        { key: '/project/pnl', label: 'Detail Laba Rugi Proyek' },
        { key: '/project/cashflow', label: 'Laporan Arus Kas' },
      ]},
    ],
  },
  {
    key: 'accounting',
    icon: <BookOutlined />,
    label: 'Akunting',
    children: [
      { key: '/accounting/dashboard', label: 'Dashboard' },
      { type: 'group', label: 'OPERATION', children: [
        { key: '/accounting.vendor_bill', label: 'Tagihan' },
        { key: '/accounting.customer_invoice', label: 'Faktur' },
        { key: '/accounting.expense', label: 'Input Biaya' },
      ]},
      { type: 'group', label: 'KAS/BANK', children: [
        { key: '/accounting.vendor_payment', label: 'Pembayaran' },
        { key: '/accounting.customer_receipt', label: 'Penerimaan' },
        { key: '/accounting.transfer_cash_bank', label: 'Transfer Kas/Bank' },
        { key: '/accounting.deposit', label: 'Deposit' },
      ]},
      { type: 'group', label: 'MASTER DATA', children: [
        { key: '/accounting.chart_of_account', label: 'COA' },
        { key: '/accounting.payment_method', label: 'Kas dan Bank' },
        { key: '/accounting/asset', label: 'Asset' },
        { key: '/accounting/cost_center', label: 'Cost Center' },
      ]},
      { type: 'group', label: 'REPORT', children: [
        {
          key: 'accounting.laporan_keuangan',
          label: 'Laporan Keuangan',
          popupClassName: 'sidebar2-menu',
          children: [
            { key: '/accounting/laba_rugi', label: 'Laba Rugi' },
            { key: '/accounting/neraca', label: 'Neraca' },
            { key: '/accounting/neraca_saldo', label: 'Neraca Saldo' },
            { key: '/accounting/buku_besar', label: 'Buku Besar' },
            { key: '/accounting/cashflow', label: 'Cashflow' },
            { key: '/accounting/catatan_laporan', label: 'Catatan atas Laporan Keuangan' },
            { key: '/accounting/perubahan_modal', label: 'Perubahan Modal' },
          ],
        },
      ]},
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: 'Pengaturan',
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

// Cari key submenu induk dari sebuah item menu (untuk highlight parent saat child aktif)
function findParentKey(items: { key?: string; children?: any[] }[], targetKey: string): string | undefined {
  for (const item of items) {
    if (item?.children?.length) {
      if (item.children.some((c) => c?.key === targetKey)) return item.key;
      const nested = findParentKey(item.children, targetKey);
      if (nested) return nested;
    }
  }
  return undefined;
}

// Cari label child aktif di dalam sebuah submenu (untuk ditampilkan di bawah label submenu)
function findChildLabel(items: any[], parentKey: string, targetKey: string): string | undefined {
  for (const item of items) {
    if (item?.key === parentKey) {
      return item?.children?.find((c: any) => c?.key === targetKey)?.label;
    }
    if (item?.children?.length) {
      const nested = findChildLabel(item.children, parentKey, targetKey);
      if (nested) return nested;
    }
  }
  return undefined;
}

export default function MainLayout() {
  const [sidebar1Collapsed, setSidebar1Collapsed] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const currentModule = getModuleKey(location.pathname);
  const selectedItem = menuItems.find((m) => m.key === currentModule);
  const subItems: any[] = selectedItem?.children || [];
  const selectedModuleLabel = selectedItem?.label;
  // Highlight parent submenu (mis. "Laporan Keuangan") saat salah satu child-nya aktif;
  // child di dalam popup sengaja TIDAK di-select supaya popup terbuka bersih (belum ada yang aktif)
  const parentKey = findParentKey(subItems, location.pathname);
  const activeChildLabel = parentKey ? findChildLabel(subItems, parentKey, location.pathname) : undefined;
  const selectedKeys = parentKey ? [parentKey] : [location.pathname];
  // Label submenu diberi baris child aktif di bawahnya (mis. "Laporan Keuangan" + "• Cashflow");
  // transform rekursif supaya submenu di dalam grup (REPORT) ikut diproses
  const decorateSubmenu = (items: any[]): any[] =>
    items.map((item: any) => {
      if (item?.type === 'group' && item?.children?.length) {
        return { ...item, children: decorateSubmenu(item.children) };
      }
      if (item?.children?.length) {
        return {
          ...item,
          label: (
            <div>
              <div>{item.label}</div>
              {item.key === parentKey && activeChildLabel && (
                <div className="sidebar2-submenu-child">
                  <span className="sidebar2-submenu-child-dot">•</span>
                  {activeChildLabel}
                </div>
              )}
            </div>
          ),
        };
      }
      return item;
    });
  const displayItems = decorateSubmenu(subItems);

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

        /* ── Submenu (mis. "Laporan Keuangan") — tampil seperti item biasa + panah kanan ── */
        .sidebar2-menu .ant-menu-submenu-title {
          height: auto !important;
          min-height: 30px;
          line-height: 1.35 !important;
          padding: 4px 30px 4px 16px !important;
          margin: 0 !important;
          font-size: 10px !important;
          border-radius: 0 !important;
          width: 100% !important;
          white-space: normal !important;
        }
        .sidebar2-menu .ant-menu-submenu-title:hover {
          background: rgba(255,255,255,0.06) !important;
        }
        .sidebar2-menu .ant-menu-submenu-selected > .ant-menu-submenu-title {
          background: rgba(24,144,255,0.12) !important;
        }
        .sidebar2-menu .ant-menu-submenu-selected > .ant-menu-submenu-title::after {
          content: '';
          position: absolute;
          left: 0;
          top: 3px;
          bottom: 3px;
          width: 3px;
          background: #1677ff;
          border-radius: 0 2px 2px 0;
        }
        .sidebar2-menu .ant-menu-submenu-arrow {
          top: 50% !important;
          transform: translateY(-50%) !important;
        }
        /* Baris child aktif di bawah label submenu (mis. "• Cashflow") */
        .sidebar2-submenu-child {
          font-size: 9px;
          color: rgba(255,255,255,0.45);
          line-height: 1.3;
          margin-top: 1px;
          padding-left: 14px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .sidebar2-submenu-child .sidebar2-submenu-child-dot {
          color: #1677ff;
          margin-right: 4px;
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
            mode="vertical"
            selectedKeys={selectedKeys}
            items={displayItems}
            triggerSubMenuAction="click"
            subMenuCloseDelay={2}
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
