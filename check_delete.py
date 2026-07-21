import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from core.models import PurchaseOrder

try:
    po = PurchaseOrder.objects.get(pk=69)
    print(f'PO #69: reference={po.reference}, status={po.status}, is_deleted={po.is_deleted}')
    
    # 1. State check
    state_cfg = po._get_state_config(po.status) if hasattr(po, '_get_state_config') else {}
    print(f'State config: {state_cfg}')
    print(f'State allow_delete: {state_cfg.get("allow_delete", True)}')
    
    # 2. Child check - _can_delete
    can_del, msg = po._can_delete()
    print(f'_can_delete: {can_del}, msg: {msg}')
    
    # Check children in document flow
    doc_flow = getattr(po, '_document_flow', None)
    print(f'Document flow: {doc_flow}')
    
    from core.model_meta import ErpModelBase
    for child_cfg in (doc_flow or {}).get('children', []):
        child_model = ErpModelBase._model_registry.get(child_cfg['model'])
        if child_model:
            source_field = child_cfg.get('source_field_in_child', 'source_document_id')
            children = child_model.objects.filter(**{source_field: po.pk, 'is_deleted': False})
            count = children.count()
            print(f'  Child {child_cfg["model"]}: {count} active records')
            if count > 0:
                for c in children:
                    print(f'    -> id={c.pk}, status={c.status}')
    
except PurchaseOrder.DoesNotExist:
    print('PO #69 NOT FOUND')
except Exception as e:
    import traceback
    print(f'Error: {e}')
    traceback.print_exc()
