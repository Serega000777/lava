"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Attribute = { key: string; label: string; value_type: string; is_required: boolean; options: string[] | null };
type Category = { id: string; name: string; attributes: Attribute[] };
type Generation = { id: string; output: { title: string; description: string } | null };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function NewListingPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [listingId, setListingId] = useState("");
  const [generation, setGeneration] = useState<Generation | null>(null);
  const [credits, setCredits] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/categories`)
      .then((response) => response.json())
      .then((data: Category[]) => setCategories(data))
      .catch(() => setMessage("Не удалось загрузить категории"));
  }, []);

  useEffect(() => {
    fetch(`${apiUrl}/credits`, { credentials: "include" })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => setCredits(data?.balance ?? null));
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    const price = String(form.get("price") ?? "");
    const selected = categories.find((category) => category.id === categoryId);
    const attributes = Object.fromEntries(
      (selected?.attributes ?? []).map((attribute) => [
        attribute.key,
        form.get(`attribute:${attribute.key}`),
      ]),
    );
    const response = await fetch(`${apiUrl}/listings`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category_id: categoryId,
        title: form.get("title"),
        description: form.get("description"),
        city: form.get("city"),
        price: price ? Number(price) : null,
        attributes,
      }),
    });
    setLoading(false);
    if (response.status === 401) {
      setMessage("Сначала войдите в аккаунт");
      return;
    }
    if (!response.ok) {
      setMessage("Проверьте заполненные поля");
      return;
    }
    const listing = await response.json() as { id: string };
    setListingId(listing.id);
    setMessage(`Черновик сохранён: ${listing.id}`);
  }

  async function improve() {
    setLoading(true);
    const response = await fetch(`${apiUrl}/listings/${listingId}/ai/text`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_request_id: crypto.randomUUID() }),
    });
    setLoading(false);
    if (response.status === 402) {
      setMessage("Недостаточно AI-кредитов.");
      return;
    }
    if (!response.ok) {
      setMessage("Не удалось подготовить предложение.");
      return;
    }
    setGeneration(await response.json() as Generation);
    setCredits((current) => current === null ? null : current - 1);
  }

  async function accept() {
    if (!generation) return;
    const response = await fetch(`${apiUrl}/ai/generations/${generation.id}/accept`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok) {
      setMessage("Не удалось применить AI-предложение.");
      return;
    }
    setMessage("AI-предложение применено и отмечено в объявлении.");
    setGeneration(null);
  }

  return (
    <main className="auth-shell"><section className="auth-card listing-form">
      <Link className="brand" href="/">Lava<span>.</span></Link>
      <p className="eyebrow">НОВОЕ ОБЪЯВЛЕНИЕ</p><h1>Создать черновик</h1>
      <form onSubmit={create}>
        <label>Категория<select name="category_id" required value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
          <option value="" disabled>Выберите категорию</option>
          {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
        </select></label>
        {categories.find((category) => category.id === categoryId)?.attributes.map((attribute) => (
          <label key={attribute.key}>{attribute.label}
            {attribute.value_type === "select" ? (
              <select name={`attribute:${attribute.key}`} required={attribute.is_required} defaultValue="">
                <option value="" disabled>Выберите значение</option>
                {attribute.options?.map((option) => <option value={option} key={option}>{option}</option>)}
              </select>
            ) : (
              <input
                name={`attribute:${attribute.key}`}
                type={attribute.value_type === "number" ? "number" : "text"}
                required={attribute.is_required}
              />
            )}
          </label>
        ))}
        <label>Название<input name="title" minLength={3} maxLength={140} required /></label>
        <label>Описание<textarea name="description" maxLength={10000} /></label>
        <label>Цена<input name="price" type="number" min="0" step="0.01" /></label>
        <label>Город<input name="city" minLength={2} maxLength={120} required /></label>
        <button disabled={loading}>{loading ? "Сохраняем…" : "Сохранить черновик"}</button>
        {message && <p role="status">{message}</p>}
      </form>
      {listingId && (
        <section className="ai-assistant">
          <p className="eyebrow">AI-ПОМОЩНИК · КРЕДИТОВ: {credits ?? "—"}</p>
          <p>Помощник улучшает структуру текста, но не добавляет характеристики и не скрывает недостатки.</p>
          <button disabled={loading} onClick={improve}>Предложить улучшение · 1 кредит</button>
          {generation?.output && (
            <div className="ai-preview">
              <h2>{generation.output.title}</h2>
              <p>{generation.output.description}</p>
              <button onClick={accept}>Применить и отметить как AI-assisted</button>
            </div>
          )}
        </section>
      )}
    </section></main>
  );
}
