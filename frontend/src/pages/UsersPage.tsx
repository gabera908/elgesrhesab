import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Search, Users, Loader2, Pencil, Shield } from "lucide-react";

import api from "../api/client";

interface UserData {
  id: string;
  full_name: string;
  email: string;
  username: string;
  role_id: string;
  role_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  twofa_enabled: boolean;
  user_permissions: { module: string; action: string }[];
}

interface Role {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
}

interface PermModules {
  modules: string[];
  actions: string[];
}

const MODULE_LABELS: Record<string, string> = {
  accounts: "الحسابات",
  journals: "القيود اليومية",
  partners: "الشركاء",
  reports: "التقارير",
  settings: "الإعدادات",
  users: "المستخدمين",
};

const ACTION_LABELS: Record<string, string> = {
  read: "عرض",
  create: "إنشاء",
  update: "تعديل",
  delete: "حذف",
  post: "ترحيل",
  cancel: "إلغاء",
};

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [perms, setPerms] = useState<Record<string, Record<string, boolean>>>({});

  const { data: users = [], isLoading } = useQuery<UserData[]>({
    queryKey: ["users-admin"],
    queryFn: async () => (await api.get("/users-admin/users")).data,
  });

  const { data: roles = [] } = useQuery<Role[]>({
    queryKey: ["users-admin-roles"],
    queryFn: async () => (await api.get("/users-admin/roles")).data,
  });

  const { data: permModules } = useQuery<PermModules>({
    queryKey: ["users-admin-perm-modules"],
    queryFn: async () => (await api.get("/users-admin/permission-modules")).data,
  });

  const resetForm = () => {
    setFullName("");
    setEmail("");
    setUsername("");
    setPassword("");
    setRoleId("");
    setIsActive(true);
    setPerms({});
    setEditingId(null);
    setShowForm(false);
  };

  const openEdit = (u: UserData) => {
    setEditingId(u.id);
    setFullName(u.full_name);
    setEmail(u.email);
    setUsername(u.username);
    setPassword("");
    setRoleId(u.role_id);
    setIsActive(u.is_active);
    const p: Record<string, Record<string, boolean>> = {};
    u.user_permissions.forEach(({ module, action }) => {
      if (!p[module]) p[module] = {};
      p[module][action] = true;
    });
    setPerms(p);
    setShowForm(true);
  };

  const togglePerm = (module: string, action: string) => {
    setPerms((prev) => {
      const next = { ...prev };
      if (!next[module]) next[module] = {};
      next[module] = { ...next[module], [action]: !next[module][action] };
      return next;
    });
  };

  const permsPayload = (): { module: string; action: string }[] => {
    const list: { module: string; action: string }[] = [];
    Object.entries(perms).forEach(([mod, actions]) => {
      Object.entries(actions).forEach(([act, on]) => {
        if (on) list.push({ module: mod, action: act });
      });
    });
    return list;
  };

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/users-admin/users", payload),
    onSuccess: () => {
      toast.success("تم إنشاء المستخدم");
      queryClient.invalidateQueries({ queryKey: ["users-admin"] });
      resetForm();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل الإنشاء");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, ...payload }: Record<string, unknown>) =>
      api.put(`/users-admin/users/${id}`, payload),
    onSuccess: () => {
      toast.success("تم تحديث المستخدم");
      queryClient.invalidateQueries({ queryKey: ["users-admin"] });
      resetForm();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل التحديث");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const permissions = permsPayload();
    if (editingId) {
      const payload: Record<string, unknown> = {
        id: editingId,
        full_name: fullName,
        email,
        username,
        role_id: roleId,
        is_active: isActive,
        permissions,
      };
      if (password) payload.password = password;
      updateMutation.mutate(payload);
    } else {
      createMutation.mutate({
        full_name: fullName,
        email,
        username,
        password,
        role_id: roleId,
        permissions,
      });
    }
  };

  const filtered = search
    ? users.filter(
        (u) =>
          u.full_name.includes(search) ||
          u.email.includes(search) ||
          u.username.includes(search)
      )
    : users;

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">إدارة المستخدمين</h1>
          <p className="text-ink-muted text-sm mt-1">المستخدمون والأدوار والصلاحيات</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(!showForm); }}
          className="btn-primary"
        >
          <Plus className="w-4 h-4" />
          مستخدم جديد
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <h2 className="font-bold text-ink">
            {editingId ? "تعديل مستخدم" : "إنشاء مستخدم جديد"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label" htmlFor="ufullname">الاسم الكامل</label>
              <input id="ufullname" className="input" value={fullName}
                onChange={(e) => setFullName(e.target.value)} required />
            </div>
            <div>
              <label className="label" htmlFor="uemail">البريد الإلكتروني</label>
              <input id="uemail" type="email" className="input" value={email}
                onChange={(e) => setEmail(e.target.value)} dir="ltr" required />
            </div>
            <div>
              <label className="label" htmlFor="uusername">اسم المستخدم</label>
              <input id="uusername" className="input" value={username}
                onChange={(e) => setUsername(e.target.value)} dir="ltr" required />
            </div>
            <div>
              <label className="label" htmlFor="upassword">
                {editingId ? "كلمة المرور (اترك فارغاً للإبقاء)" : "كلمة المرور"}
              </label>
              <input id="upassword" type="password" className="input" value={password}
                onChange={(e) => setPassword(e.target.value)} dir="ltr"
                {...(!editingId ? { required: true } : {})} />
            </div>
            <div>
              <label className="label" htmlFor="urole">الدور</label>
              <select id="urole" className="input" value={roleId}
                onChange={(e) => setRoleId(e.target.value)} required>
                <option value="">— اختر دور —</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 accent-accent" />
                <span className="text-sm font-medium text-ink">نشط</span>
              </label>
            </div>
          </div>

          {permModules && (
            <div>
              <p className="text-sm font-medium text-ink mb-2">
                <Shield className="w-4 h-4 inline-block ml-1" />
                صلاحيات إضافية (تُضاف فوق صلاحيات الدور)
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-right text-xs text-ink-muted border-b border-line">
                      <th className="px-3 py-2">الوحدة</th>
                      {permModules.actions.map((a) => (
                        <th key={a} className="px-3 py-2 text-center">{ACTION_LABELS[a] || a}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {permModules.modules.map((m) => (
                      <tr key={m} className="hover:bg-line-soft">
                        <td className="px-3 py-2 font-medium">{MODULE_LABELS[m] || m}</td>
                        {permModules.actions.map((a) => (
                          <td key={a} className="px-3 py-2 text-center">
                            <input
                              type="checkbox"
                              checked={!!perms[m]?.[a]}
                              onChange={() => togglePerm(m, a)}
                              className="w-4 h-4 accent-accent"
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button type="submit" className="btn-primary" disabled={isPending}>
              {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {editingId ? "حفظ التعديلات" : "إنشاء المستخدم"}
            </button>
            <button type="button" className="btn-secondary" onClick={resetForm}>إلغاء</button>
          </div>
        </form>
      )}

      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap gap-3">
          <div className="relative max-w-sm flex-1 min-w-[200px]">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
            <input className="input pr-9" placeholder="بحث بالاسم أو البريد أو اسم المستخدم..."
              value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري التحميل...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا يوجد مستخدمون بعد</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">الاسم</th>
                  <th className="px-4 py-2.5">البريد</th>
                  <th className="px-4 py-2.5">اسم المستخدم</th>
                  <th className="px-4 py-2.5">الدور</th>
                  <th className="px-4 py-2.5">الحالة</th>
                  <th className="px-4 py-2.5">الصلاحيات الإضافية</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {filtered.map((u) => (
                  <tr key={u.id} className="hover:bg-line-soft text-sm">
                    <td className="px-4 py-2.5 font-medium">{u.full_name}</td>
                    <td className="px-4 py-2.5 tabular" dir="ltr">{u.email}</td>
                    <td className="px-4 py-2.5 tabular" dir="ltr">{u.username}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex px-2 py-0.5 rounded text-xs font-medium bg-accent-soft text-accent-dark">
                        {u.role_name || "—"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs ${u.is_active ? "bg-success-soft text-success" : "bg-danger-soft text-danger"}`}>
                        {u.is_active ? "نشط" : "معطَّل"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-ink-muted">
                      {u.user_permissions.length > 0 ? `${u.user_permissions.length} صلاحية` : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <button onClick={() => openEdit(u)} className="p-1.5 rounded hover:bg-line-soft text-ink-muted hover:text-accent-dark transition-colors" title="تعديل">
                        <Pencil className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
