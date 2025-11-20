import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import Script from "next/script";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Bucknell Course Catalog Chatbot",
  description: "AI-powered assistant for Bucknell University course catalog",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <head>
          <Script
            id="extension-blocker"
            strategy="beforeInteractive"
            dangerouslySetInnerHTML={{
              __html: `
                // Prevent extension errors from breaking the app
                window.addEventListener('error', function(e) {
                  if (e.filename && e.filename.includes('chrome-extension://')) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.warn('Extension error blocked:', e.message);
                    return false;
                  }
                });
              `,
            }}
          />
        </head>
        <body className={inter.className} suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
