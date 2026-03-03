import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Search Across Libraries — Athenaeum",
  description: "Run semantic searches across multiple document libraries with per-library attribution.",
};

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
