"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const AUTH_URL = "https://auth.herakles.dev";

export default function Nav() {
  const path = usePathname();
  const auth = useAuth();

  const libraryMatch = path.match(/^\/library\/([^/]+)/);
  const librarySlug = libraryMatch?.[1];

  const isExact = (href: string) => path === href;
  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <header
      className="border-b px-5 flex items-center h-12"
      style={{
        borderColor: "var(--border)",
        background: "rgba(12,14,18,0.85)",
        position: "sticky",
        top: 0,
        zIndex: 40,
        backdropFilter: "blur(12px) saturate(1.4)",
      }}
    >
      {/* Brand */}
      <Link
        href="/"
        className="font-semibold text-sm tracking-tight mr-5 shrink-0 flex items-center gap-2"
        style={{ color: "var(--accent)" }}
      >
        <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        Athenaeum
      </Link>

      {/* Separator */}
      <div className="w-px h-4 mr-3" style={{ background: "var(--border)" }} />

      {/* Nav links */}
      <nav aria-label="Main navigation" className="flex items-stretch h-full text-xs gap-0.5 overflow-x-auto scrollbar-none">
        <NavLink href="/" active={!librarySlug && path === "/"}>
          Libraries
        </NavLink>
        <NavLink href="/search" active={isActive("/search")}>
          Search
        </NavLink>
        <NavLink href="/chat" active={!librarySlug && isActive("/chat")}>
          Chat
        </NavLink>

        {librarySlug && (
          <>
            <span className="flex items-center px-1" style={{ color: "var(--muted-2)" }}>/</span>
            <NavLink href={`/library/${librarySlug}`} active={isExact(`/library/${librarySlug}`)}>
              {librarySlug}
            </NavLink>
            <NavLink href={`/library/${librarySlug}/chat`} active={isActive(`/library/${librarySlug}/chat`)}>
              Chat
            </NavLink>
            {auth.authenticated && (
              <>
                <NavLink href={`/library/${librarySlug}/upload`} active={isActive(`/library/${librarySlug}/upload`)}>
                  Upload
                </NavLink>
                <NavLink href={`/library/${librarySlug}/settings`} active={isActive(`/library/${librarySlug}/settings`)}>
                  Settings
                </NavLink>
              </>
            )}
          </>
        )}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User area */}
      <div className="flex items-center gap-2.5 text-xs">
        {auth.authenticated ? (
          <>
            {auth.is_admin && (
              <span
                className="font-medium px-1.5 py-0.5 rounded text-[10px]"
                style={{
                  background: "var(--amber-dim)",
                  color: "var(--amber)",
                  border: "1px solid rgba(251,191,36,0.18)",
                }}
              >
                admin
              </span>
            )}
            <span style={{ color: "var(--muted)" }}>{auth.display_name || auth.username}</span>
            <span className="w-px h-3" style={{ background: "var(--border)" }} />
            <a
              href={`${AUTH_URL}/logout`}
              className="transition-colors hover:underline"
              style={{ color: "var(--muted-2)" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted-2)")}
            >
              Sign out
            </a>
          </>
        ) : (
          <a href={AUTH_URL} className="btn btn-ghost text-xs" style={{ padding: "0.3rem 0.75rem" }}>
            Sign in
          </a>
        )}
      </div>
    </header>
  );
}

function NavLink({ href, active, children }: { href: string; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="flex items-center px-2.5 h-full relative transition-colors"
      style={{ color: active ? "var(--text)" : "var(--muted-2)" }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--muted)"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--muted-2)"; }}
    >
      {children}
      {active && (
        <span
          className="absolute bottom-0 left-2 right-2 h-0.5 rounded-t"
          style={{ background: "var(--accent)" }}
        />
      )}
    </Link>
  );
}
