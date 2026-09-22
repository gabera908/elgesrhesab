import { FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";
import { Database, Save, AlertTriangle, Download, UserPlus } from "lucide-react";

import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";

interface BackupFile {
  filename: string;
  size: number;
  modified: string;
}

interface Role {
  id: string;
  name: string;
  description: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [companyName, setCompanyName] = useState("الجسر المصري للإعلام والتنمية");
  const [taxId, setTaxId] = useState("");
  const [phone, setPhone] = useState("");
  const [resetText, setResetText] = useState("");
  const [loading, setLoading] = useState(false);
  const [backups, setBackups] = useState<BackupFile[]>([]);

  // إنشاء حساب جديد (بديل التسجيل العام)
  const [roles, setRoles] = useState<Role[]>([]);
  const [newFullName, setNewFullName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRoleId, setNewRoleId] = useState("");
  const [creatingUser, setCreatingUser] = useState(false);

  const isAuthorized = user?.is_superuser || user?.role === "admin" || user?.role === "accountant";

  const fetchBackups = async () => {
    try {
      const { data } = await api.get("/settings/backups");
      setBackups(data);
    } catch {
      /* تجاهل — لا يمنع عرض الصفحة */
    }
  };

  const fetchRoles = async () => {
    try {
      const { data } = await api.get("/users-admin/roles");
      setRoles(data);
      if (data.length > 0) setNewRoleId((prev) => prev || data[0].id);
    } catch {
      /* تجاهل */
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchBackups();
      fetchRoles();
    }
  }, [isAuthorized]);

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
      const { data } = await api.post("/settings/backup");
      toast.success(`تم إنشاء نسخة احتياطية مشفَّرة (${data.filename})`);
      await fetchBackups();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل النسخ الاحتياطي");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBackup = async (filename: string) => {
    try {
      const res = await api.get(`/settings/backups/download/${filename}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error("فشل تحميل النسخة");
    }
  };

  const handleCreateUser = async (e: FormEvent) => {
    e.preventDefault();
    if (!newRoleId) {
      toast.error("اختر دور المستخدم");
      return;
    }
    setCreatingUser(true);
    try {
      await api.post("/users-admin/users", {
        full_name: newFullName,
        email: newEmail,
        username: newUsername,
        password: newPassword,
        role_id: newRoleId,
        permissions: [],
      });
      toast.success("تم إنشاء الحساب الجديد");
      setNewFullName("");
      setNewEmail("");
      setNewUsername("");
      setNewPassword("");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل إنشاء الحساب");
    } finally {
      setCreatingUser(false);
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
        {backups.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-line-soft border-b border-line">
                <tr className="text-right text-xs text-ink-muted">
                  <th className="px-3 py-2">الملف</th>
                  <th className="px-3 py-2">التاريخ</th>
                  <th className="px-3 py-2">الحجم</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {backups.map((b) => (
                  <tr key={b.filename}>
                    <td className="px-3 py-2 font-mono" dir="ltr">{b.filename}</td>
                    <td className="px-3 py-2 tabular">{b.modified}</td>
                    <td className="px-3 py-2 tabular">{(b.size / 1024).toFixed(1)} KB</td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => handleDownloadBackup(b.filename)}
                        className="p-1.5 rounded hover:bg-line-soft text-ink-muted"
                        title="تحميل"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* إنشاء حساب جديد */}
      <form onSubmit={handleCreateUser} className="card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <UserPlus className="w-5 h-5 text-accent-dark" />
          <h2 className="font-bold text-ink">إنشاء حساب جديد</h2>
        </div>
        <p className="text-sm text-ink-muted">
          إنشاء حساب مستخدم من داخل الإعدادات (بدل التسجيل من شاشة الدخول).
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="newFullName">الاسم الكامل</label>
            <input id="newFullName" className="input" value={newFullName}
              onChange={(e) => setNewFullName(e.target.value)} required minLength={3} />
          </div>
          <div>
            <label className="label" htmlFor="newEmail">البريد الإلكتروني</label>
            <input id="newEmail" type="email" className="input" value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)} required dir="ltr" />
          </div>
          <div>
            <label className="label" htmlFor="newUsername">اسم المستخدم</label>
            <input id="newUsername" className="input" value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)} required minLength={4} dir="ltr" />
          </div>
          <div>
            <label className="label" htmlFor="newPassword">كلمة المرور (10 أحرف + كبير/صغير/رقم/رمز)</label>
            <input id="newPassword" type="password" className="input" value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)} required minLength={10} dir="ltr" />
          </div>
          <div>
            <label className="label" htmlFor="newRole">الدور</label>
            <select id="newRole" className="input" value={newRoleId}
              onChange={(e) => setNewRoleId(e.target.value)} required>
              <option value="">— اختر الدور —</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>{r.name} — {r.description}</option>
              ))}
            </select>
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={creatingUser}>
          <UserPlus className="w-4 h-4" />
          {creatingUser ? "جاري الإنشاء..." : "إنشاء الحساب"}
        </button>
      </form>

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
