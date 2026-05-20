import { IonNote } from "@ionic/react";

import { useI18n } from "../i18n/I18nProvider";

import "./SamplingCoursePanel.css";

/**
 * Bloc pedagogique : parcours chiffre sur un vocabulaire jouet (voir i18n course.workedExample).
 */
const SamplingCourseWorkedExample = () => {
  const { messages } = useI18n();
  const wx = messages.course.workedExample;

  return (
    <section
      className="sampling-course__worked-example"
      aria-labelledby="sampling-course-worked-example-title"
    >
      <h3 id="sampling-course-worked-example-title" className="sampling-course__worked-example-title">
        {wx.title}
      </h3>
      <p className="sampling-course__worked-example-disclaimer">{wx.disclaimer}</p>
      <ol className="sampling-course__worked-example-steps">
        {wx.steps.map((step, index) => (
          <li key={index} className="sampling-course__worked-example-step">
            <strong className="sampling-course__worked-example-step-title">{step.title}</strong>
            <pre className="sampling-course__worked-example-pre" tabIndex={0}>
              {step.body}
            </pre>
          </li>
        ))}
      </ol>
      <IonNote className="sampling-course__worked-example-closing">{wx.closingNote}</IonNote>
    </section>
  );
};

export default SamplingCourseWorkedExample;
