import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from './providers';
import "./globals.css";
import "@/styles/animations.css";
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PrivNurse AI",
  description: "PrivNurse",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
      <Providers>
        {children}
      </Providers>
      </body>
    </html>
  );
}
