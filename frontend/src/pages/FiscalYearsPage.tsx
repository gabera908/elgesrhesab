import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Calendar, Loader2, Lock, Plus, Unlock, X } from "lucide-react";

import api from "../api/client";

interface FiscalYear {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
}

interface Period {
  id: string;
  fiscal_year_id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_closed: boolean;
}

export default function FiscalYearsPage() {
  const queryClient = useQueryClient();
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [showPeriodForm, setShowPeriodForm] = useState(false);
  const [periodName, setPeriodName] = useState("");
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");

  const { data: years = [], isLoading: yearsLoading } = useQuery<FiscalYear[]>({
    queryKey: ["fiscal-years"],
    queryFn: async () => (await api.get("/fiscal/years")).data,
  });

  const { data: periods = [] } = useQuery<Period[]>({
    queryKey: ["periods", selectedYear],
    queryFn: async () =>
      (await api.get("/fiscal/periods", {
        params: selectedYear ? { year_id: selectedYear } : {},
      })).data,
  });

  const closePeriod = useMutation({
    mutationFn: async (id: string) => api.post(`/fiscal/periods/${id}/close`),
    onSuccess: () => {
      toast.success("تم إقفال الفترة");
      queryClient.invalidateQueries({ queryKey: ["periods"] });
    },
    onError: () => toast.error("فشل الإقفال"),
  });

  const reopenPeriod = useMutation({
    mutationFn: async (id: string) => api.post(`/fiscal/periods/${id}/reopen`),
    onSuccess: () => {
      toast.success("تمت إعادة فتح الفترة");
      queryClient.invalidateQueries({ queryKey: ["periods"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل إعادة الفتح");
    },
  });

  const closeYear = useMutation({
    mutationFn: async (id: string) => api.post(`/fiscal/years/${id}/close`),
    onSuccess: () => {
      toast.success("تم إقفال السنة المالية");
      queryClient.invalidateQueries({ queryKey: ["fiscal-years"] });
      queryClient.invalidateQueries({ queryKey: ["periods"] });
    },
    onError: () => toast.error("فشل الإقفال"),
  });

  const createPeriod = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/fiscal/periods", payload),
    onSuccess: () => {
      toast.success("تم إنشاء الفترة");
      queryClient.invalidateQueries({ queryKey: ["periods"] });
      setShowPeriodForm(false);
      setPeriodName("");
      setPeriodFrom("");
      setPeriodTo("");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل إنشاء الفترة");
    },
  });

  const submitPeriod = (e: FormEvent) => {
    e.preventDefault();
    const yearId = selectedYear || years[0]?.id;
    if (!yearId) {
      toast.error("أنشئ سنة مالية أولاً");
      return;
    }
    createPeriod.mutate({
      fiscal_year_id: yearId,
      name: periodName,
      start_date: periodFrom,
      end_date: periodTo,
    });
  };

  const currentYear = years.find((y) => y.id === selectedYear) || years[0];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">السنوات والفترات المالية</h1>
        <p className="text-ink-muted text-sm mt-1">
          إدارة السنوات المالية وإقفال الفترات لمنع الترحيل في الماضي
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* قائمة السنوات */}
        <div className="card">
          <div className="p-4 border-b border-line">
            <h2 className="font-bold text-ink">السنوات المالية</h2>
          </div>
          <div className="p-3 space-y-2">
            {yearsLoading ? (
              <p className="text-ink-muted text-sm p-4">جاري التحميل...</p>
            ) : years.length === 0 ? (
              <p className="text-ink-muted text-sm p-4">لا توجد سنوات بعد</p>
            ) : (
              years.map((y) => (
                <button
                  key={y.id}
                  onClick={() => setSelectedYear(y.id)}
                  className={`w-full text-right p-3 rounded-lg border transition-colors ${
                    (selectedYear || years[0]?.id) === y.id
                      ? "border-accent bg-accent-soft/30"
                      : "border-line hover:bg-line-soft"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink">{y.name}</span>
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs ${y.is_closed ? "bg-danger-soft text-danger" : "bg-success-soft text-success"}`}>
                      {y.is_closed ? "مقفلة" : "مفتوحة"}
                    </span>
                  </div>
                  <p className="text-xs text-ink-muted mt-1 tabular" dir="ltr">
                    {y.start_date} ← {y.end_date}
                  </p>
                </button>
              ))
            )}
          </div>
          {currentYear && !currentYear.is_closed && (
            <div className="p-3 border-t border-line">
              <button
                onClick={() => closeYear.mutate(currentYear.id)}
                className="btn-danger w-full text-sm"
                disabled={closeYear.isPending}
              >
                <Lock className="w-4 h-4" />
                إقفال السنة {currentYear.name}
              </button>
            </div>
          )}
        </div>

        {/* الفترات */}
        <div className="card lg:col-span-2">
          <div className="p-4 border-b border-line flex items-center gap-2 flex-wrap">
            <Calendar className="w-4 h-4 text-ink-muted" />
            <h2 className="font-bold text-ink">
              فترات {currentYear?.name || ""}
            </h2>
            {currentYear && !currentYear.is_closed && (
              <button
                onClick={() => setShowPeriodForm(!showPeriodForm)}
                className="btn-secondary mr-auto text-sm"
              >
                {showPeriodForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                {showPeriodForm ? "إلغاء" : "فترة جديدة"}
              </button>
            )}
          </div>

          {showPeriodForm && currentYear && (
            <form onSubmit={submitPeriod} className="p-4 border-b border-line bg-line-soft/40 grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
              <div>
                <label className="label" htmlFor="p-name">اسم الفترة</label>
                <input id="p-name" className="input" value={periodName}
                  onChange={(e) => setPeriodName(e.target.value)} required
                  placeholder="مثال: يناير 2026" />
              </div>
              <div>
                <label className="label" htmlFor="p-from">من</label>
                <input id="p-from" type="date" className="input" value={periodFrom}
                  onChange={(e) => setPeriodFrom(e.target.value)} required
                  min={currentYear.start_date} max={currentYear.end_date} />
              </div>
              <div>
                <label className="label" htmlFor="p-to">إلى</label>
                <input id="p-to" type="date" className="input" value={periodTo}
                  onChange={(e) => setPeriodTo(e.target.value)} required
                  min={currentYear.start_date} max={currentYear.end_date} />
              </div>
              <button type="submit" className="btn-primary" disabled={createPeriod.isPending}>
                {createPeriod.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                إنشاء الفترة
              </button>
            </form>
          )}

          {periods.length === 0 ? (
            <div className="p-12 text-center text-ink-muted">لا توجد فترات</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-line-soft border-b border-line">
                  <tr className="text-right text-xs font-medium text-ink-muted">
                    <th className="px-4 py-2.5">الفترة</th>
                    <th className="px-4 py-2.5">من</th>
                    <th className="px-4 py-2.5">إلى</th>
                    <th className="px-4 py-2.5">الحالة</th>
                    <th className="px-4 py-2.5"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-soft">
                  {periods.map((p) => (
                    <tr key={p.id} className="hover:bg-line-soft text-sm">
                      <td className="px-4 py-2.5 font-medium">{p.name}</td>
                      <td className="px-4 py-2.5 tabular" dir="ltr">{p.start_date}</td>
                      <td className="px-4 py-2.5 tabular" dir="ltr">{p.end_date}</td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${p.is_closed ? "bg-danger-soft text-danger" : "bg-success-soft text-success"}`}>
                          {p.is_closed ? "مقفلة" : "مفتوحة"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        {p.is_closed ? (
                          <button
                            onClick={() => reopenPeriod.mutate(p.id)}
                            className="text-xs text-accent font-medium hover:underline flex items-center gap-1"
                            disabled={reopenPeriod.isPending}
                          >
                            <Unlock className="w-3.5 h-3.5" />
                            إعادة فتح
                          </button>
                        ) : (
                          <button
                            onClick={() => closePeriod.mutate(p.id)}
                            className="text-xs text-danger font-medium hover:underline flex items-center gap-1"
                            disabled={closePeriod.isPending}
                          >
                            <Lock className="w-3.5 h-3.5" />
                            إقفال
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card p-4 bg-warning-soft/30 border-warning/20">
        <p className="text-sm text-ink-soft">
          <strong>ملاحظة:</strong> لا يمكن ترحيل أي قيد بتاريخ يقع في فترة مقفلة.
          إعادة الفتح تتطلب صلاحية إدارية وتُسجَّل في سجل التدقيق.
        </p>
      </div>
    </div>
  );
}
