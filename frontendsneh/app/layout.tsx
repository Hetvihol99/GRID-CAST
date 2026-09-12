import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Grid Cast — Renewable Intelligence & Forecasting",
  description:
    "AI Solution for solar and wind generation forecasting with grid decision support and BESS dispatch modeling.",
};

export const viewport: Viewport = {
  themeColor: "#4CAF4F",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-display bg-[#F5F7FA] text-dark antialiased`}>
        {children}
      </body>
    </html>
  );
}

