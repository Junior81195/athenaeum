import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Chat Across Libraries — Athenaeum",
  description: "Ask questions across multiple document libraries with AI-powered answers and source citations.",
};

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
