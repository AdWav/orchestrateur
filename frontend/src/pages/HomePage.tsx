import {
  IonBadge,
  IonButton,
  IonButtons,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardSubtitle,
  IonCardTitle,
  IonContent,
  IonHeader,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonModal,
  IonNote,
  IonPage,
  IonSelect,
  IonSelectOption,
  IonSpinner,
  IonToggle,
  IonTitle,
  IonToolbar,
  useIonToast,
} from "@ionic/react";
import { moonOutline, sunnyOutline } from "ionicons/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import SamplingSettingsModal from "../components/SamplingSettingsModal";
import DevTeamsSection from "../components/DevTeamsSection";
import { useI18n } from "../i18n/I18nProvider";
import { getActiveTranslator } from "../i18n/core";
import {
  AgentDefinition,
  ServiceStatus,
  WorkflowDefinition,
  apiBaseUrl,
  createAgentDefinition,
  createWorkflowDefinition,
  fetchAgentDefinitions,
  fetchHealth,
  fetchOllamaModels,
  fetchServiceStatus,
  fetchWorkflowDefinitions,
  fetchOllamaRuntimeSettings,
  postOllamaModelUnload,
  postOllamaModelWarm,
  putOllamaRuntimeSettings,
  type OllamaRuntimeSettings,
} from "../lib/api";
import type { ThemeMode } from "../theme/theme";

import "./HomePage.css";

const backendServiceKey = "po";
const samplingServiceKey = "sampling";
const heroServiceKeys = new Set([backendServiceKey, samplingServiceKey]);

type HomePageProps = {
  themeMode: ThemeMode;
  onThemeChange: (themeMode: ThemeMode) => void;
};

type WorkflowStepDraft = {
  id: string;
  name: string;
  agentDefinitionId: string;
  objective: string;
  expectedDeliverablesText: string;
  successCriteriaText: string;
  dependsOnText: string;
};

type AgentFormState = {
  id: string;
  name: string;
  businessRole: string;
  mission: string;
  capabilitiesText: string;
  inputsText: string;
  outputsText: string;
  guardrailsText: string;
};

type WorkflowFormState = {
  id: string;
  name: string;
  goal: string;
  contextText: string;
  constraintsText: string;
  successCriteriaText: string;
  steps: WorkflowStepDraft[];
};

type OllamaModelsModalState =
  | { kind: "list"; models: string[]; settings: OllamaRuntimeSettings | null }
  | { kind: "error"; message: string };

function createEmptyWorkflowStep(index: number): WorkflowStepDraft {
  const { t } = getActiveTranslator();
  return {
    id: `step-${index + 1}`,
    name: t("workflowForm.step", { index: index + 1 }),
    agentDefinitionId: "",
    objective: "",
    expectedDeliverablesText: "",
    successCriteriaText: "",
    dependsOnText: "",
  };
}

function defaultAgentFormState(): AgentFormState {
  return {
    id: "",
    name: "",
    businessRole: "",
    mission: "",
    capabilitiesText: "",
    inputsText: "",
    outputsText: "",
    guardrailsText: "",
  };
}

function defaultWorkflowFormState(): WorkflowFormState {
  return {
    id: "",
    name: "",
    goal: "",
    contextText: "",
    constraintsText: "",
    successCriteriaText: "",
    steps: [createEmptyWorkflowStep(0)],
  };
}

function parseLineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function parseKeyValueLines(value: string): Record<string, string> {
  const { t } = getActiveTranslator();
  const entries: Record<string, string> = {};
  for (const line of value.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex < 1) {
      throw new Error(t("errors.invalidContextLine", { line: trimmed }));
    }
    const key = trimmed.slice(0, separatorIndex).trim();
    const entryValue = trimmed.slice(separatorIndex + 1).trim();
    if (!key) {
      throw new Error(t("errors.emptyContextKey"));
    }
    entries[key] = entryValue;
  }
  return entries;
}

function formatServiceTarget(service: ServiceStatus): string {
  const { messages } = getActiveTranslator();
  if (service.target === "in-process") {
    return messages.apiHealth.internalRole;
  }

  return service.port ? `:${service.port}` : service.target;
}

const HomePage = ({
  themeMode,
  onThemeChange,
}: HomePageProps) => {
  const {
    messages,
    t,
    language,
    setLanguage,
    meshServiceLabel,
    healthStatus,
    runtimeRoleLabel,
  } = useI18n();
  const queryClient = useQueryClient();
  const [presentToast] = useIonToast();
  const [isBackendCardVisible, setIsBackendCardVisible] = useState(false);
  const [isSamplingModalOpen, setIsSamplingModalOpen] = useState(false);
  const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);
  const [agentForm, setAgentForm] = useState<AgentFormState>(defaultAgentFormState);
  const [workflowForm, setWorkflowForm] = useState<WorkflowFormState>(
    defaultWorkflowFormState,
  );
  const [agentFormError, setAgentFormError] = useState<string | null>(null);
  const [workflowFormError, setWorkflowFormError] = useState<string | null>(
    null,
  );
  const [ollamaListBusy, setOllamaListBusy] = useState(false);
  const [ollamaModelsModal, setOllamaModelsModal] = useState<OllamaModelsModalState | null>(
    null,
  );
  const [runtimeDraft, setRuntimeDraft] = useState<{
    defaultModel: string;
    runners: Record<string, string>;
  } | null>(null);
  const [runtimeSaveBusy, setRuntimeSaveBusy] = useState(false);
  const [modelActionBusy, setModelActionBusy] = useState<string | null>(null);

  useEffect(() => {
    const modal = ollamaModelsModal;
    if (modal?.kind !== "list") {
      setRuntimeDraft(null);
      return;
    }
    const { models, settings } = modal;
    if (!settings) {
      setRuntimeDraft(null);
      return;
    }
    const pool = [...models].sort((a, b) => a.localeCompare(b));
    const safeDefault = pool.includes(settings.default_model)
      ? settings.default_model
      : pool[0] ?? settings.default_model;
    const runners = { ...settings.runner_models };
    for (const step of settings.pipeline_steps) {
      if (!pool.includes(runners[step])) {
        runners[step] = safeDefault;
      }
    }
    setRuntimeDraft({ defaultModel: safeDefault, runners });
  }, [ollamaModelsModal]);

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    staleTime: 30_000,
  });
  const serviceStatusQuery = useQuery({
    queryKey: ["service-status"],
    queryFn: fetchServiceStatus,
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
  const agentDefinitionsQuery = useQuery({
    queryKey: ["agent-definitions"],
    queryFn: fetchAgentDefinitions,
    staleTime: 10_000,
  });
  const workflowDefinitionsQuery = useQuery({
    queryKey: ["workflow-definitions"],
    queryFn: fetchWorkflowDefinitions,
    staleTime: 10_000,
  });
  const createAgentMutation = useMutation({
    mutationFn: createAgentDefinition,
    onSuccess: () => {
      setAgentForm(defaultAgentFormState());
      setAgentFormError(null);
      setIsAgentModalOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["agent-definitions"] });
    },
  });
  const createWorkflowMutation = useMutation({
    mutationFn: createWorkflowDefinition,
    onSuccess: () => {
      setWorkflowForm(defaultWorkflowFormState());
      setWorkflowFormError(null);
      setIsWorkflowModalOpen(false);
      void queryClient.invalidateQueries({
        queryKey: ["workflow-definitions"],
      });
    },
  });

  const bootstrapError = healthQuery.error ?? null;
  const isLoading = healthQuery.isLoading;
  const services = serviceStatusQuery.data?.services ?? [];
  const agentDefinitions = agentDefinitionsQuery.data ?? [];
  const workflowDefinitions = workflowDefinitionsQuery.data ?? [];
  const agentDefinitionsById = Object.fromEntries(
    agentDefinitions.map((definition) => [definition.id, definition]),
  );
  const hasInternalRoles = services.some(
    (service) => service.target === "in-process",
  );

  const handleOllamaModelsClick = async () => {
    setOllamaListBusy(true);
    try {
      const [modelsPayload, settingsPayload] = await Promise.all([
        fetchOllamaModels(),
        fetchOllamaRuntimeSettings().catch(() => null),
      ]);
      setOllamaModelsModal({
        kind: "list",
        models: modelsPayload.models,
        settings: settingsPayload,
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      setOllamaModelsModal({ kind: "error", message: detail });
    } finally {
      setOllamaListBusy(false);
    }
  };

  const saveRuntimeDraft = async () => {
    if (!runtimeDraft || ollamaModelsModal?.kind !== "list" || !ollamaModelsModal.settings) {
      return;
    }
    setRuntimeSaveBusy(true);
    try {
      const updated = await putOllamaRuntimeSettings({
        default_model: runtimeDraft.defaultModel,
        runner_models: runtimeDraft.runners,
      });
      setOllamaModelsModal({
        kind: "list",
        models: ollamaModelsModal.models,
        settings: updated,
      });
      presentToast({
        message: messages.header.ollamaRuntimeSaved,
        duration: 2000,
        color: "success",
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      presentToast({ message: detail, duration: 3500, color: "danger" });
    } finally {
      setRuntimeSaveBusy(false);
    }
  };

  const triggerModelWarm = async (modelName: string) => {
    const key = `warm:${modelName}`;
    setModelActionBusy(key);
    try {
      await postOllamaModelWarm(modelName);
      presentToast({
        message: t("header.ollamaWarmOk", { name: modelName }),
        duration: 2200,
        color: "success",
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      presentToast({ message: detail, duration: 4000, color: "danger" });
    } finally {
      setModelActionBusy(null);
    }
  };

  const triggerModelUnload = async (modelName: string) => {
    const key = `unload:${modelName}`;
    setModelActionBusy(key);
    try {
      await postOllamaModelUnload(modelName);
      presentToast({
        message: t("header.ollamaUnloadOk", { name: modelName }),
        duration: 2200,
        color: "medium",
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      presentToast({ message: detail, duration: 4000, color: "danger" });
    } finally {
      setModelActionBusy(null);
    }
  };

  const submitAgentDefinition = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAgentFormError(null);
    try {
      createAgentMutation.mutate({
        id: agentForm.id,
        name: agentForm.name.trim(),
        business_role: agentForm.businessRole.trim(),
        mission: agentForm.mission.trim(),
        capabilities: parseLineList(agentForm.capabilitiesText),
        inputs: parseLineList(agentForm.inputsText),
        outputs: parseLineList(agentForm.outputsText),
        guardrails: parseLineList(agentForm.guardrailsText),
      });
    } catch (error) {
      setAgentFormError(
        error instanceof Error ? error.message : messages.errors.createAgentFallback,
      );
    }
  };

  const submitWorkflowDefinition = (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    setWorkflowFormError(null);
    try {
      createWorkflowMutation.mutate({
        id: workflowForm.id,
        name: workflowForm.name.trim(),
        goal: workflowForm.goal.trim(),
        context: parseKeyValueLines(workflowForm.contextText),
        constraints: parseLineList(workflowForm.constraintsText),
        success_criteria: parseLineList(workflowForm.successCriteriaText),
        steps: workflowForm.steps.map((step) => ({
          id: step.id,
          name: step.name.trim(),
          agent_definition_id: step.agentDefinitionId,
          objective: step.objective.trim(),
          expected_deliverables: parseLineList(step.expectedDeliverablesText),
          success_criteria: parseLineList(step.successCriteriaText),
          depends_on: parseLineList(step.dependsOnText),
        })),
      });
    } catch (error) {
      setWorkflowFormError(
        error instanceof Error
          ? error.message
          : messages.errors.createWorkflowFallback,
      );
    }
  };

  const addWorkflowStep = () => {
    setWorkflowForm((current) => ({
      ...current,
      steps: [...current.steps, createEmptyWorkflowStep(current.steps.length)],
    }));
  };

  const removeWorkflowStep = (index: number) => {
    setWorkflowForm((current) => ({
      ...current,
      steps: current.steps.filter((_, currentIndex) => currentIndex !== index),
    }));
  };

  const isAgentFormValid =
    agentForm.id.trim().length > 0 &&
    agentForm.name.trim().length > 0 &&
    agentForm.businessRole.trim().length > 0 &&
    agentForm.mission.trim().length > 0;
  const isWorkflowFormValid =
    workflowForm.id.trim().length > 0 &&
    workflowForm.name.trim().length > 0 &&
    workflowForm.goal.trim().length > 0 &&
    workflowForm.steps.length > 0 &&
    workflowForm.steps.every(
      (step) =>
        step.id.trim().length > 0 &&
        step.name.trim().length > 0 &&
        step.agentDefinitionId.trim().length > 0 &&
        step.objective.trim().length > 0,
    );

  return (
    <IonPage>
      <IonHeader translucent>
        <IonToolbar>
          <IonTitle>{messages.app.title}</IonTitle>
          <IonButtons slot="end">
            <div
              className="language-switch"
              aria-label={messages.header.languageSwitcher}
            >
              <IonButton
                size="small"
                fill={language === "fr" ? "solid" : "outline"}
                onClick={() => setLanguage("fr")}
                aria-pressed={language === "fr"}
              >
                {messages.common.languageFr}
              </IonButton>
              <IonButton
                size="small"
                fill={language === "en" ? "solid" : "outline"}
                onClick={() => setLanguage("en")}
                aria-pressed={language === "en"}
              >
                {messages.common.languageEn}
              </IonButton>
            </div>
            <div className="toggle-icon">
              <IonIcon
                icon={sunnyOutline}
                aria-hidden="true"
                className={themeMode === "light" ? "is-active" : undefined}
              />
              <IonToggle
                checked={themeMode === "dark"}
                aria-label={
                  themeMode === "dark"
                    ? messages.header.switchToLight
                    : messages.header.switchToDark
                }
                onIonChange={(event) =>
                  onThemeChange(event.detail.checked ? "dark" : "light")
                }
              />
              <IonIcon
                icon={moonOutline}
                aria-hidden="true"
                className={themeMode === "dark" ? "is-active" : undefined}
              />
            </div>
            <IonButton
              fill="outline"
              size="small"
              disabled={ollamaListBusy}
              aria-label={messages.header.ollamaListAria}
              onClick={() => void handleOllamaModelsClick()}
            >
              {messages.header.ollamaListButton}
            </IonButton>
            <IonButton href={`${apiBaseUrl}/docs`} target="_blank">
              {messages.header.apiDocs}
            </IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <div className="home-shell">
          <section className="hero-card">
            <div className="service-lights">
              {services
                .filter((service) => heroServiceKeys.has(service.key))
                .map((service) => {
                  const isBackendService = service.key === backendServiceKey;
                  const isSamplingService = service.key === samplingServiceKey;
                  const isSelected = isBackendService
                    ? isBackendCardVisible
                    : isSamplingModalOpen;

                const serviceLightContent = (
                  <>
                    <span
                      className={
                        service.active
                          ? "service-light__dot service-light__dot--up"
                          : "service-light__dot service-light__dot--down"
                      }
                    />
                    <div>
                      <strong>{meshServiceLabel(service.key)}</strong>
                      <span>{formatServiceTarget(service)}</span>
                    </div>
                  </>
                );

                return (
                  <button
                    key={service.key}
                    type="button"
                    className={
                      isSelected
                        ? "service-light service-light-button service-light--selected"
                        : "service-light service-light-button"
                    }
                    onClick={() => {
                      if (isBackendService) {
                        setIsSamplingModalOpen(false);
                        setIsBackendCardVisible(true);
                        return;
                      }
                      if (isSamplingService) {
                        setIsBackendCardVisible(false);
                        setIsSamplingModalOpen(true);
                      }
                    }}
                    aria-expanded={isSelected}
                    aria-controls={
                        isBackendService ? "backend-health-modal" : "sampling-settings-modal"
                    }
                    aria-haspopup="dialog"
                  >
                    {serviceLightContent}
                  </button>
                );
              })}
            </div>
          </section>

          <IonModal
            id="backend-health-modal"
            className="popup-modal"
            isOpen={isBackendCardVisible}
            onDidDismiss={() => setIsBackendCardVisible(false)}
          >
            <IonHeader>
              <IonToolbar>
                <IonTitle>{messages.apiHealth.title}</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setIsBackendCardVisible(false)}>
                    {messages.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              <div className="home-shell modal-page-shell">
                <IonCard id="backend-health-card" className="modal-card">
                  <IonCardHeader>
                    <IonCardSubtitle>{messages.apiHealth.subtitle}</IonCardSubtitle>
                    <IonCardTitle>{messages.apiHealth.title}</IonCardTitle>
                  </IonCardHeader>
                  <IonCardContent>
                    {isLoading ? (
                      <div className="loading-row">
                        <IonSpinner name="crescent" />
                        <span>{messages.apiHealth.loading}</span>
                      </div>
                    ) : (
                      <div className="status-grid">
                        <div>
                          <span className="eyebrow">{messages.apiHealth.service}</span>
                          <strong>{healthQuery.data?.service ?? messages.common.unavailable}</strong>
                        </div>
                        <div>
                          <span className="eyebrow">{messages.apiHealth.execution}</span>
                          <strong>
                            {hasInternalRoles
                              ? messages.apiHealth.internalRoles
                              : messages.apiHealth.httpMesh}
                          </strong>
                        </div>
                        <div>
                          <span className="eyebrow">{messages.apiHealth.state}</span>
                          <IonBadge color={bootstrapError ? "danger" : "success"}>
                            {bootstrapError
                              ? messages.common.unreachable
                              : healthStatus(healthQuery.data?.status ?? "")}
                          </IonBadge>
                        </div>
                      </div>
                    )}
                  </IonCardContent>
                </IonCard>
              </div>
            </IonContent>
          </IonModal>

          <SamplingSettingsModal
            isOpen={isSamplingModalOpen}
            onDismiss={() => setIsSamplingModalOpen(false)}
          />

          <IonModal
            id="ollama-models-modal"
            className="popup-modal ollama-models-modal"
            isOpen={ollamaModelsModal !== null}
            onDidDismiss={() => setOllamaModelsModal(null)}
          >
            <IonHeader>
              <IonToolbar>
                <IonTitle>
                  {ollamaModelsModal?.kind === "error"
                    ? messages.header.ollamaListErrorTitle
                    : messages.header.ollamaListTitle}
                </IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setOllamaModelsModal(null)}>
                    {messages.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent className="ion-padding">
              {ollamaModelsModal?.kind === "list" ? (
                <>
                  <h2 className="ollama-models-modal__heading">
                    {messages.header.ollamaRuntimeHeading}
                  </h2>
                  {ollamaModelsModal.settings ? (
                    <>
                      {!ollamaModelsModal.settings.ollama_routing_active ? (
                        <IonNote color="medium" className="ollama-models-modal__note">
                          {messages.header.ollamaRoutingInactive}
                        </IonNote>
                      ) : null}
                      {ollamaModelsModal.settings.settings_persist_path ? (
                        <IonNote color="medium" className="ollama-models-modal__note">
                          {messages.header.ollamaPersistPathPrefix}{" "}
                          <code>{ollamaModelsModal.settings.settings_persist_path}</code>
                        </IonNote>
                      ) : null}
                      {!runtimeDraft || ollamaModelsModal.models.length === 0 ? (
                        <IonNote color="warning" className="ollama-models-modal__note">
                          {messages.header.ollamaListEmpty}
                        </IonNote>
                      ) : (
                        <>
                          <IonList className="ollama-models-modal__controls" lines="none">
                            <IonItem lines="full">
                              <IonLabel>{messages.header.ollamaRuntimeDefaultLabel}</IonLabel>
                              <IonSelect
                                interface="popover"
                                value={runtimeDraft.defaultModel}
                                disabled={runtimeSaveBusy}
                                onIonChange={(event) => {
                                  const value = String(event.detail.value ?? "");
                                  setRuntimeDraft((draft) =>
                                    draft ? { ...draft, defaultModel: value } : draft,
                                  );
                                }}
                                slot="end"
                                aria-label={messages.header.ollamaRuntimeDefaultLabel}
                              >
                                {ollamaModelsModal.models.map((name) => (
                                  <IonSelectOption key={name} value={name}>
                                    {name}
                                  </IonSelectOption>
                                ))}
                              </IonSelect>
                            </IonItem>
                            {ollamaModelsModal.settings.pipeline_steps.map((step: string) => (
                              <IonItem key={step} lines="full">
                                <IonLabel position="stacked">
                                  {runtimeRoleLabel(step)}
                                  <IonNote>
                                    <code>{step}</code>
                                  </IonNote>
                                </IonLabel>
                                <IonSelect
                                  interface="popover"
                                  value={runtimeDraft.runners[step]}
                                  disabled={runtimeSaveBusy}
                                  onIonChange={(event) => {
                                    const value = String(event.detail.value ?? "");
                                    setRuntimeDraft((draft) =>
                                      draft
                                        ? {
                                            ...draft,
                                            runners: {
                                              ...draft.runners,
                                              [step]: value,
                                            },
                                          }
                                        : draft,
                                  );
                                  }}
                                  slot="end"
                                  aria-label={`${runtimeRoleLabel(step)} (${step})`}
                                >
                                  {ollamaModelsModal.models.map((name) => (
                                    <IonSelectOption key={name} value={name}>
                                      {name}
                                    </IonSelectOption>
                                  ))}
                                </IonSelect>
                              </IonItem>
                            ))}
                          </IonList>
                          <IonButton
                            expand="block"
                            disabled={
                              runtimeSaveBusy ||
                              !ollamaModelsModal.settings.ollama_routing_active
                            }
                            onClick={() => void saveRuntimeDraft()}
                          >
                            {runtimeSaveBusy ? <IonSpinner name="crescent" /> : messages.header.ollamaSaveRuntime}
                          </IonButton>
                        </>
                      )}
                    </>
                  ) : (
                    <IonNote color="medium" className="ollama-models-modal__note">
                      {messages.header.ollamaRuntimeSettingsFetchError}
                    </IonNote>
                  )}
                  <h3 className="ollama-models-modal__list-title">{messages.header.ollamaModelsInstalledTitle}</h3>
                  <p className="ollama-models-modal__subtitle">
                    <IonNote>{messages.header.ollamaListSubtitle}</IonNote>
                  </p>
                  {ollamaModelsModal.models.length > 0 ? (
                    <IonList className="ollama-models-modal__list" lines="full">
                      {ollamaModelsModal.models.map((name) => (
                        <IonItem key={name}>
                          <IonLabel>
                            <code className="ollama-models-modal__model-name">{name}</code>
                          </IonLabel>
                          <IonButtons slot="end">
                            <IonButton
                              size="small"
                              fill="outline"
                              disabled={
                                modelActionBusy === `warm:${name}` ||
                                modelActionBusy === `unload:${name}`
                              }
                              onClick={() => void triggerModelWarm(name)}
                            >
                              {modelActionBusy === `warm:${name}` ? (
                                <IonSpinner name="crescent" />
                              ) : (
                                messages.header.ollamaWarm
                              )}
                            </IonButton>
                            <IonButton
                              size="small"
                              fill="outline"
                              color="medium"
                              disabled={
                                modelActionBusy === `warm:${name}` ||
                                modelActionBusy === `unload:${name}`
                              }
                              onClick={() => void triggerModelUnload(name)}
                            >
                              {modelActionBusy === `unload:${name}` ? (
                                <IonSpinner name="crescent" />
                              ) : (
                                messages.header.ollamaUnload
                              )}
                            </IonButton>
                          </IonButtons>
                        </IonItem>
                      ))}
                    </IonList>
                  ) : (
                    <IonNote color="medium" className="ollama-models-modal__empty">
                      {messages.header.ollamaListEmpty}
                    </IonNote>
                  )}
                </>
              ) : null}
              {ollamaModelsModal?.kind === "error" ? (
                <IonNote color="danger" className="ollama-models-modal__error">
                  {ollamaModelsModal.message}
                </IonNote>
              ) : null}
            </IonContent>
          </IonModal>
          <DevTeamsSection />
        </div>
      </IonContent>
    </IonPage>
  );
};

export default HomePage;
