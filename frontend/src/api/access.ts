import api from './client';

export interface AccessRole {
  id: number;
  name: string;
  code: string;
  description: string;
  active: boolean;
  /** key menu yang diizinkan, mis. '/sales.order' */
  menu_keys: string[];
  /** key section yang diizinkan, mis. 'sales:REPORT' */
  section_keys: string[];
}

export interface RoleInput {
  name: string;
  code?: string;
  description?: string;
  active?: boolean;
}

export interface PermissionsPayload {
  menu_keys: string[];
  section_keys: string[];
}

/** Hak akses user yang sedang login (`GET /access/me/`). */
export interface MyAccess {
  id: number;
  username: string;
  display_name: string;
  /** superuser/staff → tanpa pembatasan role */
  all_access: boolean;
  role_id: number | null;
  role_name: string | null;
  menu_keys: string[];
  section_keys: string[];
}

export const accessApi = {
  listRoles: async (): Promise<AccessRole[]> => (await api.get('/access/roles/')).data,
  getMe: async (): Promise<MyAccess> => (await api.get('/access/me/')).data,
  createRole: async (data: RoleInput): Promise<AccessRole> => (await api.post('/access/roles/', data)).data,
  updateRole: async (id: number, data: Partial<RoleInput>): Promise<AccessRole> =>
    (await api.patch(`/access/roles/${id}/`, data)).data,
  deleteRole: async (id: number): Promise<{ deleted: boolean }> => (await api.delete(`/access/roles/${id}/`)).data,
  savePermissions: async (id: number, data: PermissionsPayload): Promise<AccessRole> =>
    (await api.put(`/access/roles/${id}/permissions/`, data)).data,
};
