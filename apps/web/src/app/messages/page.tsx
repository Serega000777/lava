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
  unread_count: number;
};
type Message = {
  id: string;
  sender_id: string;
  body: string;
  created_at: string;
  delivered_at: string | null;
  read_at: string | null;
  media: Array<{ id: string; width: number; height: number }>;
};
type Interaction = {
  id: string;
  conversation_id: string;
  status: "awaiting_contact" | "contacted" | "completed";
  my_completion_confirmed: boolean;
  counterpart_completion_confirmed: boolean;
  completed_at: string | null;
  can_review: boolean;
  review_created: boolean;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function Inbox() {
  const params = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState(params.get("conversation") ?? "");
  const [messages, setMessages] = useState<Message[]>([]);
  const [me, setMe] = useState("");
  const [status, setStatus] = useState("Загружаем диалоги…");
  const [reputation, setReputation] = useState<{
    user_id: string;
    average_rating: string | null;
    review_count: number;
  } | null>(null);
  const [interaction, setInteraction] = useState<Interaction | null>(null);
  const [blockedUsers, setBlockedUsers] = useState<Set<string>>(new Set());
  const [reportedMessages, setReportedMessages] = useState<Set<string>>(new Set());
  const selectedConversation = conversations.find((conversation) => conversation.id === selectedId);
  const activeInteraction = interaction?.conversation_id === selectedId ? interaction : null;
  const selectedCounterpartId = selectedConversation?.counterpart_id;
  const activeReputation = reputation?.user_id === selectedCounterpartId ? reputation : null;
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
    const controller = new AbortController();
    fetch(`${apiUrl}/conversations/${selectedId}/messages`, {
      credentials: "include",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("messages failed");
        const loadedMessages = await response.json() as Message[];
        setMessages(loadedMessages);
        const delivery = await apiFetch(`${apiUrl}/conversations/${selectedId}/delivered`, {
          method: "PATCH",
          credentials: "include",
          signal: controller.signal,
        });
        const receipt = await apiFetch(`${apiUrl}/conversations/${selectedId}/read`, {
          method: "PATCH",
          credentials: "include",
          signal: controller.signal,
        });
        if (receipt.ok) {
          setConversations((current) => {
            let changed = false;
            const next = current.map((conversation) => {
              if (conversation.id !== selectedId || conversation.unread_count === 0) {
                return conversation;
              }
              changed = true;
              return { ...conversation, unread_count: 0 };
            });
            return changed ? next : current;
          });
        }
        if (!delivery.ok && !receipt.ok) {
          setStatus("Сообщения загружены, но статусы доставки не сохранены.");
        }
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setStatus("Не удалось загрузить сообщения.");
        }
      });
    fetch(`${apiUrl}/conversations/${selectedId}/interaction`, {
      credentials: "include",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("interaction failed");
        setInteraction(await response.json() as Interaction);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setStatus("Не удалось загрузить статус сделки.");
        }
      });
    if (selectedCounterpartId) {
      fetch(`${apiUrl}/users/${selectedCounterpartId}/reputation`, {
        signal: controller.signal,
      })
        .then((response) => response.ok ? response.json() : null)
        .then((data) => setReputation(data))
        .catch(() => undefined);
    }
    return () => controller.abort();
  }, [selectedCounterpartId, selectedId]);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
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
        formElement.reset();
        return;
      }
      const attached = await mediaResponse.json() as { id: string; width: number; height: number };
      setMessages((current) => current.map((item) => (
        item.id === message.id ? { ...item, media: [...item.media, attached] } : item
      )));
    }
    formElement.reset();
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
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
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
    const reviewedConversationId = selectedId;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await apiFetch(`${apiUrl}/conversations/${reviewedConversationId}/review`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rating: Number(form.get("rating")),
        comment: form.get("comment"),
      }),
    });
    if (response.status === 409) {
      setStatus("Отзыв доступен после подтверждения сделки обеими сторонами и создаётся один раз.");
      return;
    }
    if (!response.ok) {
      setStatus("Не удалось сохранить отзыв.");
      return;
    }
    setStatus("Отзыв опубликован.");
    setInteraction((current) => current?.conversation_id === reviewedConversationId ? {
        ...current,
        can_review: false,
        review_created: true,
      } : current);
    formElement.reset();
  }

  async function confirmCompletion() {
    if (!selectedId) return;
    const confirmedConversationId = selectedId;
    const response = await apiFetch(`${apiUrl}/conversations/${confirmedConversationId}/interaction/completion`, {
      method: "PUT",
      credentials: "include",
    });
    if (response.status === 409) {
      setStatus("Сначала отправьте сообщение по этому объявлению.");
      return;
    }
    if (!response.ok) {
      setStatus("Не удалось подтвердить сделку.");
      return;
    }
    const updated = await response.json() as Interaction;
    setInteraction((current) => current?.conversation_id === confirmedConversationId
      ? updated
      : current);
    setStatus(updated.status === "completed"
      ? "Сделка подтверждена обеими сторонами. Теперь можно оставить отзыв."
      : "Ваше подтверждение сохранено. Ожидаем подтверждение собеседника.");
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
              <span className="conversation-heading">
                <strong>{conversation.counterpart_name}</strong>
                {conversation.unread_count > 0 && (
                  <span
                    className="unread-badge"
                    aria-label={`Непрочитанных сообщений: ${conversation.unread_count}`}
                  >
                    {conversation.unread_count}
                  </span>
                )}
              </span>
              <span>{conversation.listing_title}</span>
            </button>
          ))}
          {status && <p role="status">{status}</p>}
        </aside>
        <section className="message-panel" aria-label="Сообщения диалога">
          {selectedId && activeReputation && (
            <p className="reputation-line">
              Репутация собеседника: {activeReputation.average_rating ?? "нет оценок"} · отзывов {activeReputation.review_count}
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
                {message.sender_id === me && (
                  <small>
                    {message.read_at ? "Прочитано" : message.delivered_at ? "Доставлено" : "Отправлено"}
                  </small>
                )}
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
              {activeInteraction && (
                <section className="review-form" aria-label="Статус сделки">
                  <strong>Подтверждение сделки</strong>
                  {activeInteraction.status === "awaiting_contact" && (
                    <p>Отправьте сообщение, чтобы начать взаимодействие.</p>
                  )}
                  {activeInteraction.status === "contacted" && (
                    <>
                      <p>
                        Ваше подтверждение: {activeInteraction.my_completion_confirmed ? "есть" : "нет"}.
                        Подтверждение собеседника: {activeInteraction.counterpart_completion_confirmed ? "есть" : "нет"}.
                      </p>
                      {!activeInteraction.my_completion_confirmed && (
                        <button type="button" onClick={() => void confirmCompletion()}>
                          Подтвердить, что сделка состоялась
                        </button>
                      )}
                    </>
                  )}
                  {activeInteraction.status === "completed" && (
                    <p>Обе стороны подтвердили, что сделка состоялась.</p>
                  )}
                </section>
              )}
              {activeInteraction?.can_review && (
                <form className="review-form" onSubmit={review}>
                  <label>Оценка
                    <select name="rating" defaultValue="5">
                      {[5, 4, 3, 2, 1].map((rating) => <option value={rating} key={rating}>{rating}</option>)}
                    </select>
                  </label>
                  <input name="comment" maxLength={2000} placeholder="Короткий отзыв" />
                  <button>Оставить отзыв</button>
                </form>
              )}
              {activeInteraction?.review_created && <p>Вы уже оставили отзыв по этой сделке.</p>}
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
