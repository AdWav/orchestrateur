export const APP_TAB_LOCAL_ORCHESTRATOR = "local-orchestrator" as const;
export const APP_TAB_SAMPLING = "sampling" as const;
export const APP_TAB_SAMPLING_COURSE = "sampling-course" as const;
export const APP_TAB_TRACE_JOURNEY = "trace-journey" as const;
export const APP_TAB_BUILDER_CATALOG = "builder-catalog" as const;

export type AppTabId =
  | typeof APP_TAB_LOCAL_ORCHESTRATOR
  | typeof APP_TAB_SAMPLING
  | typeof APP_TAB_SAMPLING_COURSE
  | typeof APP_TAB_TRACE_JOURNEY
  | typeof APP_TAB_BUILDER_CATALOG;

export const APP_TABS: AppTabId[] = [
  APP_TAB_LOCAL_ORCHESTRATOR,
  APP_TAB_SAMPLING,
  APP_TAB_SAMPLING_COURSE,
  APP_TAB_TRACE_JOURNEY,
  APP_TAB_BUILDER_CATALOG,
];

export function isAppTabId(value: string): value is AppTabId {
  return (APP_TABS as string[]).includes(value);
}
