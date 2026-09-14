import { authHeaders } from "./client";
import type { ChatEvent } from "../types";

/**
 * POST /api/chat を呼び出し、NDJSON ストリームを 1 イベントずつ返す非同期ジェネレータ。
 * EventSource は POST / Authorization ヘッダに非対応のため fetch のストリームを用いる。
 */
export async function* streamChat(
  message: string,
  conversationId: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  });

  if (!res.ok || !res.body) {
    yield {
      type: "error",
      message: `サーバーエラー (${res.status})。ログイン状態やバックエンドの起動を確認してください。`,
    };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const parse = (line: string): ChatEvent | null => {
    const trimmed = line.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed) as ChatEvent;
    } catch {
      return null;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 1);
      const ev = parse(line);
      if (ev) yield ev;
    }
  }
  const ev = parse(buffer);
  if (ev) yield ev;
}
