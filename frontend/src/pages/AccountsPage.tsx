import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronDown, Plus, Search, TreePine } from "lucide-react";

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
  const [search, setSearch] = useState("");

  const { data: tree = [], isLoading } = useQuery<AccountNode[]>({
    queryKey: ["accounts-tree"],
    queryFn: async () => (await api.get("/accounts/tree")).data,
  });

  const filtered = search
    ? tree.filter(
        (a) => a.code.includes(search) || a.name.includes(search)
      )
    : tree;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">شجرة الحسابات</h1>
          <p className="text-ink-muted text-sm mt-1">
            الهيكل الهرمي للحسابات من المستوى الأول حتى الرابع
          </p>
        </div>
        <button className="btn-primary">
          <Plus className="w-4 h-4" />
          حساب جديد
        </button>
      </div>

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
