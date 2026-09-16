import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Search, Users, Loader2 } from "lucide-react";

import api from "../api/client";

interface Partner {
  id: string;
  code: string;
  name: string;
  partner_type: string;
  phone: string | null;
  email: string | null;
  tax_id: string | null;
  is_active: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  customer: "عميل",
  supplier: "مورد",
  donor: "جهة مانحة",
  employee: "موظف",
  other: "أخرى",
};

const TYPE_COLORS: Record<string, string> = {
  customer: "bg-blue-50 text-blue-700",
  supplier: "bg-amber-50 text-amber-700",
  donor: "bg-purple-50 text-purple-700",
  employee: "bg-green-50 text-green-700",
  other: "bg-gray-50 text-gray-700",
};

export default function PartnersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [partnerType, setPartnerType] = useState("customer");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [taxId, setTaxId] = useState("");

  const { data: partners = [], isLoading } = useQuery<Partner[]>({
    queryKey: ["partners", filterType],
    queryFn: async () =>
      (await api.get("/partners", {
        params: filterType ? { partner_type: filterType } : {},
      })).data,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/partners", payload),
    onSuccess: () => {
      toast.success("تم إنشاء الشريك");
      queryClient.invalidateQueries({ queryKey: ["partners"] });
      setShowForm(false);
      setCode(""); setName(""); setPhone(""); setEmail(""); setTaxId("");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل الإنشاء");
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      code, name, partner_type: partnerType,
      phone: phone || null, email: email || null, tax_id: taxId || null,
    });
  };

  const filtered = search
    ? partners.filter((p) => p.code.includes(search) || p.name.includes(search))
    : partners;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">الشركاء</h1>
          <p className="text-ink-muted text-sm mt-1">
            العملاء والموردون والجهات المانحة
          </p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          <Plus className="w-4 h-4" />
          شريك جديد
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <h2 className="font-bold text-ink">إنشاء شريك جديد</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label" htmlFor="pcode">الكود</label>
              <input id="pcode" className="input tabular" value={code}
                onChange={(e) => setCode(e.target.value)} required dir="ltr" />
            </div>
            <div>
              <label className="label" htmlFor="pname">الاسم</label>
              <input id="pname" className="input" value={name}
                onChange={(e) => setName(e.target.value)} required />
            </div>
            <div>
              <label className="label" htmlFor="ptype">النوع</label>
              <select id="ptype" className="input" value={partnerType}
                onChange={(e) => setPartnerType(e.target.value)}>
                {Object.entries(TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label" htmlFor="pphone">الهاتف</label>
              <input id="pphone" className="input tabular" value={phone}
                onChange={(e) => setPhone(e.target.value)} dir="ltr" />
            </div>
            <div>
              <label className="label" htmlFor="pemail">البريد</label>
              <input id="pemail" type="email" className="input" value={email}
                onChange={(e) => setEmail(e.target.value)} dir="ltr" />
            </div>
            <div>
              <label className="label" htmlFor="ptax">السجل الضريبي</label>
              <input id="ptax" className="input tabular" value={taxId}
                onChange={(e) => setTaxId(e.target.value)} dir="ltr" />
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            حفظ الشريك
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
          <select className="input w-auto" value={filterType}
            onChange={(e) => setFilterType(e.target.value)}>
            <option value="">كل الأنواع</option>
            {Object.entries(TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري التحميل...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا يوجد شركاء بعد</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">الكود</th>
                  <th className="px-4 py-2.5">الاسم</th>
                  <th className="px-4 py-2.5">النوع</th>
                  <th className="px-4 py-2.5">الهاتف</th>
                  <th className="px-4 py-2.5">السجل الضريبي</th>
                  <th className="px-4 py-2.5">الحالة</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-line-soft text-sm">
                    <td className="px-4 py-2.5 tabular text-ink-muted" dir="ltr">{p.code}</td>
                    <td className="px-4 py-2.5 font-medium">{p.name}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[p.partner_type] || ""}`}>
                        {TYPE_LABELS[p.partner_type] || p.partner_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 tabular" dir="ltr">{p.phone || "—"}</td>
                    <td className="px-4 py-2.5 tabular" dir="ltr">{p.tax_id || "—"}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs ${p.is_active ? "bg-success-soft text-success" : "bg-danger-soft text-danger"}`}>
                        {p.is_active ? "نشط" : "معطَّل"}
                      </span>
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
