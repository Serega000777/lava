"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Case = { id: string; listing_id: string; status: string; assigned_to: string | null };
type Complaint = {
  id: string;
  listing_id: string;
  reason_code: string;
  details: string;
  status: string;
  coordination_signal: {
    detected: boolean;
    window_hours: number;
    reporter_count: number;
    dominant_reason_code: string | null;
    dominant_reason_count: number;
    new_account_reporter_count: number;
    indicators: string[];
  };
};
type Appeal = {
  id: string;
  case_id: string;
  reason: string;
  status: string;
};
type MessageReport = {
  id: string;
  message_id: string;
  reason_code: string;
  details: string;
  message_body: string;
  reported_user_id: string;
  media: Array<{ id: string; width: number; height: number }>;
};
type ReviewDispute = {
  id: string;
  review_id: string;
  reason_code: string;
  details: string;
  rating: number;
  review_comment: string;
  reviewer_name: string;
  reviewee_name: string;
};
type ReputationSignal = {
  user_id: string;
  display_name: string;
  detected: boolean;
  window_hours: number;
  review_count: number;
  distinct_reviewer_count: number;
  new_account_reviewer_count: number;
  dominant_rating: number | null;
  dominant_rating_count: number;
  repeat_review_count: number;
  indicators: string[];
};

const reputationIndicatorLabels: Record<string, string> = {
  review_burst: "всплеск отзывов",
  new_account_cluster: "группа новых аккаунтов",
  rating_concentration: "одинаковые оценки",
  repeat_reviewer_relationships: "повторные связи между участниками",
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ModerationPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [messageReports, setMessageReports] = useState<MessageReport[]>([]);
  const [reviewDisputes, setReviewDisputes] = useState<ReviewDispute[]>([]);
  const [reputationSignals, setReputationSignals] = useState<ReputationSignal[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const responses = await Promise.all([
        fetch(`${apiUrl}/moderation/cases`, { credentials: "include", signal }),
        fetch(`${apiUrl}/moderation/complaints`, { credentials: "include", signal }),
        fetch(`${apiUrl}/moderation/appeals`, { credentials: "include", signal }),
        fetch(`${apiUrl}/moderation/message-reports`, { credentials: "include", signal }),
        fetch(`${apiUrl}/moderation/review-disputes`, { credentials: "include", signal }),
        fetch(`${apiUrl}/moderation/reputation-signals`, { credentials: "include", signal }),
      ]);
      const failed = responses.find((response) => !response.ok);
      if (failed) {
        setMessage(failed.status === 403 ? "Недостаточно прав" : "Войдите как модератор");
        return;
      }
      const [
        caseItems,
        complaintItems,
        appealItems,
        messageReportItems,
        reviewDisputeItems,
        reputationSignalItems,
      ] = await Promise.all(responses.map((response) => response.json()));
      setCases(caseItems as Case[]);
      setComplaints(complaintItems as Complaint[]);
      setAppeals(appealItems as Appeal[]);
      setMessageReports(messageReportItems as MessageReport[]);
      setReviewDisputes(reviewDisputeItems as ReviewDispute[]);
      setReputationSignals(reputationSignalItems as ReputationSignal[]);
    } catch (error: unknown) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessage("Ошибка загрузки очереди");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // The callback performs network synchronization and updates state only after awaiting it.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function decideCase(
    caseId: string,
    decision: "approved" | "rejected" | "changes_requested",
  ) {
    const reasonCode = {
      approved: "policy_compliant",
      rejected: "misleading_content",
      changes_requested: "content_issue",
    }[decision];
    const response = await apiFetch(`${apiUrl}/moderation/cases/${caseId}/decision`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason_code: reasonCode, comment: "" }),
    });
    setMessage(response.ok ? "Решение сохранено" : "Не удалось сохранить решение");
    if (response.ok) await load();
  }

  async function decideComplaint(
    complaintId: string,
    decision: "resolved" | "dismissed",
  ) {
    const response = await apiFetch(
      `${apiUrl}/moderation/complaints/${complaintId}/decision`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision,
          resolution_code: decision === "resolved" ? "listing_restricted" : "no_violation",
          comment: "",
        }),
      },
    );
    setMessage(response.ok ? "Жалоба обработана" : "Не удалось обработать жалобу");
    if (response.ok) await load();
  }

  async function decideAppeal(appealId: string, decision: "upheld" | "overturned") {
    const response = await apiFetch(`${apiUrl}/moderation/appeals/${appealId}/decision`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        comment: decision === "upheld"
          ? "Первоначальное решение соответствует правилам."
          : "Требуется повторная независимая проверка объявления.",
      }),
    });
    setMessage(response.ok ? "Апелляция обработана" : "Не удалось обработать апелляцию");
    if (response.ok) await load();
  }

  async function decideMessageReport(reportId: string, decision: "resolved" | "dismissed") {
    const response = await apiFetch(`${apiUrl}/moderation/message-reports/${reportId}/decision`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        resolution_code: decision === "resolved" ? "user_warned" : "no_violation",
        comment: "",
      }),
    });
    setMessage(response.ok ? "Жалоба на сообщение обработана" : "Не удалось обработать жалобу");
    if (response.ok) await load();
  }

  async function decideReviewDispute(
    disputeId: string,
    outcome: "keep" | "exclude",
    disputeReason: string,
  ) {
    const response = await apiFetch(`${apiUrl}/moderation/review-disputes/${disputeId}/decision`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        outcome,
        reason_code: outcome === "keep" ? "complies" : disputeReason,
        comment: "",
      }),
    });
    setMessage(response.ok ? "Спор по отзыву обработан" : "Не удалось обработать спор");
    if (response.ok) await load();
  }

  return (
    <main className="auth-shell">
      <section className="auth-card moderation-card">
        <Link className="brand" href="/">Lava<span>.</span></Link>
        <p className="eyebrow">МОДЕРАЦИЯ</p>
        <h1>Рабочая очередь</h1>
        {message && <p role="status">{message}</p>}
        {loading && <p>Загружаем очередь…</p>}

        <h2>Объявления</h2>
        {!loading && cases.length === 0 && <p>Новых объявлений нет.</p>}
        <ul className="moderation-list">
          {cases.map((item) => (
            <li key={item.id}>
              <div><strong>Объявление</strong><small>{item.listing_id}</small></div>
              <div className="moderation-actions">
                <button onClick={() => void decideCase(item.id, "approved")}>Одобрить</button>
                <button className="danger" onClick={() => void decideCase(item.id, "rejected")}>
                  Отклонить
                </button>
                <button className="ghost" onClick={() => void decideCase(item.id, "changes_requested")}>
                  На исправление
                </button>
              </div>
            </li>
          ))}
        </ul>

        <h2>Сигналы репутации</h2>
        <p>
          Это подсказки для ручной проверки. Они не влияют на рейтинг и не применяют санкции.
        </p>
        {!loading && reputationSignals.length === 0 && <p>Подозрительных серий отзывов нет.</p>}
        <ul className="moderation-list">
          {reputationSignals.map((item) => (
            <li key={item.user_id}>
              <div>
                <strong>{item.display_name}</strong>
                <small>Пользователь {item.user_id}</small>
                <p>
                  {item.review_count} отзывов за {item.window_hours} ч. · {item.distinct_reviewer_count}
                  {" "}авторов · преобладающая оценка {item.dominant_rating ?? "—"}
                  {" "}({item.dominant_rating_count})
                </p>
                <p>
                  Новых авторов: {item.new_account_reviewer_count} · повторных связей:
                  {" "}{item.repeat_review_count}
                </p>
                <p>
                  Индикаторы: {item.indicators
                    .map((indicator) => reputationIndicatorLabels[indicator] ?? indicator)
                    .join(", ")}
                </p>
              </div>
            </li>
          ))}
        </ul>

        <h2>Жалобы</h2>
        {!loading && complaints.length === 0 && <p>Открытых жалоб нет.</p>}
        <ul className="moderation-list">
          {complaints.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.reason_code}</strong>
                <small>{item.listing_id}</small>
                {item.details && <p>{item.details}</p>}
                {item.coordination_signal.detected && (
                  <p className="coordination-warning" role="note">
                    Возможна координация: {item.coordination_signal.reporter_count} жалобщика
                    за {item.coordination_signal.window_hours} ч. Проверьте историю вручную.
                  </p>
                )}
              </div>
              <div className="moderation-actions">
                <button className="danger" onClick={() => void decideComplaint(item.id, "resolved")}>
                  Нарушение подтверждено
                </button>
                <button className="ghost" onClick={() => void decideComplaint(item.id, "dismissed")}>
                  Отклонить жалобу
                </button>
              </div>
            </li>
          ))}
        </ul>

        <h2>Сообщения</h2>
        {!loading && messageReports.length === 0 && <p>Жалоб на сообщения нет.</p>}
        <ul className="moderation-list">
          {messageReports.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.reason_code}</strong>
                <small>Сообщение {item.message_id} · пользователь {item.reported_user_id}</small>
                <p>{item.message_body}</p>
                {item.media.map((media) => (
                  // Permission-gated evidence endpoint intentionally has no public URL.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={media.id}
                    src={`${apiUrl}/moderation/message-media/${media.id}`}
                    alt="Вложение из жалобы"
                    width={media.width}
                    height={media.height}
                  />
                ))}
                {item.details && <p>{item.details}</p>}
              </div>
              <div className="moderation-actions">
                <button className="danger" onClick={() => void decideMessageReport(item.id, "resolved")}>
                  Нарушение подтверждено
                </button>
                <button className="ghost" onClick={() => void decideMessageReport(item.id, "dismissed")}>
                  Нарушения нет
                </button>
              </div>
            </li>
          ))}
        </ul>

        <h2>Споры по отзывам</h2>
        {!loading && reviewDisputes.length === 0 && <p>Открытых споров по отзывам нет.</p>}
        <ul className="moderation-list">
          {reviewDisputes.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.rating}/5 · {item.reason_code}</strong>
                <small>{item.reviewer_name} → {item.reviewee_name}</small>
                <p>{item.review_comment}</p>
                {item.details && <p>{item.details}</p>}
              </div>
              <div className="moderation-actions">
                <button className="danger" onClick={() => void decideReviewDispute(item.id, "exclude", item.reason_code)}>
                  Исключить отзыв
                </button>
                <button className="ghost" onClick={() => void decideReviewDispute(item.id, "keep", item.reason_code)}>
                  Оставить отзыв
                </button>
              </div>
            </li>
          ))}
        </ul>

        <h2>Апелляции</h2>
        {!loading && appeals.length === 0 && <p>Открытых апелляций нет.</p>}
        <ul className="moderation-list">
          {appeals.map((item) => (
            <li key={item.id}>
              <div><strong>Апелляция</strong><small>{item.case_id}</small><p>{item.reason}</p></div>
              <div className="moderation-actions">
                <button onClick={() => void decideAppeal(item.id, "overturned")}>
                  На повторную проверку
                </button>
                <button className="ghost" onClick={() => void decideAppeal(item.id, "upheld")}>
                  Оставить решение
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
