import { IonNote, IonSegment, IonSegmentButton, IonToggle } from "@ionic/react";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  fetchSamplingTokenizeCapabilities,
  postSamplingTokenize,
  type ModelTokenPiece,
  type SamplingTokenizeCapabilitiesResponse,
} from "../lib/api";

import { previewTokenTone } from "./previewTokenLayer";

export type PreviewTokenViewMode = "stream" | "bpe";

type PreviewTokenOutputProps = {
  text: string;
  streamChunks: string[];
  streaming: boolean;
  previewModel: string | null;
  showTokenLayer: boolean;
  onShowTokenLayerChange: (enabled: boolean) => void;
};

const BPE_DEBOUNCE_MS = 280;

export default function PreviewTokenOutput({
  text,
  streamChunks,
  streaming,
  previewModel,
  showTokenLayer,
  onShowTokenLayerChange,
}: PreviewTokenOutputProps) {
  const { messages, t } = useI18n();
  const hasText = text.length > 0;
  const [tokenViewMode, setTokenViewMode] = useState<PreviewTokenViewMode>("bpe");
  const [capabilities, setCapabilities] =
    useState<SamplingTokenizeCapabilitiesResponse | null>(null);
  const [bpeTokens, setBpeTokens] = useState<ModelTokenPiece[]>([]);
  const [bpeBusy, setBpeBusy] = useState(false);
  const [bpeError, setBpeError] = useState<string | null>(null);

  const bpeAvailable =
    capabilities !== null && capabilities.source !== "unavailable";

  useEffect(() => {
    if (!hasText) {
      return;
    }
    let cancelled = false;
    void fetchSamplingTokenizeCapabilities()
      .then((payload) => {
        if (!cancelled) {
          setCapabilities(payload);
          if (payload.source === "unavailable") {
            setTokenViewMode("stream");
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCapabilities({
            ollama_api: false,
            llama_cpp: false,
            source: "unavailable",
          });
          setTokenViewMode("stream");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [hasText]);

  useEffect(() => {
    if (!showTokenLayer || !bpeAvailable) {
      if (!bpeAvailable && tokenViewMode === "bpe") {
        setTokenViewMode("stream");
      }
      return;
    }
    if (tokenViewMode !== "bpe" || !hasText) {
      return;
    }

    const handle = window.setTimeout(() => {
      setBpeBusy(true);
      setBpeError(null);
      void postSamplingTokenize({
        text,
        model: previewModel,
      })
        .then((response) => {
          setBpeTokens(response.tokens);
        })
        .catch((error: unknown) => {
          setBpeTokens([]);
          setBpeError(
            error instanceof Error ? error.message : messages.sampling.bpeTokenizeError,
          );
        })
        .finally(() => {
          setBpeBusy(false);
        });
    }, streaming ? BPE_DEBOUNCE_MS : 0);

    return () => {
      window.clearTimeout(handle);
    };
  }, [
    bpeAvailable,
    hasText,
    messages.sampling.bpeTokenizeError,
    previewModel,
    showTokenLayer,
    streaming,
    text,
    tokenViewMode,
  ]);

  const activeTokenCount = useMemo(() => {
    if (!showTokenLayer) {
      return 0;
    }
    if (tokenViewMode === "bpe") {
      return bpeTokens.length;
    }
    return streamChunks.length;
  }, [bpeTokens.length, showTokenLayer, streamChunks.length, tokenViewMode]);

  const bpeSourceLabel =
    capabilities?.source === "ollama"
      ? messages.sampling.bpeSourceOllama
      : capabilities?.source === "llama_cpp"
        ? messages.sampling.bpeSourceLlamaCpp
        : null;

  return (
    <div className="sampling-settings-modal__preview-output-wrap">
      {hasText ? (
        <div className="sampling-settings-modal__preview-token-toolbar">
          <span className="sampling-settings-modal__preview-token-label">
            {messages.sampling.showTokens}
          </span>
          <IonToggle
            checked={showTokenLayer}
            aria-label={messages.sampling.showTokensToggleAria}
            onIonChange={(event) => onShowTokenLayerChange(event.detail.checked)}
          />
          {showTokenLayer ? (
            <IonSegment
              className="sampling-settings-modal__preview-token-mode"
              value={tokenViewMode}
              onIonChange={(event) => {
                const next = event.detail.value;
                if (next === "stream" || next === "bpe") {
                  setTokenViewMode(next);
                }
              }}
            >
              <IonSegmentButton value="stream" disabled={!hasText}>
                <span>{messages.sampling.tokenModeStream}</span>
              </IonSegmentButton>
              <IonSegmentButton value="bpe" disabled={!bpeAvailable}>
                <span>{messages.sampling.tokenModeBpe}</span>
              </IonSegmentButton>
            </IonSegment>
          ) : null}
          {showTokenLayer && activeTokenCount > 0 ? (
            <span className="sampling-settings-modal__preview-token-count">
              {tokenViewMode === "bpe"
                ? t("sampling.bpeTokenCount", { count: activeTokenCount })
                : t("sampling.tokenCount", { count: activeTokenCount })}
            </span>
          ) : null}
        </div>
      ) : null}

      {showTokenLayer && tokenViewMode === "bpe" && bpeSourceLabel ? (
        <IonNote className="sampling-settings-modal__preview-bpe-source">
          {bpeSourceLabel}
        </IonNote>
      ) : null}

      {showTokenLayer && tokenViewMode === "bpe" && bpeError ? (
        <IonNote color="danger" className="sampling-settings-modal__preview-bpe-error">
          {bpeError}
        </IonNote>
      ) : null}

      {showTokenLayer && tokenViewMode === "bpe" && bpeBusy && bpeTokens.length === 0 ? (
        <IonNote className="sampling-settings-modal__preview-status">
          {messages.sampling.bpeTokenizing}
        </IonNote>
      ) : null}

      <pre
        className={
          streaming && (!showTokenLayer || tokenViewMode === "stream")
            ? "sampling-settings-modal__preview-output sampling-settings-modal__preview-output--streaming"
            : "sampling-settings-modal__preview-output"
        }
      >
        {showTokenLayer && tokenViewMode === "bpe" && bpeTokens.length > 0 ? (
          <>
            {bpeTokens.map((token, index) => (
              <span
                key={`${index}-${token.id}`}
                className="sampling-preview-token sampling-preview-token--bpe"
                data-tone={previewTokenTone(index)}
                title={t("sampling.bpeTokenTitle", {
                  index: index + 1,
                  id: token.id,
                })}
              >
                {token.text}
              </span>
            ))}
            {streaming ? (
              <span className="sampling-settings-modal__preview-stream-caret" aria-hidden>
                ▋
              </span>
            ) : null}
          </>
        ) : showTokenLayer && tokenViewMode === "stream" ? (
          <>
            {streamChunks.map((chunk, index) => (
              <span
                key={index}
                className="sampling-preview-token"
                data-tone={previewTokenTone(index)}
                title={t("sampling.tokenIndex", { index: index + 1 })}
              >
                {chunk}
              </span>
            ))}
            {streaming ? (
              <span className="sampling-settings-modal__preview-stream-caret" aria-hidden>
                ▋
              </span>
            ) : null}
          </>
        ) : (
          text
        )}
      </pre>
    </div>
  );
}
