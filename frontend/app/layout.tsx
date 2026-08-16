import './globals.css';

export const metadata = {
  title: 'UAP/UFO Analytics',
  description: 'Badatelský analytický nástroj pro odtajněné UAP spisy',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="cs">
      <body>
        {children}
      </body>
    </html>
  )
}