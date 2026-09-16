import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileBarChart, FileSpreadsheet, BookOpen, Scale } from "lucide-react";

import api from "../api/client";

interface TrialBalanceAccount {
  account_id: string;
  code: string;
  name: string;
  level: number;
  account_type: string;
  opening_debit: string;
  opening_credit: string;
  period_debit: string;
  period_credit: string;
  closing_debit: string;
  closing_credit: string;
}

interface TrialBalance {
  from_date: string;
  to_date: string;
  accounts: TrialBalanceAccount[];
  total_opening_debit: string;
  total_opening_credit: string;
  total_period_debit: string;
  total_period_credit: string;
  total_closing_debit: string;
  total_closing_credit: string;
  is_balanced: boolean;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function ReportsPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);

  const { data: trial, isLoading } = useQuery<TrialBalance>({
    queryKey: ["trial-balance", fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/trial-balance", {
        params: { from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  const reports = [
    {
      id: "trial-balance",
      title: "ميزان المراجعة",
      desc: "أرصدة افتتاحية وحركة وأرصدة ختامية لكل حساب",
      icon: <Scale className="w-5 h-5" />,
    },
    {
      id: "general-ledger",
      title: "الأستاذ العام",
      desc: "كشف حركة كل حساب مع الرصيد الجاري",
      icon: <BookOpen className="w-5 h-5" />,
    },
    {
      id: "balance-sheet",
      title: "الميزانية العمومية",
      desc: "الأصول والخصوم وحقوق الملكية",
      icon: <FileBarChart className="w-5 h-5" />,
    },
    {
      id: "journal",
      title: "اليومية الأمريكية",
      desc: "قيود اليومية بأعمدة مدين ودائن",
      icon: <FileSpreadsheet className="w-5 h-5" />,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">التقارير</h1>
        <p className="text-ink-muted text-sm mt-1">
          التقارير المالية والمحاسبية لمؤسسة الجسر المصري للإعلام والتنمية
        </p>
      </div>

      {/* بطاقات التقارير */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {reports.map((r) => (
          <div key={r.id} className="card p-5 hover:shadow-card transition-shadow cursor-pointer">
            <div className="w-10 h-10 rounded-lg bg-accent-soft flex items-center justify-center text-accent-dark mb-3">
              {r.icon}
            </div>
            <h3 className="font-bold text-ink mb-1">{r.title}</h3>
            <p className="text-xs text-ink-muted leading-relaxed">{r.desc}</p>
          </div>
        ))}
      </div>

      {/* ميزان المراجعة */}
      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap items-center gap-4">
          <h2 className="font-bold text-ink">ميزان المراجعة</h2>
          <div className="flex items-center gap-2 mr-auto">
            <input
              type="date"
              className="input w-auto"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
            />
            <span className="text-ink-muted text-sm">إلى</span>
            <input
              type="date"
              className="input w-auto"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
            />
          </div>
          {trial && (
            <span
              className={`inline-flex px-3 py-1 rounded-lg text-sm font-medium ${
                trial.is_balanced
                  ? "bg-success-soft text-success"
                  : "bg-danger-soft text-danger"
              }`}
            >
              {trial.is_balanced ? "✓ متوازن" : "✗ غير متوازن"}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري إعداد ميزان المراجعة...</div>
        ) : !trial || trial.accounts.length === 0 ? (
          <div className="p-12 text-center">
            <Scale className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا توجد حركة في هذه الفترة</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-3 py-2.5" colSpan={2} rowSpan={2}>
                    الحساب
                  </th>
                  <th className="px-3 py-2.5 text-center" colSpan={2}>
                    الرصيد الافتتاحي
                  </th>
                  <th className="px-3 py-2.5 text-center" colSpan={2}>
                    الحركة
                  </th>
                  <th className="px-3 py-2.5 text-center" colSpan={2}>
                    الرصيد الختامي
                  </th>
                </tr>
                <tr className="text-right text-xs font-medium text-ink-muted border-b border-line">
                  <th className="px-3 py-2">مدين</th>
                  <th className="px-3 py-2">دائن</th>
                  <th className="px-3 py-2">مدين</th>
                  <th className="px-3 py-2">دائن</th>
                  <th className="px-3 py-2">مدين</th>
                  <th className="px-3 py-2">دائن</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {trial.accounts.map((a) => (
                  <tr key={a.account_id} className="hover:bg-line-soft text-sm">
                    <td className="px-3 py-2 tabular text-ink-muted" dir="ltr">
                      {a.code}
                    </td>
                    <td className="px-3 py-2 font-medium">{a.name}</td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">
                      {fmt(a.opening_debit)}
                    </td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">
                      {fmt(a.opening_credit)}
                    </td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">
                      {fmt(a.period_debit)}
                    </td>
                    <td className="px-3 py-2 tabular text-left" dir="ltr">
                      {fmt(a.period_credit)}
                    </td>
                    <td className="px-3 py-2 tabular text-left font-medium" dir="ltr">
                      {fmt(a.closing_debit)}
                    </td>
                    <td className="px-3 py-2 tabular text-left font-medium" dir="ltr">
                      {fmt(a.closing_credit)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-line-soft border-t-2 border-line">
                <tr className="text-sm font-bold">
                  <td className="px-3 py-3" colSpan={2}>
                    الإجمالي
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_opening_debit)}
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_opening_credit)}
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_period_debit)}
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_period_credit)}
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_closing_debit)}
                  </td>
                  <td className="px-3 py-3 tabular text-left" dir="ltr">
                    {fmt(trial.total_closing_credit)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
