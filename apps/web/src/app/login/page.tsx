"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiFetch } from "../../lib/api";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await apiFetch(`${apiUrl}/auth/login/password`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: data.get("phone"), password: data.get("password") }),
      });
      if (!response.ok) throw new Error("Проверьте телефон и пароль");
      window.location.href = "/profile";
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось войти");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell"><section className="auth-card">
      <Link className="brand" href="/">Lava<span>.</span></Link>
      <p className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</p><h1>Войти</h1>
      <form onSubmit={login}>
        <label>Телефон<input name="phone" type="tel" placeholder="+79990000000" required /></label>
        <label>Пароль<input name="password" type="password" required /></label>
        <button disabled={loading}>{loading ? "Входим…" : "Войти"}</button>
        {message && <p role="alert" className="form-error">{message}</p>}
      </form>
      <p><Link href="/recover">Забыли пароль?</Link></p>
      <p className="auth-note">SMS и VK будут доступны после подключения проверенных провайдеров.</p>
    </section></main>
  );
}
