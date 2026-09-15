import { useEffect, useRef, useState, type FormEvent } from "react";
import { streamChat } from "../api/chatStream";
import { apiDelete, apiGet, apiPost, apiPut } from "../api/client";
import ChatMessage, { type Msg } from "../components/ChatMessage";
import ConversationSidebar from "../components/ConversationSidebar";
import KindergartenDetailModal from "../components/KindergartenDetailModal";
import type { ConversationDetail, ConversationSummary, Kindergarten } from "../types";

const newId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `m-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const SUGGESTIONS = [
  "3歳の子に、世田谷区で英語教育に力を入れている園を探しています。",
  "共働きなので預かり保育が長い園を、月4万円くらいまでで知りたいです。",
  "武蔵野市で自然体験が豊富な、のびのび系の幼稚園はありますか？",
];

const deriveTitle = (msgs: Msg[]): string => {
  const fu = msgs.find((m) => m.kind === "user") as
    | Extract<Msg, { kind: "user" }>
    | undefined;
  const t = (fu?.text ?? "").trim();
  if (!t) return "新しいチャット";
  return t.length > 40 ? `${t.slice(0, 40)}…` : t;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [favoritedIds, setFavoritedIds] = useState<Set<string>>(new Set());
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [detailKg, setDetailKg] = useState<Kindergarten | null>(null);
  const dirtyRef = useRef(false);
  const sendingRef = useRef(false);
  // カードは検索直後に即描画せず、説明テキストが出始める直前まで一旦バッファに溜める
  const cardsBufferRef = useRef<Msg[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = () =>
    apiGet<ConversationSummary[]>("/api/conversations")
      .then(setConversations)
      .catch(() => {});

  // 起動時: お気に入り＋会話一覧を読み込み、最新会話を復元
  useEffect(() => {
    apiGet<Kindergarten[]>("/api/favorites")
      .then((favs) => setFavoritedIds(new Set(favs.map((f) => f.id))))
      .catch(() => {});
    apiGet<ConversationSummary[]>("/api/conversations")
      .then((list) => {
        setConversations(list);
        if (list.length > 0) void selectConversation(list[0].id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ターン完了時（streaming が false）に会話をサーバへ保存する
  useEffect(() => {
    if (streaming || !dirtyRef.current || !currentId) return;
    dirtyRef.current = false;
    apiPut(`/api/conversations/${currentId}`, { messages, title: deriveTitle(messages) })
      .then(() => loadConversations())
      .catch(() => {});
  }, [streaming, messages, currentId]);

  const markLastToolDone = (arr: Msg[]): Msg[] => {
    const last = arr[arr.length - 1];
    if (last && last.kind === "tool" && !last.done) {
      const copy = arr.slice();
      copy[copy.length - 1] = { ...last, done: true };
      return copy;
    }
    return arr;
  };

  const finalizeTools = () =>
    setMessages((prev) =>
      prev.map((m) => (m.kind === "tool" && !m.done ? { ...m, done: true } : m)),
    );

  // 溜めておいたカード（検索結果）を messages 末尾へ追加する。
  // 最初の説明テキスト到達時に呼び、カードを本文の上に置く（テキストが無い場合の保険で finally でも呼ぶ）。
  const flushCards = () => {
    if (cardsBufferRef.current.length === 0) return;
    const buffered = cardsBufferRef.current;
    cardsBufferRef.current = [];
    setMessages((prev) => [...prev, ...buffered]);
    dirtyRef.current = true;
  };

  const push = (m: Msg) => setMessages((prev) => [...markLastToolDone(prev), m]);

  const appendAssistantText = (text: string) =>
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.kind === "assistant") {
        const copy = prev.slice();
        copy[copy.length - 1] = { ...last, text: last.text + text };
        return copy;
      }
      return [...markLastToolDone(prev), { id: newId(), kind: "assistant", text }];
    });

  const selectConversation = async (id: string) => {
    if (streaming) return;
    try {
      const detail = await apiGet<ConversationDetail>(`/api/conversations/${id}`);
      dirtyRef.current = false;
      setMessages(detail.messages as Msg[]);
      setCurrentId(id);
    } catch {
      /* ignore */
    }
  };

  const newChat = () => {
    if (streaming) return;
    dirtyRef.current = false;
    setMessages([]);
    setCurrentId(null);
  };

  const removeConversation = async (id: string) => {
    if (streaming) return;
    try {
      await apiDelete(`/api/conversations/${id}`);
    } catch {
      /* ignore */
    }
    if (id === currentId) newChat();
    void loadConversations();
  };

  // currentId が無ければ会話を作成して id を返す
  const ensureConversation = async (): Promise<string> => {
    if (currentId) return currentId;
    const conv = await apiPost<ConversationDetail>("/api/conversations");
    setCurrentId(conv.id);
    setConversations((prev) => [
      { id: conv.id, title: conv.title, updated_at: new Date().toISOString(), message_count: 0 },
      ...prev,
    ]);
    return conv.id;
  };

  const runChat = async (message: string) => {
    if (!message.trim() || sendingRef.current) return;
    // 同期的なロックを await より前に取得し、連打による会話の二重生成・並行実行を防ぐ
    sendingRef.current = true;
    setStreaming(true);
    let convId: string;
    try {
      convId = await ensureConversation();
    } catch {
      push({ id: newId(), kind: "error", text: "会話の作成に失敗しました。" });
      setStreaming(false);
      sendingRef.current = false;
      return;
    }
    push({ id: newId(), kind: "user", text: message });
    setInput("");
    dirtyRef.current = true;
    try {
      for await (const ev of streamChat(message, convId)) {
        if (ev.type !== "done" && ev.type !== "error") {
          setStreaming(true);
          dirtyRef.current = true;
        }
        switch (ev.type) {
          case "text":
            // 説明テキストが出始める直前に、溜めたカードを先に描画する（カードが本文の上に来る）
            flushCards();
            appendAssistantText(ev.text);
            break;
          case "tool_use":
            push({ id: newId(), kind: "tool", label: ev.label, agent: ev.agent });
            break;
          case "cards":
            // 即時表示せずバッファへ。説明テキストが出そろうターン完了時にまとめて表示する。
            cardsBufferRef.current.push({ id: newId(), kind: "cards", items: ev.items });
            break;
          case "favorite":
            setFavoritedIds((prev) => {
              const next = new Set(prev);
              if (ev.action === "added") next.add(ev.id);
              else next.delete(ev.id);
              return next;
            });
            push({ id: newId(), kind: "favorite", action: ev.action, name: ev.name });
            break;
          case "visit":
            push({
              id: newId(),
              kind: "visit",
              confirmation_id: ev.confirmation_id,
              name: ev.name,
              preferred_dates: ev.preferred_dates,
            });
            break;
          case "visit_cancel":
            push({
              id: newId(),
              kind: "visit_cancel",
              confirmation_id: ev.confirmation_id,
              name: ev.name,
            });
            break;
          case "notice":
            push({ id: newId(), kind: "notice", text: ev.text });
            break;
          case "error":
            finalizeTools();
            setStreaming(false);
            push({ id: newId(), kind: "error", text: ev.message, detail: ev.detail });
            break;
          case "done":
            finalizeTools();
            setStreaming(false);
            break;
        }
      }
    } catch (err) {
      push({
        id: newId(),
        kind: "error",
        text: `通信エラー: ${err instanceof Error ? err.message : String(err)}`,
      });
    } finally {
      finalizeTools();
      flushCards();
      setStreaming(false);
      sendingRef.current = false;
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void runChat(input);
  };

  const toggleFavorite = async (kg: Kindergarten) => {
    const isFav = favoritedIds.has(kg.id);
    setFavoritedIds((prev) => {
      const next = new Set(prev);
      if (isFav) next.delete(kg.id);
      else next.add(kg.id);
      return next;
    });
    try {
      if (isFav) await apiDelete(`/api/favorites/${kg.id}`);
      else await apiPost(`/api/favorites/${kg.id}`);
    } catch {
      setFavoritedIds((prev) => {
        const next = new Set(prev);
        if (isFav) next.add(kg.id);
        else next.delete(kg.id);
        return next;
      });
    }
  };

  const consultVisit = (kg: Kindergarten) => {
    setDetailKg(null);
    void runChat(`「${kg.name}」（ID: ${kg.id}）の見学を申し込みたいです。`);
  };

  return (
    <div className="chat-layout">
      <ConversationSidebar
        conversations={conversations}
        currentId={currentId}
        disabled={streaming}
        onSelect={(id) => void selectConversation(id)}
        onNew={newChat}
        onDelete={(id) => void removeConversation(id)}
      />
      <div className="chat-page">
        <div className="chat-scroll">
          {messages.length === 0 && (
            <div className="welcome">
              <h2>🌷 幼稚園さがしコンシェルジュ</h2>
              <p className="muted">
                ご希望の条件（エリア・年齢・予算・重視したいこと）を教えてください。
                あなたにピッタリの幼稚園をお探しし、見学のお申し込みまでお手伝いします。
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => void runChat(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <ChatMessage
              key={m.id}
              msg={m}
              favoritedIds={favoritedIds}
              onToggleFavorite={toggleFavorite}
              onConsultVisit={consultVisit}
              onOpenDetail={setDetailKg}
            />
          ))}
          {streaming && (
            <div className="activity">
              <span className="spinner" />
              <span>考え中…</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="chat-input" onSubmit={onSubmit}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="希望条件を入力（例: 世田谷区、3歳、英語教育、月4万円まで）"
            disabled={streaming}
          />
          <button type="submit" disabled={streaming || !input.trim()}>
            送信
          </button>
        </form>
      </div>

      {detailKg && (
        <KindergartenDetailModal
          kg={detailKg}
          favorited={favoritedIds.has(detailKg.id)}
          onToggleFavorite={toggleFavorite}
          onConsultVisit={consultVisit}
          onClose={() => setDetailKg(null)}
        />
      )}
    </div>
  );
}
