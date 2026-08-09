from core.model_meta import BaseModel
from core.models.chatter_log import ChatterLog
from core.models.purchase.purchase_order import PurchaseOrder
from core.models.purchase.purchase_order_line import PurchaseOrderLine
from core.models.purchase.goods_receipt import GoodsReceipt
from core.models.purchase.goods_receipt_line import GoodsReceiptLine
from core.models.purchase.vendor import Vendor
from core.models.purchase.purchase_request import PurchaseRequest
from core.models.purchase.purchase_request_line import PurchaseRequestLine
from core.models.sales.customer import Customer
from core.models.sales.sales_order import SalesOrder
from core.models.sales.sales_order_line import SalesOrderLine
from core.models.sales.delivery_order import DeliveryOrder
from core.models.sales.delivery_order_line import DeliveryOrderLine
from core.models.settings.user import User
from core.models.settings.sequence import Sequence, SequenceDateRange
from core.models.settings.company import Company
from core.models.settings.branch import Branch
from core.models.inventory.product import Product
from core.models.inventory.product_category import ProductCategory
from core.models.inventory.warehouse import Warehouse
from core.models.accounting.chart_of_account import ChartOfAccount
from core.models.accounting.jurnal import Jurnal
from core.models.accounting.jurnal_line import JurnalLine
from core.models.accounting.vendor_bill import VendorBill
from core.models.accounting.vendor_bill_line import VendorBillLine
from core.models.accounting.customer_invoice import CustomerInvoice
from core.models.accounting.customer_invoice_line import CustomerInvoiceLine
from core.models.accounting.expense import Expense
from core.models.accounting.expense_line import ExpenseLine
from core.models.project.project import Project
from core.models.project.project_line import ProjectLine
from core.models.project.unit import Unit
from core.models.project.dokumen import Dokumen
from core.models.project.milestone import Milestone
from core.models.project.milestone_line import MilestoneLine
from core.models.project.project_category import ProjectCategory
from core.models.project.project_unit import ProjectUnit
from core.models.project.project_unit_detail import ProjectUnitDetail
from core.models.project.unit_detail_payment import UnitDetailPayment
from core.models.project.unit_detail_progress import UnitDetailProgress
# Registrasi dashboard utama (gabungan semua modul) ke registry generic
from core.models.dashboard import MAIN_DASHBOARD  # noqa: F401

__all__ = [
    'BaseModel', 'ChatterLog', 'PurchaseOrder', 'PurchaseOrderLine', 'GoodsReceipt', 'GoodsReceiptLine',
    'Vendor', 'Customer', 'SalesOrder', 'SalesOrderLine', 'DeliveryOrder', 'DeliveryOrderLine', 'Product',
    'ProductCategory',
    'Warehouse',
    'Company', 'Branch',
    'User',
    'Sequence', 'SequenceDateRange',
    'ChartOfAccount', 'Jurnal', 'JurnalLine',
    'VendorBill', 'VendorBillLine',
    'CustomerInvoice', 'CustomerInvoiceLine',
    'Expense', 'ExpenseLine',
    'PurchaseRequest', 'PurchaseRequestLine',
    'Project', 'ProjectLine', 'Unit', 'Dokumen', 'Milestone', 'MilestoneLine', 'ProjectCategory', 'ProjectUnit', 'ProjectUnitDetail',
    'UnitDetailPayment', 'UnitDetailProgress',
]
