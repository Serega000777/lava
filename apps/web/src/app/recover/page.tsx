"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "../../lib/api";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RecoveryPage() {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [requested, setRequested] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function requestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setMessage("");
    try {
      const response = await apiFetch(`${apiUrl}/auth/recovery/request`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone }) });
      if (!response.ok) throw new Error("Не удалось отправить код");
      const result = await response.json() as { dev_code?: string | null };
      setDevCode(result.dev_code ?? ""); setRequested(true);
      setMessage("Если аккаунт существует, код восстановления отправлен.");
    } catch (error: unknown) { setMessage(error instanceof Error ? error.message : "Ошибка восстановления"); }
    finally { setLoading(false); }
  }

  async function resetPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await apiFetch(`${apiUrl}/auth/recovery/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, code, new_password: String(form.get("password") ?? "") }) });
      if (!response.ok) throw new Error("Неверный или просроченный код");
      window.location.assign("/profile");
    } catch (error: unknown) { setMessage(error instanceof Error ? error.message : "Ошибка восстановления"); }
    finally { setLoading(false); }
  }

  return <main className="auth-shell"><section className="auth-card">
    <Link className="brand" href="/">Lava<span>.</span></Link>
    <p className="eyebrow">ВОССТАНОВЛЕНИЕ</p><h1>Новый пароль</h1>
    {!requested ? <form onSubmit={requestCode}>
      <label>Телефон<input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+79990000000" required /></label>
      <button disabled={loading}>{loading ? "Отправляем…" : "Получить код"}</button>
    </form> : <form onSubmit={resetPassword}>
      <label>Код<input value={code} onChange={(event) => setCode(event.target.value)} inputMode="numeric" pattern="[0-9]{6}" required /></label>
      <label>Новый пароль<input name="password" type="password" minLength={10} required /></label>
      <button disabled={loading}>{loading ? "Сохраняем…" : "Сменить пароль"}</button>
    </form>}
    {devCode && <p className="auth-note">Dev-код: {devCode}</p>}
    {message && <p role="status">{message}</p>}
    <p className="auth-note"><Link href="/login">Вернуться ко входу</Link></p>
  </section></main>;
}
