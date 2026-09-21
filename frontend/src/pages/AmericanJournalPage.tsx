import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileSpreadsheet } from "lucide-react";

import api from "../api/client";
import { useReportFilterOptions, ProjectFilter } from "../hooks/useReportFilters";

interface AmericanLine {
  entry_number: string;
  entry_date: string;
  account_code: string;
  account_name: string;
  narration: string | null;
  debit: string;
  credit: string;
}

interface DayGroup {
  entry_date: string;
  lines: AmericanLine[];
  day_debit: string;
  day_credit: string;
}

interface AmericanJournal {
  from_date: string;
  to_date: string;
  groups: DayGroup[];
  grand_debit: string;
  grand_credit: string;
  is_balanced: boolean;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function AmericanJournalPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);
  const [projectId, setProjectId] = useState("");
  const { projects } = useReportFilterOptions();

  const { data: journal, isLoading } = useQuery<AmericanJournal>({
    queryKey: ["american-journal", fromDate, toDate, projectId],
    queryFn: async () =>
      (await api.get("/reports/american-journal", {
        params: {
          from_date: fromDate,
          to_date: toDate,
          ...(projectId ? { project_id: projectId } : {}),
        },
      })).data,
    enabled: Boolean(fromDate && toDate),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">اليومية الأمريكية</h1>
        <p className="text-ink-muted text-sm mt-1">
          قيود اليومية مُجمَّعة حسب اليوم بأعمدة مدين ودائن
        </p>
      </div>

      <div className="card p-4 flex flex-wrap items-center gap-4">
        <FileSpreadsheet className="w-4 h-4 text-ink-muted" />
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
        <ProjectFilter value={projectId} onChange={setProjectId} projects={projects} />
        {journal && (
          <span
            className={`mr-auto inline-flex px-3 py-1 rounded-lg text-sm font-medium ${
              journal.is_balanced
                ? "bg-success-soft text-success"
                : "bg-danger-soft text-danger"
            }`}
          >
            {journal.is_balanced ? "✓ متوازن" : "✗ غير متوازن"}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="card p-12 text-center text-ink-muted">جاري التحضير...</div>
      ) : !journal || journal.groups.length === 0 ? (
        <div className="card p-12 text-center">
          <FileSpreadsheet className="w-12 h-12 mx-auto text-line mb-3" />
          <p className="text-ink-muted">لا توجد قيود في هذه الفترة</p>
        </div>
      ) : (
        <div className="space-y-4">
          {journal.groups.map((group) => (
            <div key={group.entry_date} className="card">
              <div className="p-4 border-b border-line flex items-center justify-between bg-line-soft/50">
                <h3 className="font-bold text-ink text-sm tabular" dir="ltr">
                  {group.entry_date}
                </h3>
                <div className="flex gap-6 text-sm">
                  <span className="text-ink-muted">
                    مدين:{" "}
                    <span className="font-bold tabular text-ink" dir="ltr">
                      {fmt(group.day_debit)}
                    </span>
                  </span>
                  <span className="text-ink-muted">
                    دائن:{" "}
                    <span className="font-bold tabular text-ink" dir="ltr">
                      {fmt(group.day_credit)}
                    </span>
                  </span>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-line-soft">
                    <tr className="text-right text-xs font-medium text-ink-muted">
                      <th className="px-4 py-2">رقم القيد</th>
                      <th className="px-4 py-2">الحساب</th>
                      <th className="px-4 py-2">البيان</th>
                      <th className="px-4 py-2 w-36">مدين</th>
                      <th className="px-4 py-2 w-36">دائن</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {group.lines.map((l, i) => (
                      <tr key={`${l.entry_number}-${i}`} className="text-sm hover:bg-line-soft">
                        <td className="px-4 py-2.5 tabular text-ink-muted" dir="ltr">
                          {l.entry_number}
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="tabular text-ink-muted" dir="ltr">
                            {l.account_code}
                          </span>
                          {" — "}
                          {l.account_name}
                        </td>
                        <td className="px-4 py-2.5 text-ink-muted">{l.narration || "—"}</td>
                        <td className="px-4 py-2.5 tabular text-left" dir="ltr">
                          {Number(l.debit) > 0 ? fmt(l.debit) : "—"}
                        </td>
                        <td className="px-4 py-2.5 tabular text-left" dir="ltr">
                          {Number(l.credit) > 0 ? fmt(l.credit) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-line-soft border-t border-line">
                    <tr className="text-sm font-bold">
                      <td className="px-4 py-3" colSpan={3}>
                        إجمالي اليوم
                      </td>
                      <td className="px-4 py-3 tabular text-left" dir="ltr">
                        {fmt(group.day_debit)}
                      </td>
                      <td className="px-4 py-3 tabular text-left" dir="ltr">
                        {fmt(group.day_credit)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          ))}

          <div className="card p-4 bg-accent-soft/30 border-accent/20">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <span className="font-bold text-ink">الإجمالي العام للفترة</span>
              <div className="flex gap-8">
                <span className="text-sm">
                  إجمالي مدين:{" "}
                  <span className="font-bold tabular text-ink" dir="ltr">
                    {fmt(journal.grand_debit)}
                  </span>
                </span>
                <span className="text-sm">
                  إجمالي دائن:{" "}
                  <span className="font-bold tabular text-ink" dir="ltr">
                    {fmt(journal.grand_credit)}
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
