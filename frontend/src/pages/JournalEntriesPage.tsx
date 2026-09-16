import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Plus, Trash2, Upload } from "lucide-react";
import { format } from "date-fns";

import api from "../api/client";

interface JournalEntry {
  id: string;
  entry_number: string;
  entry_date: string;
  reference: string | null;
  narration: string | null;
  state: string;
  amount: number;
}

interface Journal {
  id: string;
  code: string;
  name: string;
}

interface Account {
  id: string;
  code: string;
  name: string;
}

interface Line {
  account_id: string;
  debit: string;
  credit: string;
  name: string;
}

const STATE_LABELS: Record<string, string> = {
  draft: "مسودة",
  in_review: "قيد المراجعة",
  posted: "مرحَّل",
  reversed: "معكوس",
};

const STATE_COLORS: Record<string, string> = {
  draft: "bg-gray-50 text-gray-700",
  in_review: "bg-warning-soft text-warning",
  posted: "bg-success-soft text-success",
  reversed: "bg-danger-soft text-danger",
};

export default function JournalEntriesPage() {
  const queryClient = useQueryClient();

  const [journalId, setJournalId] = useState("");
  const [entryDate, setEntryDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [reference, setReference] = useState("");
  const [narration, setNarration] = useState("");
  const [lines, setLines] = useState<Line[]>([
    { account_id: "", debit: "", credit: "", name: "" },
    { account_id: "", debit: "", credit: "", name: "" },
  ]);

  const { data: journals = [] } = useQuery<Journal[]>({
    queryKey: ["journals"],
    queryFn: async () => (await api.get("/journals")).data,
  });

  const { data: accounts = [] } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: async () => (await api.get("/accounts")).data,
  });

  const { data: entries = [], isLoading } = useQuery<JournalEntry[]>({
    queryKey: ["journal-entries"],
    queryFn: async () => (await api.get("/journal-entries?limit=50")).data,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      api.post("/journal-entries", payload),
    onSuccess: () => {
      toast.success("تم إنشاء القيد");
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
      setLines([
        { account_id: "", debit: "", credit: "", name: "" },
        { account_id: "", debit: "", credit: "", name: "" },
      ]);
      setReference("");
      setNarration("");
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل إنشاء القيد");
    },
  });

  const postMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/journal-entries/${id}/post`),
    onSuccess: () => {
      toast.success("تم ترحيل القيد");
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل الترحيل");
    },
  });

  const submitReviewMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/journal-entries/${id}/submit-review`),
    onSuccess: () => {
      toast.success("تم إرسال القيد للمراجعة");
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
    },
    onError: () => toast.error("فشل الإرسال"),
  });

  const reverseMutation = useMutation({
    mutationFn: async (id: string) => api.post(`/journal-entries/${id}/reverse`),
    onSuccess: () => {
      toast.success("تم عكس القيد");
      queryClient.invalidateQueries({ queryKey: ["journal-entries"] });
    },
    onError: () => toast.error("فشل العكس"),
  });

  const totalDebit = lines.reduce((s, l) => s + (Number(l.debit) || 0), 0);
  const totalCredit = lines.reduce((s, l) => s + (Number(l.credit) || 0), 0);
  const isBalanced = totalDebit === totalCredit && totalDebit > 0;

  const updateLine = (idx: number, field: keyof Line, value: string) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };

  const addLine = () =>
    setLines([...lines, { account_id: "", debit: "", credit: "", name: "" }]);

  const removeLine = (idx: number) =>
    setLines(lines.filter((_, i) => i !== idx));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) {
      toast.error("القيد غير متوازن");
      return;
    }
    createMutation.mutate({
      journal_id: journalId,
      entry_date: entryDate,
      reference: reference || null,
      narration: narration || null,
      lines: lines.map((l) => ({
        account_id: l.account_id,
        debit: Number(l.debit) || 0,
        credit: Number(l.credit) || 0,
        name: l.name || null,
      })),
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">القيود اليومية</h1>
        <p className="text-ink-muted text-sm mt-1">صفحة الإدخال اليومي للقيود المحاسبية</p>
      </div>

      {/* نموذج الإدخال */}
      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="label" htmlFor="journal">
              الدفتر
            </label>
            <select
              id="journal"
              className="input"
              value={journalId}
              onChange={(e) => setJournalId(e.target.value)}
              required
            >
              <option value="">اختر الدفتر</option>
              {journals.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.code} — {j.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="date">
              التاريخ
            </label>
            <input
              id="date"
              type="date"
              className="input"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="ref">
              المرجع
            </label>
            <input
              id="ref"
              className="input"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="رقم المستند..."
            />
          </div>
          <div>
            <label className="label" htmlFor="narr">
              البيان
            </label>
            <input
              id="narr"
              className="input"
              value={narration}
              onChange={(e) => setNarration(e.target.value)}
              placeholder="وصف القيد..."
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-line-soft border-y border-line">
              <tr className="text-right text-xs font-medium text-ink-muted">
                <th className="px-3 py-2">الحساب</th>
                <th className="px-3 py-2">البيان</th>
                <th className="px-3 py-2 w-32">مدين</th>
                <th className="px-3 py-2 w-32">دائن</th>
                <th className="px-3 py-2 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {lines.map((line, idx) => (
                <tr key={idx}>
                  <td className="px-3 py-2">
                    <select
                      className="input"
                      value={line.account_id}
                      onChange={(e) => updateLine(idx, "account_id", e.target.value)}
                      required
                    >
                      <option value="">اختر الحساب</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} — {a.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      className="input"
                      value={line.name}
                      onChange={(e) => updateLine(idx, "name", e.target.value)}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      className="input tabular text-left"
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.debit}
                      onChange={(e) => updateLine(idx, "debit", e.target.value)}
                      dir="ltr"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      className="input tabular text-left"
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.credit}
                      onChange={(e) => updateLine(idx, "credit", e.target.value)}
                      dir="ltr"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      className="p-1.5 text-ink-muted hover:text-danger"
                      disabled={lines.length <= 2}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-line-soft border-y border-line">
              <tr className="text-sm font-bold">
                <td className="px-3 py-2.5" colSpan={2}>
                  الإجمالي
                </td>
                <td className="px-3 py-2.5 tabular text-left" dir="ltr">
                  {totalDebit.toFixed(2)}
                </td>
                <td className="px-3 py-2.5 tabular text-left" dir="ltr">
                  {totalCredit.toFixed(2)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div className="flex items-center justify-between">
          <button type="button" onClick={addLine} className="btn-secondary">
            <Plus className="w-4 h-4" />
            إضافة سطر
          </button>
          <div className="flex items-center gap-4">
            <span
              className={`text-sm font-medium ${
                isBalanced ? "text-success" : "text-danger"
              }`}
            >
              {isBalanced
                ? "✓ القيد متوازن"
                : `الفرق: ${(totalDebit - totalCredit).toFixed(2)}`}
            </span>
            <button
              type="submit"
              className="btn-primary"
              disabled={createMutation.isPending || !isBalanced}
            >
              {createMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              حفظ القيد
            </button>
          </div>
        </div>
      </form>

      {/* قائمة القيود */}
      <div className="card">
        <div className="p-4 border-b border-line">
          <h2 className="font-bold text-ink">آخر القيود</h2>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-ink-muted">جاري التحميل...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-ink-muted">لا توجد قيود بعد</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs font-medium text-ink-muted">
                  <th className="px-4 py-2.5">رقم القيد</th>
                  <th className="px-4 py-2.5">التاريخ</th>
                  <th className="px-4 py-2.5">المرجع</th>
                  <th className="px-4 py-2.5">البيان</th>
                  <th className="px-4 py-2.5">المبلغ</th>
                  <th className="px-4 py-2.5">الحالة</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-line-soft">
                    <td className="px-4 py-2.5 text-sm font-medium tabular" dir="ltr">
                      {entry.entry_number}
                    </td>
                    <td className="px-4 py-2.5 text-sm tabular" dir="ltr">
                      {entry.entry_date}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-ink-muted">
                      {entry.reference || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm">{entry.narration || "—"}</td>
                    <td className="px-4 py-2.5 text-sm tabular" dir="ltr">
                      {Number(entry.amount).toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                          STATE_COLORS[entry.state]
                        }`}
                      >
                        {STATE_LABELS[entry.state] || entry.state}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2">
                        {entry.state === "draft" && (
                          <button
                            onClick={() => submitReviewMutation.mutate(entry.id)}
                            className="text-xs text-warning font-medium hover:underline"
                          >
                            إرسال للمراجعة
                          </button>
                        )}
                        {(entry.state === "draft" || entry.state === "in_review") && (
                          <button
                            onClick={() => postMutation.mutate(entry.id)}
                            className="text-xs text-accent font-medium hover:underline"
                          >
                            ترحيل
                          </button>
                        )}
                        {entry.state === "posted" && (
                          <button
                            onClick={() => reverseMutation.mutate(entry.id)}
                            className="text-xs text-danger font-medium hover:underline"
                          >
                            عكس
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
