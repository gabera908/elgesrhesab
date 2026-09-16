import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [twofaRequired, setTwofaRequired] = useState(false);
  const [twofaCode, setTwofaCode] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password, twofaRequired ? twofaCode : undefined);
      toast.success("مرحباً بك، تم تسجيل الدخول بنجاح");
      navigate("/");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "بيانات الاعتماد غير صحيحة";
      if (message === "2FA_REQUIRED") {
        setTwofaRequired(true);
        toast.info("أدخل رمز التحقق الثنائي");
      } else {
        toast.error(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent-soft mb-4">
            <span className="text-3xl">🌉</span>
          </div>
          <h1 className="text-2xl font-bold text-ink">الجسر المصري للإعلام والتنمية</h1>
          <p className="text-ink-muted mt-2">نظام الحسابات — تسجيل الدخول</p>
        </div>

        <form onSubmit={handleSubmit} className="card p-8 space-y-5">
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
              autoComplete="username"
              autoFocus
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
              autoComplete="current-password"
            />
          </div>

          {twofaRequired && (
            <div>
              <label className="label" htmlFor="twofa">
                رمز التحقق الثنائي (6 أرقام)
              </label>
              <input
                id="twofa"
                className="input tabular"
                maxLength={6}
                value={twofaCode}
                onChange={(e) => setTwofaCode(e.target.value.replace(/\D/g, ""))}
                required
                inputMode="numeric"
                autoFocus
              />
            </div>
          )}

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {loading ? "جاري التحقق..." : "تسجيل الدخول"}
          </button>

          <p className="text-sm text-center text-ink-muted">
            ليس لديك حساب؟{" "}
            <Link to="/register" className="text-accent font-medium hover:underline">
              إنشاء حساب
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
