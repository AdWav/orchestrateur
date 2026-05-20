import {
  IonButton,
  IonNote,
  IonSpinner,
  IonTextarea,
} from "@ionic/react";
import { useCallback, useEffect, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  getJourneyConversationId,
  resetJourneyConversationId,
} from "../lib/conversationSession";
import type { ChatTurn } from "../lib/api";
import { streamSamplingPreview, type SamplingPreviewStreamEvent } from "../lib/api";
import {
  chatHistoryCharCount,
  countPriorTurns,
  journeyMessagesToChatHistory,
  tracesToChatMessages,
  type JourneyChatMessage,
} from "../lib/journeyHistory";
import {
  createTrace,
  fetchConversationTraces,
  fetchTrace,
  patchTraceMetadata,
  patchTraceSpan,
  startTraceSpan,
  traceServiceBaseUrl,
  TRACE_META_ASSISTANT_TEXT,
  TRACE_META_CONTEXT_MODE,
  TRACE_META_HISTORY_CHARS,
  TRACE_META_HISTORY_MESSAGES,
  TRACE_META_USER_TEXT,
  type TraceRecordDto,
  type TraceSpanDto,
} from "../lib/traceApi";

import "./ConversationJourneyPanel.css";

function clip(s: string, max: number): string {
  if (s.length <= max) {
    return s;
  }
  return `${s.slice(0, max)}…`;
}

function spanDurationMs(span: TraceSpanDto): number | null {
  if (!span.ended_at) {
    return null;
  }
  return new Date(span.ended_at).getTime() - new Date(span.started_at).getTime();
}

const ConversationJourneyPanel = () => {
  const { t, messages } = useI18n();
  const [conversationId, setConversationId] = useState(getJourneyConversationId);
  const [draft, setDraft] = useState("");
  const [chatMessages, setChatMessages] = useState<JourneyChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceRecordDto | null>(null);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [runError, setRunError] = useState<string | null>(null);

  const stageLabel = useCallback(
    (stage: string) => {
      const labels = messages.journey.stageLabels as Record<string, string>;
      return labels[stage] ?? stage;
    },
    [messages.journey.stageLabels],
  );

  const loadTraceTimeline = useCallback(async (traceId: string) => {
    setSelectedTraceId(traceId);
    setTrace(await fetchTrace(traceId));
  }, []);

  const reloadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const { traces } = await fetchConversationTraces(conversationId);
      const msgs = tracesToChatMessages(traces);
      setChatMessages(msgs);
      const last = traces[traces.length - 1];
      if (last) {
        await loadTraceTimeline(last.trace_id);
      } else {
        setSelectedTraceId(null);
        setTrace(null);
      }
    } catch {
      /* service indisponible : on garde l'état local */
    } finally {
      setHistoryLoading(false);
    }
  }, [conversationId, loadTraceTimeline]);

  useEffect(() => {
    void reloadHistory();
  }, [reloadHistory]);

  const runPipeline = useCallback(
    async (userText: string, priorTurns: number, chatHistory: ChatTurn[]) => {
      const historyChars = chatHistoryCharCount(chatHistory);
      const historyMsgCount = chatHistory.length;
      const { trace_id } = await createTrace({
        conversation_id: conversationId,
        metadata: { source: "orchestrateur-ui" },
      });

      const refresh = async () => {
        setTrace(await fetchTrace(trace_id));
        setSelectedTraceId(trace_id);
      };

      let sp = await startTraceSpan(trace_id, {
        stage: "user_input",
        summary_in: clip(userText, 200),
      });
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.userInput"),
      });
      await refresh();

      sp = await startTraceSpan(trace_id, {
        stage: "intent",
        summary_in: clip(userText, 120),
      });
      await new Promise((r) => setTimeout(r, 90));
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.intent", { snippet: clip(userText, 80) }),
      });
      await refresh();

      sp = await startTraceSpan(trace_id, {
        stage: "context",
        summary_in:
          historyMsgCount > 0
            ? t("journey.spanIn.contextWithHistory", { count: String(priorTurns) })
            : t("journey.spanIn.context"),
        attributes: {
          history_messages: historyMsgCount,
          history_chars: historyChars,
        },
      });
      await new Promise((r) => setTimeout(r, 90));
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out:
          historyMsgCount > 0
            ? t("journey.spanOut.contextSentToModel", {
                messages: String(historyMsgCount),
                chars: String(historyChars),
              })
            : t("journey.spanOut.context"),
      });
      await refresh();

      sp = await startTraceSpan(trace_id, {
        stage: "reasoning",
        summary_in: t("journey.spanIn.reasoning"),
      });
      await new Promise((r) => setTimeout(r, 90));
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out:
          historyMsgCount > 0
            ? t("journey.spanOut.reasoningWithHistory", {
                messages: String(historyMsgCount),
              })
            : t("journey.spanOut.reasoning"),
      });
      await refresh();

      sp = await startTraceSpan(trace_id, {
        stage: "generation",
        summary_in:
          historyMsgCount > 0
            ? t("journey.spanIn.generationWithHistory", {
                messages: String(historyMsgCount),
                snippet: clip(userText, 80),
              })
            : clip(userText, 160),
        attributes: {
          history_messages: historyMsgCount,
        },
      });
      await refresh();

      let assistant = "";
      const doneHolder: {
        ev: Extract<SamplingPreviewStreamEvent, { event: "done" }> | null;
      } = { ev: null };
      try {
        await streamSamplingPreview(
          {
            prompt: userText,
            history: chatHistory.length > 0 ? chatHistory : undefined,
          },
          {
            onToken: (tok) => {
              assistant += tok;
            },
            onDone: (ev) => {
              doneHolder.ev = ev;
            },
          },
        );
      } catch (err) {
        await patchTraceSpan(trace_id, sp.span_id, {
          status: "error",
          error_message: err instanceof Error ? err.message : String(err),
        });
        await refresh();
        throw err;
      }

      if (doneHolder.ev) {
        const de = doneHolder.ev;
        await patchTraceSpan(trace_id, sp.span_id, {
          status: "ok",
          summary_out: t("journey.spanOut.generation", {
            model: de.model,
            tokens: String(de.stats.eval_count ?? "—"),
          }),
          attributes: {
            model: de.model,
            stats: de.stats,
          },
        });
      } else {
        await patchTraceSpan(trace_id, sp.span_id, {
          status: "error",
          error_message: "Stream ended without done event",
        });
      }

      await refresh();

      const assistantText = assistant.trim() || t("journey.assistantFallback");

      const spResp = await startTraceSpan(trace_id, {
        stage: "response",
        summary_in: t("journey.spanIn.response"),
      });
      await patchTraceSpan(trace_id, spResp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.response", {
          chars: String(assistant.length),
        }),
      });

      const contextMode =
        doneHolder.ev?.context_mode ?? (historyMsgCount > 0 ? "chat" : "generate");

      await patchTraceMetadata(trace_id, {
        [TRACE_META_USER_TEXT]: userText,
        [TRACE_META_ASSISTANT_TEXT]: assistantText,
        [TRACE_META_CONTEXT_MODE]: contextMode,
        [TRACE_META_HISTORY_MESSAGES]:
          doneHolder.ev?.history_messages ?? historyMsgCount,
        [TRACE_META_HISTORY_CHARS]: doneHolder.ev?.history_chars ?? historyChars,
      });
      await refresh();
    },
    [conversationId, t],
  );

  const handleSend = useCallback(async () => {
    const text = draft.trim();
    if (!text || busy) {
      return;
    }
    const priorHistory = journeyMessagesToChatHistory(chatMessages);
    const priorTurns = countPriorTurns(chatMessages);
    setBusy(true);
    setRunError(null);
    setDraft("");
    const at = new Date().toISOString();
    setChatMessages((m) => [
      ...m,
      { role: "user", text, at, traceId: "pending" },
    ]);

    try {
      await runPipeline(text, priorTurns, priorHistory);
      await reloadHistory();
    } catch (e) {
      setRunError(
        e instanceof Error ? e.message : t("journey.previewFailed"),
      );
      setChatMessages((m) => m.filter((row) => row.traceId !== "pending"));
    } finally {
      setBusy(false);
    }
  }, [busy, chatMessages, draft, reloadHistory, runPipeline, t]);

  const handleNewConversation = useCallback(() => {
    const id = resetJourneyConversationId();
    setConversationId(id);
    setChatMessages([]);
    setTrace(null);
    setSelectedTraceId(null);
    setRunError(null);
    setHistoryLoading(false);
  }, []);

  const handleSelectTurn = useCallback(
    (traceId: string) => {
      if (traceId === "pending" || traceId === selectedTraceId) {
        return;
      }
      void loadTraceTimeline(traceId);
    },
    [loadTraceTimeline, selectedTraceId],
  );

  return (
    <div className="ion-padding">
      <h2 className="conversation-journey__page-title">
        {messages.journey.panelTitle}
      </h2>
      <IonNote className="conversation-journey__hint">
        {t("journey.traceUrlHint", { url: traceServiceBaseUrl })}
      </IonNote>
      <IonNote className="conversation-journey__hint">
        {t("journey.conversationIdHint", {
          id: conversationId.slice(0, 8),
        })}
      </IonNote>

      <div className="conversation-journey__toolbar">
        <IonButton
          fill="outline"
          size="small"
          disabled={busy}
          onClick={handleNewConversation}
        >
          {messages.journey.newConversation}
        </IonButton>
        {historyLoading ? (
          <IonNote>{messages.journey.loadingHistory}</IonNote>
        ) : null}
      </div>

      <div className="conversation-journey">
        <section
          className="conversation-journey__pane"
          aria-label={messages.journey.chatTitle}
        >
          <h3 className="conversation-journey__pane-head">{messages.journey.chatTitle}</h3>
          <div className="conversation-journey__messages">
            {historyLoading && chatMessages.length === 0 ? (
              <IonSpinner name="crescent" />
            ) : null}
            {!historyLoading && chatMessages.length === 0 ? (
              <IonNote>{messages.journey.emptyChat}</IonNote>
            ) : null}
            {chatMessages.map((msg, idx) => {
              const selected =
                msg.traceId !== "pending" && msg.traceId === selectedTraceId;
              return (
                <div
                  key={`${msg.traceId}-${msg.role}-${idx}`}
                  role={msg.traceId !== "pending" ? "button" : undefined}
                  tabIndex={msg.traceId !== "pending" ? 0 : undefined}
                  className={
                    msg.role === "user"
                      ? `conversation-journey__bubble conversation-journey__bubble--user${
                          selected ? " conversation-journey__bubble--selected" : ""
                        }${msg.traceId !== "pending" ? " conversation-journey__bubble--clickable" : ""}`
                      : `conversation-journey__bubble conversation-journey__bubble--assistant${
                          selected ? " conversation-journey__bubble--selected" : ""
                        }${msg.traceId !== "pending" ? " conversation-journey__bubble--clickable" : ""}`
                  }
                  onClick={() => handleSelectTurn(msg.traceId)}
                  onKeyDown={(ev) => {
                    if (ev.key === "Enter" || ev.key === " ") {
                      ev.preventDefault();
                      handleSelectTurn(msg.traceId);
                    }
                  }}
                >
                  {msg.text}
                  <span className="conversation-journey__meta">{msg.at}</span>
                </div>
              );
            })}
          </div>
          <div className="conversation-journey__composer">
            {runError ? <IonNote color="danger">{runError}</IonNote> : null}
            <IonTextarea
              value={draft}
              placeholder={messages.journey.placeholder}
              autoGrow
              disabled={busy}
              onIonInput={(ev) => setDraft(ev.detail.value ?? "")}
            />
            <div className="conversation-journey__composer-row">
              <IonButton
                expand="block"
                disabled={busy || !draft.trim()}
                onClick={() => void handleSend()}
              >
                {busy ? <IonSpinner name="crescent" /> : messages.journey.send}
              </IonButton>
            </div>
          </div>
        </section>

        <section
          className="conversation-journey__pane"
          aria-label={messages.journey.traceTitle}
        >
          <h3 className="conversation-journey__pane-head">{messages.journey.traceTitle}</h3>
          <IonNote className="conversation-journey__trace-select-hint">
            {messages.journey.selectTraceHint}
          </IonNote>
          <div className="conversation-journey__timeline">
            {!trace?.spans.length ? (
              <IonNote>{messages.journey.emptyTrace}</IonNote>
            ) : null}
            {trace?.spans.map((span) => {
              const ms = spanDurationMs(span);
              const pending = span.status === "pending";
              const err = span.status === "error";
              return (
                <article
                  key={span.span_id}
                  className={
                    err
                      ? "conversation-journey__span-card conversation-journey__span-card--error"
                      : pending
                        ? "conversation-journey__span-card conversation-journey__span-card--pending"
                        : "conversation-journey__span-card"
                  }
                >
                  <div className="conversation-journey__span-head">
                    <span className="conversation-journey__span-stage">
                      {stageLabel(span.stage)}
                    </span>
                    <span
                      className={
                        span.status === "ok"
                          ? "conversation-journey__badge conversation-journey__badge--ok"
                          : err
                            ? "conversation-journey__badge conversation-journey__badge--error"
                            : "conversation-journey__badge conversation-journey__badge--pending"
                      }
                    >
                      {span.status}
                    </span>
                    {ms !== null ? (
                      <span className="conversation-journey__span-dur">{ms} ms</span>
                    ) : null}
                  </div>
                  {span.summary_in ? (
                    <p className="conversation-journey__span-line">
                      <strong>in</strong> {span.summary_in}
                    </p>
                  ) : null}
                  {span.summary_out ? (
                    <p className="conversation-journey__span-line">
                      <strong>out</strong> {span.summary_out}
                    </p>
                  ) : null}
                  {span.error_message ? (
                    <p className="conversation-journey__span-line">{span.error_message}</p>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
};

export default ConversationJourneyPanel;
