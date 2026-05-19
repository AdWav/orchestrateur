import { IonBadge, IonNote } from "@ionic/react";

import { useI18n } from "../i18n/I18nProvider";
import type { DevTeamBenchmarkReport } from "../lib/api";

export default function BenchmarkWorkspacePanel({
  report,
}: {
  report: DevTeamBenchmarkReport;
}) {
  const { messages, t } = useI18n();

  if (!report.workspace_root || !report.workspace_run_id) {
    return (
      <IonNote color="medium" className="benchmark-simulation-note">
        {messages.devTeams.benchmarkWorkspaceDisabled}
      </IonNote>
    );
  }

  return (
    <section className="benchmark-workspace-panel">
      <p className="eyebrow">{messages.devTeams.benchmarkWorkspaceTitle}</p>
      <p className="trace-copy">
        <strong>{messages.devTeams.benchmarkWorkspaceRun}</strong>{" "}
        <code className="inline-code">{report.workspace_run_id}</code>
      </p>
      <p className="trace-copy muted-line">
        <strong>{messages.devTeams.benchmarkWorkspaceRoot}</strong>{" "}
        <code className="inline-code">{report.workspace_root}</code>
      </p>
      <ul className="benchmark-workspace-list">
        {report.runs.map((run) => {
          const workspace = run.workspace;
          const teamId = run.team_id ?? messages.common.emDash;
          if (!workspace) {
            return null;
          }
          return (
            <li key={teamId} className="benchmark-workspace-list__item">
              <div className="benchmark-workspace-list__head">
                <strong>{teamId}</strong>
                <IonBadge
                  color={
                    workspace.tests_passed === true
                      ? "success"
                      : workspace.tests_passed === false
                        ? "danger"
                        : "medium"
                  }
                >
                  {workspace.tests_passed === true
                    ? messages.devTeams.benchmarkWorkspaceTestsOk
                    : workspace.tests_passed === false
                      ? messages.devTeams.benchmarkWorkspaceTestsKo
                      : messages.devTeams.benchmarkWorkspaceTestsSkipped}
                </IonBadge>
              </div>
              <p className="trace-copy">
                <code className="inline-code">{workspace.path}</code>
              </p>
              <p className="trace-copy muted-line">
                {t("devTeams.benchmarkWorkspaceRunHint", {
                  command: workspace.test_command,
                })}
              </p>
              {workspace.runner_exec_command ? (
                <p className="trace-copy muted-line">
                  <strong>{messages.devTeams.benchmarkWorkspaceRunnerLabel}</strong>{" "}
                  <code className="inline-code">{workspace.runner_exec_command}</code>
                </p>
              ) : null}
              {workspace.test_output ? (
                <pre className="mono-block benchmark-workspace-output">
                  {workspace.test_output}
                </pre>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
