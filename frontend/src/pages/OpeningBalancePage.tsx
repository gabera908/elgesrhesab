import { FormEvent, useState, useEffect } from "react";
import { toast } from "sonner";
import { Loader2, Wallet, AlertCircle } from "lucide-react";

import api from "../api/client";

interface Fund {
  id: string;
  code: string;
  name: string;
  level: number;
}

interface Journal {
  id: string;
  code: string;
  name: string;
  journal_type: string;
}

export default function OpeningBalancePage() {
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));
  const [bankJournalId, setBankJournalId] = useState("");
  const [cashJournalId, setCashJournalId] = useState("");
  const [offsetAccountId, setOffsetAccountId] = useState("");
  const [funds, setFunds] = useState<Array<{ account_id: string; balance: string }>>([]);
  const [availableFunds, setAvailableFunds] = useState<Fund[]>([]);
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const loadData = async () => {
    const [fundsRes, journalsRes] = await Promise.all([
      api.get("/settings/opening-balance/funds"),
      api.get("/journals"),
    ]);
    setAvailableFunds(fundsRes.data);
    setJournals(journalsRes.data);
    const cashJ = journalsRes.data.find((j: Journal) => j.journal_type === "cash");
    const bankJ = journalsRes.data.find((j: Journal) => j.journal_type === "bank");
    if (cashJ) setCashJournalId(cashJ.id);
    if (bankJ) setBankJournalId(bankJ.id);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!funds.length) {
      toast.error("أضف رصيداً واحداً على الأقل");
      return;
    }
    setLoading(true);
    try {
      await api.post("/settings/opening-balance", {
        as_of_date: asOfDate,
        bank_journal_id: bankJournalId || null,
        cash_journal_id: cashJournalId || null,
        offset_account_id: offsetAccountId,
        funds: funds.map((f) => ({
          account_id: f.account_id,
          balance: f.balance,
        })),
      });
      toast.success("تم إنشاء قيد الرصيد الافتتاحي");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      setFunds([]);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل إنشاء القيد");
    } finally {
      setLoading(false);
    }
  };

  const addFund = () => {
    setFunds([...funds, { account_id: "", balance: "" }]);
  };

  const removeFund = (idx: number) => {
    setFunds(funds.filter((_, i) => i !== idx));
  };

  const updateFund = (idx: number, field: "account_id" | "balance", value: string) => {
    setFunds(funds.map((f, i) => (i === idx ? { ...f, [field]: value } : f)));
  };

  // تهيئة البيانات
  // Note: في بيئة حقيقية استخدم useEffect، لكن هنا نبسط

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">الرصيد الافتتاحي للبنوك والصناديق</h1>
        <p className="text-ink-muted text-sm mt-1">
          يسجل أرصدة الصناديق والحسابات البنكية كقيد افتتاحي (مدين الأصول / دائن رأس المال)
        </p>
      </div>

      {success && (
        <div className="bg-success-soft border border-success text-success p-3 rounded-lg animate-fade-in">
          تم إنشاء قيد الرصيد الافتتاحي بنجاح ✓
        </div>
      )}

      <form onSubmit={handleSubmit} className="card p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label" htmlFor="asOfDate">
              تاريخ الرصيد
            </label>
            <input
              id="asOfDate"
              type="date"
              className="input"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="bankJournal">
              الدفتر البنكي
            </label>
            <select
              id="bankJournal"
              className="input"
              value={bankJournalId}
              onChange={(e) => setBankJournalId(e.target.value)}
            >
              <option value="">— اختر —</option>
              {journals
                .filter((j) => j.journal_type === "bank")
                .map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.code} — {j.name}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="cashJournal">
              الدفتر النقدي
            </label>
            <select
              id="cashJournal"
              className="input"
              value={cashJournalId}
              onChange={(e) => setCashJournalId(e.target.value)}
            >
              <option value="">— اختر —</option>
              {journals
                .filter((j) => j.journal_type === "cash")
                .map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.code} — {j.name}
                  </option>
                ))}
            </select>
          </div>
        </div>

        <div>
          <label className="label" htmlFor="offsetAccount">
            حساب المقابل (رأس المال / أرباح مرحَّلة) <span className="text-danger">*</span>
          </label>
          <select
            id="offsetAccount"
            className="input"
            value={offsetAccountId}
            onChange={(e) => setOffsetAccountId(e.target.value)}
            required
          >
            <option value="">— اختر حساب مقابل —</option>
            {availableFunds
              .filter((a) => a.code.startsWith("3.")) // حقوق الملكية
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.code} — {a.name}
                </option>
              ))}
          </select>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-ink">الأرصدة</h3>
            <button type="button" onClick={addFund} className="btn-secondary text-sm">
              <Wallet className="w-3.5 h-3.5" />
              إضافة رصيد
            </button>
          </div>

          {funds.length === 0 ? (
            <div className="p-6 text-center border-2 border-dashed border-line rounded-lg">
              <AlertCircle className="w-10 h-10 mx-auto text-line mb-2" />
              <p className="text-ink-muted">لا توجد أرصدة مضافة بعد</p>
            </div>
          ) : (
            <div className="space-y-2">
              {funds.map((fund, idx) => (
                <div key={idx} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                  <div>
                    <label className="label">الحساب</label>
                    <select
                      className="input"
                      value={fund.account_id}
                      onChange={(e) => updateFund(idx, "account_id", e.target.value)}
                      required
                    >
                      <option value="">— اختر الصندوق/البنك —</option>
                      {availableFunds.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.code} — {a.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label">الرصيد (EGP)</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      className="input tabular text-left"
                      value={fund.balance}
                      onChange={(e) => updateFund(idx, "balance", e.target.value)}
                      required
                      dir="ltr"
                    />
                  </div>
                  <div className="md:col-span-1">
                    <button
                      type="button"
                      onClick={() => removeFund(idx)}
                      className="btn-danger w-full"
                    >
                      إزالة
                    </button>
                  </div>
                </div>
              ))}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="md:col-span-3" />
                <div className="bg-line-soft p-3 rounded-lg text-right">
                  <span className="font-bold tabular text-ink" dir="ltr">
                    إجمالي:{" "}
                    {funds.reduce((s, f) => s + (Number(f.balance) || 0), 0).toFixed(2)}
                  </span>
                  <span className="text-sm text-ink-muted ml-2">EGP</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "إنشاء قيد الرصيد الافتتاحي"}
        </button>
      </form>
    </div>
  );
}