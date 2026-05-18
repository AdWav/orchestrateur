import {
  IonBadge,
  IonButton,
  IonButtons,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardSubtitle,
  IonCardTitle,
  IonChip,
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
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
  getActiveI18nCopy,
  translateAnalysisAxis,
  translateApprovalState,
  translateMeshServiceLabel,
  translatePassState,
  translateRuntimeRoleLabel,
} from "../i18n/translations";
import {
  AgentDefinition,
  AgentOutput,
  JsonValue,
  MemoryEvent,
  RepoAuditReport,
  ServiceStatus,
  WorkflowDefinition,
  apiBaseUrl,
  createAgentDefinition,
  createWorkflowDefinition,
  fetchAgentDefinitions,
  fetchHealth,
  fetchOllamaModels,
  fetchServiceStatus,
  fetchTeam,
  fetchUseCases,
  fetchWorkflowDefinitions,
  fetchOllamaRuntimeSettings,
  postOllamaModelUnload,
  postOllamaModelWarm,
  putOllamaRuntimeSettings,
  runRepoAudit,
  type OllamaRuntimeSettings,
  type UseCaseDefinition,
} from "../lib/api";
import type { ThemeMode } from "../theme/theme";

import "./HomePage.css";

const defaultAxes = [
  "architecture",
  "tests",
  "docs",
  "security",
  "dependencies",
];
const backendServiceKey = "po";

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
  const copy = getActiveI18nCopy();
  return {
    id: `step-${index + 1}`,
    name: copy.workflowForm.step(index + 1),
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEvidenceLike(
  value: unknown,
): value is { path?: unknown; reason?: unknown; excerpt?: unknown } {
  return isRecord(value);
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function parseLineList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function parseKeyValueLines(value: string): Record<string, string> {
  const copy = getActiveI18nCopy();
  const entries: Record<string, string> = {};
  for (const line of value.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const separatorIndex = trimmed.indexOf("=");
    if (separatorIndex < 1) {
      throw new Error(copy.errors.invalidContextLine(trimmed));
    }
    const key = trimmed.slice(0, separatorIndex).trim();
    const entryValue = trimmed.slice(separatorIndex + 1).trim();
    if (!key) {
      throw new Error(copy.errors.emptyContextKey);
    }
    entries[key] = entryValue;
  }
  return entries;
}

function humanizeKey(value: string): string {
  return value.replace(/_/g, " ");
}

function formatJsonValue(value: JsonValue): string {
  if (value === null) {
    return "null";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

function formatServiceTarget(service: ServiceStatus): string {
  const copy = getActiveI18nCopy();
  if (service.target === "in-process") {
    return copy.apiHealth.internalRole;
  }

  return service.port ? `:${service.port}` : service.target;
}

function renderList(title: string, items: string[]) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="trace-block">
      <span className="trace-title">{title}</span>
      <ul className="trace-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function renderPlannerArtifacts(output: AgentOutput) {
  const copy = getActiveI18nCopy();
  return (
    <>
      {renderList(copy.artifacts.searchPlan, asStringArray(output.artifacts.search_plan))}
      {renderList(
        copy.artifacts.acceptanceCriteria,
        asStringArray(output.artifacts.acceptance_criteria),
      )}
    </>
  );
}

function renderResearcherArtifacts(output: AgentOutput) {
  const copy = getActiveI18nCopy();
  const evidenceRefs = Array.isArray(output.artifacts.evidence_refs)
    ? output.artifacts.evidence_refs.reduce<
        { path?: unknown; reason?: unknown; excerpt?: unknown }[]
      >((accumulator, item) => {
        if (isEvidenceLike(item)) {
          accumulator.push(item);
        }

        return accumulator;
      }, [])
    : [];
  const coverageMap = isRecord(output.artifacts.coverage_map)
    ? output.artifacts.coverage_map
    : null;

  return (
    <>
      {renderList(
        copy.artifacts.importantFiles,
        asStringArray(output.artifacts.important_files),
      )}
      {coverageMap ? (
        <section className="trace-block">
          <span className="trace-title">{copy.artifacts.coverageMap}</span>
          <div className="key-value-list">
            {Object.entries(coverageMap).map(([axis, paths]) => (
              <div key={axis}>
                <strong>{axis}</strong>
                <span>{asStringArray(paths).join(", ") || copy.common.none}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      {evidenceRefs.length > 0 ? (
        <section className="trace-block">
          <span className="trace-title">{copy.artifacts.evidenceExcerpts}</span>
          <div className="evidence-list">
            {evidenceRefs.slice(0, 4).map((evidence) => (
              <article
                key={`${String(evidence.path ?? copy.common.unknown)}-${String(evidence.reason ?? "reason")}`}
                className="evidence-item"
              >
                <strong>{String(evidence.path ?? copy.common.unknown)}</strong>
                <span>{String(evidence.reason ?? copy.common.noReasonProvided)}</span>
                {typeof evidence.excerpt === "string" ? (
                  <code>{evidence.excerpt}</code>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}

function renderExecutorArtifacts(output: AgentOutput, report: RepoAuditReport) {
  const copy = getActiveI18nCopy();
  const findings = report.findings;

  return (
    <>
      {typeof output.artifacts.repo_summary === "string" ? (
        <section className="trace-block">
          <span className="trace-title">{copy.artifacts.repositorySummary}</span>
          <p className="trace-copy">{output.artifacts.repo_summary}</p>
        </section>
      ) : null}
      {findings.length > 0 ? (
        <section className="trace-block">
          <span className="trace-title">{copy.artifacts.findings}</span>
          <div className="finding-list">
            {findings.map((finding) => (
              <article key={finding.id} className="finding-item">
                <div className="finding-head">
                  <strong>{finding.title}</strong>
                  <IonBadge color={finding.severity === "high" ? "danger" : "warning"}>
                    {finding.severity}
                  </IonBadge>
                </div>
                <p>{finding.summary}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {renderList(
        copy.artifacts.recommendedActions,
        asStringArray(output.artifacts.recommended_actions),
      )}
      {renderList(copy.artifacts.unknowns, asStringArray(output.artifacts.unknowns))}
    </>
  );
}

function renderVerifierArtifacts(output: AgentOutput) {
  const copy = getActiveI18nCopy();
  const validation = isRecord(output.artifacts.validation_report)
    ? output.artifacts.validation_report
    : null;

  if (!validation) {
    return null;
  }

  return (
    <>
      <section className="trace-block">
        <span className="trace-title">{copy.artifacts.validationStatus}</span>
        <div className="status-grid compact-grid">
          <div>
            <span className="eyebrow">{copy.artifacts.approved}</span>
            <IonBadge color={validation.approved ? "success" : "danger"}>
              {String(validation.approved)}
            </IonBadge>
          </div>
          <div>
            <span className="eyebrow">{copy.artifacts.evidenceCount}</span>
            <strong>{String(validation.evidence_count ?? 0)}</strong>
          </div>
        </div>
      </section>
      {renderList(copy.artifacts.coveredAxes, asStringArray(validation.covered_axes))}
      {renderList(
        copy.artifacts.policyCompliance,
        asStringArray(validation.policy_compliance),
      )}
      {renderList(
        copy.artifacts.missingRequirements,
        asStringArray(validation.missing_requirements),
      )}
      {renderList(
        copy.artifacts.unsupportedClaims,
        asStringArray(validation.unsupported_claims),
      )}
    </>
  );
}

function renderOutputArtifacts(output: AgentOutput, report: RepoAuditReport) {
  switch (output.role) {
    case "plan":
    case "Planner":
      return renderPlannerArtifacts(output);
    case "research":
    case "Researcher":
      return renderResearcherArtifacts(output);
    case "execute":
    case "Executor":
      return renderExecutorArtifacts(output, report);
    case "verify":
    case "Verifier":
      return renderVerifierArtifacts(output);
    default:
      return null;
  }
}

function renderArtifactValue(title: string, value: JsonValue) {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return (
      <section className="trace-block" key={title}>
        <span className="trace-title">{title}</span>
        <ul className="trace-list">
          {value.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    );
  }

  if (Array.isArray(value)) {
    return (
      <section className="trace-block" key={title}>
        <span className="trace-title">{title}</span>
        <pre className="mono-block">{JSON.stringify(value, null, 2)}</pre>
      </section>
    );
  }

  if (value && typeof value === "object") {
    return (
      <section className="trace-block" key={title}>
        <span className="trace-title">{title}</span>
        <div className="key-value-list">
          {Object.entries(value).map(([key, nestedValue]) => (
            <div key={key}>
              <strong>{humanizeKey(key)}</strong>
              <span>{formatJsonValue(nestedValue)}</span>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="trace-block" key={title}>
      <span className="trace-title">{title}</span>
      <p className="trace-copy">{formatJsonValue(value)}</p>
    </section>
  );
}

function renderGenericArtifacts(output: AgentOutput) {
  const entries = Object.entries(output.artifacts);
  if (entries.length === 0) {
    return null;
  }

  return entries.map(([key, value]) =>
    renderArtifactValue(humanizeKey(key), value),
  );
}

function eventLabel(event: MemoryEvent) {
  const copy = getActiveI18nCopy();
  if (event.message) {
    return event.message;
  }

  if (event.key) {
    return copy.memory.updated(event.key);
  }

  return event.type;
}

type RepoAuditTraceViewMode = "trace" | "json";

function RepoAuditStepTraceCard({
  output,
  report,
}: {
  output: AgentOutput;
  report: RepoAuditReport;
}) {
  const { copy } = useI18n();
  const [viewMode, setViewMode] = useState<RepoAuditTraceViewMode>("trace");
  const rawJson = useMemo(() => JSON.stringify(output, null, 2), [output]);

  return (
    <article className="trace-card">
      <div className="trace-card__head">
        <div>
          <span className="eyebrow">{copy.report.agent}</span>
          <h3>{translateRuntimeRoleLabel(output.role)}</h3>
        </div>
        <IonChip
          color={
            output.approved === true
              ? "success"
              : output.approved === false
                ? "danger"
                : "primary"
          }
        >
          {translateApprovalState(output.approved)}
        </IonChip>
      </div>

      <div className="toggle-wrapper trace-card__view-toggle">
        <div className="toggle-wrapper__spacer" aria-hidden="true" />
        <div className="toggle-wrapper__control">
          <IonToggle
            checked={viewMode === "json"}
            aria-label={copy.report.viewModeToggleAria}
            onIonChange={(event) =>
              setViewMode(event.detail.checked ? "json" : "trace")
            }
          />
          <span className="toggle-wrapper__json-label">{copy.report.jsonToggleCaption}</span>
        </div>
      </div>

      {viewMode === "json" ? (
        <pre className="mono-block trace-card__raw-json">{rawJson}</pre>
      ) : (
        <>
          <p className="trace-copy">{output.summary}</p>
          {renderOutputArtifacts(output, report)}
          {renderList(copy.artifacts.nextActions, output.next_actions)}
        </>
      )}
    </article>
  );
}

const HomePage = ({
  themeMode,
  onThemeChange,
}: HomePageProps) => {
  const { copy, language, setLanguage } = useI18n();
  const queryClient = useQueryClient();
  const [presentToast] = useIonToast();
  const [objective, setObjective] = useState<string>(
    () => getActiveI18nCopy().repoAudit.defaultObjective,
  );
  const [repoPath, setRepoPath] = useState(".");
  const [analysisAxes, setAnalysisAxes] = useState<string[]>(defaultAxes);
  const [isBackendCardVisible, setIsBackendCardVisible] = useState(false);
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
  const teamQuery = useQuery({
    queryKey: ["team"],
    queryFn: fetchTeam,
    staleTime: 60_000,
  });
  const useCasesQuery = useQuery({
    queryKey: ["use-cases"],
    queryFn: fetchUseCases,
    staleTime: 60_000,
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
  const repoAuditMutation = useMutation({
    mutationFn: runRepoAudit,
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

  const bootstrapError =
    healthQuery.error ?? teamQuery.error ?? useCasesQuery.error ?? null;
  const isLoading =
    healthQuery.isLoading || teamQuery.isLoading || useCasesQuery.isLoading;
  const report = repoAuditMutation.data;
  const services = serviceStatusQuery.data?.services ?? [];
  const agentDefinitions = agentDefinitionsQuery.data ?? [];
  const workflowDefinitions = workflowDefinitionsQuery.data ?? [];
  const agentDefinitionsById = Object.fromEntries(
    agentDefinitions.map((definition) => [definition.id, definition]),
  );
  const hasInternalRoles = services.some(
    (service) => service.target === "in-process",
  );

  const teamAlignedUseCases = useMemo(() => {
    const all = useCasesQuery.data ?? [];
    const ids = teamQuery.data?.use_case_ids;

    if (!ids?.length) {
      return all;
    }

    const byId: Record<string, UseCaseDefinition | undefined> = Object.fromEntries(
      all.map((useCase) => [useCase.id, useCase]),
    );

    return ids.map((id) => byId[id]).filter(
      (useCase): useCase is UseCaseDefinition => Boolean(useCase),
    );
  }, [teamQuery.data?.use_case_ids, useCasesQuery.data]);

  const teamHasPayload =
    Boolean(teamQuery.data) &&
    (Boolean(teamQuery.data?.purpose?.trim()) ||
      (teamQuery.data?.roles.length ?? 0) > 0 ||
      (teamQuery.data?.handoff_contracts?.length ?? 0) > 0 ||
      (teamQuery.data?.guardrails?.length ?? 0) > 0);

  const showTeamCard = !teamQuery.isError && (teamQuery.isPending || teamHasPayload);

  const showUseCasesCard =
    !useCasesQuery.isError &&
    (useCasesQuery.isPending || teamAlignedUseCases.length > 0);

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
        message: copy.header.ollamaRuntimeSaved,
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
        message: copy.header.ollamaWarmOk(modelName),
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
        message: copy.header.ollamaUnloadOk(modelName),
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

  const toggleAxis = (axis: string) => {
    setAnalysisAxes((current) =>
      current.includes(axis)
        ? current.filter((item) => item !== axis)
        : [...current, axis],
    );
  };

  const submitRepoAudit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    repoAuditMutation.mutate({
      objective: objective.trim(),
      repo_path: repoPath.trim() || ".",
      analysis_axes: analysisAxes,
    });
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
        error instanceof Error ? error.message : copy.errors.createAgentFallback,
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
          : copy.errors.createWorkflowFallback,
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
          <IonTitle>{copy.app.title}</IonTitle>
          <IonButtons slot="end">
            <div
              className="language-switch"
              aria-label={copy.header.languageSwitcher}
            >
              <IonButton
                size="small"
                fill={language === "fr" ? "solid" : "outline"}
                onClick={() => setLanguage("fr")}
                aria-pressed={language === "fr"}
              >
                FR
              </IonButton>
              <IonButton
                size="small"
                fill={language === "en" ? "solid" : "outline"}
                onClick={() => setLanguage("en")}
                aria-pressed={language === "en"}
              >
                EN
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
                    ? copy.header.switchToLight
                    : copy.header.switchToDark
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
              aria-label={copy.header.ollamaListAria}
              onClick={() => void handleOllamaModelsClick()}
            >
              {copy.header.ollamaListButton}
            </IonButton>
            <IonButton href={`${apiBaseUrl}/docs`} target="_blank">
              {copy.header.apiDocs}
            </IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <div className="home-shell">
          <section className="hero-card">
            <div className="service-lights">
              {services.map((service) => {
                const isBackendService = service.key === backendServiceKey;
                if (!isBackendService) {
                  return null;
                }

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
                      <strong>{translateMeshServiceLabel(service.key)}</strong>
                      <span>{formatServiceTarget(service)}</span>
                    </div>
                  </>
                );

                return (
                  <button
                    key={service.key}
                    type="button"
                    className={
                      isBackendCardVisible
                        ? "service-light service-light-button service-light--selected"
                        : "service-light service-light-button"
                    }
                    onClick={() => setIsBackendCardVisible(true)}
                    aria-expanded={isBackendCardVisible}
                    aria-controls="backend-health-modal"
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
                <IonTitle>{copy.apiHealth.title}</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setIsBackendCardVisible(false)}>
                    {copy.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              <div className="home-shell modal-page-shell">
                <IonCard id="backend-health-card" className="modal-card">
                  <IonCardHeader>
                    <IonCardSubtitle>{copy.apiHealth.subtitle}</IonCardSubtitle>
                    <IonCardTitle>{copy.apiHealth.title}</IonCardTitle>
                  </IonCardHeader>
                  <IonCardContent>
                    {isLoading ? (
                      <div className="loading-row">
                        <IonSpinner name="crescent" />
                        <span>{copy.apiHealth.loading}</span>
                      </div>
                    ) : (
                      <div className="status-grid">
                        <div>
                          <span className="eyebrow">{copy.apiHealth.service}</span>
                          <strong>{healthQuery.data?.service ?? copy.common.unavailable}</strong>
                        </div>
                        <div>
                          <span className="eyebrow">{copy.apiHealth.execution}</span>
                          <strong>
                            {hasInternalRoles
                              ? copy.apiHealth.internalRoles
                              : copy.apiHealth.httpMesh}
                          </strong>
                        </div>
                        <div>
                          <span className="eyebrow">{copy.apiHealth.state}</span>
                          <IonBadge color={bootstrapError ? "danger" : "success"}>
                            {bootstrapError
                              ? copy.common.unreachable
                              : healthQuery.data?.status}
                          </IonBadge>
                        </div>
                        <div>
                          <span className="eyebrow">{copy.apiHealth.team}</span>
                          <strong>
                            {bootstrapError
                              ? copy.common.notAvailable
                              : copy.apiHealth.rolesCount(teamQuery.data?.roles.length ?? 0)}
                          </strong>
                        </div>
                        <div>
                          <span className="eyebrow">{copy.apiHealth.useCases}</span>
                          <strong>
                            {bootstrapError
                              ? copy.common.notAvailable
                              : copy.apiHealth.useCasesCount(useCasesQuery.data?.length ?? 0)}
                          </strong>
                        </div>
                      </div>
                    )}
                  </IonCardContent>
                </IonCard>
              </div>
            </IonContent>
          </IonModal>

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
                    ? copy.header.ollamaListErrorTitle
                    : copy.header.ollamaListTitle}
                </IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setOllamaModelsModal(null)}>
                    {copy.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent className="ion-padding">
              {ollamaModelsModal?.kind === "list" ? (
                <>
                  <h2 className="ollama-models-modal__heading">
                    {copy.header.ollamaRuntimeHeading}
                  </h2>
                  {ollamaModelsModal.settings ? (
                    <>
                      {!ollamaModelsModal.settings.ollama_routing_active ? (
                        <IonNote color="medium" className="ollama-models-modal__note">
                          {copy.header.ollamaRoutingInactive}
                        </IonNote>
                      ) : null}
                      {ollamaModelsModal.settings.settings_persist_path ? (
                        <IonNote color="medium" className="ollama-models-modal__note">
                          {copy.header.ollamaPersistPathPrefix}{" "}
                          <code>{ollamaModelsModal.settings.settings_persist_path}</code>
                        </IonNote>
                      ) : null}
                      {!runtimeDraft || ollamaModelsModal.models.length === 0 ? (
                        <IonNote color="warning" className="ollama-models-modal__note">
                          {copy.header.ollamaListEmpty}
                        </IonNote>
                      ) : (
                        <>
                          <IonList className="ollama-models-modal__controls" lines="none">
                            <IonItem lines="full">
                              <IonLabel>{copy.header.ollamaRuntimeDefaultLabel}</IonLabel>
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
                                aria-label={copy.header.ollamaRuntimeDefaultLabel}
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
                                  {translateRuntimeRoleLabel(step)}
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
                                  aria-label={`${translateRuntimeRoleLabel(step)} (${step})`}
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
                            {runtimeSaveBusy ? <IonSpinner name="crescent" /> : copy.header.ollamaSaveRuntime}
                          </IonButton>
                        </>
                      )}
                    </>
                  ) : (
                    <IonNote color="medium" className="ollama-models-modal__note">
                      {copy.header.ollamaRuntimeSettingsFetchError}
                    </IonNote>
                  )}
                  <h3 className="ollama-models-modal__list-title">{copy.header.ollamaModelsInstalledTitle}</h3>
                  <p className="ollama-models-modal__subtitle">
                    <IonNote>{copy.header.ollamaListSubtitle}</IonNote>
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
                                copy.header.ollamaWarm
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
                                copy.header.ollamaUnload
                              )}
                            </IonButton>
                          </IonButtons>
                        </IonItem>
                      ))}
                    </IonList>
                  ) : (
                    <IonNote color="medium" className="ollama-models-modal__empty">
                      {copy.header.ollamaListEmpty}
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

          <div className="catalog-pair">
            <IonCard className="hero-card action-card">
              <IonCardHeader>
                <IonCardTitle>{copy.agentForm.title}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                <p className="section-copy">{copy.agentForm.actionDescription}</p>
                <div className="action-card__row">
                  <IonButton onClick={() => setIsAgentModalOpen(true)}>
                    {copy.agentForm.openAction}
                  </IonButton>
                  <IonNote color="medium">
                    {copy.agentForm.persistedNote}
                  </IonNote>
                </div>
              </IonCardContent>
            </IonCard>

            <IonCard className="hero-card">
              <IonCardHeader>
                <IonCardTitle>{copy.agentList.title}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                {agentDefinitionsQuery.error instanceof Error ? (
                  <div className="error-box">{agentDefinitionsQuery.error.message}</div>
                ) : null}
                {agentDefinitions.length === 0 ? (
                  <p className="section-copy">{copy.agentList.empty}</p>
                ) : (
                  <div className="trace-stack">
                    {agentDefinitions.map((definition) => (
                      <article key={definition.id} className="trace-card">
                        <div className="trace-card__head">
                          <div>
                            <span className="eyebrow">{definition.id}</span>
                            <h3>{definition.name}</h3>
                          </div>
                        </div>
                        <p className="trace-copy">
                          {definition.business_role} · {definition.mission}
                        </p>
                        {renderList(copy.artifacts.capabilities, definition.capabilities)}
                        {renderList(copy.artifacts.inputs, definition.inputs)}
                        {renderList(copy.artifacts.outputs, definition.outputs)}
                        {renderList(copy.artifacts.guardrails, definition.guardrails)}
                      </article>
                    ))}
                  </div>
                )}
              </IonCardContent>
            </IonCard>
          </div>

          <IonModal
            className="popup-modal"
            isOpen={isAgentModalOpen}
            onDidDismiss={() => setIsAgentModalOpen(false)}
          >
            <IonHeader>
              <IonToolbar>
                <IonTitle>{copy.agentForm.title}</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setIsAgentModalOpen(false)}>
                    {copy.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              <div className="home-shell modal-page-shell">
                <IonCard className="hero-card modal-card">
                  <IonCardHeader>
                    <IonCardSubtitle>{copy.catalog.subtitle}</IonCardSubtitle>
                    <IonCardTitle>{copy.agentForm.title}</IonCardTitle>
                  </IonCardHeader>
                  <IonCardContent>
                    <form className="workflow-form" onSubmit={submitAgentDefinition}>
                      <div className="definition-grid">
                        <label className="field-block">
                          <span>{copy.agentForm.id}</span>
                          <input
                            value={agentForm.id}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                id: event.target.value,
                              }))
                            }
                            placeholder={copy.agentForm.idPlaceholder}
                          />
                        </label>
                        <label className="field-block">
                          <span>{copy.agentForm.displayName}</span>
                          <input
                            value={agentForm.name}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                name: event.target.value,
                              }))
                            }
                            placeholder={copy.agentForm.displayNamePlaceholder}
                          />
                        </label>
                      </div>

                      <label className="field-block">
                        <span>{copy.agentForm.businessRole}</span>
                        <input
                          value={agentForm.businessRole}
                          onChange={(event) =>
                            setAgentForm((current) => ({
                              ...current,
                              businessRole: event.target.value,
                            }))
                          }
                          placeholder={copy.agentForm.businessRolePlaceholder}
                        />
                      </label>

                      <label className="field-block">
                        <span>{copy.agentForm.mission}</span>
                        <textarea
                          value={agentForm.mission}
                          onChange={(event) =>
                            setAgentForm((current) => ({
                              ...current,
                              mission: event.target.value,
                            }))
                          }
                          rows={4}
                          placeholder={copy.agentForm.missionPlaceholder}
                        />
                      </label>

                      <div className="definition-grid">
                        <label className="field-block">
                          <span>{copy.agentForm.capabilities}</span>
                          <textarea
                            value={agentForm.capabilitiesText}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                capabilitiesText: event.target.value,
                              }))
                            }
                            rows={4}
                          />
                        </label>
                        <label className="field-block">
                          <span>{copy.agentForm.inputs}</span>
                          <textarea
                            value={agentForm.inputsText}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                inputsText: event.target.value,
                              }))
                            }
                            rows={4}
                          />
                        </label>
                      </div>

                      <div className="definition-grid">
                        <label className="field-block">
                          <span>{copy.agentForm.outputs}</span>
                          <textarea
                            value={agentForm.outputsText}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                outputsText: event.target.value,
                              }))
                            }
                            rows={4}
                          />
                        </label>
                        <label className="field-block">
                          <span>{copy.agentForm.guardrails}</span>
                          <textarea
                            value={agentForm.guardrailsText}
                            onChange={(event) =>
                              setAgentForm((current) => ({
                                ...current,
                                guardrailsText: event.target.value,
                              }))
                            }
                            rows={4}
                          />
                        </label>
                      </div>

                      <div className="form-actions">
                        <IonButton
                          type="submit"
                          disabled={createAgentMutation.isPending || !isAgentFormValid}
                        >
                          {createAgentMutation.isPending
                            ? copy.common.createInProgress
                            : copy.agentForm.create}
                        </IonButton>
                        <IonNote color="medium">
                          {copy.agentForm.persistedNote}
                        </IonNote>
                      </div>
                    </form>

                    {agentFormError ? (
                      <div className="error-box top-gap">{agentFormError}</div>
                    ) : null}
                    {createAgentMutation.error instanceof Error ? (
                      <div className="error-box top-gap">
                        {createAgentMutation.error.message}
                      </div>
                    ) : null}
                  </IonCardContent>
                </IonCard>
              </div>
            </IonContent>
          </IonModal>

          <div className="catalog-pair">
            <IonCard className="hero-card action-card">
              <IonCardHeader>
                <IonCardTitle>{copy.workflowForm.title}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                <p className="section-copy">{copy.workflowForm.actionDescription}</p>
                <div className="action-card__row">
                  <IonButton onClick={() => setIsWorkflowModalOpen(true)}>
                    {copy.workflowForm.openAction}
                  </IonButton>
                  <IonNote color="medium">{copy.workflowForm.actionNote}</IonNote>
                </div>
              </IonCardContent>
            </IonCard>

            <IonCard className="hero-card">
              <IonCardHeader>
                <IonCardTitle>{copy.workflowList.title}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                {workflowDefinitionsQuery.error instanceof Error ? (
                  <div className="error-box">
                    {workflowDefinitionsQuery.error.message}
                  </div>
                ) : null}
                {workflowDefinitions.length === 0 ? (
                  <p className="section-copy">{copy.workflowList.empty}</p>
                ) : (
                  <div className="trace-stack">
                    {workflowDefinitions.map((workflow) => (
                      <article key={workflow.id} className="trace-card">
                        <div className="trace-card__head">
                          <div>
                            <span className="eyebrow">{workflow.id}</span>
                            <h3>{workflow.name}</h3>
                          </div>
                        </div>
                        <p className="trace-copy">{workflow.goal}</p>
                        {renderList(copy.artifacts.constraints, workflow.constraints)}
                        {renderList(copy.artifacts.successCriteria, workflow.success_criteria)}
                        <section className="trace-block">
                          <span className="trace-title">{copy.workflowList.steps}</span>
                          <div className="trace-stack">
                            {workflow.steps.map((step) => {
                              const definition =
                                agentDefinitionsById[step.agent_definition_id];
                              return (
                                <article key={step.id} className="event-item">
                                  <div className="event-item__head">
                                    <strong>{step.name}</strong>
                                  </div>
                                  <p>{step.objective}</p>
                                  <p className="muted-line">
                                    {copy.workflowList.agent}:{" "}
                                    {definition?.name ?? step.agent_definition_id}
                                  </p>
                                  {renderList(
                                    copy.artifacts.expectedDeliverables,
                                    step.expected_deliverables,
                                  )}
                                  {renderList(
                                    copy.artifacts.stepSuccessCriteria,
                                    step.success_criteria,
                                  )}
                                  {renderList(copy.artifacts.dependsOn, step.depends_on)}
                                </article>
                              );
                            })}
                          </div>
                        </section>
                      </article>
                    ))}
                  </div>
                )}
              </IonCardContent>
            </IonCard>
          </div>

          <IonModal
            className="popup-modal"
            isOpen={isWorkflowModalOpen}
            onDidDismiss={() => setIsWorkflowModalOpen(false)}
          >
            <IonHeader>
              <IonToolbar>
                <IonTitle>{copy.workflowForm.title}</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setIsWorkflowModalOpen(false)}>
                    {copy.common.close}
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              <div className="home-shell modal-page-shell">
                <IonCard className="hero-card modal-card">
                  <IonCardHeader>
                    <IonCardSubtitle>{copy.catalog.subtitle}</IonCardSubtitle>
                    <IonCardTitle>{copy.workflowForm.title}</IonCardTitle>
                  </IonCardHeader>
                  <IonCardContent>
                    <form className="workflow-form" onSubmit={submitWorkflowDefinition}>
                      <div className="definition-grid">
                        <label className="field-block">
                          <span>{copy.workflowForm.id}</span>
                          <input
                            value={workflowForm.id}
                            onChange={(event) =>
                              setWorkflowForm((current) => ({
                                ...current,
                                id: event.target.value,
                              }))
                            }
                            placeholder={copy.workflowForm.idPlaceholder}
                          />
                        </label>
                        <label className="field-block">
                          <span>{copy.workflowForm.name}</span>
                          <input
                            value={workflowForm.name}
                            onChange={(event) =>
                              setWorkflowForm((current) => ({
                                ...current,
                                name: event.target.value,
                              }))
                            }
                            placeholder={copy.workflowForm.namePlaceholder}
                          />
                        </label>
                      </div>

                      <label className="field-block">
                        <span>{copy.workflowForm.goal}</span>
                        <textarea
                          value={workflowForm.goal}
                          onChange={(event) =>
                            setWorkflowForm((current) => ({
                              ...current,
                              goal: event.target.value,
                            }))
                          }
                          rows={4}
                          placeholder={copy.workflowForm.goalPlaceholder}
                        />
                      </label>

                      <div className="definition-grid">
                        <label className="field-block">
                          <span>{copy.workflowForm.context}</span>
                          <textarea
                            value={workflowForm.contextText}
                            onChange={(event) =>
                              setWorkflowForm((current) => ({
                                ...current,
                                contextText: event.target.value,
                              }))
                            }
                            rows={4}
                            placeholder={copy.workflowForm.contextPlaceholder}
                          />
                        </label>
                        <label className="field-block">
                          <span>{copy.workflowForm.constraints}</span>
                          <textarea
                            value={workflowForm.constraintsText}
                            onChange={(event) =>
                              setWorkflowForm((current) => ({
                                ...current,
                                constraintsText: event.target.value,
                              }))
                            }
                            rows={4}
                          />
                        </label>
                      </div>

                      <label className="field-block">
                        <span>{copy.workflowForm.successCriteria}</span>
                        <textarea
                          value={workflowForm.successCriteriaText}
                          onChange={(event) =>
                            setWorkflowForm((current) => ({
                              ...current,
                              successCriteriaText: event.target.value,
                            }))
                          }
                          rows={4}
                        />
                      </label>

                      <div className="trace-stack">
                        {workflowForm.steps.map((step, index) => (
                          <article key={`${step.id}-${index}`} className="trace-card">
                            <div className="trace-card__head">
                              <div>
                                <span className="eyebrow">{copy.workflowForm.step(index + 1)}</span>
                                <h3>{step.name || copy.workflowForm.step(index + 1)}</h3>
                              </div>
                              <IonButton
                                type="button"
                                fill="clear"
                                color="medium"
                                disabled={workflowForm.steps.length === 1}
                                onClick={() => removeWorkflowStep(index)}
                              >
                                {copy.common.remove}
                              </IonButton>
                            </div>

                            <div className="definition-grid">
                              <label className="field-block">
                                <span>{copy.workflowForm.stepId}</span>
                                <input
                                  value={step.id}
                                  onChange={(event) =>
                                    setWorkflowForm((current) => ({
                                      ...current,
                                      steps: current.steps.map((currentStep, currentIndex) =>
                                        currentIndex === index
                                          ? { ...currentStep, id: event.target.value }
                                          : currentStep,
                                      ),
                                    }))
                                  }
                                />
                              </label>
                              <label className="field-block">
                                <span>{copy.workflowForm.stepName}</span>
                                <input
                                  value={step.name}
                                  onChange={(event) =>
                                    setWorkflowForm((current) => ({
                                      ...current,
                                      steps: current.steps.map((currentStep, currentIndex) =>
                                        currentIndex === index
                                          ? { ...currentStep, name: event.target.value }
                                          : currentStep,
                                      ),
                                    }))
                                  }
                                />
                              </label>
                            </div>

                            <label className="field-block">
                              <span>{copy.workflowForm.linkedAgent}</span>
                              <select
                                value={step.agentDefinitionId}
                                onChange={(event) =>
                                  setWorkflowForm((current) => ({
                                    ...current,
                                    steps: current.steps.map((currentStep, currentIndex) =>
                                      currentIndex === index
                                        ? {
                                            ...currentStep,
                                            agentDefinitionId: event.target.value,
                                          }
                                        : currentStep,
                                    ),
                                  }))
                                }
                              >
                                <option value="">{copy.workflowForm.selectAgent}</option>
                                {agentDefinitions.map((definition) => (
                                  <option key={definition.id} value={definition.id}>
                                    {definition.name}
                                  </option>
                                ))}
                              </select>
                            </label>

                            <label className="field-block">
                              <span>{copy.workflowForm.objective}</span>
                              <textarea
                                value={step.objective}
                                onChange={(event) =>
                                  setWorkflowForm((current) => ({
                                    ...current,
                                    steps: current.steps.map((currentStep, currentIndex) =>
                                      currentIndex === index
                                        ? { ...currentStep, objective: event.target.value }
                                        : currentStep,
                                    ),
                                  }))
                                }
                                rows={3}
                              />
                            </label>

                            <div className="definition-grid">
                              <label className="field-block">
                                <span>{copy.workflowForm.expectedDeliverables}</span>
                                <textarea
                                  value={step.expectedDeliverablesText}
                                  onChange={(event) =>
                                    setWorkflowForm((current) => ({
                                      ...current,
                                      steps: current.steps.map((currentStep, currentIndex) =>
                                        currentIndex === index
                                          ? {
                                              ...currentStep,
                                              expectedDeliverablesText: event.target.value,
                                            }
                                          : currentStep,
                                      ),
                                    }))
                                  }
                                  rows={3}
                                />
                              </label>
                              <label className="field-block">
                                <span>{copy.workflowForm.stepSuccessCriteria}</span>
                                <textarea
                                  value={step.successCriteriaText}
                                  onChange={(event) =>
                                    setWorkflowForm((current) => ({
                                      ...current,
                                      steps: current.steps.map((currentStep, currentIndex) =>
                                        currentIndex === index
                                          ? {
                                              ...currentStep,
                                              successCriteriaText: event.target.value,
                                            }
                                          : currentStep,
                                      ),
                                    }))
                                  }
                                  rows={3}
                                />
                              </label>
                            </div>

                            <label className="field-block">
                              <span>{copy.workflowForm.dependsOn}</span>
                              <textarea
                                value={step.dependsOnText}
                                onChange={(event) =>
                                  setWorkflowForm((current) => ({
                                    ...current,
                                    steps: current.steps.map((currentStep, currentIndex) =>
                                      currentIndex === index
                                        ? {
                                            ...currentStep,
                                            dependsOnText: event.target.value,
                                          }
                                        : currentStep,
                                    ),
                                  }))
                                }
                                rows={2}
                              />
                            </label>
                          </article>
                        ))}
                      </div>

                      <div className="form-actions">
                        <IonButton type="button" fill="outline" onClick={addWorkflowStep}>
                          {copy.common.addStep}
                        </IonButton>
                        <IonButton
                          type="submit"
                          disabled={
                            createWorkflowMutation.isPending ||
                            !isWorkflowFormValid ||
                            agentDefinitions.length === 0
                          }
                        >
                          {createWorkflowMutation.isPending
                            ? copy.common.createInProgress
                            : copy.workflowForm.create}
                        </IonButton>
                        <IonNote color="medium">{copy.workflowForm.actionNote}</IonNote>
                      </div>
                    </form>

                    {workflowFormError ? (
                      <div className="error-box top-gap">{workflowFormError}</div>
                    ) : null}
                    {createWorkflowMutation.error instanceof Error ? (
                      <div className="error-box top-gap">
                        {createWorkflowMutation.error.message}
                      </div>
                    ) : null}
                  </IonCardContent>
                </IonCard>
              </div>
            </IonContent>
          </IonModal>

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>{copy.repoAudit.subtitle}</IonCardSubtitle>
              <IonCardTitle>{copy.repoAudit.title}</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <form className="workflow-form" onSubmit={submitRepoAudit}>
                <label className="field-block">
                  <span>{copy.repoAudit.objective}</span>
                  <textarea
                    value={objective}
                    onChange={(event) => setObjective(event.target.value)}
                    rows={4}
                    placeholder={copy.repoAudit.objectivePlaceholder}
                  />
                </label>

                <label className="field-block">
                  <span>{copy.repoAudit.repoPath}</span>
                  <input
                    value={repoPath}
                    onChange={(event) => setRepoPath(event.target.value)}
                    placeholder="."
                  />
                </label>

                <div className="field-block">
                  <span>{copy.repoAudit.analysisAxes}</span>
                  <div className="chip-row">
                    {defaultAxes.map((axis) => (
                      <button
                        key={axis}
                        type="button"
                        className={
                          analysisAxes.includes(axis)
                            ? "axis-chip axis-chip--active"
                            : "axis-chip"
                        }
                        onClick={() => toggleAxis(axis)}
                      >
                        {translateAnalysisAxis(axis)}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="form-actions">
                  <IonButton
                    type="submit"
                    disabled={
                      repoAuditMutation.isPending ||
                      objective.trim().length === 0 ||
                      analysisAxes.length === 0
                    }
                  >
                    {repoAuditMutation.isPending
                      ? copy.repoAudit.running
                      : copy.repoAudit.run}
                  </IonButton>
                  <IonNote color="medium">{copy.repoAudit.note}</IonNote>
                </div>
              </form>

              {repoAuditMutation.isPending ? (
                <div className="loading-row top-gap">
                  <IonSpinner name="crescent" />
                  <span>{copy.repoAudit.running}</span>
                </div>
              ) : null}

              {repoAuditMutation.error instanceof Error ? (
                <div className="error-box top-gap">
                  {repoAuditMutation.error.message}
                </div>
              ) : null}
            </IonCardContent>
          </IonCard>

          {report ? (
            <>
              <IonCard>
                <IonCardHeader>
                  <IonCardSubtitle>{copy.report.summarySubtitle}</IonCardSubtitle>
                  <IonCardTitle>{copy.report.summaryTitle}</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <div className="status-grid">
                    <div>
                      <span className="eyebrow">{copy.report.verification}</span>
                      <IonBadge
                        color={report.verification_passed ? "success" : "danger"}
                      >
                        {translatePassState(report.verification_passed)}
                      </IonBadge>
                    </div>
                    <div>
                      <span className="eyebrow">{copy.report.filesScanned}</span>
                      <strong>{report.inventory?.total_files_scanned ?? 0}</strong>
                    </div>
                    <div>
                      <span className="eyebrow">{copy.report.findings}</span>
                      <strong>{report.findings.length}</strong>
                    </div>
                    <div>
                      <span className="eyebrow">{copy.report.evidenceCount}</span>
                      <strong>
                        {report.validation_report?.evidence_count ?? 0}
                      </strong>
                    </div>
                  </div>
                  {report.inventory ? (
                    <div className="top-gap">
                      <span className="eyebrow">{copy.report.detectedLanguages}</span>
                      <div className="chip-row">
                        {report.inventory.detected_languages.map((language) => (
                          <span key={language} className="mini-chip">
                            {language}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </IonCardContent>
              </IonCard>

              <IonCard>
                <IonCardHeader>
                  <IonCardSubtitle>{copy.report.timelineSubtitle}</IonCardSubtitle>
                  <IonCardTitle>{copy.report.timelineTitle}</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <div className="trace-stack">
                    {report.outputs.map((output) => (
                      <RepoAuditStepTraceCard
                        key={output.role}
                        output={output}
                        report={report}
                      />
                    ))}
                  </div>
                </IonCardContent>
              </IonCard>

              <IonCard>
                <IonCardHeader>
                  <IonCardSubtitle>{copy.report.journalSubtitle}</IonCardSubtitle>
                  <IonCardTitle>{copy.report.journalTitle}</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <div className="event-list">
                    {report.memory.events.map((event, index) => (
                      <article
                        key={`${event.role}-${event.type}-${index}`}
                        className="event-item"
                      >
                        <div className="event-item__head">
                          <strong>{event.role}</strong>
                          <IonBadge color="medium">{event.type}</IonBadge>
                        </div>
                        <p>{eventLabel(event)}</p>
                        {event.data ? (
                          <div className="key-value-list">
                            {Object.entries(event.data).map(([key, value]) => (
                              <div key={key}>
                                <strong>{key}</strong>
                                <span>
                                  {Array.isArray(value)
                                    ? value.join(", ")
                                    : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </IonCardContent>
              </IonCard>
            </>
          ) : null}

          {showTeamCard ? (
            <IonCard>
              <IonCardHeader>
                <IonCardSubtitle>
                  {teamQuery.isPending
                    ? copy.team.loadingRoles
                    : copy.team.subtitleLive(teamQuery.data?.roles.length ?? 0)}
                </IonCardSubtitle>
                <IonCardTitle>
                  {teamQuery.data?.name ?? copy.team.fallbackName}
                </IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                {teamQuery.data?.purpose?.trim() ? (
                  <p className="section-copy">{teamQuery.data.purpose}</p>
                ) : null}
                {teamQuery.data?.handoff_contracts.length ? (
                  <div className="team-spec-block">
                    <p className="eyebrow">{copy.team.handoffsTitle}</p>
                    <ul className="team-spec-list">
                      {teamQuery.data.handoff_contracts.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {teamQuery.data?.guardrails.length ? (
                  <div className="team-spec-block">
                    <p className="eyebrow">{copy.team.guardrailsTitle}</p>
                    <ul className="team-spec-list">
                      {teamQuery.data.guardrails.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {(teamQuery.data?.roles ?? []).length > 0 ? (
                  <IonList inset>
                    {(teamQuery.data?.roles ?? []).map((role) => (
                      <IonItem key={role.role}>
                        <IonLabel>
                          <h2>{translateRuntimeRoleLabel(role.role)}</h2>
                          <p>{role.responsibility}</p>
                          <p className="muted-line">
                            {copy.team.capabilities}: {role.capabilities.join(", ")}
                          </p>
                        </IonLabel>
                      </IonItem>
                    ))}
                  </IonList>
                ) : null}
              </IonCardContent>
            </IonCard>
          ) : null}

          {showUseCasesCard ? (
            <IonCard>
              <IonCardHeader>
                <IonCardSubtitle>
                  {useCasesQuery.isPending
                    ? copy.useCases.loading
                    : copy.useCases.subtitleLive(teamAlignedUseCases.length)}
                </IonCardSubtitle>
                <IonCardTitle>{copy.useCases.title}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                <IonList inset>
                  {teamAlignedUseCases.map((useCase) => (
                    <IonItem key={useCase.id}>
                      <IonLabel>
                        <h2>{useCase.title}</h2>
                        <p>{useCase.description}</p>
                        <p className="muted-line">
                          {copy.useCases.expectedOutcome}: {useCase.primary_outcome}
                        </p>
                      </IonLabel>
                    </IonItem>
                  ))}
                </IonList>
              </IonCardContent>
            </IonCard>
          ) : null}
        </div>
      </IonContent>
    </IonPage>
  );
};

export default HomePage;
