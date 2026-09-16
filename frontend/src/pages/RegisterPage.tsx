import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, CheckCircle2 } from "lucide-react";

import { useAuth } from "../contexts/AuthContext";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordChecks = [
    { ok: password.length >= 10, label: "10 أحرف على الأقل" },
    { ok: /[A-Z]/.test(password), label: "حرف كبير" },
    { ok: /[a-z]/.test(password), label: "حرف صغير" },
    { ok: /[0-9]/.test(password), label: "رقم" },
    { ok: /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password), label: "رمز خاص" },
  ];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      toast.error("كلمتا المرور غير متطابقتين");
      return;
    }
    if (!passwordChecks.every((c) => c.ok)) {
      toast.error("كلمة المرور لا تستوفي متطلبات القوة");
      return;
    }

    setLoading(true);
    try {
      await register({ full_name: fullName, email, username, password });
      toast.success("تم إنشاء الحساب بنجاح. سجّل الدخول الآن");
      navigate("/login");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "فشل التسجيل");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent-soft mb-4">
            <span className="text-3xl">🌉</span>
          </div>
          <h1 className="text-2xl font-bold text-ink">إنشاء حساب جديد</h1>
          <p className="text-ink-muted mt-2">الجسر المصري للإعلام والتنمية</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-8 space-y-4">
          <div>
            <label className="label" htmlFor="fullName">
              الاسم الكامل
            </label>
            <input
              id="fullName"
              className="input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              minLength={3}
            />
          </div>

          <div>
            <label className="label" htmlFor="email">
              البريد الإلكتروني
            </label>
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              dir="ltr"
            />
          </div>

          <div>
            <label className="label" htmlFor="username">
              اسم المستخدم
            </label>
            <input
              id="username"
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={4}
              dir="ltr"
            />
          </div>

          <div>
            <label className="label" htmlFor="password">
              كلمة المرور
            </label>
            <input
              id="password"
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              dir="ltr"
            />
            <ul className="mt-2 space-y-1">
              {passwordChecks.map((c) => (
                <li
                  key={c.label}
                  className={`text-xs flex items-center gap-1.5 ${
                    c.ok ? "text-success" : "text-ink-muted"
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {c.label}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <label className="label" htmlFor="confirm">
              تأكيد كلمة المرور
            </label>
            <input
              id="confirm"
              type="password"
              className="input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              dir="ltr"
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {loading ? "جاري الإنشاء..." : "إنشاء الحساب"}
          </button>

          <p className="text-sm text-center text-ink-muted">
            لديك حساب؟{" "}
            <Link to="/login" className="text-accent font-medium hover:underline">
              تسجيل الدخول
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
