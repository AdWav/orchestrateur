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
  IonModal,
  IonNote,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from "@ionic/react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import BenchmarkStepTrace from "./BenchmarkStepTrace";
import BenchmarkWorkspacePanel from "./BenchmarkWorkspacePanel";
import { useI18n } from "../i18n/I18nProvider";
import {
  AgentDescriptor,
  DevTeamBenchmarkReport,
  TeamSpecification,
  fetchTeams,
  runDevTeamBenchmark,
} from "../lib/api";

import "./DevTeamsSection.css";

function roleDetailList(title: string, items: string[]) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="dev-team-role-modal__block">
      <span className="trace-title">{title}</span>
      <ul className="trace-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function TeamRoleModal({
  role,
  teamName,
  isOpen,
  onClose,
}: {
  role: AgentDescriptor | null;
  teamName: string;
  isOpen: boolean;
  onClose: () => void;
}) {
  const { messages, runtimeRoleLabel, roleResponsibility } = useI18n();

  return (
    <IonModal
      className="popup-modal dev-team-role-modal"
      isOpen={isOpen && role !== null}
      onDidDismiss={onClose}
    >
      <IonHeader>
        <IonToolbar>
          <IonTitle>
            {role ? runtimeRoleLabel(role.role) : messages.devTeams.pipeline}
          </IonTitle>
          <IonButtons slot="end">
            <IonButton onClick={onClose}>{messages.common.close}</IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent>
        {role ? (
          <div className="home-shell modal-page-shell dev-team-role-modal__body">
            <p className="eyebrow">{teamName}</p>
            <p className="trace-copy">
              {roleResponsibility(role.role, role.responsibility)}
            </p>
            {roleDetailList(messages.artifacts.capabilities, role.capabilities)}
            {roleDetailList(messages.artifacts.inputs, role.allowed_inputs)}
            {roleDetailList(messages.artifacts.outputs, role.produces)}
          </div>
        ) : null}
      </IonContent>
    </IonModal>
  );
}

function TeamCard({ team }: { team: TeamSpecification }) {
  const {
    messages,
    t,
    runtimeRoleLabel,
    teamName,
    teamPurpose,
    teamMethodology,
    teamHandoffs,
    teamGuardrails,
  } = useI18n();
  const [selectedRole, setSelectedRole] = useState<AgentDescriptor | null>(null);
  const steps =
    team.pipeline_step_ids.length > 0
      ? team.pipeline_step_ids
      : team.roles.map((role) => role.role);

  const rolesByStep = useMemo(() => {
    const map = new Map<string, AgentDescriptor>();
    for (const role of team.roles) {
      map.set(role.role, role);
    }
    return map;
  }, [team.roles]);

  const localizedName = teamName(team.id, team.name);
  const localizedPurpose = teamPurpose(team.id, team.purpose);
  const localizedHandoffs = teamHandoffs(team.id, team.handoff_contracts);
  const localizedGuardrails = teamGuardrails(team.id, team.guardrails);
  const methodologyLabel = team.methodology
    ? teamMethodology(team.methodology)
    : team.id;
  const runnersLabel =
    steps.length === 1
      ? t("devTeams.runnersOne")
      : t("devTeams.runnersMany", { count: steps.length });

  const openRole = (stepId: string) => {
    const role = rolesByStep.get(stepId);
    if (role) {
      setSelectedRole(role);
    }
  };

  return (
    <>
      <IonCard className="hero-card dev-team-card">
        <IonCardHeader>
          <IonCardSubtitle>
            {methodologyLabel} · {runnersLabel}
          </IonCardSubtitle>
          <IonCardTitle>{localizedName}</IonCardTitle>
        </IonCardHeader>
        <IonCardContent>
          <p className="section-copy">{localizedPurpose}</p>
          <div className="dev-team-card__block">
            <p className="eyebrow">{messages.devTeams.pipeline}</p>
            <IonNote color="medium" className="dev-team-card__pipeline-hint">
              {messages.devTeams.pipelineChipHint}
            </IonNote>
            <div className="chip-row dev-team-card__pipeline-chips">
              {steps.map((step) => {
                const hasDetail = rolesByStep.has(step);
                return (
                  <IonChip
                    key={step}
                    color="primary"
                    outline
                    className={hasDetail ? "dev-team-chip--interactive" : undefined}
                    onClick={hasDetail ? () => openRole(step) : undefined}
                  >
                    {runtimeRoleLabel(step)}
                  </IonChip>
                );
              })}
            </div>
          </div>
          {localizedHandoffs.length > 0 ? (
            <div className="dev-team-card__block">
              <p className="eyebrow">{messages.devTeams.handoffsTitle}</p>
              <ul className="team-spec-list">
                {localizedHandoffs.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {localizedGuardrails.length > 0 ? (
            <div className="dev-team-card__block">
              <p className="eyebrow">{messages.devTeams.guardrailsTitle}</p>
              <ul className="team-spec-list">
                {localizedGuardrails.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </IonCardContent>
      </IonCard>
      <TeamRoleModal
        role={selectedRole}
        teamName={localizedName}
        isOpen={selectedRole !== null}
        onClose={() => setSelectedRole(null)}
      />
    </>
  );
}

function BenchmarkResults({ report }: { report: DevTeamBenchmarkReport }) {
  const { messages, t, runtimeRoleLabel } = useI18n();
  const { comparison } = report;

  return (
    <IonCard className="hero-card dev-benchmark-results">
      <IonCardHeader>
        <IonCardSubtitle>{messages.devTeams.benchmarkResultsTitle}</IonCardSubtitle>
        <IonCardTitle>{report.request.objective}</IonCardTitle>
      </IonCardHeader>
      <IonCardContent>
        {comparison.fastest_team_id ? (
          <div className="status-grid">
            <div>
              <span className="eyebrow">{messages.devTeams.benchmarkFastest}</span>
              <strong>{comparison.fastest_team_id}</strong>
            </div>
          </div>
        ) : null}
        <IonNote color="medium" className="benchmark-simulation-note">
          {messages.devTeams.benchmarkSimulationNote}
        </IonNote>
        <BenchmarkWorkspacePanel report={report} />
        <div className="trace-stack top-gap benchmark-runs">
          {report.runs.map((run) => {
            const teamId = run.team_id ?? messages.common.emDash;
            const ok = comparison.success_by_team[teamId];
            const duration = comparison.duration_ms_by_team[teamId];
            return (
              <section key={teamId} className="benchmark-team-run">
                <article className="trace-card benchmark-team-run__summary">
                  <div className="trace-card__head">
                    <div>
                      <span className="eyebrow">{teamId}</span>
                      <h3>
                        {messages.devTeams.benchmarkSuccess}:{" "}
                        {ok ? messages.devTeams.benchmarkYes : messages.devTeams.benchmarkNo}
                      </h3>
                    </div>
                    <IonBadge color={ok ? "success" : "danger"}>
                      {duration != null
                        ? t("common.durationMs", { value: Math.round(duration) })
                        : messages.common.notAvailable}
                    </IonBadge>
                  </div>
                  <p className="trace-copy muted-line">
                    {run.outputs
                      .map((output) => runtimeRoleLabel(output.role))
                      .join(messages.common.pipelineSeparator)}
                  </p>
                </article>
                <div className="benchmark-team-run__steps">
                  <p className="eyebrow">{messages.devTeams.benchmarkDeliverables}</p>
                  <div className="trace-stack">
                    {run.outputs.map((output, index) => (
                      <BenchmarkStepTrace
                        key={`${teamId}-${output.role}-${index}`}
                        output={output}
                      />
                    ))}
                  </div>
                </div>
              </section>
            );
          })}
        </div>
        {comparison.notes.length > 0 ? (
          <div className="dev-team-card__block top-gap">
            <p className="eyebrow">{messages.devTeams.benchmarkNotes}</p>
            <ul className="team-spec-list">
              {comparison.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </IonCardContent>
    </IonCard>
  );
}

export default function DevTeamsSection() {
  const { messages, t, language } = useI18n();
  const benchmarkObjectiveEditedRef = useRef(false);
  const [benchmarkObjective, setBenchmarkObjective] = useState(
    () => messages.devTeams.benchmarkDefaultObjective,
  );

  useEffect(() => {
    if (!benchmarkObjectiveEditedRef.current) {
      setBenchmarkObjective(messages.devTeams.benchmarkDefaultObjective);
    }
  }, [language, messages.devTeams.benchmarkDefaultObjective]);

  const teamsQuery = useQuery({
    queryKey: ["teams", language],
    queryFn: fetchTeams,
    staleTime: 60_000,
  });

  const benchmarkMutation = useMutation({
    mutationFn: runDevTeamBenchmark,
  });

  const teams = teamsQuery.data ?? [];
  const orderedTeams = [...teams].sort((a, b) => a.id.localeCompare(b.id));

  const submitBenchmark = (event: FormEvent) => {
    event.preventDefault();
    const objective = benchmarkObjective.trim();
    if (!objective) {
      return;
    }
    benchmarkMutation.mutate({ objective });
  };

  return (
    <>
      <IonCard className="hero-card dev-teams-intro">
        <IonCardHeader>
          <IonCardSubtitle>{messages.devTeams.subtitle}</IonCardSubtitle>
          <IonCardTitle>{messages.devTeams.title}</IonCardTitle>
        </IonCardHeader>
      </IonCard>

      {teamsQuery.isLoading ? (
        <div className="loading-row">
          <IonSpinner name="crescent" />
          <span>{messages.devTeams.loading}</span>
        </div>
      ) : null}

      {teamsQuery.error instanceof Error ? (
        <div className="error-box">{teamsQuery.error.message}</div>
      ) : null}

      {orderedTeams.length > 0 ? (
        <div className="dev-teams-pair">
          {orderedTeams.map((team) => (
            <TeamCard key={team.id} team={team} />
          ))}
        </div>
      ) : null}

      <IonCard className="hero-card">
        <IonCardHeader>
          <IonCardSubtitle>{messages.devTeams.benchmarkSubtitle}</IonCardSubtitle>
          <IonCardTitle>{messages.devTeams.benchmarkTitle}</IonCardTitle>
        </IonCardHeader>
        <IonCardContent>
          <form className="workflow-form" onSubmit={submitBenchmark}>
            <label className="field-block">
              <span>{messages.devTeams.benchmarkObjective}</span>
              <textarea
                value={benchmarkObjective}
                onChange={(event) => {
                  benchmarkObjectiveEditedRef.current = true;
                  setBenchmarkObjective(event.target.value);
                }}
                rows={4}
                placeholder={messages.devTeams.benchmarkObjectivePlaceholder}
              />
            </label>
            <div className="form-actions">
              <IonButton
                type="submit"
                disabled={
                  benchmarkMutation.isPending || benchmarkObjective.trim().length === 0
                }
              >
                {benchmarkMutation.isPending
                  ? messages.devTeams.benchmarkRunning
                  : messages.devTeams.benchmarkRun}
              </IonButton>
              <IonNote color="medium">{messages.devTeams.benchmarkNote}</IonNote>
            </div>
          </form>
          {benchmarkMutation.isPending ? (
            <div className="loading-row top-gap">
              <IonSpinner name="crescent" />
              <span>{messages.devTeams.benchmarkRunning}</span>
            </div>
          ) : null}
          {benchmarkMutation.error instanceof Error ? (
            <div className="error-box top-gap">{benchmarkMutation.error.message}</div>
          ) : null}
        </IonCardContent>
      </IonCard>

      {benchmarkMutation.data ? <BenchmarkResults report={benchmarkMutation.data} /> : null}
    </>
  );
}
