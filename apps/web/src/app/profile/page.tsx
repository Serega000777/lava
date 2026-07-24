"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Profile = { display_name: string; phone: string; role: string; verification_level: number };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch(`${apiUrl}/me`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Войдите, чтобы открыть профиль");
        setProfile(await response.json() as Profile);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Ошибка"));
  }, []);

  return (
    <main className="auth-shell"><section className="auth-card">
      <Link className="brand" href="/">Lava<span>.</span></Link><p className="eyebrow">ПРОФИЛЬ</p>
      {!profile && !error && <p>Загружаем профиль…</p>}
      {error && <><p role="alert" className="form-error">{error}</p><Link href="/login">Перейти ко входу</Link></>}
      {profile && <><h1>{profile.display_name}</h1><dl>
        <dt>Телефон</dt><dd>{profile.phone}</dd><dt>Роль</dt><dd>{profile.role}</dd>
        <dt>Уровень проверки</dt><dd>{profile.verification_level}</dd>
      </dl></>}
    </section></main>
  );
}

