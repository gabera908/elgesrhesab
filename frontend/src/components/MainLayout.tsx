import { ReactNode, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  BookOpen,
  FileText,
  LayoutDashboard,
  LogOut,
  Settings,
  TreePine,
  Users,
  FileSpreadsheet,
  TrendingUp,
  TrendingDown,
  Scale,
  Calendar,
  BarChart3,
} from "lucide-react";

import { useAuth } from "../contexts/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  children?: NavItem[];
}

const navItems: NavItem[] = [
  { to: "/", label: "الرئيسية", icon: <LayoutDashboard className="w-4 h-4" /> },
  { to: "/accounts", label: "شجرة الحسابات", icon: <TreePine className="w-4 h-4" /> },
  { to: "/entries", label: "القيود اليومية", icon: <BookOpen className="w-4 h-4" /> },
  { to: "/partners", label: "الشركاء", icon: <Users className="w-4 h-4" /> },
  { to: "/fiscal", label: "السنوات والفترات", icon: <Calendar className="w-4 h-4" /> },
  {
    to: "/reports",
    label: "التقارير",
    icon: <FileText className="w-4 h-4" />,
    children: [
      { to: "/reports/income-statement", label: "قائمة الدخل", icon: <TrendingUp className="w-3.5 h-3.5" /> },
      { to: "/reports/cash-flow", label: "التدفقات النقدية", icon: <TrendingDown className="w-3.5 h-3.5" /> },
      { to: "/reports/american-journal", label: "اليومية الأمريكية", icon: <FileSpreadsheet className="w-3.5 h-3.5" /> },
      { to: "/reports", label: "ميزان المراجعة", icon: <Scale className="w-3.5 h-3.5" /> },
      { to: "/reports/extra", label: "تقارير إضافية", icon: <BarChart3 className="w-3.5 h-3.5" /> },
    ],
  },
  { to: "/settings", label: "الإعدادات", icon: <Settings className="w-4 h-4" /> },
];

function NavItemComponent({ item, level = 0 }: { item: NavItem; level?: number }) {
  const [open, setOpen] = useState<boolean>(Boolean(level === 0 && item.children?.length));

  if (item.children && item.children.length > 0) {
    return (
      <div>
        <NavLink
          to={item.to}
          className={({ isActive }) =>
            `flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? "bg-accent-soft text-accent-dark"
                : "text-ink-soft hover:bg-line-soft"
            }`
          }
          onClick={(e) => {
            e.preventDefault();
            setOpen(!open);
          }}
        >
          <span className="flex items-center gap-3">
            {item.icon}
            {item.label}
          </span>
          {item.children && (
            <span className={`transition-transform ${open ? "rotate-90" : ""}`}>
              ▸
            </span>
          )}
        </NavLink>
        {open && (
          <div className="mt-1 ml-2 border-r border-line-soft pl-2 space-y-0.5">
            {item.children.map((child) => (
              <NavLink
                key={child.to}
                to={child.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-2 py-2 rounded text-sm transition-colors ${
                    isActive
                      ? "bg-accent-soft/50 text-accent-dark"
                      : "text-ink-muted hover:bg-line-soft"
                  }`
                }
              >
                {child.icon}
                {child.label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
<NavLink
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-accent-soft text-accent-dark"
            : "text-ink-soft hover:bg-line-soft"
        }`
      }
    >
      {item.icon}
      {item.label}
    </NavLink>
  );
}

export default function MainLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed top-0 right-0 bottom-0 w-64 bg-surface border-l border-line">
        <div className="p-5 border-b border-line">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-soft flex items-center justify-center">
              <span className="text-xl">🌉</span>
            </div>
            <div>
              <p className="font-bold text-sm text-ink">الجسر المصري</p>
              <p className="text-xs text-ink-muted">للإعلام والتنمية</p>
            </div>
          </div>
        </div>

        <nav className="p-3 space-y-1">
          {navItems.map((item) => (
            <NavItemComponent key={item.to} item={item} />
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-line">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-9 h-9 rounded-full bg-accent-soft flex items-center justify-center">
              <Users className="w-4 h-4 text-accent-dark" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ink truncate">{user?.full_name}</p>
              <p className="text-xs text-ink-muted truncate">{user?.role || "—"}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-ink-muted hover:text-danger transition-colors"
              title="تسجيل الخروج"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      <main className="mr-64 p-8">{children}</main>
    </div>
  );
}