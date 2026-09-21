import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronLeft, ChevronDown, Loader2, Plus, Search, TreePine, X } from "lucide-react";

import api from "../api/client";

interface AccountNode {
  id: string;
  code: string;
  name: string;
  level: number;
  account_type: string;
  is_postable: boolean;
  is_active: boolean;
  children: AccountNode[];
}

const TYPE_LABELS: Record<string, string> = {
  asset: "أصول",
  liability: "خصوم",
  equity: "حقوق ملكية",
  income: "إيرادات",
  expense: "مصروفات",
};

const TYPE_COLORS: Record<string, string> = {
  asset: "bg-blue-50 text-blue-700",
  liability: "bg-amber-50 text-amber-700",
  equity: "bg-purple-50 text-purple-700",
  income: "bg-green-50 text-green-700",
  expense: "bg-red-50 text-red-700",
};

/** يسطّح الشجرة لقائمة الأباء المحتملة مع بادئة المستوى. */
function flatten(nodes: AccountNode[], depth = 0): { node: AccountNode; depth: number }[] {
  const out: { node: AccountNode; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ node: n, depth });
    out.push(...flatten(n.children, depth + 1));
  }
  return out;
}

/** يقترح الكود التالي: أكبر فرع داخل الأب + 1، أو أكبر جذر + 1 للمستوى الأول. */
function suggestCode(parent: AccountNode | null, tree: AccountNode[]): string {
  const siblings = parent ? parent.children : tree;
  let max = 0;
  for (const s of siblings) {
    const seg = Number(s.code.split(".").pop());
    if (!Number.isNaN(seg)) max = Math.max(max, seg);
  }
  return parent ? `${parent.code}.${max + 1}` : String(max + 1);
}

function AccountRow({ node, depth }: { node: AccountNode; depth: number }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children.length > 0;

  return (
    <>
      <tr className="hover:bg-line-soft transition-colors">
        <td
          className="px-4 py-2.5 text-sm font-medium"
          style={{ paddingRight: `${depth * 24 + 16}px` }}
        >
          <div className="flex items-center gap-1.5">
            {hasChildren ? (
              <button
                onClick={() => setOpen(!open)}
                className="p-0.5 text-ink-muted hover:text-ink"
              >
                {open ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronLeft className="w-3.5 h-3.5" />
                )}
              </button>
            ) : (
              <span className="w-4" />
            )}
            <span className="tabular text-ink-muted" dir="ltr">
              {node.code}
            </span>
            <span>{node.name}</span>
          </div>
        </td>
        <td className="px-4 py-2.5">
          <span
            className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
              TYPE_COLORS[node.account_type] || "bg-gray-50 text-gray-700"
            }`}
          >
            {TYPE_LABELS[node.account_type] || node.account_type}
          </span>
        </td>
        <td className="px-4 py-2.5 text-sm text-ink-muted text-center">
          {node.is_postable ? "نعم" : "تجميعي"}
        </td>
        <td className="px-4 py-2.5 text-center">
          <span
            className={`inline-flex px-2 py-0.5 rounded text-xs ${
              node.is_active ? "bg-success-soft text-success" : "bg-danger-soft text-danger"
            }`}
          >
            {node.is_active ? "نشط" : "معطَّل"}
          </span>
        </td>
      </tr>
      {open &&
        node.children.map((child) => (
          <AccountRow key={child.id} node={child} depth={depth + 1} />
        ))}
    </>
  );
}

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [parentId, setParentId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState("asset");
  const [isPostable, setIsPostable] = useState(true);

  const { data: tree = [], isLoading } = useQuery<AccountNode[]>({
    queryKey: ["accounts-tree"],
    queryFn: async () => (await api.get("/accounts/tree")).data,
  });

  const flat = useMemo(() => flatten(tree), [tree]);
  const parentOptions = flat.filter((f) => f.node.level < 4);
  const selectedParent = useMemo(
    () => flat.find((f) => f.node.id === parentId)?.node ?? null,
    [flat, parentId]
  );

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => api.post("/accounts", payload),
    onSuccess: () => {
      toast.success("تم إنشاء الحساب");
      queryClient.invalidateQueries({ queryKey: ["accounts-tree"] });
      closeForm();
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg).join("، ")
        : (detail as string) ?? "فشل الإنشاء";
      toast.error(msg);
    },
  });

  const openForm = () => {
    setShowForm(true);
    setParentId("");
    setCode(suggestCode(null, tree));
    setName("");
    setAccountType("asset");
    setIsPostable(true);
  };

  const closeForm = () => setShowForm(false);

  const onParentChange = (id: string) => {
    setParentId(id);
    const p = flat.find((f) => f.node.id === id)?.node ?? null;
    setCode(suggestCode(p, tree));
    if (p) setAccountType(p.account_type); // النوع يتبع الأب
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      code: code.trim(),
      name: name.trim(),
      parent_id: parentId || null,
      account_type: accountType,
      is_postable: isPostable,
    });
  };

  // بحث متكرر: تُبقى العقدة إذا طابقت هي أو أحد فروعها
  const filterTree = (nodes: AccountNode[], q: string): AccountNode[] => {
    const out: AccountNode[] = [];
    for (const n of nodes) {
      const kids = filterTree(n.children, q);
      if (n.code.includes(q) || n.name.includes(q) || kids.length > 0) {
        out.push({ ...n, children: kids.length > 0 ? kids : n.children });
      }
    }
    return out;
  };
  const filtered = search.trim() ? filterTree(tree, search.trim()) : tree;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">شجرة الحسابات</h1>
          <p className="text-ink-muted text-sm mt-1">
            الهيكل الهرمي للحسابات من المستوى الأول حتى الرابع
          </p>
        </div>
        <button onClick={openForm} className="btn-primary">
          <Plus className="w-4 h-4" />
          حساب جديد
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-ink">إنشاء حساب جديد</h2>
            <button type="button" onClick={closeForm} className="p-1.5 text-ink-muted hover:text-danger" title="إغلاق">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="acc-parent">الحساب الأب (اختياري)</label>
              <select
                id="acc-parent"
                className="input"
                value={parentId}
                onChange={(e) => onParentChange(e.target.value)}
              >
                <option value="">— حساب رئيسي (المستوى 1) —</option>
                {parentOptions.map(({ node, depth }) => (
                  <option key={node.id} value={node.id}>
                    {"\u00A0".repeat(depth * 4)}
                    {node.code} — {node.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-ink-muted mt-1">
                المستوى يُحدَّد تلقائياً من الأب (بحد أقصى 4 مستويات)
              </p>
            </div>

            <div>
              <label className="label" htmlFor="acc-code">كود الحساب *</label>
              <input
                id="acc-code"
                className="input tabular"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                dir="ltr"
                placeholder={suggestCode(selectedParent, tree)}
              />
              <p className="text-xs text-ink-muted mt-1">مقترح تلقائياً — يمكنك تعديله</p>
            </div>

            <div className="md:col-span-2">
              <label className="label" htmlFor="acc-name">اسم الحساب *</label>
              <input
                id="acc-name"
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="مثال: الصندوق الرئيسي"
              />
            </div>

            <div>
              <label className="label" htmlFor="acc-type">النوع *</label>
              <select
                id="acc-type"
                className="input"
                value={accountType}
                onChange={(e) => setAccountType(e.target.value)}
                disabled={Boolean(selectedParent)}
              >
                {Object.entries(TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
              <p className="text-xs text-ink-muted mt-1">
                {selectedParent
                  ? `موروث من الأب (${TYPE_LABELS[selectedParent.account_type]}) — غير قابل للتغيير`
                  : "يحدد موقع الحساب في القوائم المالية"}
              </p>
            </div>

            <div>
              <label className="label">قابل للترحيل</label>
              <label className="flex items-center gap-2 text-sm cursor-pointer mt-1">
                <input
                  type="checkbox"
                  checked={isPostable}
                  onChange={(e) => setIsPostable(e.target.checked)}
                  className="w-4 h-4 accent-[#D97757]"
                />
                يقبل القيود مباشرة (وإلا فهو حساب تجميعي)
              </label>
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            إنشاء الحساب
          </button>
        </form>
      )}

      <div className="card">
        <div className="p-4 border-b border-line">
          <div className="relative max-w-sm">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
            <input
              className="input pr-9"
              placeholder="بحث بالكود أو الاسم..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري التحميل...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <TreePine className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا توجد حسابات بعد. ابدأ بإنشاء الحسابات الرئيسية.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">الحساب</th>
                  <th className="px-4 py-2.5">النوع</th>
                  <th className="px-4 py-2.5">قابل للترحيل</th>
                  <th className="px-4 py-2.5">الحالة</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {filtered.map((node) => (
                  <AccountRow key={node.id} node={node} depth={0} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
