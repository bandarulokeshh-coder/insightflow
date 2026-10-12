import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "InsightFlow — Customer Feedback & Decision Platform",
  description:
    "Turn raw customer feedback into decisions. Powered by an adaptive data layer (Adaption).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full">
        <div className="mx-auto flex min-h-screen w-full max-w-[1500px] flex-col lg:flex-row">
          <Sidebar />
          <main className="min-w-0 flex-1 px-4 pb-16 pt-5 sm:px-6 lg:px-8 lg:pt-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
