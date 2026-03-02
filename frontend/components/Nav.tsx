"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const path = usePathname();

  // Extract library slug from path if we're in a library context
  const libraryMatch = path.match(/^\/library\/([^/]+)/);
  const librarySlug = libraryMatch?.[1];

  const isActive = (href: string) =>
    href === "/" ? path === "/" : path === href || path.startsWith(href + "/");

  return (
    <header
      className="border-b px-6 flex items-center gap-0 h-14"
      style={{
        borderColor: "var(--border)",
        background: "var(--surface)",
        position: "sticky",
        top: 0,
        zIndex: 40,
        backdropFilter: "blur(8px)",
      }}
    >
      {/* Brand */}
      <Link
        href="/"
        className="font-semibold text-base tracking-tight mr-6 shrink-0"
        style={{ color: "var(--accent)" }}
      >
        Library
      </Link>

      {/* Breadcrumb / nav */}
      <nav className="flex items-stretch h-full text-sm gap-1">
        <Link
          href="/"
          className="flex items-center px-3 h-full relative transition-colors"
          style={{ color: !librarySlug && path === "/" ? "var(--text)" : "var(--muted)" }}
        >
          Libraries
          {!librarySlug && path === "/" && (
            <span
              className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t"
              style={{ background: "var(--accent)" }}
            />
          )}
        </Link>

        {librarySlug && (
          <>
            <span className="flex items-center" style={{ color: "var(--muted-2)" }}>
              /
            </span>
            <Link
              href={`/library/${librarySlug}`}
              className="flex items-center px-3 h-full relative transition-colors"
              style={{
                color: path === `/library/${librarySlug}` ? "var(--text)" : "var(--muted)",
              }}
            >
              {librarySlug}
              {path === `/library/${librarySlug}` && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </Link>
            <Link
              href={`/library/${librarySlug}/chat`}
              className="flex items-center px-3 h-full relative transition-colors"
              style={{
                color: isActive(`/library/${librarySlug}/chat`) ? "var(--text)" : "var(--muted)",
              }}
            >
              Chat
              {isActive(`/library/${librarySlug}/chat`) && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </Link>
            <Link
              href={`/library/${librarySlug}/upload`}
              className="flex items-center px-3 h-full relative transition-colors"
              style={{
                color: isActive(`/library/${librarySlug}/upload`) ? "var(--text)" : "var(--muted)",
              }}
            >
              Upload
              {isActive(`/library/${librarySlug}/upload`) && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t"
                  style={{ background: "var(--accent)" }}
                />
              )}
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
