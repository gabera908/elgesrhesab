import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookText, Filter, X } from "lucide-react";

import api from "../api/client";
import { useReportFilterOptions, ProjectFilter } from "../hooks/useReportFilters";

interface GJLine {
  account_code: string;
  account_name: string;
  name: string | null;
  debit: string;
  credit: string;
}

interface GJEntry {
  entry_id: string;
  entry_number: string;
  entry_date: string;
  journal_code: string | null;
  journal_name: string | null;
  reference: string | null;
  narration: string | null;
  state: string;
  lines: GJLine[];
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
}

interface GJReport {
  from_date: string;
  to_date: string;
  entries: GJEntry[];
  entries_count: number;
  grand_debit: string;
  grand_credit: string;
  is_balanced: boolean;
}

const fmt = (v: string | number) => Number(v || 0).toFixed(2);

const STATE_LABELS: Record<string, string> = {
  draft: "مسودة",
  in_review: "قيد مراجعة",
  posted: "مرحَّل",
  reversed: "معكوس",
};
export default function GeneralJournalPage() {
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);
  const [fiscalYearId, setFiscalYearId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [journalId, setJournalId] = useState("");
  const [stateFilter, setStateFilter] = useState("");

  const { projects, fiscalYears, journals } = useReportFilterOptions();

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (fiscalYearId) {
      p.fiscal_year_id = fiscalYearId;
    } else {
      p.from_date = fromDate;
      p.to_date = toDate;
    }
    if (projectId) p.project_id = projectId;
    if (journalId) p.journal_id = journalId;
    if (stateFilter) p.state = stateFilter;
    return p;
  }, [fiscalYearId, fromDate, toDate, projectId, journalId, stateFilter]);

  const { data: report, isLoading, error } = useQuery<GJReport>({
    queryKey: ["general-journal", params],
    queryFn: async () => (await api.get("/reports/general-journal", { params })).data,
    enabled: Boolean(fiscalYearId || (fromDate && toDate)),
  });

  const activeFiltersCount = [fiscalYearId, projectId, journalId, stateFilter].filter(Boolean).length;
  const selectedProject = projects.find((p) => p.id === projectId);

  const reset = () => {
    setFiscalYearId("");
    setProjectId("");
    setJournalId("");
    setStateFilter("");
    setFromDate(today.slice(0, 8) + "01");
    setToDate(today);
  };
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink">اليومية العامة</h1>
          <p className="text-ink-muted text-sm mt-1">
            كل القيود في الفترة بسطورها — فلترة بالفترة أو السنة المالية والمشروع والدفتر
          </p>
        </div>
        {report && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-ink-muted">
              عدد القيود: <span className="font-bold text-ink tabular">{report.entries_count}</span>
            </span>
            <span
              className={`inline-flex px-3 py-1 rounded-lg text-sm font-medium ${
                report.is_balanced ? "bg-success-soft text-success" : "bg-danger-soft text-danger"
              }`}
            >
              {report.is_balanced ? "✓ متوازن" : "✗ غير متوازن"}
            </span>
          </div>
        )}
      </div>

      <div className="card p-4 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Filter className="w-4 h-4 text-ink-muted" />

          <select
            className="input w-auto"
            value={fiscalYearId}
            onChange={(e) => setFiscalYearId(e.target.value)}
            title="اختيار سنة مالية يضبط الفترة تلقائياً"
          >
            <option value="">فترة مخصصة</option>
            {fiscalYears.map((fy) => (
              <option key={fy.id} value={fy.id}>
                {fy.name}
              </option>
            ))}
          </select>

          <input
            type="date"
            className="input w-auto disabled:opacity-50"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            disabled={Boolean(fiscalYearId)}
          />
          <span className="text-ink-muted text-sm">إلى</span>
          <input
            type="date"
            className="input w-auto disabled:opacity-50"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            disabled={Boolean(fiscalYearId)}
          />

          <ProjectFilter value={projectId} onChange={setProjectId} projects={projects} />

          <select
            className="input w-auto"
            value={journalId}
            onChange={(e) => setJournalId(e.target.value)}
          >
            <option value="">كل الدفاتر</option>
            {journals.map((j) => (
              <option key={j.id} value={j.id}>
                {j.code} — {j.name}
              </option>
            ))}
          </select>

          <select
            className="input w-auto"
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
          >
            <option value="">كل الحالات</option>
            {Object.entries(STATE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>

          {activeFiltersCount > 0 && (
            <button onClick={reset} className="btn-secondary" title="مسح الفلاتر">
              <X className="w-4 h-4" />
              مسح ({activeFiltersCount})
            </button>
          )}
        </div>

        {selectedProject && !selectedProject.cost_center_name && (
          <p className="text-sm text-warning bg-warning-soft rounded-lg px-3 py-2">
            ⚠️ المشروع «{selectedProject.name}» غير مرتبط بمركز تكلفة — التصفية المالية تحتاج ربطه
            بمركز تكلفة من صفحة المشاريع.
          </p>
        )}
      </div>
      {isLoading ? (
        <div className="card p-12 text-center text-ink-muted">جاري التحضير...</div>
      ) : error ? (
        <div className="card p-12 text-center text-danger">
          {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            "تعذّر جلب التقرير"}
        </div>
      ) : !report || report.entries.length === 0 ? (
        <div className="card p-12 text-center">
          <BookText className="w-12 h-12 mx-auto text-line mb-3" />
          <p className="text-ink-muted">لا توجد قيود مطابقة للفلاتر المحددة</p>
        </div>
      ) : (
        <div className="space-y-4">
          {report.entries.map((entry) => (
            <div key={entry.entry_id} className="card overflow-hidden">
              <div className="p-3.5 border-b border-line bg-line-soft/50 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
                <span className="font-bold text-ink tabular" dir="ltr">
                  {entry.entry_number}
                </span>
                <span className="text-ink-muted tabular" dir="ltr">
                  {entry.entry_date}
                </span>
                {entry.journal_name && (
                  <span className="text-ink-muted">
                    الدفتر: <span className="text-ink">{entry.journal_name}</span>
                  </span>
                )}
                {entry.reference && (
                  <span className="text-ink-muted">
                    المرجع: <span className="tabular" dir="ltr">{entry.reference}</span>
                  </span>
                )}
                <span
                  className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                    entry.state === "posted"
                      ? "bg-success-soft text-success"
                      : entry.state === "reversed"
                        ? "bg-danger-soft text-danger"
                        : "bg-warning-soft text-warning"
                  }`}
                >
                  {STATE_LABELS[entry.state] ?? entry.state}
                </span>
                <span className="mr-auto flex gap-6">
                  <span className="text-ink-muted">
                    مدين:{" "}
                    <span className="font-bold tabular text-ink" dir="ltr">
                      {fmt(entry.total_debit)}
                    </span>
                  </span>
                  <span className="text-ink-muted">
                    دائن:{" "}
                    <span className="font-bold tabular text-ink" dir="ltr">
                      {fmt(entry.total_credit)}
                    </span>
                  </span>
                </span>
              </div>

              {entry.narration && (
                <div className="px-4 py-2 border-b border-line-soft text-sm text-ink-soft">
                  {entry.narration}
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-line-soft">
                    <tr className="text-right text-xs font-medium text-ink-muted">
                      <th className="px-4 py-2">الحساب</th>
                      <th className="px-4 py-2">بيان السطر</th>
                      <th className="px-4 py-2 w-36">مدين</th>
                      <th className="px-4 py-2 w-36">دائن</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line-soft">
                    {entry.lines.map((l, i) => (
                      <tr key={`${entry.entry_id}-${i}`} className="text-sm hover:bg-line-soft">
                        <td className="px-4 py-2.5">
                          <span className="tabular text-ink-muted" dir="ltr">
                            {l.account_code}
                          </span>
                          {" — "}
                          {l.account_name}
                        </td>
                        <td className="px-4 py-2.5 text-ink-muted">{l.name || "—"}</td>
                        <td className="px-4 py-2.5 tabular text-left" dir="ltr">
                          {Number(l.debit) > 0 ? fmt(l.debit) : "—"}
                        </td>
                        <td className="px-4 py-2.5 tabular text-left" dir="ltr">
                          {Number(l.credit) > 0 ? fmt(l.credit) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          <div className="card p-4 bg-accent-soft/30 border-accent/20">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <span className="font-bold text-ink">
                الإجمالي العام — {report.entries_count} قيد
              </span>
              <div className="flex gap-8">
                <span className="text-sm">
                  إجمالي مدين:{" "}
                  <span className="font-bold tabular text-ink" dir="ltr">
                    {fmt(report.grand_debit)}
                  </span>
                </span>
                <span className="text-sm">
                  إجمالي دائن:{" "}
                  <span className="font-bold tabular text-ink" dir="ltr">
                    {fmt(report.grand_credit)}
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