import { createBrowserRouter, Navigate } from 'react-router-dom';
import MainLayout from '../components/MainLayout';
import DashboardPage from '../pages/Dashboard';
import DocumentationPage from '../pages/docs/DocumentationPage';
import FormPage from '../pages/base/FormPage';
import ListPage from '../pages/base/ListPage';
import ReportPivotPage from '../pages/base/ReportPivotPage';
import ReportTablePage from '../pages/base/ReportTablePage';
import LoginPage from '../pages/Login';
import ModelListPage from '../pages/model/ModelListPage';
import ModelFormPage from '../pages/model/ModelFormPage';
import GenericDashboardPage from '../pages/dashboard/DashboardPage';
import ComingSoon from '../pages/ComingSoon';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'docs', element: <DocumentationPage /> },
      { path: 'form', element: <FormPage /> },
      { path: 'list', element: <ListPage /> },
      { path: 'report-pivot', element: <ReportPivotPage /> },
      { path: 'report-table', element: <ReportTablePage /> },
      // Purchase custom routes
      { path: 'purchase/dashboard', element: <GenericDashboardPage dashboardKey="purchase" /> },
      { path: 'purchase/insight', element: <ComingSoon /> },
      { path: 'purchase/pivot', element: <ComingSoon /> },
      { path: 'purchase/detail', element: <ComingSoon /> },
      // Purchase model routes (coming soon)
      { path: 'purchase.quick_purchase', element: <ComingSoon /> },
      { path: 'purchase.order_template', element: <ComingSoon /> },
      { path: 'purchase.vendor_pricelist', element: <ComingSoon /> },
      // Purchase -> Product = menu alias → konten model inventory.product (URL tetap /purchase.product)
      { path: 'purchase.product', element: <ModelListPage modelName="inventory.product" basePath="/purchase.product" /> },
      { path: 'purchase.product/new', element: <ModelFormPage modelName="inventory.product" basePath="/purchase.product" /> },
      { path: 'purchase.product/:recordId', element: <ModelFormPage modelName="inventory.product" basePath="/purchase.product" /> },
      // Sales custom routes
      { path: 'sales/dashboard', element: <GenericDashboardPage dashboardKey="sales" /> },
      { path: 'sales/insight', element: <ComingSoon /> },
      { path: 'sales.quick_sales', element: <ComingSoon /> },
      { path: 'sales/pivot', element: <ComingSoon /> },
      { path: 'sales/detail', element: <ComingSoon /> },
      // Sales -> Product = menu alias → konten model inventory.product (URL tetap /sales.product)
      { path: 'sales.product', element: <ModelListPage modelName="inventory.product" basePath="/sales.product" /> },
      { path: 'sales.product/new', element: <ModelFormPage modelName="inventory.product" basePath="/sales.product" /> },
      { path: 'sales.product/:recordId', element: <ModelFormPage modelName="inventory.product" basePath="/sales.product" /> },
      // Sales -> Pricelist = coming soon (belum ada model)
      { path: 'sales.pricelist', element: <ComingSoon /> },
      // Inventory custom routes
      { path: 'inventory/dashboard', element: <GenericDashboardPage dashboardKey="inventory" /> },
      { path: 'inventory/insight', element: <ComingSoon /> },
      // Inventory -> Stock Receipt = menu alias → konten model purchase.goods_receipt (URL tetap /inventory.stock_receipt)
      { path: 'inventory.stock_receipt', element: <ModelListPage modelName="purchase.goods_receipt" basePath="/inventory.stock_receipt" /> },
      { path: 'inventory.stock_receipt/new', element: <ModelFormPage modelName="purchase.goods_receipt" basePath="/inventory.stock_receipt" /> },
      { path: 'inventory.stock_receipt/:recordId', element: <ModelFormPage modelName="purchase.goods_receipt" basePath="/inventory.stock_receipt" /> },
      // Inventory -> Stock Delivery = menu alias → konten model sales.delivery_order (URL tetap /inventory.stock_delivery)
      { path: 'inventory.stock_delivery', element: <ModelListPage modelName="sales.delivery_order" basePath="/inventory.stock_delivery" /> },
      { path: 'inventory.stock_delivery/new', element: <ModelFormPage modelName="sales.delivery_order" basePath="/inventory.stock_delivery" /> },
      { path: 'inventory.stock_delivery/:recordId', element: <ModelFormPage modelName="sales.delivery_order" basePath="/inventory.stock_delivery" /> },
      { path: 'inventory.stock_adjustment', element: <ComingSoon /> },
      { path: 'inventory/pivot', element: <ComingSoon /> },
      { path: 'inventory/detail', element: <ComingSoon /> },
      // Project custom routes
      { path: 'project/dashboard', element: <GenericDashboardPage dashboardKey="project" /> },
      // Project Update = menu alias → konten model project.project (URL tetap /project/progress, read-only)
      { path: 'project/progress', element: <ModelListPage modelName="project.project" basePath="/project/progress" readOnly /> },
      { path: 'project/progress/:recordId', element: <ModelFormPage modelName="project.project" basePath="/project/progress" readOnly /> },
      { path: 'project/wbs', element: <ComingSoon /> },
      { path: 'project/budgeting', element: <ComingSoon /> },
      { path: 'project/pivot', element: <ComingSoon /> },
      { path: 'project/pnl', element: <ComingSoon /> },
      { path: 'project/cashflow', element: <ComingSoon /> },
      // Project model routes (coming soon)
      // project.dokumen now uses generic model pages
      // Accounting report routes (coming soon)
      { path: 'accounting/dashboard', element: <GenericDashboardPage dashboardKey="accounting" /> },
      { path: 'accounting/laba_rugi', element: <ComingSoon /> },
      { path: 'accounting/neraca', element: <ComingSoon /> },
      { path: 'accounting/cashflow', element: <ComingSoon /> },
      // Generic model pages — e.g., /purchase-order, /purchase-order/new, /purchase-order/1
      { path: ':modelName', element: <ModelListPage /> },
      { path: ':modelName/new', element: <ModelFormPage /> },
      { path: ':modelName/:recordId', element: <ModelFormPage /> },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
