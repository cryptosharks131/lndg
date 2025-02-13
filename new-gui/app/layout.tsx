import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { TokenRefreshProvider } from "@/components/token-refresh-provider";
import { Toaster } from "@/components/ui/toaster";
import { inter } from '@/app/ui/fonts';



export const metadata: Metadata = {
  title: "LNDg Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.className} antialiased`}
      >
        <TokenRefreshProvider refreshIntervalSeconds={240}>

          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
            <Toaster />
          </ThemeProvider>
        </TokenRefreshProvider>
      </body>
    </html>
  );
}
