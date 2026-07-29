"use client";

export type PublicListing = {
  id: string;
  title: string;
  description: string;
  price: string | null;
  city: string;
  ai_generated_fields?: string[];
  cover_image_url?: string | null;
};

type Props = {
  listing: PublicListing;
  favorite?: boolean;
  favoriteBusy?: boolean;
  onFavorite?: (listingId: string, favorite: boolean) => void;
  onMessage?: (listingId: string) => void;
};

function formatPrice(price: string | null) {
  return price === null ? "Цена по запросу" : `${new Intl.NumberFormat("ru-RU").format(Number(price))} ₽`;
}

export function ListingCard({
  listing, favorite = false, favoriteBusy = false, onFavorite, onMessage,
}: Props) {
  return (
    <article className="listing-card">
      {listing.cover_image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className="listing-image"
          src={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}${listing.cover_image_url}`}
          alt=""
        />
      ) : (
        <div className="listing-placeholder" aria-hidden="true">Lava.</div>
      )}
      <div className="listing-body">
        {onFavorite && (
          <button
            className={`favorite-button${favorite ? " is-favorite" : ""}`}
            disabled={favoriteBusy}
            onClick={() => onFavorite(listing.id, favorite)}
            aria-label={favorite ? "Удалить из избранного" : "Добавить в избранное"}
            aria-pressed={favorite}
          >
            {favorite ? "♥" : "♡"}
          </button>
        )}
        <p className="listing-city">{listing.city}</p>
        {listing.ai_generated_fields?.length ? <span className="ai-label">AI-assisted</span> : null}
        <h2>{listing.title}</h2>
        <p>{listing.description || "Продавец пока не добавил описание."}</p>
        <strong>{formatPrice(listing.price)}</strong>
        {onMessage && <button className="message-button" onClick={() => onMessage(listing.id)}>Написать</button>}
      </div>
    </article>
  );
}
