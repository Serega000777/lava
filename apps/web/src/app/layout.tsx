import type { Metadata } from "next";
import "./styles.css";
import "./auth.css";
import "./search.css";

export const metadata: Metadata = {
  title: "Lava — объявления по-честному",
  description: "Автомобили, товары и услуги рядом с вами без платного влияния на органическую выдачу.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
