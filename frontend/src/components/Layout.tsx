import { NavLink, Outlet, useNavigate } from "react-router";
import { LogOut } from "lucide-react";
import { HealthBadge } from "./HealthBadge";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "./ui/button";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/", label: "Projects" },
    { to: "/glossary", label: "Glossary" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-8 px-4">
          <span className="flex items-center gap-2 font-semibold">
            <span aria-hidden className="h-3 w-3 rounded-full bg-red-600" />
            Rotpunkt Translate
          </span>
          <nav className="flex gap-1" aria-label="Main">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm ${
                    isActive
                      ? "bg-stone-100 font-medium text-stone-900"
                      : "text-stone-500 hover:text-stone-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <HealthBadge />
            {user && (
              <div className="flex items-center gap-3 border-l border-stone-200 pl-4">
                <span className="text-xs text-muted-foreground hidden sm:inline-block">
                  {user.email} <span className="uppercase text-[10px] bg-stone-100 px-1 py-0.5 rounded ml-1">{user.role}</span>
                </span>
                <Button variant="ghost" size="icon" onClick={handleLogout} title="Log out" className="h-8 w-8 text-stone-500">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
