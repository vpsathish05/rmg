import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "RMG Resource Management",
  description: "JMan Group Resource Management System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex bg-background text-foreground antialiased" style={{ fontFamily: "Arial, sans-serif", color: "#19105B" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
