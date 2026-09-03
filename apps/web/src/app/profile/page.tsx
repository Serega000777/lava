"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Profile = {
  id: string;
  display_name: string;
  phone: string;
  role: string;
  verification_level: number;
};
type ActiveSession = { id: string; created_at: string; expires_at: string; is_current: boolean };
type ReviewReply = { responder_name: string; body: string; created_at: string };
type Review = {
  id: string;
  reviewer_name: string;
  rating: number;
  comment: string;
  created_at: string;
  reply: ReviewReply | null;
  dispute_status: "open" | "keep" | "exclude" | null;
  dispute_resolution_reason: string | null;
  dispute_resolution_comment: string | null;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const verificationLabels = [
  "Новый",
  "Телефон подтверждён",
  "Личность проверена",
  "Расширенная проверка",
  "Организация проверена",
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [sessionMessage, setSessionMessage] = useState("");
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [reviewMessage, setReviewMessage] = useState("");

  useEffect(() => {
    fetch(`${apiUrl}/me`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Войдите, чтобы открыть профиль");
        const loadedProfile = await response.json() as Profile;
        setProfile(loadedProfile);
        void fetch(`${apiUrl}/reviews/received`, { credentials: "include" })
          .then(async (reviewsResponse) => {
            if (!reviewsResponse.ok) throw new Error("reviews failed");
            setReviews(await reviewsResponse.json() as Review[]);
          })
          .catch(() => {
            setReviews([]);
            setReviewMessage("Не удалось загрузить отзывы.");
          });
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Ошибка загрузки");
      });
    fetch(`${apiUrl}/auth/sessions`, { credentials: "include" })
      .then(async (response) => {
        if (response.ok) setSessions(await response.json() as ActiveSession[]);
      })
      .catch(() => setSessionMessage("Не удалось загрузить активные сеансы."));
  }, []);

  async function revoke(sessionId: string) {
    const response = await apiFetch(`${apiUrl}/auth/sessions/${sessionId}`, {
      method: "DELETE", credentials: "include",
    });
    if (response.ok) setSessions((items) => items.filter((item) => item.id !== sessionId));
    else setSessionMessage("Не удалось завершить сеанс.");
  }

  async function revokeOthers() {
    const response = await apiFetch(`${apiUrl}/auth/sessions/revoke-others`, {
      method: "POST", credentials: "include",
    });
    if (response.ok) {
      setSessions((items) => items.filter((item) => item.is_current));
      setSessionMessage("Остальные сеансы завершены.");
    } else setSessionMessage("Не удалось завершить остальные сеансы.");
  }

  async function replyToReview(event: FormEvent<HTMLFormElement>, reviewId: string) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await apiFetch(`${apiUrl}/reviews/${reviewId}/reply`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: form.get("body") }),
    });
    if (response.status === 409) {
      setReviewMessage("Ответ на этот отзыв уже опубликован.");
      return;
    }
    if (!response.ok || !profile) {
      setReviewMessage("Не удалось опубликовать ответ.");
      return;
    }
    const reply = await response.json() as {
      body: string;
      created_at: string;
    };
    setReviews((current) => current?.map((review) => review.id === reviewId ? {
      ...review,
      reply: {
        responder_name: profile.display_name,
        body: reply.body,
        created_at: reply.created_at,
      },
    } : review) ?? current);
    setReviewMessage("Ответ опубликован.");
    formElement.reset();
  }

  async function disputeReview(event: FormEvent<HTMLFormElement>, reviewId: string) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await apiFetch(`${apiUrl}/reviews/${reviewId}/dispute`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reason_code: form.get("reason_code"),
        details: form.get("details"),
      }),
    });
    if (response.status === 409) {
      setReviewMessage("Спор по этому отзыву уже открыт.");
      return;
    }
    if (!response.ok) {
      setReviewMessage("Не удалось открыть спор по отзыву.");
      return;
    }
    setReviews((current) => current?.map((review) => review.id === reviewId
      ? { ...review, dispute_status: "open" }
      : review) ?? current);
    setReviewMessage("Спор отправлен на независимую модерацию.");
    formElement.reset();
  }

  return (
    <main className="auth-shell">
      <section className="auth-card profile-card">
        <Link className="brand" href="/">Lava<span>.</span></Link>
        <p className="eyebrow">ПРОФИЛЬ</p>
        {!profile && !error && <p>Загружаем профиль…</p>}
        {error && (
          <>
            <p role="alert" className="form-error">{error}</p>
            <Link href="/login">Перейти ко входу</Link>
          </>
        )}
        {profile && (
          <>
            <h1>{profile.display_name}</h1>
            <dl>
              <dt>Телефон</dt><dd>{profile.phone}</dd>
              <dt>Роль</dt><dd>{profile.role}</dd>
              <dt>Уровень проверки</dt>
              <dd>{verificationLabels[profile.verification_level] ?? verificationLabels[0]}</dd>
            </dl>
            <p className="auth-note">
              LAVA публично показывает только уровень доверия. Телефон и внутренние
              сведения о проверке не публикуются.
            </p>
            <h2>Активные сеансы</h2>
            {sessions.length === 0 && <p>Других активных сеансов нет.</p>}
            <ul className="session-list">
              {sessions.map((item) => <li key={item.id}>
                <span>{new Date(item.created_at).toLocaleString("ru-RU")}{item.is_current ? " · текущий" : ""}</span>
                {!item.is_current && <button onClick={() => void revoke(item.id)}>Завершить</button>}
              </li>)}
            </ul>
            {sessions.some((item) => !item.is_current) && <button onClick={() => void revokeOthers()}>Завершить все остальные</button>}
            {sessionMessage && <p role="status">{sessionMessage}</p>}
            <h2>Отзывы обо мне</h2>
            {reviews === null && <p>Загружаем отзывы…</p>}
            {reviews?.length === 0 && <p>Отзывов пока нет.</p>}
            {reviews && reviews.length > 0 && (
              <ul className="review-list">
                {reviews.map((review) => (
                  <li key={review.id}>
                    <strong>{review.rating}/5 · {review.reviewer_name}</strong>
                    {review.comment && <p>{review.comment}</p>}
                    {review.reply ? (
                      <blockquote>
                        <strong>{review.reply.responder_name} ответил:</strong>
                        <p>{review.reply.body}</p>
                      </blockquote>
                    ) : (
                      <form onSubmit={(event) => void replyToReview(event, review.id)}>
                        <label htmlFor={`reply-${review.id}`}>Ответ на отзыв</label>
                        <input
                          id={`reply-${review.id}`}
                          name="body"
                          minLength={1}
                          maxLength={2000}
                          required
                        />
                        <button>Опубликовать ответ</button>
                      </form>
                    )}
                    {review.dispute_status ? (
                      <div>
                        <p>
                          Статус спора: {{
                            open: "на рассмотрении",
                            keep: "отзыв оставлен",
                            exclude: "отзыв исключён из публичной репутации",
                          }[review.dispute_status]}
                        </p>
                        {review.dispute_resolution_reason && (
                          <p>Причина решения: {review.dispute_resolution_reason}</p>
                        )}
                        {review.dispute_resolution_comment && (
                          <p>{review.dispute_resolution_comment}</p>
                        )}
                      </div>
                    ) : (
                      <form onSubmit={(event) => void disputeReview(event, review.id)}>
                        <label htmlFor={`dispute-reason-${review.id}`}>Оспорить отзыв</label>
                        <select id={`dispute-reason-${review.id}`} name="reason_code" defaultValue="other">
                          <option value="transaction_not_completed">Сделка не состоялась</option>
                          <option value="abusive">Оскорбление</option>
                          <option value="personal_data">Персональные данные</option>
                          <option value="fraudulent">Недостоверный отзыв</option>
                          <option value="other">Другая причина</option>
                        </select>
                        <input name="details" maxLength={4000} placeholder="Пояснение модератору" />
                        <button className="ghost">Открыть спор</button>
                      </form>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {reviewMessage && <p role="status">{reviewMessage}</p>}
          </>
        )}
      </section>
    </main>
  );
}
