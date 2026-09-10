/**
 * Sumber tunggal struktur menu ERP (sidebar 1 = modul, sidebar 2 = detail).
 *
 * Dipakai oleh:
 *   - `components/MainLayout.tsx`  → render sidebar
 *   - `pages/base/HakAksesPage.tsx` → daftar menu yang bisa dichecklist per role
 *
 * Jangan duplikasi daftar menu di tempat lain — tambah menu di sini.
 */
import type { ReactNode } from 'react';
import {
  DashboardOutlined,
  AppstoreOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  SettingOutlined,
  BookOutlined,
  ProjectOutlined,
} from '@ant-design/icons';

export interface MenuNode {
  key?: string;
  label?: string;
  icon?: ReactNode;
  /** 'group' = header section di sidebar 2 (OPERATION / MASTER DATA / REPORT) */
  type?: string;
  popupClassName?: string;
  children?: MenuNode[];
}

export const menuItems: MenuNode[] = [
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
        { key: '/inventory/stock_balance', label: 'Stock Balance' },
        { key: '/inventory/stock_card', label: 'Stock Card' },
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
        { key: '/accounting.tax', label: 'Pajak' },
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
        { key: '/accounting/pajak', label: 'Report Pajak' },
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
      { key: '/settings/hak_akses', label: 'Hak Akses' },
    ],
  },
];

// Top-level items for sidebar 1 (icon-only when collapsed)
export const topLevelItems = menuItems.map(({ key, icon, label }) => ({ key, icon, label }));

export function getModuleKey(pathname: string): string {
  if (pathname === '/') return '/';
  if (pathname.startsWith('/purchase.') || pathname.startsWith('/purchase/')) return 'purchase';
  if (pathname.startsWith('/sales.') || pathname.startsWith('/sales/')) return 'sales';
  if (pathname.startsWith('/inventory.') || pathname.startsWith('/inventory/')) return 'inventory';
  if (pathname.startsWith('/project.') || pathname.startsWith('/project/')) return 'project';
  if (pathname.startsWith('/accounting.') || pathname.startsWith('/accounting/')) return 'accounting';
  if (pathname.startsWith('/settings.') || pathname.startsWith('/settings/')) return 'settings';
  return '/';
}

// Cari key submenu induk dari sebuah item menu (untuk highlight parent saat child aktif)
export function findParentKey(items: { key?: string; children?: MenuNode[] }[], targetKey: string): string | undefined {
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
export function findChildLabel(items: MenuNode[], parentKey: string, targetKey: string): string | undefined {
  for (const item of items) {
    if (item?.key === parentKey) {
      return item?.children?.find((c) => c?.key === targetKey)?.label;
    }
    if (item?.children?.length) {
      const nested = findChildLabel(item.children, parentKey, targetKey);
      if (nested) return nested;
    }
  }
  return undefined;
}

// ─────────────────────────────────────────────────────────────────────────────
// Struktur akses (dipakai halaman Hak Akses)
// ─────────────────────────────────────────────────────────────────────────────

export interface AccessMenuEntry {
  key: string;
  label: string;
}

export interface AccessSubgroup {
  key: string;
  label: string;
  menus: AccessMenuEntry[];
}

export interface AccessSection {
  /** `${moduleKey}:${label}` — dipakai sebagai key section yang dicentang */
  key: string;
  label: string;
  menus: AccessMenuEntry[];
  subgroups: AccessSubgroup[];
}

export interface AccessModule {
  /** key modul, mis. 'sales' atau '/' untuk Dashboard */
  key: string;
  label: string;
  sections: AccessSection[];
}

const toEntries = (items: MenuNode[] | undefined): AccessMenuEntry[] =>
  (items ?? [])
    .filter((i) => i?.key && i.type !== 'group')
    .map((i) => ({ key: i.key as string, label: i.label ?? (i.key as string) }));

/**
 * Bangun struktur tab-per-modul → section → menu dari `menuItems`.
 * Dipakai halaman Hak Akses agar checklist selalu sinkron dengan menu asli.
 */
export function buildAccessTree(): AccessModule[] {
  return menuItems.map((mod) => {
    const moduleKey = mod.key ?? '/';
    const children = mod.children ?? [];

    if (!children.length) {
      // Modul tanpa anak (mis. Dashboard) → satu section berisi dirinya sendiri
      return {
        key: moduleKey,
        label: mod.label ?? moduleKey,
        sections: [
          {
            key: `${moduleKey}:MENU`,
            label: 'MENU',
            menus: [{ key: moduleKey, label: mod.label ?? moduleKey }],
            subgroups: [],
          },
        ],
      };
    }

    const sections: AccessSection[] = [];
    const plainMenus: AccessMenuEntry[] = [];

    for (const child of children) {
      if (child.type === 'group') {
        const menus: AccessMenuEntry[] = [];
        const subgroups: AccessSubgroup[] = [];
        for (const entry of child.children ?? []) {
          if (entry.children?.length) {
            subgroups.push({
              key: entry.key ?? entry.label ?? '',
              label: entry.label ?? entry.key ?? '',
              menus: toEntries(entry.children),
            });
          } else if (entry.key) {
            menus.push({ key: entry.key, label: entry.label ?? entry.key });
          }
        }
        sections.push({
          key: `${moduleKey}:${child.label ?? 'SECTION'}`,
          label: child.label ?? 'SECTION',
          menus,
          subgroups,
        });
      } else if (child.key) {
        plainMenus.push({ key: child.key, label: child.label ?? child.key });
      }
    }

    if (plainMenus.length) {
      sections.unshift({
        key: `${moduleKey}:UMUM`,
        label: 'UMUM',
        menus: plainMenus,
        subgroups: [],
      });
    }

    return { key: moduleKey, label: mod.label ?? moduleKey, sections };
  });
}
