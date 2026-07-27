"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

type Conversation = {
  id: string;
  listing_title: string;
  counterpart_name: string;
};
type Message = {
  id: string;
  sender_id: string;
  body: string;
  created_at: string;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Inbox() {
  const params = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState(params.get("conversation") ?? "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [me, setMe] = useState("");
  const [status, setStatus] = useState("Загружаем диалоги…");

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/conversations`, { credentials: "include" }),
      fetch(`${apiUrl}/me`, { credentials: "include" }),
    ]).then(async ([conversationResponse, meResponse]) => {
      if (conversationResponse.status === 401) {
        setStatus("Войдите, чтобы увидеть сообщения.");
        return;
      }
      if (!conversationResponse.ok || !meResponse.ok) throw new Error("inbox failed");
      const loaded = await conversationResponse.json() as Conversation[];
      const currentUser = await meResponse.json() as { id: string };
      setConversations(loaded);
      setMe(currentUser.id);
      setSelectedId((current) => current || loaded[0]?.id || "");
      setStatus(loaded.length ? "" : "Диалогов пока нет.");
    }).catch(() => setStatus("Не удалось загрузить диалоги."));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    fetch(`${apiUrl}/conversations/${selectedId}/messages`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("messages failed");
        setMessages(await response.json() as Message[]);
      })
      .catch(() => setStatus("Не удалось загрузить сообщения."));
  }, [selectedId]);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = String(form.get("body") ?? "").trim();
    if (!body || !selectedId) return;
    const response = await fetch(`${apiUrl}/conversations/${selectedId}/messages`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body, client_message_id: crypto.randomUUID() }),
    });
    if (!response.ok) {
      setStatus("Не удалось отправить сообщение.");
      return;
    }
    const message = await response.json() as Message;
    setMessages((current) => [...current, message]);
    event.currentTarget.reset();
  }

  return (
    <main>
      <header className="nav">
        <Link className="brand" href="/">Lava<span>.</span></Link>
        <Link className="button-link ghost" href="/search">К поиску</Link>
      </header>
      <section className="inbox-shell">
        <aside className="conversation-list">
          <p className="eyebrow">СООБЩЕНИЯ</p><h1>Диалоги</h1>
          {conversations.map((conversation) => (
            <button
              className={conversation.id === selectedId ? "selected" : ""}
              key={conversation.id}
              onClick={() => setSelectedId(conversation.id)}
            >
              <strong>{conversation.counterpart_name}</strong>
              <span>{conversation.listing_title}</span>
            </button>
          ))}
          {status && <p role="status">{status}</p>}
        </aside>
        <section className="message-panel" aria-label="Сообщения диалога">
          <div className="message-feed">
            {messages.map((message) => (
              <p className={message.sender_id === me ? "message mine" : "message"} key={message.id}>
                {message.body}
              </p>
            ))}
          </div>
          {selectedId && (
            <form className="message-form" onSubmit={send}>
              <label className="sr-only" htmlFor="message-body">Сообщение</label>
              <textarea id="message-body" name="body" maxLength={4000} required placeholder="Напишите сообщение…" />
              <button>Отправить</button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}

export default function MessagesPage() {
  return <Suspense fallback={<p>Загружаем сообщения…</p>}><Inbox /></Suspense>;
}
