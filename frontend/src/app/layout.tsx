import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { ApiHealthBanner } from "@/components/api-health-banner";
import { Navbar } from "@/components/navbar";
import { Footer } from "@/components/footer";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Gapwright · Automated Syllabus-to-Industry Gap Analyzer",
  description:
    "Build the fix for the gap between syllabus and skills using live job-market data and semantic gap analysis.",
  icons: {
    icon: "/growth.png",
    shortcut: "/growth.png",
    apple: "/growth.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/growth.png" type="image/png" sizes="any" />
        <link rel="shortcut icon" href="/growth.png" type="image/png" />
        <link rel="apple-touch-icon" href="/growth.png" />
      </head>
      <body className={`${inter.variable} font-sans antialiased flex flex-col min-h-screen`}>
        <ThemeProvider>
          <ApiHealthBanner />
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
