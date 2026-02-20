import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "xProject",
  description: "Project memory and audit trail",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen">
          <header className="border-b bg-[hsl(var(--card))] px-6 py-3">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-semibold tracking-tight">
                xProject
              </h1>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                Project Memory
              </span>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
