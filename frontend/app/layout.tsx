import type { Metadata } from 'next'
import { Inter, Instrument_Serif } from 'next/font/google'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter'
});

const instrumentSerif = Instrument_Serif({ 
  subsets: ["latin"],
  weight: "400",
  variable: '--font-serif'
});

export const metadata: Metadata = {
  title: 'Hawker',
  description: 'AI-powered news discovery',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/hawker-logo.png',
        type: 'image/png',
      },
    ],
    apple: [
      {
        url: '/hawker-logo.png',
        sizes: '180x180',
        type: 'image/png',
      },
      {
        url: '/hawker-logo.png',
        sizes: '192x192',
        type: 'image/png',
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${instrumentSerif.variable}`}>
      <body className="font-sans antialiased bg-background text-foreground">
        {children}
      </body>
    </html>
  )
}
