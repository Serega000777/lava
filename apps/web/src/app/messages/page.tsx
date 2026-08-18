"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Conversation = {
  id: string;
  listing_title: string;
  counterpart_id: string;
  counterpart_name: string;
  is_muted: boolean;
};
type Message = {
  id: string;
  sender_id: string;
  body: string;
  created_at: string;
  read_at: string | null;
  media: Array<{ id: string; width: number; height: number }>;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Inbox() {
  const params = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState(params.get("conversation") ?? "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [me, setMe] = useState("");
  const [status, setStatus] = useState("Загружаем диалоги…");
  const [reputation, setReputation] = useState<{ average_rating: string | null; review_count: number } | null>(null);
  const [blockedUsers, setBlockedUsers] = useState<Set<string>>(new Set());
  const [reportedMessages, setReportedMessages] = useState<Set<string>>(new Set());
  const selectedConversation = conversations.find((conversation) => conversation.id === selectedId);
  const selectedIsBlocked = selectedConversation
    ? blockedUsers.has(selectedConversation.counterpart_id)
    : false;

  useEffect(() => {
    Promise.all([
      fetch(`${apiUrl}/conversations`, { credentials: "include" }),
      fetch(`${apiUrl}/me`, { credentials: "include" }),
      fetch(`${apiUrl}/blocks`, { credentials: "include" }),
    ]).then(async ([conversationResponse, meResponse, blocksResponse]) => {
      if (conversationResponse.status === 401) {
        setStatus("Войдите, чтобы увидеть сообщения.");
        return;
      }
      if (!conversationResponse.ok || !meResponse.ok || !blocksResponse.ok) throw new Error("inbox failed");
      const loaded = await conversationResponse.json() as Conversation[];
      const currentUser = await meResponse.json() as { id: string };
      const blocks = await blocksResponse.json() as { user_id: string }[];
      setConversations(loaded);
      setMe(currentUser.id);
      setBlockedUsers(new Set(blocks.map((item) => item.user_id)));
      setSelectedId((current) => current || loaded[0]?.id || "");
      setStatus(loaded.length ? "" : "Диалогов пока нет.");
    }).catch(() => setStatus("Не удалось загрузить диалоги."));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const selected = conversations.find((conversation) => conversation.id === selectedId);
    fetch(`${apiUrl}/conversations/${selectedId}/messages`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new Error("messages failed");
        const loadedMessages = await response.json() as Message[];
        setMessages(loadedMessages);
        const receipt = await apiFetch(`${apiUrl}/conversations/${selectedId}/read`, {
          method: "PATCH",
          credentials: "include",
        });
        if (!receipt.ok) setStatus("Сообщения загружены, но отметка о прочтении не сохранена.");
      })
      .catch(() => setStatus("Не удалось загрузить сообщения."));
    if (selected) {
      fetch(`${apiUrl}/users/${selected.counterpart_id}/reputation`)
        .then((response) => response.ok ? response.json() : null)
        .then((data) => setReputation(data));
    }
  }, [conversations, selectedId]);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = String(form.get("body") ?? "").trim();
    const media = form.get("media");
    if (!body || !selectedId) return;
    const response = await apiFetch(`${apiUrl}/conversations/${selectedId}/messages`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body, client_message_id: crypto.randomUUID() }),
    });
    if (response.status === 429) {
      setStatus("Слишком много сообщений. Подождите минуту и попробуйте снова.");
      return;
    }
    if (response.status === 503) {
      setStatus("Отправка временно недоступна из-за защитной проверки. Попробуйте позже.");
      return;
    }
    if (response.status === 409) {
      setStatus("Сообщения между этими пользователями заблокированы.");
      return;
    }
    if (!response.ok) {
      setStatus("Не удалось отправить сообщение.");
      return;
    }
    const message = await response.json() as Message;
    setMessages((current) => [...current, { ...message, media: message.media ?? [] }]);
    if (media instanceof File && media.size > 0) {
      const upload = new FormData();
      upload.set("file", media);
      const mediaResponse = await apiFetch(`${apiUrl}/messages/${message.id}/media`, {
        method: "POST",
        credentials: "include",
        body: upload,
      });
      if (!mediaResponse.ok) {
        setStatus("Сообщение отправлено, но изображение загрузить не удалось.");
        event.currentTarget.reset();
        return;
      }
      const attached = await mediaResponse.json() as { id: string; width: number; height: number };
      setMessages((current) => current.map((item) => (
        item.id === message.id ? { ...item, media: [...item.media, attached] } : item
      )));
    }
    event.currentTarget.reset();
  }

  async function toggleBlock() {
    const selected = conversations.find((conversation) => conversation.id === selectedId);
    if (!selected) return;
    const isBlocked = blockedUsers.has(selected.counterpart_id);
    const response = await apiFetch(`${apiUrl}/users/${selected.counterpart_id}/block`, {
      method: isBlocked ? "DELETE" : "PUT",
      credentials: "include",
    });
    if (!response.ok) {
      setStatus("Не удалось изменить блокировку пользователя.");
      return;
    }
    setBlockedUsers((current) => {
      const next = new Set(current);
      if (isBlocked) next.delete(selected.counterpart_id);
      else next.add(selected.counterpart_id);
      return next;
    });
    setStatus(isBlocked ? "Пользователь разблокирован." : "Пользователь заблокирован. История сохранена.");
  }

  async function toggleMute() {
    if (!selectedConversation) return;
    const response = await apiFetch(`${apiUrl}/conversations/${selectedConversation.id}/mute`, {
      method: selectedConversation.is_muted ? "DELETE" : "PUT",
      credentials: "include",
    });
    if (!response.ok) {
      setStatus("Не удалось изменить уведомления диалога.");
      return;
    }
    setConversations((current) => current.map((conversation) => (
      conversation.id === selectedConversation.id
        ? { ...conversation, is_muted: !conversation.is_muted }
        : conversation
    )));
    setStatus(selectedConversation.is_muted ? "Уведомления включены." : "Уведомления отключены.");
  }

  async function reportMessage(event: FormEvent<HTMLFormElement>, messageId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await apiFetch(`${apiUrl}/messages/${messageId}/reports`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_request_id: crypto.randomUUID(),
        reason_code: form.get("reason_code"),
        details: "",
      }),
    });
    if (response.status === 429) {
      setStatus("Лимит жалоб исчерпан. Попробуйте позже.");
      return;
    }
    if (response.status === 503) {
      setStatus("Защита жалоб временно недоступна. Попробуйте позже.");
      return;
    }
    if (!response.ok) {
      setStatus("Не удалось отправить жалобу на сообщение.");
      return;
    }
    setReportedMessages((current) => new Set(current).add(messageId));
    setStatus("Жалоба на сообщение отправлена модератору.");
  }

  async function review(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const response = await apiFetch(`${apiUrl}/conversations/${selectedId}/review`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating: Number(form.get("rating")),
        comment: form.get("comment"),
      }),
    });
    if (response.status === 409) {
      setStatus("Отзыв доступен после двустороннего общения и создаётся один раз.");
      return;
    }
    if (!response.ok) {
      setStatus("Не удалось сохранить отзыв.");
      return;
    }
    setStatus("Отзыв опубликован.");
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
          {selectedId && reputation && (
            <p className="reputation-line">
              Репутация собеседника: {reputation.average_rating ?? "нет оценок"} · отзывов {reputation.review_count}
            </p>
          )}
          {selectedId && (() => {
            const selected = selectedConversation;
            if (!selected) return null;
            const isBlocked = blockedUsers.has(selected.counterpart_id);
            return (
              <button className="ghost" type="button" onClick={() => void toggleBlock()}>
                {isBlocked ? "Разблокировать пользователя" : "Заблокировать пользователя"}
              </button>
            );
          })()}
          {selectedConversation && (
            <button className="ghost" type="button" onClick={() => void toggleMute()}>
              {selectedConversation.is_muted ? "Включить уведомления" : "Отключить уведомления"}
            </button>
          )}
          <div className="message-feed">
            {messages.map((message) => (
              <div className={message.sender_id === me ? "message mine" : "message"} key={message.id}>
                <p>{message.body}</p>
                {message.media.map((item) => (
                  // Authenticated media endpoint intentionally has no public URL.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={item.id}
                    src={`${apiUrl}/message-media/${item.id}`}
                    alt="Изображение в сообщении"
                    width={item.width}
                    height={item.height}
                  />
                ))}
                {message.sender_id === me && message.read_at && <small>Прочитано</small>}
                {message.sender_id !== me && (
                  <form onSubmit={(event) => void reportMessage(event, message.id)}>
                    <label className="sr-only" htmlFor={`report-reason-${message.id}`}>Причина жалобы</label>
                    <select id={`report-reason-${message.id}`} name="reason_code" defaultValue="spam" disabled={reportedMessages.has(message.id)}>
                      <option value="spam">Спам</option>
                      <option value="fraud">Мошенничество</option>
                      <option value="harassment">Оскорбления или преследование</option>
                      <option value="prohibited_content">Запрещённый контент</option>
                      <option value="other">Другое</option>
                    </select>
                    <button className="ghost" disabled={reportedMessages.has(message.id)}>
                      {reportedMessages.has(message.id) ? "Жалоба отправлена" : "Пожаловаться"}
                    </button>
                  </form>
                )}
              </div>
            ))}
          </div>
          {selectedId && (
            <>
              <form className="review-form" onSubmit={review}>
                <label>Оценка
                  <select name="rating" defaultValue="5">
                    {[5, 4, 3, 2, 1].map((rating) => <option value={rating} key={rating}>{rating}</option>)}
                  </select>
                </label>
                <input name="comment" maxLength={2000} placeholder="Короткий отзыв" />
                <button>Оставить отзыв</button>
              </form>
              <form className="message-form" onSubmit={send}>
                <label className="sr-only" htmlFor="message-body">Сообщение</label>
                <textarea id="message-body" name="body" maxLength={4000} required disabled={selectedIsBlocked} placeholder="Напишите сообщение…" />
                <label>Изображение
                  <input name="media" type="file" accept="image/jpeg,image/png,image/webp" disabled={selectedIsBlocked} />
                </label>
                <button disabled={selectedIsBlocked}>Отправить</button>
              </form>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

export default function MessagesPage() {
  return <Suspense fallback={<p>Загружаем сообщения…</p>}><Inbox /></Suspense>;
}
