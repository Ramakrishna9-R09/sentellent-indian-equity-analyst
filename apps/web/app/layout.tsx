import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sentellent Equity Analyst",
  description: "Grounded, cited Indian-equity research. Not investment advice."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
