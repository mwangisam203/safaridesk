import { useState } from "react";
import { BookOpen, CircleUserRound, FilePenLine, Menu, Search, X } from "lucide-react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthDialog } from "./AuthDialog";
import { NotificationBell } from "./NotificationBell";
import { TierBadge } from "./TierBadge";

export function AppShell({ children }) {
  const { user, logout } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  function openAuth(mode) {
    setAuthMode(mode);
    setAuthOpen(true);
    setMobileOpen(false);
  }

  function submitSearch(event) {
    event.preventDefault();
    const query = search.trim();
    navigate(query ? `/?q=${encodeURIComponent(query)}` : "/");
    setMobileOpen(false);
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-paper/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-5 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex shrink-0 items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-green-600 text-white">
              <BookOpen size={20} strokeWidth={2.2} />
            </span>
            <span className="font-display text-2xl font-semibold text-ink">SafariDesk</span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            <NavItem to="/">Library</NavItem>
            <NavItem to="/plans">Plans</NavItem>
            {user && <NavItem to="/account">Account</NavItem>}
            {user?.is_admin && <NavItem to="/admin/articles">Articles</NavItem>}
            {user?.is_admin && <NavItem to="/admin/users">Users</NavItem>}
          </nav>

          <form
            onSubmit={submitSearch}
            className="ml-auto hidden h-10 min-w-0 max-w-sm flex-1 items-center rounded-md border border-neutral-300 bg-white px-3 lg:flex"
          >
            <Search size={17} className="shrink-0 text-neutral-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search the library"
              className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none"
            />
          </form>

          <div className="hidden items-center gap-2 md:flex">
            {user ? (
              <>
                <NotificationBell />
                <Link
                  to="/account"
                  className="flex h-10 items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 text-sm font-semibold text-ink"
                >
                  <CircleUserRound size={18} />
                  <span className="max-w-28 truncate">{user.full_name.split(" ")[0]}</span>
                  <TierBadge tier={user.subscription_tier} compact />
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  className="h-10 px-2 text-sm font-semibold text-neutral-500 hover:text-ink"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => openAuth("login")}
                  className="h-10 px-3 text-sm font-semibold text-ink"
                >
                  Sign in
                </button>
                <button
                  type="button"
                  onClick={() => openAuth("register")}
                  className="h-10 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-green-700"
                >
                  Join free
                </button>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={() => setMobileOpen((value) => !value)}
            className="ml-auto grid h-10 w-10 place-items-center rounded-md border border-neutral-300 bg-white md:hidden"
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {mobileOpen && (
          <div className="border-t border-neutral-200 bg-paper px-4 py-4 md:hidden">
            <form onSubmit={submitSearch} className="flex h-11 items-center rounded-md border border-neutral-300 bg-white px-3">
              <Search size={17} className="text-neutral-400" />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search the library"
                className="min-w-0 flex-1 bg-transparent px-2 text-sm outline-none"
              />
            </form>
            <nav className="mt-3 grid gap-1">
              <MobileLink to="/" onClick={() => setMobileOpen(false)}>Library</MobileLink>
              <MobileLink to="/plans" onClick={() => setMobileOpen(false)}>Plans</MobileLink>
              {user && <MobileLink to="/account" onClick={() => setMobileOpen(false)}>Account</MobileLink>}
              {user?.is_admin && (
                <MobileLink to="/admin/articles" onClick={() => setMobileOpen(false)}>
                  <span className="inline-flex items-center gap-2"><FilePenLine size={17} />Articles</span>
                </MobileLink>
              )}
              {user?.is_admin && (
                <MobileLink to="/admin/users" onClick={() => setMobileOpen(false)}>
                  Users
                </MobileLink>
              )}
            </nav>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {user ? (
                <>
                  <NotificationBell compact />
                  <button type="button" onClick={logout} className="h-11 rounded-md border border-neutral-300 bg-white font-semibold">
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <button type="button" onClick={() => openAuth("login")} className="h-11 rounded-md border border-neutral-300 bg-white font-semibold">
                    Sign in
                  </button>
                  <button type="button" onClick={() => openAuth("register")} className="h-11 rounded-md bg-ink font-semibold text-white">
                    Join free
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      <main key={location.pathname}>{children}</main>

      <footer className="border-t border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-7 text-sm text-neutral-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p>SafariDesk. Practical backend knowledge, built in Nairobi.</p>
          <nav className="flex flex-wrap gap-x-4 gap-y-2">
            <FooterLink to="/terms">Terms</FooterLink>
            <FooterLink to="/privacy">Privacy</FooterLink>
            <FooterLink to="/contact">Contact</FooterLink>
          </nav>
        </div>
      </footer>

      <AuthDialog
        open={authOpen}
        mode={authMode}
        onClose={() => setAuthOpen(false)}
      />
    </div>
  );
}

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        `rounded-md px-3 py-2 text-sm font-semibold ${
          isActive ? "bg-green-50 text-green-700" : "text-neutral-600 hover:text-ink"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

function MobileLink({ to, onClick, children }) {
  return (
    <Link to={to} onClick={onClick} className="rounded-md px-3 py-2.5 font-semibold text-ink hover:bg-white">
      {children}
    </Link>
  );
}

function FooterLink({ to, children }) {
  return (
    <Link to={to} className="font-semibold hover:text-ink">
      {children}
    </Link>
  );
}
