import {
  IonChip,
  IonItem,
  IonLabel,
  IonNote,
  IonSegment,
  IonSegmentButton,
} from "@ionic/react";
import { useLayoutEffect, useMemo, useRef, useState } from "react";

import {
  COURSE_FIELD_ORDER,
  PIPELINE_STEPS,
  SAMPLING_COURSE_ENTRIES,
  courseEntryForField,
  type CourseFieldKey,
  type PipelineStepId,
} from "../course/samplingCourseCatalog";
import { SAMPLING_FIELD_SPECS } from "./samplingFieldSpecs";
import SamplingCourseWorkedExample from "./SamplingCourseWorkedExample";
import { useI18n } from "../i18n/I18nProvider";

import "./SamplingCoursePanel.css";

type CourseViewMode = "pipeline" | "knobs";

type SamplingCoursePanelProps = {
  /** Met en surbrillance le reglage selectionne (depuis la vue reglages). */
  highlightField?: CourseFieldKey | null;
  onHighlightField?: (field: CourseFieldKey | null) => void;
};

const SamplingCoursePanel = ({
  highlightField = null,
  onHighlightField,
}: SamplingCoursePanelProps) => {
  const { messages } = useI18n();
  const course = messages.course;
  const [viewMode, setViewMode] = useState<CourseViewMode>("pipeline");
  const [selectedField, setSelectedField] = useState<CourseFieldKey | null>(
    highlightField ?? null,
  );

  const activeField = highlightField ?? selectedField;

  const pipelineLabels = course.pipelineSteps as Record<PipelineStepId, string>;
  const equationTexts = course.equations as Record<string, string>;
  const referenceTexts = course.references as Record<
    string,
    { title: string; url: string }
  >;

  const entriesByStep = useMemo(() => {
    const map = new Map<PipelineStepId, typeof SAMPLING_COURSE_ENTRIES>();
    for (const step of PIPELINE_STEPS) {
      map.set(
        step.id,
        SAMPLING_COURSE_ENTRIES.filter((e) => e.pipelineStepId === step.id),
      );
    }
    return map;
  }, []);

  const activeFieldStepId: PipelineStepId | null = useMemo(() => {
    if (!activeField) {
      return null;
    }
    return courseEntryForField(activeField)?.pipelineStepId ?? null;
  }, [activeField]);

  const pipelineDetailRef = useRef<HTMLDivElement | null>(null);
  const knobListDetailRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (viewMode === "pipeline") {
      pipelineDetailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else if (viewMode === "knobs" && activeField) {
      knobListDetailRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activeField, viewMode]);

  const selectField = (field: CourseFieldKey) => {
    setSelectedField(field);
    onHighlightField?.(field);
  };

  const renderFieldDetail = (fieldKey: CourseFieldKey) => {
    const entry = courseEntryForField(fieldKey);
    if (!entry) {
      return null;
    }
    const knobLabel = messages.sampling.fields[fieldKey as keyof typeof messages.sampling.fields];
    const spec =
      fieldKey in SAMPLING_FIELD_SPECS
        ? SAMPLING_FIELD_SPECS[fieldKey as keyof typeof SAMPLING_FIELD_SPECS]
        : null;
    const equation = equationTexts[entry.equationKey] ?? "";
    const help =
      messages.sampling.help[fieldKey as keyof typeof messages.sampling.help] ?? "";

    const roleMeta = entry.roleGroupId
      ? messages.sampling.roleGroups[
          entry.roleGroupId as keyof typeof messages.sampling.roleGroups
        ]
      : null;
    const impactMeta = entry.impactGroupId
      ? messages.sampling.impactGroups[
          entry.impactGroupId as keyof typeof messages.sampling.impactGroups
        ]
      : null;

    return (
      <article className="sampling-course__detail" key={fieldKey}>
        <h3 className="sampling-course__detail-title">{knobLabel}</h3>
        <p className="sampling-course__api-key">
          <code>{entry.apiKey}</code>
          {spec ? (
            <span className="sampling-course__range">
              {" "}
              · {course.rangeLabel}: [{spec.min}, {spec.max}]
              {spec.integer ? ` · ${course.integer}` : ""}
            </span>
          ) : null}
        </p>
        {help ? <p className="sampling-course__help">{help}</p> : null}
        <div className="sampling-course__symbols">
          <span className="sampling-course__meta-label">{course.symbolsLabel}</span>
          {entry.symbols.map((sym) => (
            <IonChip key={sym} outline className="sampling-course__sym-chip">
              {sym}
            </IonChip>
          ))}
        </div>
        <pre className="sampling-course__equation" aria-label={course.equationLabel}>
          {equation}
        </pre>
        <div className="sampling-course__meta-row">
          {roleMeta ? (
            <span>
              <strong>{course.roleGroupLabel}</strong> {roleMeta.title}
            </span>
          ) : null}
          {impactMeta ? (
            <span>
              <strong>{course.impactGroupLabel}</strong> {impactMeta.title}
            </span>
          ) : null}
        </div>
        {entry.relatedFields && entry.relatedFields.length > 0 ? (
          <p className="sampling-course__related">
            <strong>{course.relatedKnobsLabel}</strong>{" "}
            {entry.relatedFields
              .map(
                (f) =>
                  messages.sampling.fields[f as keyof typeof messages.sampling.fields],
              )
              .join(", ")}
          </p>
        ) : null}
        <ul className="sampling-course__refs">
          {entry.referenceKeys.map((refKey) => {
            const ref = referenceTexts[refKey];
            if (!ref) {
              return null;
            }
            const href = ref.url?.trim();
            const isExternal = href?.startsWith("http") ?? false;
            return (
              <li key={refKey}>
                {isExternal ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    {ref.title}
                  </a>
                ) : (
                  <span>{ref.title}</span>
                )}
              </li>
            );
          })}
        </ul>
      </article>
    );
  };

  return (
    <section className="sampling-course" aria-labelledby="sampling-course-title">
      <header className="sampling-course__hero">
        <p className="sampling-course__eyebrow">{course.eyebrow}</p>
        <h2 id="sampling-course-title" className="sampling-course__title">
          {course.title}
        </h2>
        <p className="sampling-course__intro">{course.intro}</p>
        <div className="sampling-course__doc-pill">
          <IonNote className="sampling-course__doc-link">
            <span className="sampling-course__doc-hint">{course.docHint}</span>{" "}
            <code className="sampling-course__doc-path">docs/cours-echantillonnage.md</code>
          </IonNote>
        </div>
      </header>

      <SamplingCourseWorkedExample />

      <div className="sampling-course__toolbar" aria-label={course.viewsLabel}>
        <span className="sampling-course__toolbar-label">{course.viewsLabel}</span>
        <IonSegment
          value={viewMode}
          onIonChange={(e) => setViewMode((e.detail.value as CourseViewMode) ?? "pipeline")}
          className="sampling-course__segment"
        >
          <IonSegmentButton value="pipeline">
            <IonLabel>{course.views.pipeline}</IonLabel>
          </IonSegmentButton>
          <IonSegmentButton value="knobs">
            <IonLabel>{course.views.knobs}</IonLabel>
          </IonSegmentButton>
        </IonSegment>
      </div>

      {viewMode === "pipeline" ? (
        <ol className="sampling-course__pipeline">
          {PIPELINE_STEPS.map((step) => {
            const entries = entriesByStep.get(step.id) ?? [];
            const stepLabel = pipelineLabels[step.id];
            return (
              <li key={step.id} className="sampling-course__pipeline-step">
                <div className="sampling-course__pipeline-head">
                  <span className="sampling-course__pipeline-index">{step.order}</span>
                  <span className="sampling-course__pipeline-name">{stepLabel}</span>
                </div>
                {step.id === "logits" ? (
                  <pre className="sampling-course__equation sampling-course__equation--inline">
                    {equationTexts.logits_raw}
                  </pre>
                ) : null}
                {step.id === "sample" ? (
                  <pre className="sampling-course__equation sampling-course__equation--inline">
                    {equationTexts.sample}
                  </pre>
                ) : null}
                {entries.length > 0 ? (
                  <div className="sampling-course__pipeline-knobs">
                    {entries.map((entry) => {
                      const label =
                        messages.sampling.fields[
                          entry.fieldKey as keyof typeof messages.sampling.fields
                        ];
                      const isActive = activeField === entry.fieldKey;
                      return (
                        <button
                          key={entry.fieldKey}
                          type="button"
                          className={
                            isActive
                              ? "sampling-course__knob-btn sampling-course__knob-btn--active"
                              : "sampling-course__knob-btn"
                          }
                          onClick={() => selectField(entry.fieldKey)}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
                {activeField && activeFieldStepId === step.id ? (
                  <div
                    ref={pipelineDetailRef}
                    className="sampling-course__detail-wrap sampling-course__detail-wrap--in-step"
                  >
                    {renderFieldDetail(activeField)}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="sampling-course__knob-list" role="list">
          {COURSE_FIELD_ORDER.map((fieldKey) => {
            const label =
              messages.sampling.fields[fieldKey as keyof typeof messages.sampling.fields];
            const isActive = activeField === fieldKey;
            return (
              <div key={fieldKey} className="sampling-course__knob-row">
                <IonItem
                  button
                  detail
                  lines="none"
                  className={isActive ? "sampling-course__knob-item--active" : undefined}
                  onClick={() => selectField(fieldKey)}
                >
                  <IonLabel>
                    <h3 className="sampling-course__knob-title">{label}</h3>
                    <p className="sampling-course__knob-meta">
                      <code>{fieldKey}</code>
                    </p>
                  </IonLabel>
                </IonItem>
                {isActive ? (
                  <div
                    ref={knobListDetailRef}
                    className="sampling-course__detail-wrap sampling-course__detail-wrap--after-knob"
                  >
                    {renderFieldDetail(fieldKey)}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {!activeField ? (
        <IonNote className="sampling-course__pick-hint sampling-course__pick-hint--callout">
          {course.pickKnobHint}
        </IonNote>
      ) : null}
    </section>
  );
};

export default SamplingCoursePanel;
