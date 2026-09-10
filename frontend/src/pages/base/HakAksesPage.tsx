import { useEffect, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Typography, Button, Card, Input, Modal, Form, Checkbox, Tabs, Empty, Popconfirm,
  Tag, message, Spin,
} from 'antd';
import { accessApi, type AccessRole, type RoleInput } from '../../api/access';
import { buildAccessTree, type AccessModule, type AccessSection } from '../../config/menu';

const { Title, Text } = Typography;

/** Semua menu di satu section (termasuk sub-grup seperti "Laporan Keuangan"). */
const sectionMenuKeys = (sec: AccessSection): string[] => [
  ...sec.menus.map((m) => m.key),
  ...sec.subgroups.flatMap((g) => [g.key, ...g.menus.map((m) => m.key)]),
];

/**
 * Halaman Hak Akses (RBAC).
 *
 * Kiri  : daftar Role (tambah / ubah / hapus).
 * Kanan : Tab per modul → section (OPERATION/…) → menu yang bisa dichecklist.
 *
 * Checklist disimpan per role: `menu_keys` (menu individual) dan `section_keys`
 * (section yang digrant sekaligus — menu di dalamnya otomatis tercentang).
 * Route: /settings/hak_akses
 */
export default function HakAksesPage() {
  const qc = useQueryClient();
  const tree = useMemo<AccessModule[]>(() => buildAccessTree(), []);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [menuKeys, setMenuKeys] = useState<Set<string>>(new Set());
  const [sectionKeys, setSectionKeys] = useState<Set<string>>(new Set());
  const [dirty, setDirty] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form] = Form.useForm<RoleInput>();

  const rolesQuery = useQuery({ queryKey: ['access-roles'], queryFn: accessApi.listRoles });
  const roles = rolesQuery.data ?? [];
  const selected = roles.find((r) => r.id === selectedId) ?? null;

  // Muat checklist saat role dipilih / data di-refresh
  useEffect(() => {
    const role = (rolesQuery.data ?? []).find((r) => r.id === selectedId);
    setMenuKeys(new Set(role?.menu_keys ?? []));
    setSectionKeys(new Set(role?.section_keys ?? []));
    setDirty(false);
  }, [selectedId, rolesQuery.dataUpdatedAt]);

  const saveMutation = useMutation({
    mutationFn: (payload: { id: number; menu: string[]; section: string[] }) =>
      accessApi.savePermissions(payload.id, { menu_keys: payload.menu, section_keys: payload.section }),
    onSuccess: () => {
      message.success('Hak akses disimpan.');
      setDirty(false);
      qc.invalidateQueries({ queryKey: ['access-roles'] });
    },
    onError: (e: Error) => message.error(e.message || 'Gagal menyimpan hak akses.'),
  });

  const createMutation = useMutation({
    mutationFn: (data: RoleInput) => accessApi.createRole(data),
    onSuccess: (role) => {
      message.success(`Role "${role.name}" dibuat.`);
      setModalOpen(false);
      form.resetFields();
      qc.invalidateQueries({ queryKey: ['access-roles'] });
      setSelectedId(role.id);
    },
    onError: (e: Error) => message.error(e.message || 'Gagal membuat role.'),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { id: number; data: RoleInput }) => accessApi.updateRole(payload.id, payload.data),
    onSuccess: () => {
      message.success('Role diperbarui.');
      setModalOpen(false);
      setEditId(null);
      form.resetFields();
      qc.invalidateQueries({ queryKey: ['access-roles'] });
    },
    onError: (e: Error) => message.error(e.message || 'Gagal memperbarui role.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => accessApi.deleteRole(id),
    onSuccess: (_res, id) => {
      message.success('Role dihapus.');
      if (selectedId === id) setSelectedId(null);
      qc.invalidateQueries({ queryKey: ['access-roles'] });
    },
    onError: (e: Error) => message.error(e.message || 'Gagal menghapus role.'),
  });

  // ── Interaksi checklist ──
  const markDirty = () => setDirty(true);

  /** Section dianggap tercentang bila di-grant langsung atau semua menunya dicentang. */
  const isSectionChecked = (sec: AccessSection) => {
    if (sectionKeys.has(sec.key)) return true;
    const keys = sectionMenuKeys(sec);
    return keys.length > 0 && keys.every((k) => menuKeys.has(k));
  };

  const isSectionIndeterminate = (sec: AccessSection) => {
    if (sectionKeys.has(sec.key)) return false;
    const keys = sectionMenuKeys(sec);
    const some = keys.some((k) => menuKeys.has(k));
    return some && !keys.every((k) => menuKeys.has(k));
  };

  /** Menu tercentang bila dicentang sendiri atau diwarisi dari section-nya. */
  const isMenuChecked = (key: string, secKey: string) => menuKeys.has(key) || sectionKeys.has(secKey);

  const toggleSection = (sec: AccessSection, checked: boolean) => {
    const nextSections = new Set(sectionKeys);
    const nextMenus = new Set(menuKeys);
    const keys = sectionMenuKeys(sec);
    if (checked) {
      nextSections.add(sec.key);
      keys.forEach((k) => nextMenus.delete(k)); // cukup section-nya, menu diwarisi
    } else {
      nextSections.delete(sec.key);
      keys.forEach((k) => nextMenus.delete(k));
    }
    setSectionKeys(nextSections);
    setMenuKeys(nextMenus);
    markDirty();
  };

  const toggleMenu = (key: string, sec: AccessSection) => {
    const nextMenus = new Set(menuKeys);
    const nextSections = new Set(sectionKeys);
    if (nextMenus.has(key)) {
      nextMenus.delete(key);
    } else if (nextSections.has(sec.key)) {
      // Grant lewat section → pecah jadi menu eksplisit saat satu menu dilepas
      nextSections.delete(sec.key);
      sectionMenuKeys(sec).forEach((k) => { if (k !== key) nextMenus.add(k); });
    } else {
      nextMenus.add(key);
    }
    // Rapikan: buang section_key yang menunya sudah tidak lengkap
    nextSections.forEach((sk) => {
      const found = tree.flatMap((m) => m.sections).find((s) => s.key === sk);
      if (!found) return;
      if (!sectionMenuKeys(found).every((k) => nextMenus.has(k))) nextSections.delete(sk);
    });
    setMenuKeys(nextMenus);
    setSectionKeys(nextSections);
    markDirty();
  };

  // ── Simpan ──
  const handleSave = () => {
    if (!selected) return;
    saveMutation.mutate({
      id: selected.id,
      menu: Array.from(menuKeys).sort(),
      section: Array.from(sectionKeys).sort(),
    });
  };

  const handleReset = () => {
    setMenuKeys(new Set(selected?.menu_keys ?? []));
    setSectionKeys(new Set(selected?.section_keys ?? []));
    setDirty(false);
  };

  const openCreate = () => { setEditId(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (role: AccessRole) => {
    setEditId(role.id);
    form.setFieldsValue({ name: role.name, code: role.code, description: role.description, active: role.active });
    setModalOpen(true);
  };
  const submitModal = async () => {
    const values = await form.validateFields();
    if (editId) updateMutation.mutate({ id: editId, data: values });
    else createMutation.mutate(values);
  };

  const grantedCount = menuKeys.size + sectionKeys.size;

  return (
    <div style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>Hak Akses</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Atur menu yang boleh diakses oleh setiap role.
        </Text>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        {/* ── Daftar role ── */}
        <Card
          size="small"
          title="Roles"
          styles={{ body: { padding: 8, height: '100%', overflow: 'auto' } }}
          extra={<Button type="link" size="small" style={{ padding: 0 }} onClick={openCreate}>+ Tambah</Button>}
          style={{ width: 260, flex: '0 0 260px', display: 'flex', flexDirection: 'column' }}
        >
          {rolesQuery.isLoading ? (
            <div style={{ textAlign: 'center', padding: 24 }}><Spin size="small" /></div>
          ) : roles.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Belum ada role" />
          ) : (
            roles.map((role) => {
              const isActive = role.id === selectedId;
              return (
                <div
                  key={role.id}
                  onClick={() => setSelectedId(role.id)}
                  style={{
                    padding: '6px 8px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    background: isActive ? 'rgba(24,144,255,0.10)' : 'transparent',
                    borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
                    marginBottom: 2,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: isActive ? '#1677ff' : undefined, fontWeight: isActive ? 600 : 400 }}>
                      {role.name}
                    </span>
                    {!role.active && <Tag color="default" style={{ marginInlineEnd: 0, fontSize: 10 }}>nonaktif</Tag>}
                  </div>
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    {role.code || '—'} · {role.menu_keys.length + role.section_keys.length} akses
                  </div>
                  <div style={{ marginTop: 2 }}>
                    <Button type="link" size="small" style={{ padding: 0, fontSize: 11, height: 18 }}
                      onClick={(e) => { e.stopPropagation(); openEdit(role); }}>Ubah</Button>
                    <Popconfirm
                      title="Hapus role ini?"
                      description="Checklist hak aksesnya ikut terhapus."
                      okText="Hapus" cancelText="Batal"
                      onConfirm={() => deleteMutation.mutate(role.id)}
                    >
                      <Button danger type="link" size="small" style={{ padding: 0, fontSize: 11, height: 18, marginLeft: 10 }}
                        onClick={(e) => e.stopPropagation()}>Hapus</Button>
                    </Popconfirm>
                  </div>
                </div>
              );
            })
          )}
        </Card>

        {/* ── Checklist menu ── */}
        <Card
          size="small"
          title={selected ? (
            <span>
              Akses menu — <b>{selected.name}</b>
              {selected.code ? <Text type="secondary" style={{ fontSize: 12 }}> ({selected.code})</Text> : null}
            </span>
          ) : 'Akses menu'}
          styles={{ body: { padding: 0, height: '100%', display: 'flex', flexDirection: 'column' } }}
          style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}
        >
          {!selected ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Pilih role di kiri untuk mengatur hak akses" />
            </div>
          ) : (
            <>
              <div style={{ flex: 1, overflow: 'auto', padding: '0 12px 12px' }}>
                <Tabs
                  size="small"
                  items={tree.map((mod) => ({
                    key: mod.key,
                    label: mod.label,
                    children: (
                      <div style={{ maxWidth: 760 }}>
                        {mod.sections.map((sec) => {
                          const checked = isSectionChecked(sec);
                          const indeterminate = isSectionIndeterminate(sec);
                          return (
                            <div key={sec.key} style={{ marginBottom: 14 }}>
                              <div style={{
                                display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0',
                                borderBottom: '1px solid #f0f0f0', marginBottom: 6,
                              }}>
                                <Checkbox
                                  checked={checked}
                                  indeterminate={indeterminate}
                                  onChange={(e) => toggleSection(sec, e.target.checked)}
                                />
                                <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: 0.4, color: '#595959' }}>
                                  {sec.label}
                                </span>
                              </div>
                              <div style={{ paddingLeft: 24 }}>
                                {sec.menus.map((m) => (
                                  <div key={m.key} style={{ lineHeight: '22px' }}>
                                    <Checkbox
                                      checked={isMenuChecked(m.key, sec.key)}
                                      onChange={() => toggleMenu(m.key, sec)}
                                    >
                                      <span style={{ fontSize: 13 }}>{m.label}</span>
                                    </Checkbox>
                                  </div>
                                ))}
                                {sec.subgroups.map((g) => (
                                  <div key={g.key} style={{ marginTop: 4 }}>
                                    <div style={{ lineHeight: '22px' }}>
                                      <Checkbox
                                        checked={isMenuChecked(g.key, sec.key)}
                                        onChange={() => toggleMenu(g.key, sec)}
                                      >
                                        <span style={{ fontSize: 13, fontWeight: 500 }}>{g.label}</span>
                                      </Checkbox>
                                    </div>
                                    <div style={{ paddingLeft: 24 }}>
                                      {g.menus.map((m) => (
                                        <div key={m.key} style={{ lineHeight: '22px' }}>
                                          <Checkbox
                                            checked={isMenuChecked(m.key, sec.key)}
                                            onChange={() => toggleMenu(m.key, sec)}
                                          >
                                            <span style={{ fontSize: 13 }}>{m.label}</span>
                                          </Checkbox>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ),
                  }))}
                />
              </div>
              <div style={{
                borderTop: '1px solid #f0f0f0', padding: '10px 16px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: '#fafafa',
              }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {grantedCount} akses dipilih{dirty ? ' · belum disimpan' : ''}
                </Text>
                <div>
                  <Button size="small" onClick={handleReset} disabled={!dirty} style={{ marginRight: 8 }}>
                    Reset
                  </Button>
                  <Button type="primary" size="small" loading={saveMutation.isPending} disabled={!dirty} onClick={handleSave}>
                    Simpan
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>

      <Modal
        title={editId ? 'Ubah Role' : 'Tambah Role'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditId(null); }}
        onOk={submitModal}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
        okText="Simpan"
        cancelText="Batal"
        width={420}
        destroyOnClose
      >
        <Form form={form} layout="vertical" initialValues={{ active: true }} style={{ marginTop: 12 }}>
          <Form.Item name="name" label="Nama Role" rules={[{ required: true, message: 'Nama role wajib diisi' }]}>
            <Input placeholder="mis. Admin, Sales, Gudang" />
          </Form.Item>
          <Form.Item name="code" label="Kode">
            <Input placeholder="mis. ADMIN, SALES" />
          </Form.Item>
          <Form.Item name="description" label="Keterangan">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="active" label="Aktif" valuePropName="checked">
            <Checkbox>Aktif</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
