"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import { ListingCard, PublicListing } from "../../components/listing-card";
import { apiFetch } from "../../lib/api";

type SearchResponse = { items: PublicListing[]; total: number };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const pageSize = 24;

function SearchResults() {
  const params = useSearchParams();
  const router = useRouter();
  const initialQuery = params.get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [activeQuery, setActiveQuery] = useState(initialQuery);
  const [sort, setSort] = useState("relevance");
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [favoriteBusy, setFavoriteBusy] = useState<Set<string>>(new Set());
  const [favoriteMessage, setFavoriteMessage] = useState("");

  const load = useCallback(async (q: string, order: string, start: number) => {
    const search = new URLSearchParams({ q, sort: order, limit: String(pageSize), offset: String(start) });
    try {
      const response = await fetch(`${apiUrl}/search/listings?${search}`);
      if (!response.ok) throw new Error("search failed");
      setResult(await response.json() as SearchResponse);
    } catch {
      setError("Не удалось загрузить объявления. Попробуйте ещё раз.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // This effect synchronizes the page with the URL's initial search query.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(initialQuery, "relevance", 0);
    void fetch(`${apiUrl}/favorites`, { credentials: "include" }).then(async (response) => {
      if (response.ok) {
        const favorites = await response.json() as PublicListing[];
        setFavoriteIds(new Set(favorites.map((listing) => listing.id)));
      }
    });
  }, [initialQuery, load]);

  async function toggleFavorite(listingId: string, isFavorite: boolean) {
    setFavoriteBusy((current) => new Set(current).add(listingId));
    setFavoriteMessage("");
    try {
      const response = await apiFetch(`${apiUrl}/favorites/${listingId}`, {
        method: isFavorite ? "DELETE" : "PUT",
        credentials: "include",
      });
      if (response.status === 401) {
        setFavoriteMessage("Войдите, чтобы сохранять объявления.");
        return;
      }
      if (!response.ok) throw new Error("favorite failed");
      setFavoriteIds((current) => {
        const next = new Set(current);
        if (isFavorite) next.delete(listingId);
        else next.add(listingId);
        return next;
      });
    } catch {
      setFavoriteMessage("Не удалось обновить избранное.");
    } finally {
      setFavoriteBusy((current) => {
        const next = new Set(current);
        next.delete(listingId);
        return next;
      });
    }
  }

  async function startConversation(listingId: string) {
    const response = await apiFetch(`${apiUrl}/conversations`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ listing_id: listingId }),
    });
    if (response.status === 401) {
      setFavoriteMessage("Войдите, чтобы написать продавцу.");
      return;
    }
    if (response.status === 409) {
      setFavoriteMessage("Нельзя начать диалог со своим объявлением.");
      return;
    }
    if (!response.ok) {
      setFavoriteMessage("Не удалось открыть диалог.");
      return;
    }
    const conversation = await response.json() as { id: string };
    router.push(`/messages?conversation=${conversation.id}`);
  }

  async function reportListing(listingId: string) {
    const response = await apiFetch(`${apiUrl}/listings/${listingId}/complaints`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_request_id: crypto.randomUUID(),
        reason_code: "misleading_content",
        details: "",
      }),
    });
    if (response.status === 401) {
      setFavoriteMessage("Войдите, чтобы отправить жалобу.");
      return;
    }
    if (response.status === 409) {
      setFavoriteMessage("Нельзя пожаловаться на собственное объявление.");
      return;
    }
    if (response.status === 429) {
      setFavoriteMessage("Лимит жалоб исчерпан. Попробуйте позже.");
      return;
    }
    if (response.status === 503) {
      setFavoriteMessage("Защита жалоб временно недоступна. Попробуйте позже.");
      return;
    }
    setFavoriteMessage(
      response.ok ? "Жалоба отправлена на проверку." : "Не удалось отправить жалобу.",
    );
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setActiveQuery(query);
    setOffset(0);
    window.history.replaceState(null, "", query ? `/search?q=${encodeURIComponent(query)}` : "/search");
    void load(query, sort, 0);
  }

  function changeSort(nextSort: string) {
    setSort(nextSort);
    setOffset(0);
    setLoading(true);
    setError("");
    void load(activeQuery, nextSort, 0);
  }

  function changePage(nextOffset: number) {
    setOffset(nextOffset);
    setLoading(true);
    setError("");
    void load(activeQuery, sort, nextOffset);
  }

  const hasPrevious = offset > 0;
  const hasNext = result !== null && offset + result.items.length < result.total;

  return (
    <main>
      <header className="nav">
        <Link className="brand" href="/" aria-label="Lava, главная">Lava<span>.</span></Link>
        <div className="actions">
          <Link className="button-link ghost" href="/login">Войти</Link>
          <Link className="button-link" href="/listings/new">Разместить объявление</Link>
        </div>
      </header>
      <section className="results-shell">
        <p className="eyebrow">ПОИСК ПО ОБЪЯВЛЕНИЯМ</p>
        <h1>{activeQuery ? `Результаты для «${activeQuery}»` : "Все объявления"}</h1>
        <form className="search results-search" role="search" onSubmit={submit}>
          <label className="sr-only" htmlFor="search-query">Поиск объявлений</label>
          <input id="search-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Что вы ищете?" />
          <button type="submit">Найти</button>
        </form>
        <div className="results-toolbar">
          <p>{loading ? "Ищем…" : `Найдено: ${result?.total ?? 0}`}</p>
          <label>Сортировка
            <select value={sort} onChange={(event) => changeSort(event.target.value)}>
              <option value="relevance">По релевантности</option>
              <option value="newest">Сначала новые</option>
              <option value="price_asc">Сначала дешевле</option>
              <option value="price_desc">Сначала дороже</option>
            </select>
          </label>
        </div>
        {error && <p className="results-message" role="alert">{error}</p>}
        {favoriteMessage && <p className="favorite-message" role="status">{favoriteMessage}</p>}
        {!loading && !error && result?.items.length === 0 && (
          <div className="empty-state"><h2>Ничего не найдено</h2><p>Попробуйте изменить запрос или посмотреть все объявления.</p></div>
        )}
        <div className="listing-grid" aria-busy={loading}>
          {result?.items.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              favorite={favoriteIds.has(listing.id)}
              favoriteBusy={favoriteBusy.has(listing.id)}
              onFavorite={toggleFavorite}
              onMessage={startConversation}
              onReport={reportListing}
            />
          ))}
        </div>
        {(hasPrevious || hasNext) && (
          <nav className="pagination" aria-label="Страницы результатов">
            <button disabled={!hasPrevious || loading} onClick={() => changePage(Math.max(0, offset - pageSize))}>← Назад</button>
            <span>Страница {Math.floor(offset / pageSize) + 1}</span>
            <button disabled={!hasNext || loading} onClick={() => changePage(offset + pageSize)}>Вперёд →</button>
          </nav>
        )}
      </section>
    </main>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<main><section className="results-shell"><p>Загружаем объявления…</p></section></main>}>
      <SearchResults />
    </Suspense>
  );
}
