import type { ConversationSummary } from "../types";

interface Props {
  conversations: ConversationSummary[];
  currentId: string | null;
  disabled?: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function ConversationSidebar({
  conversations,
  currentId,
  disabled,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <aside className="conv-sidebar">
      <button className="new-chat" onClick={onNew} disabled={disabled}>
        ＋ 新しいチャット
      </button>
      <div className="conv-list">
        {conversations.length === 0 && (
          <div className="muted small conv-empty">まだ会話はありません</div>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conv-item ${c.id === currentId ? "active" : ""}`}
            onClick={() => !disabled && onSelect(c.id)}
          >
            <span className="conv-title" title={c.title}>
              {c.title || "（無題）"}
            </span>
            <button
              className="conv-del"
              title="削除"
              onClick={(e) => {
                e.stopPropagation();
                if (!disabled) onDelete(c.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
