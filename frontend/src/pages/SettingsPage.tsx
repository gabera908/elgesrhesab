import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Database, Save, AlertTriangle } from "lucide-react";

import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";

export default function SettingsPage() {
  const { user } = useAuth();
  const [companyName, setCompanyName] = useState("الجسر المصري للإعلام والتنمية");
  const [taxId, setTaxId] = useState("");
  const [phone, setPhone] = useState("");
  const [resetText, setResetText] = useState("");
  const [loading, setLoading] = useState(false);

  const isAuthorized = user?.is_superuser || user?.role === "admin" || user?.role === "accountant";

  const handleSaveCompany = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.put("/settings/company", {
        name: companyName,
        tax_id: taxId || null,
        phone: phone || null,
      });
      toast.success("تم حفظ بيانات المؤسسة");
    } catch {
      toast.error("فشل الحفظ");
    } finally {
      setLoading(false);
    }
  };

  const handleBackup = async () => {
    setLoading(true);
    try {
      await api.post("/settings/backup");
      toast.success("تم إنشاء نسخة احتياطية مشفَّرة");
    } catch {
      toast.error("فشل النسخ الاحتياطي");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: FormEvent) => {
    e.preventDefault();
    if (resetText !== "RESET") {
      toast.error("اكتب RESET للتأكيد");
      return;
    }
    setLoading(true);
    try {
      await api.post("/settings/reset", { confirmation: resetText, archive: true });
      toast.success("تم تصفير الحسابات مع الأرشفة");
      setResetText("");
    } catch {
      toast.error("فشل التصفير");
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthorized) {
    return (
      <div className="card p-12 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto text-warning mb-3" />
        <p className="text-ink-muted">ليس لديك صلاحية للوصول إلى الإعدادات</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">الإعدادات</h1>
        <p className="text-ink-muted text-sm mt-1">إعدادات النظام والمؤسسة</p>
      </div>

      {/* بيانات المؤسسة */}
      <form onSubmit={handleSaveCompany} className="card p-6 space-y-4">
        <h2 className="font-bold text-ink">بيانات المؤسسة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="companyName">اسم المؤسسة</label>
            <input
              id="companyName"
              className="input"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="taxId">السجل الضريبي</label>
            <input
              id="taxId"
              className="input tabular"
              value={taxId}
              onChange={(e) => setTaxId(e.target.value)}
              dir="ltr"
            />
          </div>
          <div>
            <label className="label" htmlFor="phone">الهاتف</label>
            <input
              id="phone"
              className="input tabular"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              dir="ltr"
            />
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          <Save className="w-4 h-4" />
          حفظ البيانات
        </button>
      </form>

      {/* النسخ الاحتياطي */}
      <div className="card p-6">
        <h2 className="font-bold text-ink mb-2">النسخ الاحتياطي</h2>
        <p className="text-sm text-ink-muted mb-4">
          إنشاء نسخة احتياطية مشفَّرة (AES-256) من قاعدة البيانات بالكامل.
        </p>
        <button onClick={handleBackup} className="btn-secondary" disabled={loading}>
          <Database className="w-4 h-4" />
          إنشاء نسخة احتياطية الآن
        </button>
      </div>

      {/* تصفير الحسابات */}
      <form onSubmit={handleReset} className="card p-6 space-y-4 border-danger/30">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-danger mt-0.5" />
          <div>
            <h2 className="font-bold text-danger">تصفير الحسابات</h2>
            <p className="text-sm text-ink-muted mt-1">
              عملية خطيرة: تحذف كل القيود والحركات. سيتم أرشفة نسخة قبل التصفير. لا يمكن التراجع.
            </p>
          </div>
        </div>
        <div>
          <label className="label" htmlFor="resetConfirm">
            اكتب <span className="font-mono font-bold text-danger" dir="ltr">RESET</span> للتأكيد
          </label>
          <input
            id="resetConfirm"
            className="input font-mono"
            value={resetText}
            onChange={(e) => setResetText(e.target.value)}
            dir="ltr"
            placeholder="RESET"
          />
        </div>
        <button type="submit" className="btn-danger" disabled={loading || resetText !== "RESET"}>
          تصفير الحسابات
        </button>
      </form>
    </div>
  );
}
