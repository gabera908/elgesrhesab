import { useQuery } from "@tanstack/react-query";

import api from "../api/client";

export interface ProjectOption {
  id: string;
  code: string;
  name: string;
  cost_center_name: string | null;
}

export interface FiscalYearOption {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export interface JournalOption {
  id: string;
  code: string;
  name: string;
  journal_type: string;
}

/** خيارات الفلاتر المشتركة للتقارير: المشاريع + السنوات المالية + الدفاتر. */
export function useReportFilterOptions() {
  const projects = useQuery<ProjectOption[]>({
    queryKey: ["projects", "options"],
    queryFn: async () => (await api.get("/projects", { params: { active_only: true } })).data,
    staleTime: 60_000,
  });

  const fiscalYears = useQuery<FiscalYearOption[]>({
    queryKey: ["fiscal-years", "options"],
    queryFn: async () => (await api.get("/fiscal/years")).data,
    staleTime: 60_000,
  });

  const journals = useQuery<JournalOption[]>({
    queryKey: ["journals", "options"],
    queryFn: async () => (await api.get("/journals")).data,
    staleTime: 60_000,
  });

  return {
    projects: projects.data ?? [],
    fiscalYears: fiscalYears.data ?? [],
    journals: journals.data ?? [],
  };
}

/**
 * قائمة المشاريع المنسدلة — تُستخدم في كل صفحات التقارير.
 * المشاريع بلا مركز تكلفة تُعرض معطَّلة لأن التصفية المالية تتم عبر مركز التكلفة.
 */
export function ProjectFilter({
  value,
  onChange,
  projects,
  className = "input w-auto",
}: {
  value: string;
  onChange: (v: string) => void;
  projects: ProjectOption[];
  className?: string;
}) {
  return (
    <select
      className={className}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      title="تصفية التقرير بمشروع محدد (عبر مركز التكلفة)"
    >
      <option value="">كل المشاريع</option>
      {projects.map((p) => (
        <option key={p.id} value={p.id} disabled={!p.cost_center_name}>
          {p.code} — {p.name}
          {!p.cost_center_name ? " (بدون مركز تكلفة)" : ""}
        </option>
      ))}
    </select>
  );
}
