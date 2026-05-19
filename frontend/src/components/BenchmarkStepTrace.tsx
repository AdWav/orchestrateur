import { IonChip, IonToggle } from "@ionic/react";
import { useMemo, useState } from "react";

import { useI18n } from "../i18n/I18nProvider";
import {
type  ArtifactBucket,
  formatJsonValue,
  groupArtifactsByBucket,
} from "../lib/artifactView";
import type { AgentOutput, JsonValue } from "../lib/api";

type TraceViewMode = "trace" | "json";

const SUMMARY_PREVIEW_LENGTH = 480;

function renderStringList(title: string, items: string[]) {
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

function isRecord(value: unknown): value is Record<string, JsonValue> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function renderArtifactValue(
  title: string,
  value: JsonValue,
  labelForKey: (key: string) => string,
) {
  if (Array.isArray(value) && value.every((item) => typeof item === "string")) {
    return renderStringList(title, value);
  }

  if (Array.isArray(value)) {
    return (
      <section className="trace-block" key={title}>
        <span className="trace-title">{title}</span>
        <pre className="mono-block">{JSON.stringify(value, null, 2)}</pre>
      </section>
    );
  }

  if (isRecord(value)) {
    return (
      <section className="trace-block" key={title}>
        <span className="trace-title">{title}</span>
        <div className="key-value-list">
          {Object.entries(value).map(([key, nestedValue]) => (
            <div key={key}>
              <strong>{labelForKey(key)}</strong>
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

function renderArtifactBucket(
  bucket: ArtifactBucket,
  sectionTitle: string,
  artifacts: Record<string, JsonValue>,
  labelForKey: (key: string) => string,
) {
  const entries = Object.entries(artifacts);
  if (entries.length === 0) {
    return null;
  }

  return (
    <section className="benchmark-deliverable-section" key={bucket}>
      <h4 className="benchmark-deliverable-section__title">{sectionTitle}</h4>
      {entries.map(([key, value]) =>
        renderArtifactValue(labelForKey(key), value, labelForKey),
      )}
    </section>
  );
}

function SummaryBlock({ summary }: { summary: string }) {
  const { messages } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const trimmed = summary.trim();
  if (!trimmed) {
    return null;
  }

  const isLong = trimmed.length > SUMMARY_PREVIEW_LENGTH;
  const preview = isLong ? `${trimmed.slice(0, SUMMARY_PREVIEW_LENGTH)}…` : trimmed;

  return (
    <section className="trace-block">
      <span className="trace-title">{messages.devTeams.benchmarkStepSummary}</span>
      <p className="trace-copy benchmark-step-summary">
        {expanded || !isLong ? trimmed : preview}
      </p>
      {isLong ? (
        <button
          type="button"
          className="benchmark-step-summary__toggle"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded
            ? messages.devTeams.benchmarkHideFullSummary
            : messages.devTeams.benchmarkShowFullSummary}
        </button>
      ) : null}
    </section>
  );
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

function GroupedArtifacts({ output }: { output: AgentOutput }) {
  const { messages, artifactKey } = useI18n();
  const grouped = groupArtifactsByBucket(output.artifacts);

  return (
    <>
      {renderArtifactBucket(
        "code",
        messages.devTeams.benchmarkSectionCode,
        grouped.code,
        artifactKey,
      )}
      {renderArtifactBucket(
        "tests",
        messages.devTeams.benchmarkSectionTests,
        grouped.tests,
        artifactKey,
      )}
      {renderArtifactBucket(
        "documentation",
        messages.devTeams.benchmarkSectionDocs,
        grouped.documentation,
        artifactKey,
      )}
      {renderArtifactBucket(
        "other",
        messages.devTeams.benchmarkSectionOther,
        grouped.other,
        artifactKey,
      )}
    </>
  );
}

export default function BenchmarkStepTrace({ output }: { output: AgentOutput }) {
  const { messages, runtimeRoleLabel, approvalState } = useI18n();
  const [viewMode, setViewMode] = useState<TraceViewMode>("trace");
  const rawJson = useMemo(() => JSON.stringify(output, null, 2), [output]);

  return (
    <article className="trace-card benchmark-step-trace">
      <div className="trace-card__head">
        <div>
          <span className="eyebrow">{messages.report.agent}</span>
          <h3>{runtimeRoleLabel(output.role)}</h3>
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
          {approvalState(output.approved)}
        </IonChip>
      </div>

      <div className="toggle-wrapper trace-card__view-toggle">
        <div className="toggle-wrapper__spacer" aria-hidden="true" />
        <div className="toggle-wrapper__control">
          <IonToggle
            checked={viewMode === "json"}
            aria-label={messages.report.viewModeToggleAria}
            onIonChange={(event) =>
              setViewMode(event.detail.checked ? "json" : "trace")
            }
          />
          <span className="toggle-wrapper__json-label">
            {messages.report.jsonToggleCaption}
          </span>
        </div>
      </div>

      {viewMode === "json" ? (
        <pre className="mono-block trace-card__raw-json">{rawJson}</pre>
      ) : (
        <>
          <SummaryBlock summary={output.summary} />
          <GroupedArtifacts output={output} />
          {renderList(messages.artifacts.nextActions, output.next_actions)}
        </>
      )}
    </article>
  );
}
