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
  IonNote,
  IonPage,
  IonSpinner,
  IonToggle,
  IonTitle,
  IonToolbar,
} from "@ionic/react";
import { moonOutline, sunnyOutline } from "ionicons/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  AgentOutput,
  MemoryEvent,
  RepoAuditReport,
  apiBaseUrl,
  fetchHealth,
  fetchServiceStatus,
  fetchTeam,
  fetchUseCases,
  runRepoAudit,
} from "../lib/api";
import type { ThemeMode } from "../theme/theme";

import "./HomePage.css";

const defaultObjective =
  "Auditer ce depot pour exposer les signaux d'architecture, de tests, de documentation et de securite.";
const defaultAxes = [
  "architecture",
  "tests",
  "docs",
  "security",
  "dependencies",
];

type HomePageProps = {
  themeMode: ThemeMode;
  onThemeChange: (themeMode: ThemeMode) => void;
};

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
  return (
    <>
      {renderList("Search plan", asStringArray(output.artifacts.search_plan))}
      {renderList(
        "Acceptance criteria",
        asStringArray(output.artifacts.acceptance_criteria),
      )}
    </>
  );
}

function renderResearcherArtifacts(output: AgentOutput) {
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
        "Important files",
        asStringArray(output.artifacts.important_files),
      )}
      {coverageMap ? (
        <section className="trace-block">
          <span className="trace-title">Coverage map</span>
          <div className="key-value-list">
            {Object.entries(coverageMap).map(([axis, paths]) => (
              <div key={axis}>
                <strong>{axis}</strong>
                <span>{asStringArray(paths).join(", ") || "none"}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      {evidenceRefs.length > 0 ? (
        <section className="trace-block">
          <span className="trace-title">Evidence excerpts</span>
          <div className="evidence-list">
            {evidenceRefs.slice(0, 4).map((evidence) => (
              <article
                key={`${String(evidence.path ?? "unknown")}-${String(evidence.reason ?? "reason")}`}
                className="evidence-item"
              >
                <strong>{String(evidence.path ?? "unknown")}</strong>
                <span>{String(evidence.reason ?? "No reason provided")}</span>
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
  const findings = report.findings;

  return (
    <>
      {typeof output.artifacts.repo_summary === "string" ? (
        <section className="trace-block">
          <span className="trace-title">Repository summary</span>
          <p className="trace-copy">{output.artifacts.repo_summary}</p>
        </section>
      ) : null}
      {findings.length > 0 ? (
        <section className="trace-block">
          <span className="trace-title">Findings</span>
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
        "Recommended actions",
        asStringArray(output.artifacts.recommended_actions),
      )}
      {renderList("Unknowns", asStringArray(output.artifacts.unknowns))}
    </>
  );
}

function renderVerifierArtifacts(output: AgentOutput) {
  const validation = isRecord(output.artifacts.validation_report)
    ? output.artifacts.validation_report
    : null;

  if (!validation) {
    return null;
  }

  return (
    <>
      <section className="trace-block">
        <span className="trace-title">Validation status</span>
        <div className="status-grid compact-grid">
          <div>
            <span className="eyebrow">Approved</span>
            <IonBadge color={validation.approved ? "success" : "danger"}>
              {String(validation.approved)}
            </IonBadge>
          </div>
          <div>
            <span className="eyebrow">Evidence count</span>
            <strong>{String(validation.evidence_count ?? 0)}</strong>
          </div>
        </div>
      </section>
      {renderList("Covered axes", asStringArray(validation.covered_axes))}
      {renderList(
        "Policy compliance",
        asStringArray(validation.policy_compliance),
      )}
      {renderList(
        "Missing requirements",
        asStringArray(validation.missing_requirements),
      )}
      {renderList(
        "Unsupported claims",
        asStringArray(validation.unsupported_claims),
      )}
    </>
  );
}

function renderOutputArtifacts(output: AgentOutput, report: RepoAuditReport) {
  switch (output.role) {
    case "Planner":
      return renderPlannerArtifacts(output);
    case "Researcher":
      return renderResearcherArtifacts(output);
    case "Executor":
      return renderExecutorArtifacts(output, report);
    case "Verifier":
      return renderVerifierArtifacts(output);
    default:
      return null;
  }
}

function eventLabel(event: MemoryEvent) {
  if (event.message) {
    return event.message;
  }

  if (event.key) {
    return `Memory updated: ${event.key}`;
  }

  return event.type;
}

const HomePage = ({
  themeMode,
  onThemeChange,
}: HomePageProps) => {
  const [objective, setObjective] = useState(defaultObjective);
  const [repoPath, setRepoPath] = useState(".");
  const [analysisAxes, setAnalysisAxes] = useState<string[]>(defaultAxes);

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
  const repoAuditMutation = useMutation({
    mutationFn: runRepoAudit,
  });

  const bootstrapError =
    healthQuery.error ?? teamQuery.error ?? useCasesQuery.error ?? null;
  const isLoading =
    healthQuery.isLoading || teamQuery.isLoading || useCasesQuery.isLoading;
  const report = repoAuditMutation.data;
  const poService =
    serviceStatusQuery.data?.services.find((service) => service.key === "po") ??
    null;
  const poChipColor = serviceStatusQuery.isLoading
    ? "medium"
    : serviceStatusQuery.error || poService?.active === false
      ? "danger"
      : "primary";
  const poChipStateLabel = serviceStatusQuery.isLoading
    ? "Loading..."
    : serviceStatusQuery.error instanceof Error
      ? serviceStatusQuery.error.message
      : poService?.active === false
        ? "Offline"
        : "Online";

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

  return (
    <IonPage>
      <IonHeader translucent>
        <IonToolbar>
          <IonTitle>Orchestrateur Local</IonTitle>
          <IonButtons slot="end">
            <div className="toggle-icon">
              <IonIcon
                icon={sunnyOutline}
                aria-hidden="true"
                className={themeMode === "light" ? "is-active" : undefined}
              />
              <IonToggle
                checked={themeMode === "dark"}
                aria-label={`Basculer vers le mode ${themeMode === "dark" ? "clair" : "sombre"}`}
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
            <IonButton href={`${apiBaseUrl}/docs`} target="_blank">
              API
            </IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <div className="home-shell">
          <section className="hero-card">
            <div className="hero-card__head">
              <div>
                <span className="eyebrow">Containers</span>
                <h1>Lumieres du mesh</h1>
              </div>
              <IonChip color={poChipColor} className="hero-status-chip">
                {serviceStatusQuery.isLoading ? (
                  <IonSpinner name="crescent" className="hero-status-chip__spinner" />
                ) : null}
                <span className="hero-status-chip__label">PO / :8000</span>
                <span className="hero-status-chip__state">{poChipStateLabel}</span>
              </IonChip>
            </div>
            <div className="service-lights">
              {(serviceStatusQuery.data?.services ?? []).map((service) => (
                <article key={service.key} className="service-light">
                  <span
                    className={
                      service.active
                        ? "service-light__dot service-light__dot--up"
                        : "service-light__dot service-light__dot--down"
                    }
                  />
                  <div>
                    <strong>{service.label}</strong>
                    <span>
                      {service.port ? `:${service.port}` : service.target}
                    </span>
                  </div>
                </article>
              ))}
            </div>
            <IonNote color="medium">Vert = actif, rouge = eteint</IonNote>
          </section>

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>Connexion backend</IonCardSubtitle>
              <IonCardTitle>Sante du service</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              {isLoading ? (
                <div className="loading-row">
                  <IonSpinner name="crescent" />
                  <span>Chargement des informations de demarrage...</span>
                </div>
              ) : (
                <div className="status-grid">
                  <div>
                    <span className="eyebrow">Service</span>
                    <strong>{healthQuery.data?.service ?? "unavailable"}</strong>
                  </div>
                  <div>
                    <span className="eyebrow">Etat</span>
                    <IonBadge color={bootstrapError ? "danger" : "success"}>
                      {bootstrapError ? "unreachable" : healthQuery.data?.status}
                    </IonBadge>
                  </div>
                  <div>
                    <span className="eyebrow">Equipe</span>
                    <strong>
                      {bootstrapError
                        ? "n/a"
                        : `${teamQuery.data?.roles.length ?? 0} roles`}
                    </strong>
                  </div>
                  <div>
                    <span className="eyebrow">Use cases</span>
                    <strong>
                      {bootstrapError
                        ? "n/a"
                        : `${useCasesQuery.data?.length ?? 0} exposes`}
                    </strong>
                  </div>
                </div>
              )}
            </IonCardContent>
          </IonCard>

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>Trace observable</IonCardSubtitle>
              <IonCardTitle>Lancer un repo audit depuis `:8000`</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <form className="workflow-form" onSubmit={submitRepoAudit}>
                <label className="field-block">
                  <span>Objective</span>
                  <textarea
                    value={objective}
                    onChange={(event) => setObjective(event.target.value)}
                    rows={4}
                    placeholder="Decris le type d'audit a demander a l'orchestrateur."
                  />
                </label>

                <label className="field-block">
                  <span>Repo path</span>
                  <input
                    value={repoPath}
                    onChange={(event) => setRepoPath(event.target.value)}
                    placeholder="."
                  />
                </label>

                <div className="field-block">
                  <span>Analysis axes</span>
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
                        {axis}
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
                      ? "Running audit..."
                      : "Run repo audit"}
                  </IonButton>
                  <IonNote color="medium">
                    La vue affiche une trace structuree, pas la pensee brute
                    cachee.
                  </IonNote>
                </div>
              </form>

              {repoAuditMutation.isPending ? (
                <div className="loading-row top-gap">
                  <IonSpinner name="crescent" />
                  <span>Execution du workflow en cours...</span>
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
                  <IonCardSubtitle>Run summary</IonCardSubtitle>
                  <IonCardTitle>Etat global du workflow</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <div className="status-grid">
                    <div>
                      <span className="eyebrow">Verification</span>
                      <IonBadge
                        color={report.verification_passed ? "success" : "danger"}
                      >
                        {report.verification_passed ? "passed" : "blocked"}
                      </IonBadge>
                    </div>
                    <div>
                      <span className="eyebrow">Files scanned</span>
                      <strong>{report.inventory?.total_files_scanned ?? 0}</strong>
                    </div>
                    <div>
                      <span className="eyebrow">Findings</span>
                      <strong>{report.findings.length}</strong>
                    </div>
                    <div>
                      <span className="eyebrow">Evidence count</span>
                      <strong>
                        {report.validation_report?.evidence_count ?? 0}
                      </strong>
                    </div>
                  </div>
                  {report.inventory ? (
                    <div className="top-gap">
                      <span className="eyebrow">Detected languages</span>
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
                  <IonCardSubtitle>Agent timeline</IonCardSubtitle>
                  <IonCardTitle>Reflexion observable par etape</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <div className="trace-stack">
                    {report.outputs.map((output) => (
                      <article key={output.role} className="trace-card">
                        <div className="trace-card__head">
                          <div>
                            <span className="eyebrow">Agent</span>
                            <h3>{output.role}</h3>
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
                            {output.approved === true
                              ? "approved"
                              : output.approved === false
                                ? "blocked"
                                : "in flow"}
                          </IonChip>
                        </div>

                        <p className="trace-copy">{output.summary}</p>
                        {renderOutputArtifacts(output, report)}
                        {renderList("Next actions", output.next_actions)}
                      </article>
                    ))}
                  </div>
                </IonCardContent>
              </IonCard>

              <IonCard>
                <IonCardHeader>
                  <IonCardSubtitle>Workflow journal</IonCardSubtitle>
                  <IonCardTitle>Evenements traces par l'orchestrateur</IonCardTitle>
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

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>Equipe actuelle</IonCardSubtitle>
              <IonCardTitle>
                {teamQuery.data?.name ?? "Specification Team"}
              </IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <p className="section-copy">
                {teamQuery.data?.purpose ??
                  "Le frontend est pret a afficher les roles et les contrats de handoff exposes par l'API."}
              </p>
              <IonList inset>
                {(teamQuery.data?.roles ?? []).map((role) => (
                  <IonItem key={role.role}>
                    <IonLabel>
                      <h2>{role.role}</h2>
                      <p>{role.responsibility}</p>
                      <p className="muted-line">
                        Capacites: {role.capabilities.join(", ")}
                      </p>
                    </IonLabel>
                  </IonItem>
                ))}
              </IonList>
            </IonCardContent>
          </IonCard>

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>Workflows exposes</IonCardSubtitle>
              <IonCardTitle>Cas d'usage disponibles</IonCardTitle>
            </IonCardHeader>
            <IonCardContent>
              <IonList inset>
                {(useCasesQuery.data ?? []).map((useCase) => (
                  <IonItem key={useCase.id}>
                    <IonLabel>
                      <h2>{useCase.title}</h2>
                      <p>{useCase.description}</p>
                      <p className="muted-line">
                        Resultat attendu: {useCase.primary_outcome}
                      </p>
                    </IonLabel>
                  </IonItem>
                ))}
              </IonList>
            </IonCardContent>
          </IonCard>
        </div>
      </IonContent>
    </IonPage>
  );
};

export default HomePage;
