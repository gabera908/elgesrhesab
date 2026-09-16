import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";

import api from "../api/client";

interface CostCenterItem {
  cost_center_id: string;
  cost_center_code: string;
  cost_center_name: string;
  total_debit: string;
  total_credit: string;
  net: string;
}

interface PartnerStatementLine {
  entry_number: string;
  entry_date: string;
  account_code: string;
  account_name: string;
  narration: string | null;
  debit: string;
  credit: string;
  running_balance: string;
}

interface Partner {
  id: string;
  code: string;
  name: string;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function ExtraReportsPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);
  const [partnerId, setPartnerId] = useState("");
  const [exporting, setExporting] = useState(false);

  const { data: ccBalance } = useQuery<{
    items: CostCenterItem[];
    grand_debit: string;
    grand_credit: string;
  }>({
    queryKey: ["cc-trial", fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/extra/cost-center-trial-balance", {
        params: { from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  const { data: partners = [] } = useQuery<Partner[]>({
    queryKey: ["partners-list"],
    queryFn: async () => (await api.get("/partners")).data,
  });

  const { data: partnerStmt } = useQuery<{
    partner: { code: string; name: string };
    opening_balance: string;
    lines: PartnerStatementLine[];
    total_debit: string;
    total_credit: string;
    closing_balance: string;
  } | null>({
    queryKey: ["partner-stmt", partnerId, fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/extra/partner-statement", {
        params: { partner_id: partnerId, from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(partnerId && fromDate && toDate),
  });

  const { data: incomeComp } = useQuery<{
    current: { total_revenues: string; total_expenses: string; net_profit: string };
    previous: { total_revenues: string; total_expenses: string; net_profit: string };
    revenue_change_pct: number | null;
    expense_change_pct: number | null;
    profit_change: string;
  } | null>({
    queryKey: ["income-comp", fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/extra/income-comparison", {
        params: { from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  const handleExport = async (format: "csv" | "excel") => {
    setExporting(true);
    try {
      const res = await api.get(`/export/trial-balance/${format}`, {
        params: { from_date: fromDate, to_date: toDate },
        responseType: "blob",
      });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `trial-balance-${fromDate}-${toDate}.${format === "csv" ? "csv" : "xlsx"}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("تم تنزيل الملف");
    } catch {
      toast.error("فشل التصدير");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">تقارير إضافية</h1>
          <p className="text-ink-muted text-sm mt-1">
            ميزان مراكز التكلفة، كشف الشريك، مقارنة الدخل، والتصدير
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => handleExport("csv")} className="btn-secondary text-sm" disabled={exporting}>
            <FileText className="w-4 h-4" />
            CSV
          </button>
          <button onClick={() => handleExport("excel")} className="btn-secondary text-sm" disabled={exporting}>
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileSpreadsheet className="w-4 h-4" />}
            Excel
          </button>
        </div>
      </div>

      <div className="card p-4 flex flex-wrap items-center gap-4">
        <input type="date" className="input w-auto" value={fromDate}
          onChange={(e) => setFromDate(e.target.value)} />
        <span className="text-ink-muted text-sm">إلى</span>
        <input type="date" className="input w-auto" value={toDate}
          onChange={(e) => setToDate(e.target.value)} />
      </div>

      {/* ميزان مراكز التكلفة */}
      <div className="card">
        <div className="p-4 border-b border-line">
          <h2 className="font-bold text-ink">ميزان المراجعة حسب مركز التكلفة</h2>
        </div>
        {!ccBalance || ccBalance.items.length === 0 ? (
          <div className="p-8 text-center text-ink-muted">لا توجد حركة على مراكز التكلفة</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">المركز</th>
                  <th className="px-4 py-2.5">مدين</th>
                  <th className="px-4 py-2.5">دائن</th>
                  <th className="px-4 py-2.5">الصافي</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {ccBalance.items.map((i) => (
                  <tr key={i.cost_center_id} className="text-sm hover:bg-line-soft">
                    <td className="px-4 py-2.5 font-medium">{i.cost_center_name}
                      <span className="text-ink-muted tabular mr-2" dir="ltr">{i.cost_center_code}</span>
                    </td>
                    <td className="px-4 py-2.5 tabular text-left" dir="ltr">{fmt(i.total_debit)}</td>
                    <td className="px-4 py-2.5 tabular text-left" dir="ltr">{fmt(i.total_credit)}</td>
                    <td className={`px-4 py-2.5 tabular text-left font-medium ${Number(i.net) >= 0 ? "text-success" : "text-danger"}`} dir="ltr">
                      {fmt(i.net)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-line-soft border-t border-line">
                <tr className="text-sm font-bold">
                  <td className="px-4 py-3">الإجمالي</td>
                  <td className="px-4 py-3 tabular text-left" dir="ltr">{fmt(ccBalance.grand_debit)}</td>
                  <td className="px-4 py-3 tabular text-left" dir="ltr">{fmt(ccBalance.grand_credit)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* كشف الشريك */}
      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap items-center gap-3">
          <h2 className="font-bold text-ink">كشف حساب الشريك</h2>
          <select className="input w-auto mr-auto" value={partnerId}
            onChange={(e) => setPartnerId(e.target.value)}>
            <option value="">اختر الشريك...</option>
            {partners.map((p) => (
              <option key={p.id} value={p.id}>{p.code} — {p.name}</option>
            ))}
          </select>
        </div>
        {!partnerStmt ? (
          <div className="p-8 text-center text-ink-muted">اختر شريكاً لعرض الكشف</div>
        ) : partnerStmt.lines.length === 0 ? (
          <div className="p-8 text-center text-ink-muted">
            لا توجد حركة — الرصيد الافتتاحي: <span className="tabular font-bold" dir="ltr">{fmt(partnerStmt.opening_balance)}</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-3 py-2">القيد</th>
                  <th className="px-3 py-2">التاريخ</th>
                  <th className="px-3 py-2">الحساب</th>
                  <th className="px-3 py-2">مدين</th>
                  <th className="px-3 py-2">دائن</th>
                  <th className="px-3 py-2">الرصيد الجاري</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {partnerStmt.lines.map((l, i) => (
                  <tr key={i} className="text-sm hover:bg-line-soft">
                    <td className="px-3 py-2 tabular text-ink-muted" dir="ltr">{l.entry_number}</td>
                    <td className="px-3 py-2 tabular" dir="ltr">{l.entry_date}</td>
                    <td className="px-3 py-2">{l.account_name}</td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">{Number(l.debit) > 0 ? fmt(l.debit) : "—"}</td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">{Number(l.credit) > 0 ? fmt(l.credit) : "—"}</td>
                    <td className="px-3 py-2 tabular text-left font-medium" dir="ltr">{fmt(l.running_balance)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-line-soft border-t border-line">
                <tr className="text-sm font-bold">
                  <td className="px-3 py-3" colSpan={3}>الرصيد الختامي</td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(partnerStmt.total_debit)}</td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(partnerStmt.total_credit)}</td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(partnerStmt.closing_balance)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* مقارنة الدخل */}
      {incomeComp && (
        <div className="card p-6">
          <h2 className="font-bold text-ink mb-4">مقارنة قائمة الدخل بالفترة السابقة</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-line-soft/50">
              <p className="text-xs text-ink-muted mb-1">الإيرادات</p>
              <p className="text-lg font-bold tabular" dir="ltr">{fmt(incomeComp.current.total_revenues)}</p>
              <p className={`text-xs mt-1 ${incomeComp.revenue_change_pct !== null && incomeComp.revenue_change_pct >= 0 ? "text-success" : "text-danger"}`}>
                {incomeComp.revenue_change_pct !== null ? `${incomeComp.revenue_change_pct.toFixed(1)}%` : "—"}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-line-soft/50">
              <p className="text-xs text-ink-muted mb-1">المصروفات</p>
              <p className="text-lg font-bold tabular" dir="ltr">{fmt(incomeComp.current.total_expenses)}</p>
              <p className={`text-xs mt-1 ${incomeComp.expense_change_pct !== null && incomeComp.expense_change_pct <= 0 ? "text-success" : "text-danger"}`}>
                {incomeComp.expense_change_pct !== null ? `${incomeComp.expense_change_pct.toFixed(1)}%` : "—"}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-accent-soft/30">
              <p className="text-xs text-ink-muted mb-1">صافي الربح</p>
              <p className="text-lg font-bold tabular" dir="ltr">{fmt(incomeComp.current.net_profit)}</p>
              <p className={`text-xs mt-1 ${Number(incomeComp.profit_change) >= 0 ? "text-success" : "text-danger"}`}>
                التغير: <span className="tabular" dir="ltr">{fmt(incomeComp.profit_change)}</span>
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="card p-4 bg-line-soft/50">
        <button className="btn-secondary text-sm" onClick={() => handleExport("excel")} disabled={exporting}>
          <Download className="w-4 h-4" />
          تصدير ميزان المراجعة Excel
        </button>
      </div>
    </div>
  );
}
