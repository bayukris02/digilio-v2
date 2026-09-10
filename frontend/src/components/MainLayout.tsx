import { useState } from 'react';
import { Layout, Menu, Button } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined, LogoutOutlined } from '@ant-design/icons';
import { Outlet, useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';
import { menuItems, topLevelItems, getModuleKey, findParentKey, findChildLabel } from '../config/menu';

const { Header, Sider, Content } = Layout;

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
