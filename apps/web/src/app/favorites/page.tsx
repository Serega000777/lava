"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ListingCard, PublicListing } from "../../components/listing-card";
import { apiFetch } from "../../lib/api";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function FavoritesPage() {
  const [items, setItems] = useState<PublicListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch(`${apiUrl}/favorites`, { credentials: "include" })
      .then(async (response) => {
        if (response.status === 401) {
          setMessage("Войдите, чтобы увидеть избранное.");
          return;
        }
        if (!response.ok) throw new Error("favorites failed");
        setItems(await response.json() as PublicListing[]);
      })
      .catch(() => setMessage("Не удалось загрузить избранное."))
      .finally(() => setLoading(false));
  }, []);

  async function remove(listingId: string) {
    const response = await apiFetch(`${apiUrl}/favorites/${listingId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (response.ok) setItems((current) => current.filter((item) => item.id !== listingId));
    else setMessage("Не удалось удалить объявление из избранного.");
  }

  return (
    <main>
      <header className="nav">
        <Link className="brand" href="/">Lava<span>.</span></Link>
        <div className="actions"><Link className="button-link ghost" href="/search">Поиск</Link></div>
      </header>
      <section className="results-shell">
        <p className="eyebrow">ВАША ПОДБОРКА</p><h1>Избранное</h1>
        {loading && <p>Загружаем…</p>}
        {message && <p className="results-message" role="status">{message}</p>}
        {!loading && !message && items.length === 0 && (
          <div className="empty-state"><h2>Здесь пока пусто</h2><p>Сохраняйте интересные объявления из поиска.</p></div>
        )}
        <div className="listing-grid">
          {items.map((listing) => (
            <ListingCard key={listing.id} listing={listing} favorite onFavorite={(id) => void remove(id)} />
          ))}
        </div>
      </section>
    </main>
  );
}
