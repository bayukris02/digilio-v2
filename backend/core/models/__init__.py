from core.model_meta import BaseModel
from core.models.chatter_log import ChatterLog
from core.models.purchase.purchase_order import PurchaseOrder
from core.models.purchase.purchase_order_line import PurchaseOrderLine
from core.models.purchase.goods_receipt import GoodsReceipt
from core.models.purchase.goods_receipt_line import GoodsReceiptLine
from core.models.purchase.vendor import Vendor
from core.models.purchase.purchase_request import PurchaseRequest
from core.models.purchase.purchase_request_line import PurchaseRequestLine
from core.models.purchase.quick_purchase import QuickPurchase
from core.models.purchase.quick_purchase_line import QuickPurchaseLine
from core.models.sales.quick_sales import QuickSales
from core.models.sales.quick_sales_line import QuickSalesLine
from core.models.sales.pricelist import SalesPricelist
from core.models.sales.pricelist_line import SalesPricelistLine
from core.models.purchase.order_template import OrderTemplate
from core.models.purchase.order_template_line import OrderTemplateLine
from core.models.purchase.vendor_pricelist import VendorPricelist
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
from core.models.inventory.warehouse_location import WarehouseLocation
from core.models.inventory.stock_request import StockRequest
from core.models.inventory.stock_request_line import StockRequestLine
from core.models.inventory.stock_out import StockOut
from core.models.inventory.stock_out_line import StockOutLine
from core.models.inventory.stock_in import StockIn
from core.models.inventory.stock_in_line import StockInLine
from core.models.inventory.stock_ledger import StockLedger
from core.models.inventory.uom import Uom
from core.models.accounting.chart_of_account import ChartOfAccount
from core.models.accounting.jurnal import Jurnal
from core.models.accounting.jurnal_line import JurnalLine
from core.models.accounting.vendor_bill import VendorBill
from core.models.accounting.vendor_bill_line import VendorBillLine
from core.models.accounting.customer_invoice import CustomerInvoice
from core.models.accounting.customer_invoice_line import CustomerInvoiceLine
from core.models.accounting.expense import Expense
from core.models.accounting.expense_line import ExpenseLine
from core.models.accounting.transfer_cash_bank import TransferCashBank
from core.models.accounting.deposit import Deposit
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

# Registrasi config pivot per modul ke registry generic
from core.models.purchase import pivot  # noqa: F401

__all__ = [
    'BaseModel', 'ChatterLog', 'PurchaseOrder', 'PurchaseOrderLine', 'GoodsReceipt', 'GoodsReceiptLine',
    'Vendor', 'Customer', 'SalesOrder', 'SalesOrderLine', 'DeliveryOrder', 'DeliveryOrderLine', 'Product',
    'ProductCategory',
    'Warehouse',
    'WarehouseLocation',
    'StockRequest', 'StockRequestLine',
    'StockOut', 'StockOutLine',
    'StockIn', 'StockInLine',
    'StockLedger',
    'Uom',
    'Company', 'Branch',
    'User',
    'Sequence', 'SequenceDateRange',
    'ChartOfAccount', 'Jurnal', 'JurnalLine',
    'VendorBill', 'VendorBillLine',
    'CustomerInvoice', 'CustomerInvoiceLine',
    'Expense', 'ExpenseLine',
    'TransferCashBank', 'Deposit',
    'PurchaseRequest', 'PurchaseRequestLine',
    'QuickPurchase', 'QuickPurchaseLine',
    'QuickSales', 'QuickSalesLine',
    'SalesPricelist', 'SalesPricelistLine',
    'OrderTemplate', 'OrderTemplateLine',
    'VendorPricelist',
    'Project', 'ProjectLine', 'Unit', 'Dokumen', 'Milestone', 'MilestoneLine', 'ProjectCategory', 'ProjectUnit', 'ProjectUnitDetail',
    'UnitDetailPayment', 'UnitDetailProgress',
]
