import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown } from "lucide-react";

import api from "../api/client";

interface IncomeLine {
  account_code: string;
  account_name: string;
  debit: string;
  credit: string;
  balance: string;
}

interface IncomeSection {
  section: string;
  label: string;
  lines: IncomeLine[];
  total: string;
}

interface IncomeStatement {
  from_date: string;
  to_date: string;
  revenues: IncomeSection[];
  expenses: IncomeSection[];
  total_revenues: string;
  total_expenses: string;
  net_profit: string;
  is_loss: boolean;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function IncomeStatementPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);

  const { data: stmt, isLoading } = useQuery<IncomeStatement>({
    queryKey: ["income-statement", fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/income-statement", {
        params: { from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  const SectionTable = ({ section }: { section: IncomeSection }) => (
    <div className="mb-4">
      <h3 className="font-bold text-ink text-sm mb-2">{section.label}</h3>
      <table className="w-full">
        <tbody className="divide-y divide-line-soft">
          {section.lines.map((l) => (
            <tr key={l.account_code} className="text-sm hover:bg-line-soft">
              <td className="px-4 py-2 tabular text-ink-muted" dir="ltr">
                {l.account_code}
              </td>
              <td className="px-4 py-2">{l.account_name}</td>
              <td className="px-4 py-2 tabular text-left" dir="ltr">
                {fmt(l.balance)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-line-soft font-bold text-sm">
            <td className="px-4 py-2.5" colSpan={2}>
              إجمالي {section.label}
            </td>
            <td className="px-4 py-2.5 tabular text-left" dir="ltr">
              {fmt(section.total)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">قائمة الدخل</h1>
        <p className="text-ink-muted text-sm mt-1">
          الإيرادات والمصروفات وصافي النتيجة للفترة
        </p>
      </div>

      <div className="card p-4 flex flex-wrap items-center gap-4">
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

      {isLoading ? (
        <div className="card p-12 text-center text-ink-muted">جاري التحضير...</div>
      ) : !stmt ? (
        <div className="card p-12 text-center text-ink-muted">لا توجد بيانات</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-5">
              <div className="w-10 h-10 rounded-lg bg-success-soft flex items-center justify-center text-success mb-3">
                <TrendingUp className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold tabular" dir="ltr">
                {fmt(stmt.total_revenues)}
              </p>
              <p className="text-sm text-ink-muted mt-1">إجمالي الإيرادات</p>
            </div>
            <div className="card p-5">
              <div className="w-10 h-10 rounded-lg bg-danger-soft flex items-center justify-center text-danger mb-3">
                <TrendingDown className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold tabular" dir="ltr">
                {fmt(stmt.total_expenses)}
              </p>
              <p className="text-sm text-ink-muted mt-1">إجمالي المصروفات</p>
            </div>
            <div className="card p-5">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                  stmt.is_loss
                    ? "bg-danger-soft text-danger"
                    : "bg-accent-soft text-accent-dark"
                }`}
              >
                <span className="text-lg font-bold">
                  {stmt.is_loss ? "−" : "+"}
                </span>
              </div>
              <p
                className={`text-2xl font-bold tabular ${
                  stmt.is_loss ? "text-danger" : "text-success"
                }`}
                dir="ltr"
              >
                {fmt(stmt.net_profit)}
              </p>
              <p className="text-sm text-ink-muted mt-1">
                {stmt.is_loss ? "صافي الخسارة" : "صافي الربح"}
              </p>
            </div>
          </div>

          <div className="card p-6">
            {stmt.revenues.map((s) => (
              <SectionTable key={s.section} section={s} />
            ))}
            {stmt.expenses.map((s) => (
              <SectionTable key={s.section} section={s} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
