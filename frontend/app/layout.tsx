import type { ReactNode } from "react";
import "./globals.css";

export default function RootLayout(props: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        {props.children}
      </body>
    </html>
  );
}

