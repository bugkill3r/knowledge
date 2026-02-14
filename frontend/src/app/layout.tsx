import type { Metadata } from 'next'
import './globals.css'
import 'reactflow/dist/style.css'
import { Providers } from './providers'

const appName = process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'

export const metadata: Metadata = {
  title: appName,
  description: 'Import docs, store in Obsidian, search and chat.',
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%234f46e5' rx='4'/><path fill='%23fff' d='M8 10h16v2H8zm0 4h12v2H8zm0 4h16v2H8z'/></svg>",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
