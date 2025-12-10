import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EPDM Vacuum Test Fixture',
  description: 'Web control interface for vacuum seal testing system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}


