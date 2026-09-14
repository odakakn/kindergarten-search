import type { Kindergarten } from "../types";
import KindergartenCard from "./KindergartenCard";

export type Msg =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "assistant"; text: string }
  | { id: string; kind: "tool"; label: string; agent?: string | null; done?: boolean }
  | { id: string; kind: "cards"; items: Kindergarten[] }
  | { id: string; kind: "favorite"; action: "added" | "removed"; name: string }
  | {
      id: string;
      kind: "visit";
      confirmation_id: string;
      name: string;
      preferred_dates: string[];
    }
  | { id: string; kind: "visit_cancel"; name: string; confirmation_id: string }
  | { id: string; kind: "notice"; text: string }
  | { id: string; kind: "error"; text: string; detail?: string };

interface Props {
  msg: Msg;
  favoritedIds: Set<string>;
  onToggleFavorite: (kg: Kindergarten) => void;
  onConsultVisit: (kg: Kindergarten) => void;
}

export default function ChatMessage({
  msg,
  favoritedIds,
  onToggleFavorite,
  onConsultVisit,
}: Props) {
  switch (msg.kind) {
    case "user":
      return (
        <div className="bubble-row right">
          <div className="bubble user">{msg.text}</div>
        </div>
      );
    case "assistant":
      return (
        <div className="bubble-row left">
          <div className="avatar">🌷</div>
          <div className="bubble assistant">{msg.text}</div>
        </div>
      );
    case "tool":
      return (
        <div className={`activity ${msg.done ? "done" : ""}`}>
          {msg.done ? <span className="check">✓</span> : <span className="spinner" />}
          {msg.agent ? (
            <span>
              <strong>{msg.agent}</strong> — {msg.label}
            </span>
          ) : (
            <span>{msg.label}</span>
          )}
        </div>
      );
    case "cards":
      return (
        <div className="cards-grid">
          {msg.items.map((kg) => (
            <KindergartenCard
              key={kg.id}
              kg={kg}
              favorited={favoritedIds.has(kg.id)}
              onToggleFavorite={onToggleFavorite}
              onConsultVisit={onConsultVisit}
            />
          ))}
        </div>
      );
    case "favorite":
      return (
        <div className="chip-note">
          {msg.action === "added" ? "♥" : "♡"} 「{msg.name}」を
          {msg.action === "added" ? "お気に入りに登録しました" : "お気に入りから外しました"}
        </div>
      );
    case "visit":
      return (
        <div className="visit-note">
          <div className="visit-badge">見学申込 受付</div>
          <div>
            <strong>{msg.name}</strong> の見学を申し込みました。
          </div>
          <div className="muted small">
            確認番号: <code>{msg.confirmation_id}</code>
            {msg.preferred_dates.length > 0 && (
              <> ／ 希望日: {msg.preferred_dates.join(", ")}</>
            )}
          </div>
          <div className="muted small">※ アプリ内のローカル記録です（外部送信はしません）。</div>
        </div>
      );
    case "visit_cancel":
      return (
        <div className="chip-note muted">
          ✕ 「{msg.name}」の見学申込を取り消しました（{msg.confirmation_id}）
        </div>
      );
    case "notice":
      return <div className="chip-note muted">{msg.text}</div>;
    case "error":
      return (
        <div className="error-box">
          {msg.text}
          {msg.detail && <div className="small mono">詳細: {msg.detail}</div>}
        </div>
      );
  }
}
