import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calendar, Wallet } from "lucide-react";

import api from "../api/client";

interface FlowLine {
  account_code: string;
  account_name: string;
  inflow: string;
  outflow: string;
  net: string;
}

interface FlowSection {
  category: string;
  label: string;
  lines: FlowLine[];
  total: string;
}

interface CashFlow {
  from_date: string;
  to_date: string;
  sections: FlowSection[];
  net_change: string;
  opening_cash: string;
  closing_cash: string;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function CashFlowPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);

  const { data: flow, isLoading } = useQuery<CashFlow>({
    queryKey: ["cash-flow", fromDate, toDate],
    queryFn: async () =>
      (await api.get("/reports/cash-flow", {
        params: { from_date: fromDate, to_date: toDate },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">قائمة التدفقات النقدية</h1>
        <p className="text-ink-muted text-sm mt-1">
          الحركة النقدية الواردة والصادرة خلال الفترة
        </p>
      </div>

      <div className="card p-4 flex flex-wrap items-center gap-4">
        <Calendar className="w-4 h-4 text-ink-muted" />
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
      ) : !flow ? (
        <div className="card p-12 text-center text-ink-muted">لا توجد بيانات</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-5">
              <div className="w-10 h-10 rounded-lg bg-line-soft flex items-center justify-center text-ink-muted mb-3">
                <Wallet className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold tabular" dir="ltr">
                {fmt(flow.opening_cash)}
              </p>
              <p className="text-sm text-ink-muted mt-1">الرصيد النقدي الافتتاحي</p>
            </div>
            <div className="card p-5">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                  Number(flow.net_change) >= 0
                    ? "bg-success-soft text-success"
                    : "bg-danger-soft text-danger"
                }`}
              >
                <span className="text-lg font-bold">
                  {Number(flow.net_change) >= 0 ? "▲" : "▼"}
                </span>
              </div>
              <p
                className={`text-2xl font-bold tabular ${
                  Number(flow.net_change) >= 0 ? "text-success" : "text-danger"
                }`}
                dir="ltr"
              >
                {fmt(flow.net_change)}
              </p>
              <p className="text-sm text-ink-muted mt-1">صافي التغير النقدي</p>
            </div>
            <div className="card p-5">
              <div className="w-10 h-10 rounded-lg bg-accent-soft flex items-center justify-center text-accent-dark mb-3">
                <Wallet className="w-5 h-5" />
              </div>
              <p className="text-2xl font-bold tabular" dir="ltr">
                {fmt(flow.closing_cash)}
              </p>
              <p className="text-sm text-ink-muted mt-1">الرصيد النقدي الختامي</p>
            </div>
          </div>

          <div className="card">
            {flow.sections.length === 0 ? (
              <div className="p-12 text-center text-ink-muted">
                لا توجد حركة نقدية في هذه الفترة
              </div>
            ) : (
              flow.sections.map((section) => (
                <div key={section.category} className="border-b border-line last:border-0">
                  <div className="p-4 border-b border-line-soft bg-line-soft/50">
                    <h3 className="font-bold text-ink text-sm">{section.label}</h3>
                  </div>
                  <table className="w-full">
                    <thead className="border-b border-line-soft">
                      <tr className="text-right text-xs font-medium text-ink-muted">
                        <th className="px-4 py-2">الحساب</th>
                        <th className="px-4 py-2 w-40">وارد</th>
                        <th className="px-4 py-2 w-40">صادر</th>
                        <th className="px-4 py-2 w-40">الصافي</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line-soft">
                      {section.lines.map((l) => (
                        <tr key={l.account_code} className="text-sm hover:bg-line-soft">
                          <td className="px-4 py-2.5">
                            <span className="tabular text-ink-muted" dir="ltr">
                              {l.account_code}
                            </span>
                            {" — "}
                            {l.account_name}
                          </td>
                          <td className="px-4 py-2.5 tabular text-left text-success" dir="ltr">
                            {fmt(l.inflow)}
                          </td>
                          <td className="px-4 py-2.5 tabular text-left text-danger" dir="ltr">
                            {fmt(l.outflow)}
                          </td>
                          <td
                            className={`px-4 py-2.5 tabular text-left font-medium ${
                              Number(l.net) >= 0 ? "text-success" : "text-danger"
                            }`}
                            dir="ltr"
                          >
                            {fmt(l.net)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-line-soft border-t border-line">
                      <tr className="text-sm font-bold">
                        <td className="px-4 py-3">إجمالي {section.label}</td>
                        <td className="px-4 py-3"></td>
                        <td className="px-4 py-3"></td>
                        <td className="px-4 py-3 tabular text-left" dir="ltr">
                          {fmt(section.total)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
