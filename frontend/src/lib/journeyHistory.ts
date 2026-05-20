import type { ChatTurn } from "./api";
import {
  TRACE_META_ASSISTANT_TEXT,
  TRACE_META_USER_TEXT,
  type TraceSummaryDto,
} from "./traceApi";

/** Limite alignée sur le backend (JOURNEY_MAX_HISTORY_MESSAGES, défaut 40). */
export const JOURNEY_MAX_HISTORY_MESSAGES = 40;

export type JourneyChatMessage = {
  role: "user" | "assistant";
  text: string;
  at: string;
  traceId: string;
};

export function tracesToChatMessages(traces: TraceSummaryDto[]): JourneyChatMessage[] {
  const rows: JourneyChatMessage[] = [];
  for (const tr of traces) {
    const user = tr.metadata[TRACE_META_USER_TEXT];
    const asst = tr.metadata[TRACE_META_ASSISTANT_TEXT];
    const at = tr.created_at;
    if (typeof user === "string" && user.trim()) {
      rows.push({ role: "user", text: user, at, traceId: tr.trace_id });
    }
    if (typeof asst === "string" && asst.trim()) {
      rows.push({ role: "assistant", text: asst, at, traceId: tr.trace_id });
    }
  }
  return rows;
}

export function countPriorTurns(messages: JourneyChatMessage[]): number {
  return messages.filter((m) => m.role === "assistant").length;
}

/** Historique envoye au backend (tours precedents, sans message courant). */
export function journeyMessagesToChatHistory(
  messages: JourneyChatMessage[],
): ChatTurn[] {
  const rows: ChatTurn[] = [];
  for (const msg of messages) {
    if (msg.traceId === "pending") {
      continue;
    }
    const text = msg.text.trim();
    if (!text) {
      continue;
    }
    rows.push({
      role: msg.role,
      content: text,
    });
  }
  if (rows.length <= JOURNEY_MAX_HISTORY_MESSAGES) {
    return rows;
  }
  return rows.slice(-JOURNEY_MAX_HISTORY_MESSAGES);
}

export function chatHistoryCharCount(history: ChatTurn[]): number {
  return history.reduce((n, row) => n + row.content.length, 0);
}
