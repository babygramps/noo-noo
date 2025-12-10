import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Noo-Noo | Vacuum Seal Test System',
  description: 'Professional web control interface for EPDM gasket vacuum seal testing',
  keywords: ['vacuum testing', 'EPDM gasket', 'seal testing', 'quality control'],
  authors: [{ name: 'Noo-Noo Team' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
