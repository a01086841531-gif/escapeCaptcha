import { Cinzel } from "next/font/google";
import "./globals.css";

const cinzel = Cinzel({
  variable: "--font-cinzel",
  subsets: ["latin"],
  weight: ["400", "600", "700", "900"],
});

export const metadata = {
  title: "Escape Room CAPTCHA - 방탈출 인증",
  description: "방탈출 테마의 독특한 캡챠 시스템으로 보안 로그인을 경험하세요.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko" className={cinzel.variable}>
      <body>{children}</body>
    </html>
  );
}
