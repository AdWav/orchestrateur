import {
  IonButton,
  IonNote,
  IonSpinner,
  IonTextarea,
} from "@ionic/react";
import { useCallback, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import { streamSamplingPreview, type SamplingPreviewStreamEvent } from "../lib/api";
import {
  createTrace,
  fetchTrace,
  patchTraceSpan,
  startTraceSpan,
  traceServiceBaseUrl,
  type TraceRecordDto,
  type TraceSpanDto,
} from "../lib/traceApi";

import "./ConversationJourneyPanel.css";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  at: string;
};

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
  const [draft, setDraft] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceRecordDto | null>(null);
  const [busy, setBusy] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const stageLabel = useCallback(
    (stage: string) => {
      const labels = messages.journey.stageLabels as Record<string, string>;
      return labels[stage] ?? stage;
    },
    [messages.journey.stageLabels],
  );

  const runPipeline = useCallback(
    async (userText: string) => {
      const { trace_id } = await createTrace({
        conversation_id: `ui-${Date.now()}`,
        metadata: { source: "orchestrateur-ui" },
      });

      const refresh = async () => {
        setTrace(await fetchTrace(trace_id));
      };

      // 1 — user_input
      let sp = await startTraceSpan(trace_id, {
        stage: "user_input",
        summary_in: clip(userText, 200),
      });
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.userInput"),
      });
      await refresh();

      // 2 — intent
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

      // 3 — context
      sp = await startTraceSpan(trace_id, {
        stage: "context",
        summary_in: t("journey.spanIn.context"),
      });
      await new Promise((r) => setTimeout(r, 90));
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.context"),
      });
      await refresh();

      // 4 — reasoning
      sp = await startTraceSpan(trace_id, {
        stage: "reasoning",
        summary_in: t("journey.spanIn.reasoning"),
      });
      await new Promise((r) => setTimeout(r, 90));
      await patchTraceSpan(trace_id, sp.span_id, {
        status: "ok",
        summary_out: t("journey.spanOut.reasoning"),
      });
      await refresh();

      // 5 — generation (stream LLM via backend)
      sp = await startTraceSpan(trace_id, {
        stage: "generation",
        summary_in: clip(userText, 160),
      });
      await refresh();

      let assistant = "";
      const doneHolder: {
        ev: Extract<SamplingPreviewStreamEvent, { event: "done" }> | null;
      } = { ev: null };
      try {
        await streamSamplingPreview(
          { prompt: userText },
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

      setChatMessages((rows) => [
        ...rows,
        {
          role: "assistant",
          text: assistant.trim() || t("journey.assistantFallback"),
          at: new Date().toISOString(),
        },
      ]);

      // 6 — response
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
      await refresh();
    },
    [t],
  );

  const handleSend = useCallback(async () => {
    const text = draft.trim();
    if (!text || busy) {
      return;
    }
    setBusy(true);
    setRunError(null);
    setDraft("");
    setChatMessages((m) => [
      ...m,
      { role: "user", text, at: new Date().toISOString() },
    ]);

    try {
      await runPipeline(text);
    } catch (e) {
      setRunError(
        e instanceof Error ? e.message : t("journey.previewFailed"),
      );
    } finally {
      setBusy(false);
    }
  }, [busy, draft, runPipeline, t]);

  return (
    <div className="ion-padding">
      <h2 className="conversation-journey__page-title">
        {messages.journey.panelTitle}
      </h2>
      <IonNote className="conversation-journey__hint">
        {t("journey.traceUrlHint", { url: traceServiceBaseUrl })}
      </IonNote>

      <div className="conversation-journey">
        <section
          className="conversation-journey__pane"
          aria-label={messages.journey.chatTitle}
        >
          <h3 className="conversation-journey__pane-head">{messages.journey.chatTitle}</h3>
          <div className="conversation-journey__messages">
            {chatMessages.length === 0 ? (
              <IonNote>{messages.journey.emptyChat}</IonNote>
            ) : null}
            {chatMessages.map((msg, idx) => (
              <div
                key={`${msg.at}-${idx}`}
                className={
                  msg.role === "user"
                    ? "conversation-journey__bubble conversation-journey__bubble--user"
                    : "conversation-journey__bubble conversation-journey__bubble--assistant"
                }
              >
                {msg.text}
                <span className="conversation-journey__meta">{msg.at}</span>
              </div>
            ))}
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
