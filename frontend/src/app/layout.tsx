import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finhaus — Financial Terminal",
  description: "Bloomberg-style financial terminal for the common investor. Portfolio aggregator, real-time news, market data, earnings calendar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
