export const APP_TAB_LOCAL_ORCHESTRATOR = "local-orchestrator" as const;
export const APP_TAB_SAMPLING = "sampling" as const;

export type AppTabId =
  | typeof APP_TAB_LOCAL_ORCHESTRATOR
  | typeof APP_TAB_SAMPLING;

export const APP_TABS: AppTabId[] = [
  APP_TAB_LOCAL_ORCHESTRATOR,
  APP_TAB_SAMPLING,
];

export function isAppTabId(value: string): value is AppTabId {
  return (APP_TABS as string[]).includes(value);
}
