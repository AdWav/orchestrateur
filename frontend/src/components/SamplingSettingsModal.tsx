import {
  IonButton,
  IonButtons,
  IonChip,
  IonContent,
  IonHeader,
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
import { useEffect, useRef, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  SamplingProfile,
  fetchSamplingSettings,
  postSamplingPreview,
  putLiveSamplingSettings,
} from "../lib/api";

import {
  LIVE_NUMERIC_FIELD_ORDER,
  SAMPLING_FIELD_SPECS,
  type FieldSpec,
  type LiveFormState,
  type LiveNumericKey,
  DIAL_STEPS,
  dialToSamplingValue,
  formatNumericDisplay,
  formToSamplingProfile,
  profileToLiveForm,
  samplingValueToDial,
  snapToSpec,
} from "./samplingFieldSpecs";
import DialRegulator from "./DialRegulator";
import type { DialRegulatorVariant } from "./dialRegulatorUtils";
import MirostatRockerSwitch, { stepMirostatValue } from "./MirostatRockerSwitch";
import {
  groupsForMode,
  type SamplingFieldGroup,
  type SamplingGroupMode,
  type SamplingTextFieldKey,
} from "./samplingFieldGroups";
import "./SamplingSettingsModal.css";

const SAMPLING_DIAL_VARIANTS: Record<LiveNumericKey, DialRegulatorVariant> = {
  temperature: "digital",
  top_k: "digital",
  top_p: "digital",
  min_p: "digital",
  mirostat: "digital",
  mirostat_eta: "digital",
  mirostat_tau: "digital",
  presence_penalty: "digital",
  frequency_penalty: "digital",
  repeat_penalty: "digital",
  repeat_last_n: "digital",
  num_predict: "digital",
};

const GROUPING_MODES: SamplingGroupMode[] = ["flat", "role", "impact"];

type RoleGroupMeta = (typeof import("../i18n/locales/fr.json"))["sampling"]["roleGroups"];
type ImpactGroupMeta = (typeof import("../i18n/locales/fr.json"))["sampling"]["impactGroups"];
type GroupMetaEntry = { title: string; hint: string };

function lookupGroupMeta(
  groupMode: SamplingGroupMode,
  groupId: string,
  roleGroups: RoleGroupMeta,
  impactGroups: ImpactGroupMeta,
): GroupMetaEntry | undefined {
  if (groupMode === "role") {
    return roleGroups[groupId as keyof RoleGroupMeta];
  }
  if (groupMode === "impact") {
    return impactGroups[groupId as keyof ImpactGroupMeta];
  }
  return undefined;
}

type SamplingSettingsModalProps = {
  isOpen: boolean;
  onDismiss?: () => void;
  embedded?: boolean;
};

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

const SamplingSettingsModal = ({
  isOpen,
  onDismiss,
  embedded = false,
}: SamplingSettingsModalProps) => {
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
  const [groupMode, setGroupMode] = useState<SamplingGroupMode>("flat");
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);

  const shouldLoad = embedded || isOpen;

  useEffect(() => {
    if (!shouldLoad) {
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
        setLiveForm(profileToLiveForm(settings.live));
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
  }, [shouldLoad]);

  const updateNumericField = (field: LiveNumericKey, value: number | null) => {
    setLiveForm((current) => (current ? { ...current, [field]: value } : current));
  };

  const updateTextField = (field: "stopText" | "logitBiasText", value: string) => {
    setLiveForm((current) => (current ? { ...current, [field]: value } : current));
  };

  const handleSave = async () => {
    if (!liveForm) {
      return;
    }
    setSaveBusy(true);
    try {
      const saved = await putLiveSamplingSettings(formToSamplingProfile(liveForm));
      setOrchestration(saved.orchestration);
      setLiveForm(profileToLiveForm(saved.live));
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

  const shellClass = embedded
    ? "sampling-settings-panel ion-padding"
    : "sampling-settings-modal__body ion-padding";

  const body = (
    <div className={shellClass}>
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

            <SamplingGroupingToolbar
              groupMode={groupMode}
              activeGroupId={activeGroupId}
              onGroupModeChange={(mode) => {
                setGroupMode(mode);
                setActiveGroupId(null);
              }}
              onActiveGroupChange={setActiveGroupId}
            />

            <LiveSamplingDials
              liveForm={liveForm}
              groupMode={groupMode}
              activeGroupId={activeGroupId}
              onNumericChange={updateNumericField}
              onTextChange={updateTextField}
            />

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
    </div>
  );

  if (embedded) {
    return body;
  }

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
      <IonContent>{body}</IonContent>
    </IonModal>
  );
};

function SamplingGroupingToolbar({
  groupMode,
  activeGroupId,
  onGroupModeChange,
  onActiveGroupChange,
}: {
  groupMode: SamplingGroupMode;
  activeGroupId: string | null;
  onGroupModeChange: (mode: SamplingGroupMode) => void;
  onActiveGroupChange: (groupId: string | null) => void;
}) {
  const { messages } = useI18n();
  const groups = groupsForMode(groupMode);

  return (
    <div
      className="sampling-settings-modal__grouping"
      role="toolbar"
      aria-label={messages.sampling.groupingModeLabel}
    >
      <p className="sampling-settings-modal__grouping-label">
        {messages.sampling.groupingModeLabel}
      </p>
      <div className="sampling-settings-modal__grouping-chips">
        {GROUPING_MODES.map((mode) => (
          <IonChip
            key={mode}
            outline={groupMode !== mode}
            color={groupMode === mode ? "primary" : undefined}
            onClick={() => onGroupModeChange(mode)}
          >
            {messages.sampling.groupingModes[mode]}
          </IonChip>
        ))}
      </div>
      {groups.length > 0 && groupMode !== "flat" ? (
        <>
          <p className="sampling-settings-modal__grouping-label">
            {messages.sampling.groupingFilterLabel}
          </p>
          <div className="sampling-settings-modal__grouping-chips">
            <IonChip
              outline={activeGroupId !== null}
              color={activeGroupId === null ? "primary" : undefined}
              onClick={() => onActiveGroupChange(null)}
            >
              {messages.sampling.groupingFilterAll}
            </IonChip>
            {groups.map((group) => {
              const meta = lookupGroupMeta(
                groupMode,
                group.id,
                messages.sampling.roleGroups,
                messages.sampling.impactGroups,
              );
              if (!meta) {
                return null;
              }
              return (
                <IonChip
                  key={group.id}
                  outline={activeGroupId !== group.id}
                  color={activeGroupId === group.id ? "primary" : undefined}
                  onClick={() => onActiveGroupChange(group.id)}
                >
                  {meta.title}
                </IonChip>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
}

function LiveSamplingDials({
  liveForm,
  groupMode,
  activeGroupId,
  onNumericChange,
  onTextChange,
}: {
  liveForm: LiveFormState;
  groupMode: SamplingGroupMode;
  activeGroupId: string | null;
  onNumericChange: (field: LiveNumericKey, value: number | null) => void;
  onTextChange: (field: "stopText" | "logitBiasText", value: string) => void;
}) {
  const { messages } = useI18n();

  if (groupMode === "flat") {
    return (
      <div
        className="sampling-settings-modal__dials"
        role="group"
        aria-label={messages.sampling.liveHeading}
      >
        <div className="sampling-settings-modal__dials-grid">
          {LIVE_NUMERIC_FIELD_ORDER.map((fieldKey) => (
            <NumericDialField
              key={fieldKey}
              fieldKey={fieldKey}
              label={messages.sampling.fields[fieldKey]}
              help={messages.sampling.help[fieldKey]}
              wheelHint={messages.sampling.wheelHint}
              spec={SAMPLING_FIELD_SPECS[fieldKey]}
              variant={SAMPLING_DIAL_VARIANTS[fieldKey]}
              value={liveForm[fieldKey]}
              unsetLabel={messages.common.none}
              closeLabel={messages.common.close}
              onChange={(value) => onNumericChange(fieldKey, value)}
            />
          ))}
        </div>
        <SamplingTextFields liveForm={liveForm} onTextChange={onTextChange} />
      </div>
    );
  }

  const groups = groupsForMode(groupMode).filter(
    (group) => activeGroupId === null || group.id === activeGroupId,
  );

  return (
    <div
      className="sampling-settings-modal__dials sampling-settings-modal__dials--grouped"
      role="group"
      aria-label={messages.sampling.liveHeading}
    >
      {groups.map((group) => {
        const meta = lookupGroupMeta(
          groupMode,
          group.id,
          messages.sampling.roleGroups,
          messages.sampling.impactGroups,
        );
        if (!meta) {
          return null;
        }
        return (
          <SamplingFieldGroupSection
            key={group.id}
            group={group}
            title={meta.title}
            hint={meta.hint}
            liveForm={liveForm}
            onNumericChange={onNumericChange}
            onTextChange={onTextChange}
          />
        );
      })}
    </div>
  );
}

function SamplingFieldGroupSection({
  group,
  title,
  hint,
  liveForm,
  onNumericChange,
  onTextChange,
}: {
  group: SamplingFieldGroup;
  title: string;
  hint: string;
  liveForm: LiveFormState;
  onNumericChange: (field: LiveNumericKey, value: number | null) => void;
  onTextChange: (field: "stopText" | "logitBiasText", value: string) => void;
}) {
  const { messages } = useI18n();
  if (group.numeric.length === 0 && !group.text?.length) {
    return null;
  }

  return (
    <section className="sampling-settings-modal__dial-group">
      <header className="sampling-settings-modal__dial-group-header">
        <h3 className="sampling-settings-modal__dial-group-title">{title}</h3>
        <p className="sampling-settings-modal__dial-group-hint">{hint}</p>
      </header>
      {group.numeric.length > 0 ? (
        <div className="sampling-settings-modal__dials-grid">
          {group.numeric.map((fieldKey) => (
            <NumericDialField
              key={fieldKey}
              fieldKey={fieldKey}
              label={messages.sampling.fields[fieldKey]}
              help={messages.sampling.help[fieldKey]}
              wheelHint={messages.sampling.wheelHint}
              spec={SAMPLING_FIELD_SPECS[fieldKey]}
              variant={SAMPLING_DIAL_VARIANTS[fieldKey]}
              value={liveForm[fieldKey]}
              unsetLabel={messages.common.none}
              closeLabel={messages.common.close}
              onChange={(value) => onNumericChange(fieldKey, value)}
            />
          ))}
        </div>
      ) : null}
      {group.text && group.text.length > 0 ? (
        <SamplingTextFields
          liveForm={liveForm}
          fields={group.text}
          onTextChange={onTextChange}
          compact
        />
      ) : null}
    </section>
  );
}

function SamplingTextFields({
  liveForm,
  onTextChange,
  fields = ["stop", "logit_bias"],
  compact = false,
}: {
  liveForm: LiveFormState;
  onTextChange: (field: "stopText" | "logitBiasText", value: string) => void;
  fields?: SamplingTextFieldKey[];
  compact?: boolean;
}) {
  const { messages } = useI18n();

  const listClass = [
    "sampling-settings-modal__form",
    "sampling-settings-modal__form--text",
    compact ? "sampling-settings-modal__form--text-compact" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <IonList className={listClass} lines="full">
      {fields.includes("stop") ? (
        <IonItem>
          <IonLabel position="stacked">{messages.sampling.fields.stop}</IonLabel>
          <IonTextarea
            autoGrow
            value={liveForm.stopText}
            placeholder={messages.sampling.placeholders.stop}
            onIonInput={(event) => onTextChange("stopText", event.detail.value ?? "")}
          />
          <IonNote slot="helper">{messages.sampling.help.stop}</IonNote>
        </IonItem>
      ) : null}
      {fields.includes("logit_bias") ? (
        <IonItem>
          <IonLabel position="stacked">{messages.sampling.fields.logit_bias}</IonLabel>
          <IonTextarea
            autoGrow
            value={liveForm.logitBiasText}
            placeholder={messages.sampling.placeholders.logit_bias}
            onIonInput={(event) => onTextChange("logitBiasText", event.detail.value ?? "")}
          />
          <IonNote slot="helper">{messages.sampling.help.logit_bias}</IonNote>
        </IonItem>
      ) : null}
    </IonList>
  );
}

function EditableDialCenterValue({
  value,
  spec,
  unsetLabel,
  editAriaLabel,
  onChange,
}: {
  value: number | null;
  spec: FieldSpec;
  unsetLabel: string;
  editAriaLabel: string;
  onChange: (value: number | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const active = value !== null;
  const display = active ? formatNumericDisplay(value, spec) : unsetLabel;

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const commit = () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      onChange(null);
    } else {
      const parsed = Number(trimmed);
      if (Number.isFinite(parsed)) {
        onChange(snapToSpec(parsed, spec));
      }
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="number"
        className="dial-regulator__value-input"
        value={draft}
        min={spec.min}
        max={spec.max}
        step={spec.step}
        aria-label={editAriaLabel}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          event.stopPropagation();
          if (event.key === "Enter") {
            event.preventDefault();
            commit();
          } else if (event.key === "Escape") {
            event.preventDefault();
            setEditing(false);
          }
        }}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      />
    );
  }

  return (
    <button
      type="button"
      className="dial-regulator__value-button"
      aria-label={editAriaLabel}
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        setDraft(active ? formatNumericDisplay(value, spec) : String(spec.min));
        setEditing(true);
      }}
    >
      {display}
    </button>
  );
}

function NumericDialField({
  fieldKey,
  label,
  help,
  wheelHint,
  spec,
  variant,
  value,
  unsetLabel,
  closeLabel,
  onChange,
}: {
  fieldKey: LiveNumericKey;
  label: string;
  help: string;
  wheelHint: string;
  spec: FieldSpec;
  variant: DialRegulatorVariant;
  value: number | null;
  unsetLabel: string;
  closeLabel: string;
  onChange: (value: number | null) => void;
}) {
  const fieldRef = useRef<HTMLElement>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const isMirostat = fieldKey === "mirostat";
  const isEditableCenter = fieldKey === "num_predict";
  const active = value !== null;
  const display = active ? formatNumericDisplay(value, spec) : unsetLabel;
  const dialValue = active ? samplingValueToDial(value, spec, DIAL_STEPS) : 0;
  const helpText = `${help} ${wheelHint}`;

  useEffect(() => {
    const node = fieldRef.current;
    if (!node) {
      return;
    }
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const direction = event.deltaY < 0 ? 1 : -1;
      if (isMirostat) {
        onChange(stepMirostatValue(value, direction > 0 ? 1 : -1));
        return;
      }
      const base = value ?? spec.min;
      onChange(snapToSpec(base + direction * spec.step, spec));
    };
    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  }, [isMirostat, onChange, spec, value]);

  const fieldClass = [
    "sampling-settings-modal__dial-field",
    "sampling-settings-modal__dial-field--wheel",
    isMirostat ? "sampling-settings-modal__dial-field--mirostat" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article ref={fieldRef} className={fieldClass}>
      <div className="sampling-settings-modal__dial-field-header">
        <h3 className="sampling-settings-modal__dial-field-label">{label}</h3>
        <button
          type="button"
          className="sampling-settings-modal__dial-info"
          aria-label={`${label}, informations`}
          aria-expanded={helpOpen}
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            setHelpOpen(true);
          }}
        >
          i
        </button>
        {helpOpen ? (
          <div
            className="sampling-settings-modal__dial-help-panel"
            role="dialog"
            aria-label={label}
          >
            <p className="sampling-settings-modal__dial-help">{helpText}</p>
            <IonButton
              fill="clear"
              size="small"
              className="sampling-settings-modal__dial-help-close"
              aria-label={closeLabel}
              onClick={() => setHelpOpen(false)}
            >
              ×
            </IonButton>
          </div>
        ) : null}
      </div>
      <div className="sampling-settings-modal__dial-wrap">
        {isMirostat ? (
          <MirostatRockerSwitch
            value={value}
            onChange={(next) => onChange(next)}
            ariaLabel={`${label}, ${display}`}
          />
        ) : (
          <DialRegulator
            variant={variant}
            size="sm"
            value={dialValue}
            min={0}
            max={DIAL_STEPS}
            valueLabel={!isEditableCenter ? display : undefined}
            valueContent={
              isEditableCenter ? (
                <EditableDialCenterValue
                  value={value}
                  spec={spec}
                  unsetLabel={unsetLabel}
                  editAriaLabel={`${label}, modifier la valeur`}
                  onChange={onChange}
                />
              ) : undefined
            }
            ariaLabel={`${label}, ${display}`}
            className={
              active
                ? "sampling-settings-modal__dial"
                : "sampling-settings-modal__dial sampling-settings-modal__dial--inactive"
            }
            onChange={(next) => onChange(dialToSamplingValue(next, spec, DIAL_STEPS))}
          />
        )}
        {active ? (
          <IonButton
            fill="clear"
            size="small"
            className="sampling-settings-modal__dial-unset"
            aria-label={unsetLabel}
            onClick={() => onChange(null)}
          >
            ×
          </IonButton>
        ) : null}
      </div>
      <p className="sampling-settings-modal__dial-bounds">
        {isMirostat
          ? "0, 1 ou 2"
          : `${formatNumericDisplay(spec.min, spec)} — ${formatNumericDisplay(spec.max, spec)}`}
      </p>
    </article>
  );
}

export default SamplingSettingsModal;
