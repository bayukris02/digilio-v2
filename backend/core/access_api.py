"""RBAC — role & checklist akses menu.

Endpoint:
    GET    /api/access/roles/                   → [{id, name, code, description, active, menu_keys, section_keys}]
    POST   /api/access/roles/                   → buat role {name, code, description, active}
    PATCH  /api/access/roles/<id>/              → ubah role
    DELETE /api/access/roles/<id>/              → nonaktifkan role (soft delete) + bersihkan checklist
    GET    /api/access/roles/<id>/permissions/  → {menu_keys, section_keys}
    PUT    /api/access/roles/<id>/permissions/  → simpan checklist {menu_keys, section_keys} (replace)

Catatan: menu tree (label/key/section/modul) adalah milik frontend
(`src/config/menu.tsx`) — backend hanya menyimpan key yang dicentang.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models.settings.role import Role, RoleMenuAccess


_EDITABLE = ('name', 'code', 'description', 'active')


def _get_role(role_id):
    return Role.objects.filter(pk=role_id, is_deleted=False).first()


def _role_payload(role):
    """Role + checklist akses-nya (dipisah menu vs section)."""
    menu_keys, section_keys = [], []
    rows = RoleMenuAccess.objects.filter(
        role_id=role.pk, is_deleted=False, allow=True,
    )
    for row in rows:
        if row.menu_type == 'section':
            section_keys.append(row.menu_key)
        else:
            menu_keys.append(row.menu_key)
    return {
        'id': role.pk,
        'name': role.name,
        'code': role.code,
        'description': role.description,
        'active': role.active,
        'menu_keys': sorted(menu_keys),
        'section_keys': sorted(section_keys),
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def access_roles(request):
    """List / buat role."""
    if request.method == 'GET':
        roles = Role.objects.filter(is_deleted=False).order_by('name')
        return Response([_role_payload(r) for r in roles])

    data = request.data or {}
    name = (data.get('name') or '').strip()
    if not name:
        return Response({'error': 'Nama role wajib diisi.'}, status=400)
    if Role.objects.filter(name=name, is_deleted=False).exists():
        return Response({'error': f'Role "{name}" sudah ada.'}, status=400)
    role = Role.objects.create(
        name=name,
        code=(data.get('code') or '').strip(),
        description=data.get('description') or '',
        active=bool(data.get('active', True)),
    )
    return Response(_role_payload(role), status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def access_role_detail(request, role_id):
    """Ubah / nonaktifkan role."""
    role = _get_role(role_id)
    if not role:
        return Response({'error': 'Role tidak ditemukan.'}, status=404)

    if request.method == 'DELETE':
        role.soft_delete()
        RoleMenuAccess.objects.filter(role_id=role.pk).delete()
        return Response({'deleted': True})

    data = request.data or {}
    if 'name' in data and not (data.get('name') or '').strip():
        return Response({'error': 'Nama role wajib diisi.'}, status=400)
    for field in _EDITABLE:
        if field in data:
            setattr(role, field, data[field])
    role.save()
    return Response(_role_payload(role))


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def access_role_permissions(request, role_id):
    """Checklist akses menu untuk satu role."""
    role = _get_role(role_id)
    if not role:
        return Response({'error': 'Role tidak ditemukan.'}, status=404)

    if request.method == 'PUT':
        data = request.data or {}
        rows = []
        for key in (data.get('menu_keys') or []):
            if key:
                rows.append(RoleMenuAccess(role_id=role, menu_key=str(key), menu_type='menu', allow=True))
        for key in (data.get('section_keys') or []):
            if key:
                rows.append(RoleMenuAccess(role_id=role, menu_key=str(key), menu_type='section', allow=True))
        # Replace penuh — tabel internal, hapus hard supaya tidak menumpuk baris.
        RoleMenuAccess.objects.filter(role_id=role.pk).delete()
        RoleMenuAccess.objects.bulk_create(rows)

    return Response(_role_payload(role))
