import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonModal,
  IonNote,
  IonTitle,
  IonToggle,
  IonToolbar,
} from "@ionic/react";
import { type CSSProperties, useEffect, useMemo, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  fetchSamplingTokenizeCapabilities,
  postSamplingTokenize,
  type ModelTokenPiece,
  type SamplingTokenizeResponse,
  type SamplingTokenizeCapabilitiesResponse,
} from "../lib/api";

import { previewTokenTone } from "./previewTokenLayer";

type TokenSection = "input" | "output";

type SelectedToken = {
  section: TokenSection;
  index: number;
} | null;

type PreviewTokenOutputProps = {
  promptText: string;
  text: string;
  streamChunks: string[];
  streaming: boolean;
  previewModel: string | null;
  tokenGaugeMax: number | null;
  showTokenLayer: boolean;
  onShowTokenLayerChange: (enabled: boolean) => void;
};

const BPE_DEBOUNCE_MS = 280;

function TokenSpanList({
  tokens,
  section,
  toneOffset,
  selected,
  onSelect,
}: {
  tokens: ModelTokenPiece[];
  section: TokenSection;
  toneOffset: number;
  selected: SelectedToken;
  onSelect: (section: TokenSection, index: number) => void;
}) {
  const { t } = useI18n();

  return (
    <>
      {tokens.map((token, index) => (
        <span
          key={`${section}-${index}-${token.id}`}
          className={
            selected?.section === section && selected.index === index
              ? "sampling-preview-token sampling-preview-token--bpe sampling-preview-token--active"
              : "sampling-preview-token sampling-preview-token--bpe"
          }
          data-tone={previewTokenTone(toneOffset + index)}
          title={t("sampling.bpeTokenTitle", {
            index: index + 1,
            id: token.id,
          })}
          role="button"
          tabIndex={0}
          onClick={() => onSelect(section, index)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onSelect(section, index);
            }
          }}
        >
          {token.text}
        </span>
      ))}
    </>
  );
}

export default function PreviewTokenOutput({
  promptText,
  text,
  streamChunks: _streamChunks,
  streaming,
  previewModel,
  tokenGaugeMax,
  showTokenLayer,
  onShowTokenLayerChange,
}: PreviewTokenOutputProps) {
  const { messages, t } = useI18n();
  const hasOutput = text.length > 0;
  const hasPrompt = promptText.length > 0;
  const hasContent = hasOutput || hasPrompt;
  const [capabilities, setCapabilities] =
    useState<SamplingTokenizeCapabilitiesResponse | null>(null);
  const [inputBpeTokens, setInputBpeTokens] = useState<ModelTokenPiece[]>([]);
  const [outputBpeTokens, setOutputBpeTokens] = useState<ModelTokenPiece[]>([]);
  const [inputBpePayload, setInputBpePayload] = useState<SamplingTokenizeResponse | null>(null);
  const [outputBpePayload, setOutputBpePayload] = useState<SamplingTokenizeResponse | null>(
    null,
  );
  const [inputBpeBusy, setInputBpeBusy] = useState(false);
  const [outputBpeBusy, setOutputBpeBusy] = useState(false);
  const [bpeError, setBpeError] = useState<string | null>(null);
  const [selectedToken, setSelectedToken] = useState<SelectedToken>(null);
  const [detailsMode, setDetailsMode] = useState<"gguf" | "token" | null>(null);

  const bpeAvailable =
    capabilities !== null && capabilities.source !== "unavailable";
  const bpeBusy = inputBpeBusy || outputBpeBusy;

  useEffect(() => {
    if (!hasContent) {
      return;
    }
    let cancelled = false;
    void fetchSamplingTokenizeCapabilities()
      .then((payload) => {
        if (!cancelled) {
          setCapabilities(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCapabilities({
            ollama_api: false,
            llama_cpp: false,
            source: "unavailable",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [hasContent]);

  useEffect(() => {
    if (!showTokenLayer || !bpeAvailable || !hasPrompt) {
      setInputBpeTokens([]);
      setInputBpePayload(null);
      return;
    }

    let cancelled = false;
    setInputBpeBusy(true);
    setBpeError(null);
    void postSamplingTokenize({
      text: promptText,
      model: previewModel,
    })
      .then((response) => {
        if (!cancelled) {
          setInputBpeTokens(response.tokens);
          setInputBpePayload(response);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setInputBpeTokens([]);
          setInputBpePayload(null);
          setBpeError(
            error instanceof Error ? error.message : messages.sampling.bpeTokenizeError,
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setInputBpeBusy(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [
    bpeAvailable,
    hasPrompt,
    messages.sampling.bpeTokenizeError,
    previewModel,
    promptText,
    showTokenLayer,
  ]);

  useEffect(() => {
    if (!showTokenLayer || !bpeAvailable || !hasOutput) {
      setOutputBpeTokens([]);
      setOutputBpePayload(null);
      return;
    }

    let cancelled = false;
    const handle = window.setTimeout(() => {
      setOutputBpeBusy(true);
      setBpeError(null);
      void postSamplingTokenize({
        text,
        model: previewModel,
      })
        .then((response) => {
          if (!cancelled) {
            setOutputBpeTokens(response.tokens);
            setOutputBpePayload(response);
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            setOutputBpeTokens([]);
            setOutputBpePayload(null);
            setBpeError(
              error instanceof Error ? error.message : messages.sampling.bpeTokenizeError,
            );
          }
        })
        .finally(() => {
          if (!cancelled) {
            setOutputBpeBusy(false);
          }
        });
    }, streaming ? BPE_DEBOUNCE_MS : 0);

    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [
    bpeAvailable,
    hasOutput,
    messages.sampling.bpeTokenizeError,
    previewModel,
    showTokenLayer,
    streaming,
    text,
  ]);

  useEffect(() => {
    if (selectedToken === null) {
      return;
    }
    const tokens = selectedToken.section === "input" ? inputBpeTokens : outputBpeTokens;
    if (selectedToken.index >= tokens.length) {
      setSelectedToken(null);
    }
  }, [inputBpeTokens.length, outputBpeTokens.length, selectedToken]);

  const activeOutputTokenCount = useMemo(() => {
    if (!showTokenLayer || !bpeAvailable) {
      return 0;
    }
    if (streaming) {
      return Math.max(outputBpeTokens.length, _streamChunks.length);
    }
    return outputBpeTokens.length;
  }, [
    bpeAvailable,
    outputBpeTokens.length,
    showTokenLayer,
    streaming,
    _streamChunks.length,
  ]);

  const effectiveTokenGaugeMax =
    tokenGaugeMax !== null && Number.isFinite(tokenGaugeMax) && tokenGaugeMax > 0
      ? tokenGaugeMax
      : Math.max(activeOutputTokenCount, 1);
  const tokenGaugeRatio = useMemo(
    () => Math.max(0, Math.min(activeOutputTokenCount / effectiveTokenGaugeMax, 1)),
    [activeOutputTokenCount, effectiveTokenGaugeMax],
  );
  const tokenGaugeAngle = `${(tokenGaugeRatio * 360).toFixed(1)}deg`;
  const tokenGaugeLevel =
    tokenGaugeRatio >= 0.85 ? "danger" : tokenGaugeRatio >= 0.65 ? "warning" : "safe";
  const tokenGaugeLabel = `${streaming ? "~ " : ""}${t("sampling.bpeTokenCount", { count: activeOutputTokenCount })}`;

  const bpeSourceLabel =
    capabilities?.source === "ollama"
      ? messages.sampling.bpeSourceOllama
      : capabilities?.source === "llama_cpp"
        ? messages.sampling.bpeSourceLlamaCpp
        : null;

  const selectedBpeToken =
    selectedToken !== null
      ? (selectedToken.section === "input" ? inputBpeTokens : outputBpeTokens)[
          selectedToken.index
        ] ?? null
      : null;

  const showTokenSections =
    showTokenLayer && bpeAvailable && (inputBpeTokens.length > 0 || outputBpeTokens.length > 0);

  const handleTokenSelect = (section: TokenSection, index: number) => {
    setSelectedToken({ section, index });
    setDetailsMode("token");
  };

  return (
    <div className="sampling-settings-modal__preview-output-wrap">
      {hasContent ? (
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
            <span
              className="sampling-settings-modal__preview-token-mode-pill"
              role="button"
              tabIndex={0}
              onClick={() => setDetailsMode("gguf")}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setDetailsMode("gguf");
                }
              }}
              title={messages.sampling.tokenPayloadTitle}
            >
              {messages.sampling.tokenModeBpe}
            </span>
          ) : null}
          {showTokenLayer && activeOutputTokenCount > 0 ? (
            <span
              className={`sampling-settings-modal__preview-token-gauge sampling-settings-modal__preview-token-gauge--${tokenGaugeLevel}`}
              style={
                {
                  "--sampling-token-gauge-angle": tokenGaugeAngle,
                } as CSSProperties
              }
              role="img"
              aria-label={tokenGaugeLabel}
              title={`${tokenGaugeLabel} / ${effectiveTokenGaugeMax}`}
            >
              <span className="sampling-settings-modal__preview-token-gauge-core" aria-hidden>
                <span className="sampling-settings-modal__preview-token-gauge-value">
                  {activeOutputTokenCount}
                </span>
              </span>
            </span>
          ) : null}
        </div>
      ) : null}

      {showTokenLayer && bpeSourceLabel ? (
        <IonNote className="sampling-settings-modal__preview-bpe-source">
          {bpeSourceLabel}
        </IonNote>
      ) : null}

      {showTokenLayer && bpeError ? (
        <IonNote color="danger" className="sampling-settings-modal__preview-bpe-error">
          {bpeError}
        </IonNote>
      ) : null}

      {showTokenLayer && bpeBusy && !showTokenSections ? (
        <IonNote className="sampling-settings-modal__preview-status">
          {messages.sampling.bpeTokenizing}
        </IonNote>
      ) : null}

      {showTokenSections ? (
        <div className="sampling-settings-modal__preview-token-sections">
          {hasPrompt ? (
            <section className="sampling-settings-modal__preview-token-section">
              <header className="sampling-settings-modal__preview-token-section-header">
                <span className="sampling-settings-modal__preview-token-section-label">
                  {messages.sampling.tokenSectionInput}
                </span>
                {inputBpeTokens.length > 0 ? (
                  <span className="sampling-settings-modal__preview-token-section-count">
                    {t("sampling.bpeTokenCount", { count: inputBpeTokens.length })}
                  </span>
                ) : null}
              </header>
              <pre className="sampling-settings-modal__preview-output sampling-settings-modal__preview-output--section">
                {inputBpeTokens.length > 0 ? (
                  <TokenSpanList
                    tokens={inputBpeTokens}
                    section="input"
                    toneOffset={0}
                    selected={selectedToken}
                    onSelect={handleTokenSelect}
                  />
                ) : inputBpeBusy ? (
                  messages.sampling.bpeTokenizing
                ) : (
                  promptText
                )}
              </pre>
            </section>
          ) : null}
          {hasOutput ? (
            <section className="sampling-settings-modal__preview-token-section">
              <header className="sampling-settings-modal__preview-token-section-header">
                <span className="sampling-settings-modal__preview-token-section-label">
                  {messages.sampling.tokenSectionOutput}
                </span>
                {activeOutputTokenCount > 0 ? (
                  <span className="sampling-settings-modal__preview-token-section-count">
                    {t("sampling.bpeTokenCount", { count: activeOutputTokenCount })}
                  </span>
                ) : null}
              </header>
              <pre
                className={
                  streaming
                    ? "sampling-settings-modal__preview-output sampling-settings-modal__preview-output--section sampling-settings-modal__preview-output--streaming"
                    : "sampling-settings-modal__preview-output sampling-settings-modal__preview-output--section"
                }
              >
                {outputBpeTokens.length > 0 ? (
                  <>
                    <TokenSpanList
                      tokens={outputBpeTokens}
                      section="output"
                      toneOffset={inputBpeTokens.length}
                      selected={selectedToken}
                      onSelect={handleTokenSelect}
                    />
                    {streaming ? (
                      <span className="sampling-settings-modal__preview-stream-caret" aria-hidden>
                        ▋
                      </span>
                    ) : null}
                  </>
                ) : outputBpeBusy ? (
                  messages.sampling.bpeTokenizing
                ) : (
                  text
                )}
              </pre>
            </section>
          ) : null}
        </div>
      ) : (
        <pre
          className={
            streaming && !showTokenLayer
              ? "sampling-settings-modal__preview-output sampling-settings-modal__preview-output--streaming"
              : "sampling-settings-modal__preview-output"
          }
        >
          {text}
        </pre>
      )}

      <IonModal isOpen={detailsMode === "gguf"} onDidDismiss={() => setDetailsMode(null)}>
        <IonHeader>
          <IonToolbar>
            <IonTitle>{messages.sampling.selectedTokenDetails}</IonTitle>
            <IonButtons slot="end">
              <IonButton onClick={() => setDetailsMode(null)}>{messages.common.close}</IonButton>
            </IonButtons>
          </IonToolbar>
        </IonHeader>
        <IonContent className="ion-padding">
          <pre className="sampling-settings-modal__preview-token-json">
            {JSON.stringify(
              {
                input: inputBpePayload,
                output: outputBpePayload,
              },
              null,
              2,
            )}
          </pre>
        </IonContent>
      </IonModal>

      <IonModal
        isOpen={detailsMode === "token" && selectedBpeToken !== null}
        onDidDismiss={() => setDetailsMode(null)}
      >
        <IonHeader>
          <IonToolbar>
            <IonTitle>{messages.sampling.selectedTokenDetails}</IonTitle>
            <IonButtons slot="end">
              <IonButton onClick={() => setDetailsMode(null)}>{messages.common.close}</IonButton>
            </IonButtons>
          </IonToolbar>
        </IonHeader>
        <IonContent className="ion-padding">
          <pre className="sampling-settings-modal__preview-token-json">
            {JSON.stringify(
              selectedBpeToken
                ? {
                    section: selectedToken?.section,
                    id: selectedBpeToken.id,
                    text: selectedBpeToken.text,
                  }
                : null,
              null,
              2,
            )}
          </pre>
        </IonContent>
      </IonModal>
    </div>
  );
}
