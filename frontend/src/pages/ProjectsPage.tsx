import { FormEvent, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Plus, Search, Briefcase, Loader2, X, Pencil, Ban, Wallet, CalendarDays, Building2,
} from "lucide-react";

import api from "../api/client";

interface Project {
  id: string;
  code: string;
  name: string;
  donor_id: string | null;
  donor_name: string | null;
  grant_reference: string | null;
  program: string | null;
  status: string;
  start_date: string | null;
  end_date: string | null;
  budget_total: string | number;
  currency: string;
  manager: string | null;
  cost_center_id: string | null;
  cost_center_name: string | null;
  description: string | null;
  is_active: boolean;
}

interface Partner {
  id: string;
  code: string;
  name: string;
}

interface CostCenter {
  id: string;
  code: string;
  name: string;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "مسودة",
  active: "نشط",
  on_hold: "موقوف مؤقتاً",
  completed: "مكتمل",
  closed: "مقفل مالياً",
  cancelled: "ملغي",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  active: "bg-success-soft text-success",
  on_hold: "bg-warning-soft text-warning",
  completed: "bg-blue-50 text-blue-700",
  closed: "bg-purple-50 text-purple-700",
  cancelled: "bg-danger-soft text-danger",
};

const fmtMoney = (v: string | number, cur: string) =>
  `${Number(v || 0).toLocaleString("ar-EG", { minimumFractionDigits: 2 })} ${cur || "EGP"}`;

const emptyForm = {
  code: "",
  name: "",
  donor_id: "",
  grant_reference: "",
  program: "",
  status: "draft",
  start_date: "",
  end_date: "",
  budget_total: "",
  currency: "EGP",
  manager: "",
  cost_center_id: "",
  description: "",
};
export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form, setForm] = useState(emptyForm);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ["projects", filterStatus],
    queryFn: async () =>
      (await api.get("/projects", {
        params: filterStatus ? { status_filter: filterStatus } : {},
      })).data,
  });

  const { data: donors = [] } = useQuery<Partner[]>({
    queryKey: ["donors"],
    queryFn: async () => (await api.get("/partners", { params: { partner_type: "donor" } })).data,
  });

  const { data: costCenters = [] } = useQuery<CostCenter[]>({
    queryKey: ["cost-centers"],
    queryFn: async () => (await api.get("/accounts/cost-centers")).data,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["projects"] });

  const saveMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      editing ? api.put(`/projects/${editing.id}`, payload) : api.post("/projects", payload),
    onSuccess: () => {
      toast.success(editing ? "تم حفظ التعديلات" : "تم إنشاء المشروع");
      invalidate();
      closeForm();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg).join("، ")
        : (detail as string) ?? "فشل الحفظ";
      toast.error(msg);
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/projects/${id}/deactivate`),
    onSuccess: () => {
      toast.success("تم تعطيل المشروع");
      invalidate();
    },
    onError: () => toast.error("فشل التعطيل"),
  });
  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (p: Project) => {
    setEditing(p);
    setForm({
      code: p.code,
      name: p.name,
      donor_id: p.donor_id || "",
      grant_reference: p.grant_reference || "",
      program: p.program || "",
      status: p.status,
      start_date: p.start_date || "",
      end_date: p.end_date || "",
      budget_total: String(p.budget_total ?? ""),
      currency: p.currency || "EGP",
      manager: p.manager || "",
      cost_center_id: p.cost_center_id || "",
      description: p.description || "",
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const closeForm = () => {
    setShowForm(false);
    setEditing(null);
    setForm(emptyForm);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const payload: Record<string, unknown> = {
      name: form.name,
      donor_id: form.donor_id || null,
      grant_reference: form.grant_reference || null,
      program: form.program || null,
      status: form.status,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      budget_total: form.budget_total === "" ? 0 : Number(form.budget_total),
      currency: form.currency || "EGP",
      manager: form.manager || null,
      cost_center_id: form.cost_center_id || null,
      description: form.description || null,
    };
    if (!editing) payload.code = form.code;
    saveMutation.mutate(payload);
  };
  const filtered = useMemo(() => {
    const q = search.trim();
    if (!q) return projects;
    return projects.filter((p) => p.code.includes(q) || p.name.includes(q));
  }, [projects, search]);

  const stats = useMemo(() => {
    const active = projects.filter((p) => p.status === "active").length;
    const total = projects.reduce((s, p) => s + Number(p.budget_total || 0), 0);
    return { count: projects.length, active, total };
  }, [projects]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink">المشاريع</h1>
          <p className="text-ink-muted text-sm mt-1">
            مشاريع المؤسسة الممولة — المانح، المنحة، البرنامج، الموازنة، المدة
          </p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          <Plus className="w-4 h-4" />
          مشروع جديد
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-accent-soft flex items-center justify-center">
            <Briefcase className="w-5 h-5 text-accent-dark" />
          </div>
          <div>
            <p className="text-2xl font-bold text-ink tabular">{stats.count}</p>
            <p className="text-xs text-ink-muted">إجمالي المشاريع</p>
          </div>
        </div>
        <div className="card p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-success-soft flex items-center justify-center">
            <CalendarDays className="w-5 h-5 text-success" />
          </div>
          <div>
            <p className="text-2xl font-bold text-ink tabular">{stats.active}</p>
            <p className="text-xs text-ink-muted">مشاريع نشطة</p>
          </div>
        </div>
        <div className="card p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-warning-soft flex items-center justify-center">
            <Wallet className="w-5 h-5 text-warning" />
          </div>
          <div>
            <p className="text-lg font-bold text-ink tabular">{fmtMoney(stats.total, "EGP")}</p>
            <p className="text-xs text-ink-muted">إجمالي الموازنات المعتمدة</p>
          </div>
        </div>
      </div>
      {showForm && (
        <form onSubmit={handleSubmit} className="card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-ink">{editing ? "تعديل المشروع" : "إنشاء مشروع جديد"}</h2>
            <button type="button" onClick={closeForm} className="p-1.5 text-ink-muted hover:text-danger" title="إغلاق">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label" htmlFor="pj-code">كود المشروع *</label>
              <input id="pj-code" className="input tabular" value={form.code}
                onChange={(e) => set("code", e.target.value)} required disabled={!!editing} dir="ltr"
                placeholder="PRJ-2026-001" />
            </div>
            <div className="md:col-span-2">
              <label className="label" htmlFor="pj-name">اسم المشروع *</label>
              <input id="pj-name" className="input" value={form.name}
                onChange={(e) => set("name", e.target.value)} required
                placeholder="مثال: تمكين المرأة إعلامياً — المرحلة الثانية" />
            </div>
            <div>
              <label className="label" htmlFor="pj-donor">الجهة المانحة</label>
              <select id="pj-donor" className="input" value={form.donor_id}
                onChange={(e) => set("donor_id", e.target.value)}>
                <option value="">— بدون —</option>
                {donors.map((d) => (
                  <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="pj-grant">رقم المنحة / الاتفاقية</label>
              <input id="pj-grant" className="input tabular" value={form.grant_reference}
                onChange={(e) => set("grant_reference", e.target.value)} dir="ltr"
                placeholder="GRANT-2026-042" />
            </div>
            <div>
              <label className="label" htmlFor="pj-program">البرنامج</label>
              <input id="pj-program" className="input" value={form.program}
                onChange={(e) => set("program", e.target.value)}
                placeholder="الإعلام المجتمعي / التدريب / ..." />
            </div>
            <div>
              <label className="label" htmlFor="pj-status">الحالة</label>
              <select id="pj-status" className="input" value={form.status}
                onChange={(e) => set("status", e.target.value)}>
                {Object.entries(STATUS_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="pj-start">تاريخ البداية</label>
              <input id="pj-start" type="date" className="input" value={form.start_date}
                onChange={(e) => set("start_date", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="pj-end">تاريخ النهاية</label>
              <input id="pj-end" type="date" className="input" value={form.end_date}
                onChange={(e) => set("end_date", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="pj-budget">الموازنة المعتمدة</label>
              <input id="pj-budget" type="number" min="0" step="0.01" className="input tabular"
                value={form.budget_total} onChange={(e) => set("budget_total", e.target.value)} dir="ltr" />
            </div>
            <div>
              <label className="label" htmlFor="pj-cur">العملة</label>
              <select id="pj-cur" className="input" value={form.currency}
                onChange={(e) => set("currency", e.target.value)}>
                <option value="EGP">EGP — جنيه مصري</option>
                <option value="USD">USD — دولار</option>
                <option value="EUR">EUR — يورو</option>
              </select>
            </div>
            <div>
              <label className="label" htmlFor="pj-manager">مدير المشروع</label>
              <input id="pj-manager" className="input" value={form.manager}
                onChange={(e) => set("manager", e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="pj-cc">مركز التكلفة</label>
              <select id="pj-cc" className="input" value={form.cost_center_id}
                onChange={(e) => set("cost_center_id", e.target.value)}>
                <option value="">— بدون —</option>
                {costCenters.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="label" htmlFor="pj-desc">الوصف / النطاق</label>
              <textarea id="pj-desc" className="input" rows={2} value={form.description}
                onChange={(e) => set("description", e.target.value)} />
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {editing ? "حفظ التعديلات" : "إنشاء المشروع"}
          </button>
        </form>
      )}
      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap gap-3">
          <div className="relative max-w-sm flex-1 min-w-[200px]">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
            <input className="input pr-9" placeholder="بحث بالكود أو الاسم..."
              value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input w-auto" value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">كل الحالات</option>
            {Object.entries(STATUS_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري التحميل...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Briefcase className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا توجد مشاريع بعد — أنشئ أول مشروع</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">الكود</th>
                  <th className="px-4 py-2.5">المشروع</th>
                  <th className="px-4 py-2.5">المانح / المنحة</th>
                  <th className="px-4 py-2.5">البرنامج</th>
                  <th className="px-4 py-2.5">الحالة</th>
                  <th className="px-4 py-2.5">المدة</th>
                  <th className="px-4 py-2.5">الموازنة</th>
                  <th className="px-4 py-2.5">مدير المشروع</th>
                  <th className="px-4 py-2.5">إجراءات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-line-soft text-sm">
                    <td className="px-4 py-2.5 tabular text-ink-muted" dir="ltr">{p.code}</td>
                    <td className="px-4 py-2.5 font-medium">
                      {p.name}
                      {p.cost_center_name && (
                        <span className="block text-xs font-normal text-ink-muted">
                          <Building2 className="w-3 h-3 inline ml-1" />
                          {p.cost_center_name}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {p.donor_name || "—"}
                      {p.grant_reference && (
                        <span className="block text-xs tabular text-ink-muted" dir="ltr">
                          {p.grant_reference}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-ink-muted">{p.program || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[p.status] || ""}`}>
                        {STATUS_LABELS[p.status] || p.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 tabular text-xs whitespace-nowrap" dir="ltr">
                      {p.start_date || "—"} → {p.end_date || "—"}
                    </td>
                    <td className="px-4 py-2.5 tabular whitespace-nowrap">
                      {fmtMoney(p.budget_total, p.currency)}
                    </td>
                    <td className="px-4 py-2.5 text-ink-muted">{p.manager || "—"}</td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <button onClick={() => openEdit(p)} className="p-1.5 text-ink-muted hover:text-accent" title="تعديل">
                        <Pencil className="w-4 h-4" />
                      </button>
                      {p.is_active && (
                        <button onClick={() => deactivateMutation.mutate(p.id)}
                          className="p-1.5 text-ink-muted hover:text-danger" title="تعطيل">
                          <Ban className="w-4 h-4" />
                        </button>
                      )}
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