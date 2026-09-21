import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileBarChart, FileSpreadsheet, BookOpen, BookText, Scale } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";

import api from "../api/client";
import { useReportFilterOptions, ProjectFilter } from "../hooks/useReportFilters";

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

interface AccountOption {
  id: string;
  code: string;
  name: string;
  is_postable: boolean;
  is_active: boolean;
}

interface LedgerLine {
  entry_number: string;
  entry_date: string;
  account_id: string;
  debit: string;
  credit: string;
  name: string | null;
  reference: string | null;
  running_balance: string;
}

interface GeneralLedger {
  account: { id: string; code: string; name: string; account_type: string };
  from_date: string;
  to_date: string;
  opening_balance: string;
  lines: LedgerLine[];
  total_debit: string;
  total_credit: string;
  closing_balance: string;
}

interface BalanceSheetItem {
  section: string;
  accounts: { code: string; name: string; debit: string; credit: string; balance: string }[];
  total: string;
}

interface BalanceSheet {
  as_of_date: string;
  assets: BalanceSheetItem[];
  liabilities: BalanceSheetItem[];
  equity: BalanceSheetItem[];
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  is_balanced: boolean;
}

const fmt = (v: string | number) => Number(v).toFixed(2);

export default function ReportsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const activeReport = searchParams.get("report") || "trial-balance";
  const today = new Date().toISOString().slice(0, 10);
  const [fromDate, setFromDate] = useState(today.slice(0, 8) + "01");
  const [toDate, setToDate] = useState(today);
  const [projectId, setProjectId] = useState("");
  const [ledgerAccountId, setLedgerAccountId] = useState("");
  const { projects } = useReportFilterOptions();

  const { data: accounts = [] } = useQuery<AccountOption[]>({
    queryKey: ["accounts", "options"],
    queryFn: async () => (await api.get("/accounts")).data,
    staleTime: 60_000,
  });

  const { data: trial, isLoading } = useQuery<TrialBalance>({
    queryKey: ["trial-balance", fromDate, toDate, projectId],
    queryFn: async () =>
      (await api.get("/reports/trial-balance", {
        params: {
          from_date: fromDate,
          to_date: toDate,
          ...(projectId ? { project_id: projectId } : {}),
        },
      })).data,
    enabled: Boolean(fromDate && toDate) && activeReport === "trial-balance",
  });

  const { data: ledger, isLoading: ledgerLoading } = useQuery<GeneralLedger>({
    queryKey: ["general-ledger", ledgerAccountId, fromDate, toDate, projectId],
    queryFn: async () =>
      (await api.get("/reports/general-ledger", {
        params: {
          account_id: ledgerAccountId,
          from_date: fromDate,
          to_date: toDate,
          ...(projectId ? { project_id: projectId } : {}),
        },
      })).data,
    enabled: Boolean(ledgerAccountId && fromDate && toDate) && activeReport === "general-ledger",
  });

  const { data: sheet, isLoading: sheetLoading } = useQuery<BalanceSheet>({
    queryKey: ["balance-sheet", toDate, projectId],
    queryFn: async () =>
      (await api.get("/reports/balance-sheet", {
        params: {
          as_of_date: toDate,
          ...(projectId ? { project_id: projectId } : {}),
        },
      })).data,
    enabled: Boolean(toDate) && activeReport === "balance-sheet",
  });

  const postableAccounts = accounts.filter((a) => a.is_active && a.is_postable);

  const reports = [
    {
      id: "trial-balance",
      title: "ميزان المراجعة",
      desc: "أرصدة افتتاحية وحركة وأرصدة ختامية لكل حساب",
      icon: <Scale className="w-5 h-5" />,
      to: "/reports",
    },
    {
      id: "general-ledger",
      title: "الأستاذ العام",
      desc: "كشف حركة كل حساب مع الرصيد الجاري",
      icon: <BookOpen className="w-5 h-5" />,
      to: "/reports?report=general-ledger",
    },
    {
      id: "balance-sheet",
      title: "الميزانية العمومية",
      desc: "الأصول والخصوم وحقوق الملكية",
      icon: <FileBarChart className="w-5 h-5" />,
      to: "/reports?report=balance-sheet",
    },
    {
      id: "journal",
      title: "اليومية الأمريكية",
      desc: "قيود اليومية بأعمدة مدين ودائن",
      icon: <FileSpreadsheet className="w-5 h-5" />,
      to: "/reports/american-journal",
    },
    {
      id: "general-journal",
      title: "اليومية العامة",
      desc: "كل القيود بسطورها — الفترة والسنة المالية والمشروع والدفتر",
      icon: <BookText className="w-5 h-5" />,
      to: "/reports/general-journal",
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
        {reports.map((r) => {
          const isActive =
            (r.id === "trial-balance" && activeReport === "trial-balance") ||
            (r.id === "general-ledger" && activeReport === "general-ledger") ||
            (r.id === "balance-sheet" && activeReport === "balance-sheet");
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => navigate(r.to)}
              className={`card p-5 hover:shadow-card transition-shadow cursor-pointer text-right ${
                isActive ? "ring-2 ring-accent border-accent" : ""
              }`}
            >
              <div className="w-10 h-10 rounded-lg bg-accent-soft flex items-center justify-center text-accent-dark mb-3">
                {r.icon}
              </div>
              <h3 className="font-bold text-ink mb-1">{r.title}</h3>
              <p className="text-xs text-ink-muted leading-relaxed">{r.desc}</p>
            </button>
          );
        })}
      </div>

      {/* ميزان المراجعة */}
      {activeReport === "trial-balance" && (
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
            <ProjectFilter value={projectId} onChange={setProjectId} projects={projects} />
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
      )}

      {/* الأستاذ العام */}
      {activeReport === "general-ledger" && (
      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap items-center gap-4">
          <h2 className="font-bold text-ink">الأستاذ العام</h2>
          <div className="flex items-center gap-2 mr-auto flex-wrap">
            <select
              className="input w-auto"
              value={ledgerAccountId}
              onChange={(e) => setLedgerAccountId(e.target.value)}
            >
              <option value="">اختر الحساب…</option>
              {postableAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} — {a.name}
                </option>
              ))}
            </select>
            <input type="date" className="input w-auto" value={fromDate}
              onChange={(e) => setFromDate(e.target.value)} />
            <span className="text-ink-muted text-sm">إلى</span>
            <input type="date" className="input w-auto" value={toDate}
              onChange={(e) => setToDate(e.target.value)} />
            <ProjectFilter value={projectId} onChange={setProjectId} projects={projects} />
          </div>
        </div>
        {!ledgerAccountId ? (
          <div className="p-12 text-center">
            <BookOpen className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">اختر حساباً لعرض كشف حركته مع الرصيد الجاري</p>
          </div>
        ) : ledgerLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري إعداد الأستاذ العام...</div>
        ) : !ledger || ledger.lines.length === 0 ? (
          <div className="p-12 text-center">
            <BookOpen className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">لا توجد حركة لهذا الحساب في هذه الفترة</p>
          </div>
        ) : (          <>
            <div className="p-4 border-b border-line-soft flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <span className="text-ink-muted">
                الحساب:{" "}
                <span className="font-bold text-ink tabular" dir="ltr">{ledger.account.code}</span>{" "}
                <span className="font-bold text-ink">{ledger.account.name}</span>
              </span>
              <span className="text-ink-muted">
                الرصيد الافتتاحي:{" "}
                <span className="font-bold tabular text-ink" dir="ltr">{fmt(ledger.opening_balance)}</span>
              </span>
              <span className="text-ink-muted">
                الرصيد الختامي:{" "}
                <span className="font-bold tabular text-ink" dir="ltr">{fmt(ledger.closing_balance)}</span>
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-line-soft border-b border-line">
                  <tr className="text-right text-xs font-medium text-ink-muted">
                    <th className="px-3 py-2.5">التاريخ</th>
                    <th className="px-3 py-2.5">رقم القيد</th>
                    <th className="px-3 py-2.5">البيان</th>
                    <th className="px-3 py-2">مدين</th>
                    <th className="px-3 py-2">دائن</th>
                    <th className="px-3 py-2">الرصيد الجاري</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft">
                  {ledger.lines.map((l, i) => (
                    <tr key={`${l.entry_number}-${i}`} className="hover:bg-line-soft text-sm">
                      <td className="px-3 py-2 tabular text-ink-muted" dir="ltr">{l.entry_date}</td>
                      <td className="px-3 py-2 tabular text-ink-muted" dir="ltr">{l.entry_number}</td>
                      <td className="px-3 py-2">{l.name || l.reference || "—"}</td>
                      <td className="px-3 py-2 tabular text-left" dir="ltr">
                        {Number(l.debit) > 0 ? fmt(l.debit) : "—"}
                      </td>
                      <td className="px-3 py-2 tabular text-left" dir="ltr">
                        {Number(l.credit) > 0 ? fmt(l.credit) : "—"}
                      </td>
                      <td className="px-3 py-2 tabular text-left font-medium" dir="ltr">
                        {fmt(l.running_balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-line-soft border-t-2 border-line">
                  <tr className="text-sm font-bold">
                    <td className="px-3 py-3" colSpan={3}>الإجمالي</td>
                    <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(ledger.total_debit)}</td>
                    <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(ledger.total_credit)}</td>
                    <td className="px-3 py-3 tabular text-left" dir="ltr">{fmt(ledger.closing_balance)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </>
        )}
      </div>
      )}

      {/* الميزانية العمومية */}
      {activeReport === "balance-sheet" && (
      <div className="card">
        <div className="p-4 border-b border-line flex flex-wrap items-center gap-4">
          <h2 className="font-bold text-ink">الميزانية العمومية</h2>
          <div className="flex items-center gap-2 mr-auto">
            <span className="text-ink-muted text-sm">حتى تاريخ</span>
            <input type="date" className="input w-auto" value={toDate}
              onChange={(e) => setToDate(e.target.value)} />
            <ProjectFilter value={projectId} onChange={setProjectId} projects={projects} />
          </div>
          {sheet && (
            <span className={`inline-flex px-3 py-1 rounded-lg text-sm font-medium ${
              sheet.is_balanced ? "bg-success-soft text-success" : "bg-danger-soft text-danger"
            }`}>
              {sheet.is_balanced ? "✓ متوازنة" : "✗ غير متوازنة"}
            </span>
          )}
        </div>

        {sheetLoading ? (
          <div className="p-12 text-center text-ink-muted">جاري إعداد الميزانية...</div>
        ) : !sheet ? (
          <div className="p-12 text-center">
            <FileBarChart className="w-12 h-12 mx-auto text-line mb-3" />
            <p className="text-ink-muted">اختر التاريخ لعرض الميزانية العمومية</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">
              {[
                { title: "الأصول", items: sheet.assets, total: sheet.total_assets },
                { title: "الخصوم", items: sheet.liabilities, total: sheet.total_liabilities },
                { title: "حقوق الملكية", items: sheet.equity, total: sheet.total_equity },
              ].map((group) => (
                <div key={group.title} className="rounded-xl border border-line overflow-hidden">
                  <div className="bg-line-soft px-4 py-2.5 font-bold text-ink text-sm flex justify-between">
                    <span>{group.title}</span>
                    <span className="tabular" dir="ltr">{fmt(group.total)}</span>
                  </div>
                  <div className="divide-y divide-line-soft">
                    {group.items.length === 0 ? (
                      <p className="px-4 py-3 text-sm text-ink-muted">—</p>
                    ) : (
                      group.items.map((sec) => (
                        <div key={sec.section}>
                          <p className="px-4 py-1.5 text-xs font-medium text-ink-muted bg-canvas">
                            {sec.section}
                          </p>
                          {sec.accounts.map((a) => (
                            <div key={a.code} className="px-4 py-1.5 flex justify-between text-sm">
                              <span>
                                <span className="tabular text-ink-muted" dir="ltr">{a.code}</span>{" "}
                                {a.name}
                              </span>
                              <span className="tabular" dir="ltr">{fmt(a.balance)}</span>
                            </div>
                          ))}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 border-t border-line flex justify-between items-center text-sm font-bold">
              <span>المعادلة: الأصول = الخصوم + حقوق الملكية</span>
              <span className="tabular" dir="ltr">
                {fmt(sheet.total_assets)} = {fmt(sheet.total_liabilities)} + {fmt(sheet.total_equity)}
              </span>
            </div>
          </>
        )}
      </div>
      )}
    </div>
  );
}
