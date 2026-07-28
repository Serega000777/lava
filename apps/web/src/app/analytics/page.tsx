"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Metrics = {
  listing_id: string;
  title: string;
  status: string;
  favorites: number;
  conversations: number;
  messages: number;
  reviews: number;
};
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AnalyticsPage() {
  const [items, setItems] = useState<Metrics[]>([]);
  const [status, setStatus] = useState("Загружаем аналитику…");

  useEffect(() => {
    fetch(`${apiUrl}/analytics/seller`, { credentials: "include" })
      .then(async (response) => {
        if (response.status === 401) {
          setStatus("Войдите, чтобы увидеть аналитику.");
          return;
        }
        if (!response.ok) throw new Error("analytics failed");
        const data = await response.json() as Metrics[];
        setItems(data);
        setStatus(data.length ? "" : "У вас пока нет объявлений.");
      })
      .catch(() => setStatus("Не удалось загрузить аналитику."));
  }, []);

  return (
    <main>
      <header className="nav"><Link className="brand" href="/">Lava<span>.</span></Link></header>
      <section className="results-shell">
        <p className="eyebrow">ТОЛЬКО РЕАЛЬНЫЕ СОБЫТИЯ</p><h1>Аналитика продавца</h1>
        {status && <p className="results-message" role="status">{status}</p>}
        <div className="analytics-grid">
          {items.map((item) => (
            <article className="analytics-card" key={item.listing_id}>
              <p>{item.status}</p><h2>{item.title}</h2>
              <dl>
                <div><dt>Избранное</dt><dd>{item.favorites}</dd></div>
                <div><dt>Диалоги</dt><dd>{item.conversations}</dd></div>
                <div><dt>Сообщения</dt><dd>{item.messages}</dd></div>
                <div><dt>Отзывы</dt><dd>{item.reviews}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
