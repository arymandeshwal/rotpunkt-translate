import { NavLink, Outlet } from "react-router";

import { HealthBadge } from "./HealthBadge";

const navItems = [
  { to: "/", label: "Projects" },
  { to: "/glossary", label: "Glossary" },
];

export function Layout() {
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
          <div className="ml-auto">
            <HealthBadge />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
