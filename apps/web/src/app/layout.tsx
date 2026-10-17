import type { Metadata } from "next";
import "./globals.css";
import { I18nProvider } from "@vigil/ui";
import { Header } from "@/components/Header";
import { ClinicalDisclaimer } from "@/components/ClinicalDisclaimer";

export const metadata: Metadata = {
  title: "Vigil Clinician Workstation (M9) | Precision Oncology Surveillance",
  description: "Evidence-disciplined precision oncology surveillance workstation for breast cancer monitoring.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased font-sans">
        <I18nProvider initialLocale="en-NG">
          <Header />
          <main className="flex-1 p-4 sm:p-6 max-w-7xl w-full mx-auto space-y-6">
            {children}
            <ClinicalDisclaimer />
          </main>
        </I18nProvider>
      </body>
    </html>
  );
}
