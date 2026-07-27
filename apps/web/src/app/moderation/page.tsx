"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Case = { id: string; listing_id: string; status: string; assigned_to: string | null };
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ModerationPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [message, setMessage] = useState("");

  async function load() {
    const response = await fetch(`${apiUrl}/moderation/cases`, { credentials: "include" });
    if (!response.ok) {
      setMessage(response.status === 403 ? "Недостаточно прав" : "Войдите как модератор");
      return;
    }
    setCases(await response.json() as Case[]);
  }

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiUrl}/moderation/cases`, { credentials: "include", signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          setMessage(response.status === 403 ? "Недостаточно прав" : "Войдите как модератор");
          return;
        }
        setCases(await response.json() as Case[]);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) setMessage("Ошибка загрузки");
      });
    return () => controller.abort();
  }, []);

  async function decide(caseId: string, decision: "approved" | "rejected" | "changes_requested") {
    const reasonCode = {
      approved: "policy_compliant",
      rejected: "misleading_content",
      changes_requested: "content_issue",
    }[decision];
    const response = await fetch(`${apiUrl}/moderation/cases/${caseId}/decision`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        reason_code: reasonCode,
        comment: "",
      }),
    });
    setMessage(response.ok ? "Решение сохранено" : "Не удалось сохранить решение");
    if (response.ok) await load();
  }

  return (
    <main className="auth-shell"><section className="auth-card moderation-card">
      <Link className="brand" href="/">Lava<span>.</span></Link>
      <p className="eyebrow">МОДЕРАЦИЯ</p><h1>Очередь</h1>
      {message && <p role="status">{message}</p>}
      {!message && cases.length === 0 && <p>Очередь пуста</p>}
      <ul className="moderation-list">{cases.map((item) => <li key={item.id}>
        <div><strong>Объявление</strong><small>{item.listing_id}</small></div>
        <div className="moderation-actions">
          <button onClick={() => void decide(item.id, "approved")}>Одобрить</button>
          <button className="danger" onClick={() => void decide(item.id, "rejected")}>Отклонить</button>
          <button className="ghost" onClick={() => void decide(item.id, "changes_requested")}>На исправление</button>
        </div>
      </li>)}</ul>
    </section></main>
  );
}
