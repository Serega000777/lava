"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Profile = {
  display_name: string;
  phone: string;
  role: string;
  verification_level: number;
};
type ActiveSession = { id: string; created_at: string; expires_at: string; is_current: boolean };

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

  useEffect(() => {
    fetch(`${apiUrl}/me`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Войдите, чтобы открыть профиль");
        setProfile(await response.json() as Profile);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Ошибка загрузки");
      });
    fetch(`${apiUrl}/auth/sessions`, { credentials: "include" })
      .then(async (response) => {
        if (response.ok) setSessions(await response.json() as ActiveSession[]);
      });
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

  return (
    <main className="auth-shell">
      <section className="auth-card">
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
          </>
        )}
      </section>
    </main>
  );
}
