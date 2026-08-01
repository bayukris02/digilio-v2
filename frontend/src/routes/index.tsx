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
      { path: 'purchase/dashboard', element: <ComingSoon /> },
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
      // Project custom routes (coming soon)
      { path: 'project/dashboard', element: <ComingSoon /> },
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
