import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonInput,
  IonItem,
  IonLabel,
  IonList,
  IonModal,
  IonNote,
  IonSpinner,
  IonTextarea,
  IonTitle,
  IonToolbar,
  useIonToast,
} from "@ionic/react";
import { useEffect, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  SamplingProfile,
  fetchSamplingSettings,
  postSamplingPreview,
  putLiveSamplingSettings,
} from "../lib/api";

import "./SamplingSettingsModal.css";

type SamplingSettingsModalProps = {
  isOpen: boolean;
  onDismiss: () => void;
};

type LiveFormState = {
  temperature: string;
  top_k: string;
  top_p: string;
  min_p: string;
  mirostat: string;
  mirostat_eta: string;
  mirostat_tau: string;
  presence_penalty: string;
  frequency_penalty: string;
  repeat_penalty: string;
  repeat_last_n: string;
  num_predict: string;
  stopText: string;
  logitBiasText: string;
};

function profileToForm(profile: SamplingProfile): LiveFormState {
  return {
    temperature: formatOptionalNumber(profile.temperature),
    top_k: formatOptionalNumber(profile.top_k),
    top_p: formatOptionalNumber(profile.top_p),
    min_p: formatOptionalNumber(profile.min_p),
    mirostat: formatOptionalNumber(profile.mirostat),
    mirostat_eta: formatOptionalNumber(profile.mirostat_eta),
    mirostat_tau: formatOptionalNumber(profile.mirostat_tau),
    presence_penalty: formatOptionalNumber(profile.presence_penalty),
    frequency_penalty: formatOptionalNumber(profile.frequency_penalty),
    repeat_penalty: formatOptionalNumber(profile.repeat_penalty),
    repeat_last_n: formatOptionalNumber(profile.repeat_last_n),
    num_predict: formatOptionalNumber(profile.num_predict),
    stopText: (profile.stop ?? []).join("\n"),
    logitBiasText: formatLogitBias(profile.logit_bias),
  };
}

function formatOptionalNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function formatLogitBias(bias: Record<string, number> | null | undefined): string {
  if (!bias) {
    return "";
  }
  return Object.entries(bias)
    .map(([token, weight]) => `${token}:${weight}`)
    .join("\n");
}

function parseOptionalNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseStopLines(raw: string): string[] | null {
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  return lines.length > 0 ? lines : null;
}

function parseLogitBiasLines(raw: string): Record<string, number> | null {
  const entries: Record<string, number> = {};
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const separator = trimmed.indexOf(":");
    if (separator <= 0) {
      continue;
    }
    const token = trimmed.slice(0, separator).trim();
    const weight = Number(trimmed.slice(separator + 1).trim());
    if (!token || !Number.isFinite(weight)) {
      continue;
    }
    entries[token] = weight;
  }
  return Object.keys(entries).length > 0 ? entries : null;
}

function formToPayload(form: LiveFormState): SamplingProfile {
  return {
    temperature: parseOptionalNumber(form.temperature),
    top_k: parseOptionalNumber(form.top_k),
    top_p: parseOptionalNumber(form.top_p),
    min_p: parseOptionalNumber(form.min_p),
    mirostat: parseOptionalNumber(form.mirostat),
    mirostat_eta: parseOptionalNumber(form.mirostat_eta),
    mirostat_tau: parseOptionalNumber(form.mirostat_tau),
    presence_penalty: parseOptionalNumber(form.presence_penalty),
    frequency_penalty: parseOptionalNumber(form.frequency_penalty),
    repeat_penalty: parseOptionalNumber(form.repeat_penalty),
    repeat_last_n: parseOptionalNumber(form.repeat_last_n),
    num_predict: parseOptionalNumber(form.num_predict),
    stop: parseStopLines(form.stopText),
    logit_bias: parseLogitBiasLines(form.logitBiasText),
  };
}

function profileSummaryLines(
  profile: SamplingProfile,
  labels: Record<string, string>,
): string[] {
  const lines: string[] = [];
  const entries: [keyof SamplingProfile, string][] = [
    ["temperature", labels.temperature],
    ["top_k", labels.top_k],
    ["top_p", labels.top_p],
    ["min_p", labels.min_p],
    ["num_predict", labels.num_predict],
    ["mirostat", labels.mirostat],
  ];
  for (const [key, label] of entries) {
    const value = profile[key];
    if (value !== null && value !== undefined) {
      lines.push(`${label}: ${value}`);
    }
  }
  return lines;
}

const SamplingSettingsModal = ({ isOpen, onDismiss }: SamplingSettingsModalProps) => {
  const { messages } = useI18n();
  const [presentToast] = useIonToast();
  const [loading, setLoading] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [liveForm, setLiveForm] = useState<LiveFormState | null>(null);
  const [orchestration, setOrchestration] = useState<SamplingProfile | null>(null);
  const [previewPrompt, setPreviewPrompt] = useState("");
  const [previewResult, setPreviewResult] = useState<string | null>(null);
  const [meta, setMeta] = useState<{
    settings_persist_path: string | null;
    ollama_active: boolean;
  } | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setPreviewResult(null);
    void fetchSamplingSettings()
      .then((settings) => {
        if (cancelled) {
          return;
        }
        setOrchestration(settings.orchestration);
        setLiveForm(profileToForm(settings.live));
        setMeta({
          settings_persist_path: settings.settings_persist_path,
          ollama_active: settings.ollama_active,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setLoadError(error instanceof Error ? error.message : String(error));
        setLiveForm(null);
        setOrchestration(null);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  const updateField = (field: keyof LiveFormState, value: string) => {
    setLiveForm((current) => (current ? { ...current, [field]: value } : current));
  };

  const handleSave = async () => {
    if (!liveForm) {
      return;
    }
    setSaveBusy(true);
    try {
      const saved = await putLiveSamplingSettings(formToPayload(liveForm));
      setOrchestration(saved.orchestration);
      setLiveForm(profileToForm(saved.live));
      setMeta({
        settings_persist_path: saved.settings_persist_path,
        ollama_active: saved.ollama_active,
      });
      void presentToast({
        message: messages.sampling.saved,
        duration: 2200,
        color: "success",
      });
    } catch (error: unknown) {
      void presentToast({
        message: error instanceof Error ? error.message : messages.sampling.saveError,
        duration: 3500,
        color: "danger",
      });
    } finally {
      setSaveBusy(false);
    }
  };

  const handlePreview = async () => {
    const prompt = previewPrompt.trim();
    if (!prompt) {
      return;
    }
    setPreviewBusy(true);
    setPreviewResult(null);
    try {
      const response = await postSamplingPreview({ prompt });
      setPreviewResult(response.content);
      void presentToast({
        message: messages.sampling.previewOk,
        duration: 2200,
        color: "success",
      });
    } catch (error: unknown) {
      void presentToast({
        message: error instanceof Error ? error.message : messages.sampling.previewError,
        duration: 3500,
        color: "danger",
      });
    } finally {
      setPreviewBusy(false);
    }
  };

  const orchLines =
    orchestration !== null
      ? profileSummaryLines(orchestration, messages.sampling.fields)
      : [];

  return (
    <IonModal
      id="sampling-settings-modal"
      className="popup-modal sampling-settings-modal"
      isOpen={isOpen}
      onDidDismiss={onDismiss}
    >
      <IonHeader>
        <IonToolbar>
          <IonTitle>{messages.sampling.title}</IonTitle>
          <IonButtons slot="end">
            <IonButton onClick={onDismiss}>{messages.common.close}</IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent className="ion-padding">
        {loading ? (
          <div className="sampling-settings-modal__loading">
            <IonSpinner name="crescent" />
            <span>{messages.sampling.loading}</span>
          </div>
        ) : loadError ? (
          <IonNote color="danger">{loadError}</IonNote>
        ) : liveForm && orchestration ? (
          <>
            <p className="sampling-settings-modal__intro">{messages.sampling.intro}</p>
            {!meta?.ollama_active ? (
              <IonNote color="medium" className="sampling-settings-modal__note">
                {messages.sampling.ollamaInactive}
              </IonNote>
            ) : null}
            {meta?.settings_persist_path ? (
              <IonNote color="medium" className="sampling-settings-modal__note">
                {messages.sampling.persistPathPrefix}{" "}
                <code>{meta.settings_persist_path}</code>
              </IonNote>
            ) : null}

            <h2 className="sampling-settings-modal__section-title">
              {messages.sampling.orchestrationHeading}
            </h2>
            <IonNote className="sampling-settings-modal__note">
              {messages.sampling.orchestrationHelp}
            </IonNote>
            <IonList className="sampling-settings-modal__readonly" lines="none">
              {orchLines.length > 0 ? (
                orchLines.map((line) => (
                  <IonItem key={line}>
                    <IonLabel>{line}</IonLabel>
                  </IonItem>
                ))
              ) : (
                <IonItem>
                  <IonLabel>{messages.common.none}</IonLabel>
                </IonItem>
              )}
            </IonList>

            <h2 className="sampling-settings-modal__section-title">
              {messages.sampling.liveHeading}
            </h2>
            <IonNote className="sampling-settings-modal__note">
              {messages.sampling.liveHelp}
            </IonNote>
            <IonList className="sampling-settings-modal__form" lines="full">
              <NumericField
                label={messages.sampling.fields.temperature}
                help={messages.sampling.help.temperature}
                value={liveForm.temperature}
                onChange={(value) => updateField("temperature", value)}
              />
              <NumericField
                label={messages.sampling.fields.top_k}
                help={messages.sampling.help.top_k}
                value={liveForm.top_k}
                onChange={(value) => updateField("top_k", value)}
              />
              <NumericField
                label={messages.sampling.fields.top_p}
                help={messages.sampling.help.top_p}
                value={liveForm.top_p}
                onChange={(value) => updateField("top_p", value)}
              />
              <NumericField
                label={messages.sampling.fields.min_p}
                help={messages.sampling.help.min_p}
                value={liveForm.min_p}
                onChange={(value) => updateField("min_p", value)}
              />
              <NumericField
                label={messages.sampling.fields.mirostat}
                help={messages.sampling.help.mirostat}
                value={liveForm.mirostat}
                onChange={(value) => updateField("mirostat", value)}
              />
              <NumericField
                label={messages.sampling.fields.mirostat_eta}
                help={messages.sampling.help.mirostat_eta}
                value={liveForm.mirostat_eta}
                onChange={(value) => updateField("mirostat_eta", value)}
              />
              <NumericField
                label={messages.sampling.fields.mirostat_tau}
                help={messages.sampling.help.mirostat_tau}
                value={liveForm.mirostat_tau}
                onChange={(value) => updateField("mirostat_tau", value)}
              />
              <NumericField
                label={messages.sampling.fields.presence_penalty}
                help={messages.sampling.help.presence_penalty}
                value={liveForm.presence_penalty}
                onChange={(value) => updateField("presence_penalty", value)}
              />
              <NumericField
                label={messages.sampling.fields.frequency_penalty}
                help={messages.sampling.help.frequency_penalty}
                value={liveForm.frequency_penalty}
                onChange={(value) => updateField("frequency_penalty", value)}
              />
              <NumericField
                label={messages.sampling.fields.repeat_penalty}
                help={messages.sampling.help.repeat_penalty}
                value={liveForm.repeat_penalty}
                onChange={(value) => updateField("repeat_penalty", value)}
              />
              <NumericField
                label={messages.sampling.fields.repeat_last_n}
                help={messages.sampling.help.repeat_last_n}
                value={liveForm.repeat_last_n}
                onChange={(value) => updateField("repeat_last_n", value)}
              />
              <NumericField
                label={messages.sampling.fields.num_predict}
                help={messages.sampling.help.num_predict}
                value={liveForm.num_predict}
                onChange={(value) => updateField("num_predict", value)}
              />
              <IonItem>
                <IonLabel position="stacked">{messages.sampling.fields.stop}</IonLabel>
                <IonTextarea
                  autoGrow
                  value={liveForm.stopText}
                  placeholder={messages.sampling.placeholders.stop}
                  onIonInput={(event) => updateField("stopText", event.detail.value ?? "")}
                />
                <IonNote slot="helper">{messages.sampling.help.stop}</IonNote>
              </IonItem>
              <IonItem>
                <IonLabel position="stacked">{messages.sampling.fields.logit_bias}</IonLabel>
                <IonTextarea
                  autoGrow
                  value={liveForm.logitBiasText}
                  placeholder={messages.sampling.placeholders.logit_bias}
                  onIonInput={(event) =>
                    updateField("logitBiasText", event.detail.value ?? "")
                  }
                />
                <IonNote slot="helper">{messages.sampling.help.logit_bias}</IonNote>
              </IonItem>
            </IonList>
            <IonButton expand="block" disabled={saveBusy} onClick={() => void handleSave()}>
              {saveBusy ? <IonSpinner name="crescent" /> : messages.sampling.save}
            </IonButton>

            <h2 className="sampling-settings-modal__section-title">
              {messages.sampling.preview}
            </h2>
            <IonItem>
              <IonLabel position="stacked">{messages.sampling.previewPromptLabel}</IonLabel>
              <IonTextarea
                autoGrow
                value={previewPrompt}
                placeholder={messages.sampling.previewPromptPlaceholder}
                onIonInput={(event) => setPreviewPrompt(event.detail.value ?? "")}
              />
            </IonItem>
            <IonButton
              expand="block"
              fill="outline"
              disabled={previewBusy || !previewPrompt.trim()}
              onClick={() => void handlePreview()}
            >
              {previewBusy ? <IonSpinner name="crescent" /> : messages.sampling.preview}
            </IonButton>
            {previewResult ? (
              <pre className="sampling-settings-modal__preview-output">{previewResult}</pre>
            ) : null}
          </>
        ) : null}
      </IonContent>
    </IonModal>
  );
};

function NumericField({
  label,
  help,
  value,
  onChange,
}: {
  label: string;
  help: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <IonItem>
      <IonLabel position="stacked">{label}</IonLabel>
      <IonInput
        type="number"
        inputMode="decimal"
        value={value}
        onIonInput={(event) => onChange(event.detail.value ?? "")}
      />
      <IonNote slot="helper">{help}</IonNote>
    </IonItem>
  );
}

export default SamplingSettingsModal;
