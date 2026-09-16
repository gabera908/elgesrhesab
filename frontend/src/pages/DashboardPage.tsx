import { FileText, BookOpen, Scale, TrendingUp } from "lucide-react";

import { useAuth } from "../contexts/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();

  const stats = [
    { label: "القيود هذا الشهر", value: "—", icon: <BookOpen className="w-5 h-5" /> },
    { label: "الحسابات النشطة", value: "—", icon: <FileText className="w-5 h-5" /> },
    { label: "توازن الميزانية", value: "✓", icon: <Scale className="w-5 h-5" /> },
    { label: "التقارير المتاحة", value: "4", icon: <TrendingUp className="w-5 h-5" /> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">
          أهلاً، {user?.full_name?.split(" ")[0] || "مستخدم"} 👋
        </h1>
        <p className="text-ink-muted text-sm mt-1">
          لوحة تحكم نظام الحسابات — الجسر المصري للإعلام والتنمية
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="card p-5">
            <div className="w-10 h-10 rounded-lg bg-accent-soft flex items-center justify-center text-accent-dark mb-3">
              {s.icon}
            </div>
            <p className="text-2xl font-bold text-ink tabular">{s.value}</p>
            <p className="text-sm text-ink-muted mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="card p-8 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent-soft mb-4">
          <span className="text-3xl">🌉</span>
        </div>
        <h2 className="font-bold text-ink mb-2">الجسر المصري للإعلام والتنمية</h2>
        <p className="text-sm text-ink-muted max-w-md mx-auto">
          نظام محاسبة مؤسسي متكامل بالقيد المزدوج. ابدأ من شجرة الحسابات، ثم سجّل القيود اليومية،
          وأنشئ التقارير المالية.
        </p>
      </div>
    </div>
  );
}
