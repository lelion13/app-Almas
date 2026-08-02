import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export default function AppShell() {
  const { me, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const isAdmin = me?.role === "admin";
  const isInstructor = me?.role === "instructor";
  const isAlumno = me?.role === "alumno";

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `block rounded-lg px-3 py-2 text-sm font-medium ${
      isActive ? "bg-brand-100 text-brand-900" : "text-slate-700 hover:bg-slate-100"
    }`;

  return (
    <div className="min-h-dvh flex flex-col md:flex-row">
      <header className="border-b border-slate-200 bg-white md:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="font-semibold text-brand-900">Almas</span>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
          >
            Menú
          </button>
        </div>
        {open && (
          <nav className="border-t border-slate-100 px-2 pb-3 flex flex-col gap-1">
            {!isAlumno && !isInstructor && <NavLink to="/" className={linkCls} onClick={() => setOpen(false)} end>
              Cierres
            </NavLink>}
            {isAdmin && (
              <NavLink to="/teachers" className={linkCls} onClick={() => setOpen(false)}>
                Profesoras
              </NavLink>
            )}
            {isAdmin && (
              <NavLink to="/conciliacion" className={linkCls} onClick={() => setOpen(false)}>
                Conciliación
              </NavLink>
            )}
            {isAdmin && <NavLink to="/studio" className={linkCls} onClick={() => setOpen(false)}>Estudio</NavLink>}
            {isInstructor && <NavLink to="/instructor" className={linkCls} onClick={() => setOpen(false)}>Mi agenda</NavLink>}
            {isAlumno && <NavLink to="/mis-clases" className={linkCls} onClick={() => setOpen(false)}>Mis clases</NavLink>}
            <button
              type="button"
              className="text-left rounded-lg px-3 py-2 text-sm text-red-700 hover:bg-red-50"
              onClick={() => {
                logout();
                setOpen(false);
              }}
            >
              Salir
            </button>
          </nav>
        )}
      </header>

      <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
        <Link to="/" className="mb-6 text-lg font-semibold text-brand-900">
          Almas
        </Link>
        <nav className="flex flex-col gap-1">
          {!isAlumno && !isInstructor && <NavLink to="/" className={linkCls} end>Cierres</NavLink>}
          {isAdmin && <NavLink to="/teachers" className={linkCls}>Profesoras</NavLink>}
          {isAdmin && <NavLink to="/conciliacion" className={linkCls}>Conciliación</NavLink>}
          {isAdmin && <NavLink to="/studio" className={linkCls}>Estudio</NavLink>}
          {isInstructor && <NavLink to="/instructor" className={linkCls}>Mi agenda</NavLink>}
          {isAlumno && <NavLink to="/mis-clases" className={linkCls}>Mis clases</NavLink>}
        </nav>
        <div className="mt-auto pt-6 text-xs text-slate-500 truncate">{me?.email}</div>
        <button
          type="button"
          className="mt-2 rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
          onClick={() => logout()}
        >
          Salir
        </button>
      </aside>

      <main className="flex-1 p-4 md:p-8 max-w-6xl w-full mx-auto">
        <Outlet />
      </main>
    </div>
  );
}
