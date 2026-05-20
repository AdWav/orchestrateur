import { useI18n } from "../i18n/I18nProvider";
import {
  APP_TAB_LOCAL_ORCHESTRATOR,
  APP_TAB_SAMPLING,
  APP_TAB_SAMPLING_COURSE,
  APP_TAB_TRACE_JOURNEY,
  APP_TAB_BUILDER_CATALOG,
  type AppTabId,
} from "../navigation/appTabs";

import "./AppNavBar.css";

type AppNavBarProps = {
  activeTab: AppTabId;
  onTabChange: (tab: AppTabId) => void;
  serviceActive?: Partial<Record<AppTabId, boolean>>;
};

const AppNavBar = ({
  activeTab,
  onTabChange,
  serviceActive = {},
}: AppNavBarProps) => {
  const { messages } = useI18n();

  const tabs: { id: AppTabId; label: string }[] = [
    {
      id: APP_TAB_LOCAL_ORCHESTRATOR,
      label: messages.nav.tabs.localOrchestrator,
    },
    {
      id: APP_TAB_SAMPLING,
      label: messages.nav.tabs.sampling,
    },
    {
      id: APP_TAB_SAMPLING_COURSE,
      label: messages.nav.tabs.samplingCourse,
    },
    {
      id: APP_TAB_TRACE_JOURNEY,
      label: messages.nav.tabs.traceJourney,
    },
    {
      id: APP_TAB_BUILDER_CATALOG,
      label: messages.nav.tabs.builderCatalog,
    },
  ];

  return (
    <nav className="app-nav-bar" aria-label={messages.nav.ariaLabel}>
      <div className="app-nav-bar__list" role="tablist">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          const isUp = serviceActive[tab.id];

          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={
                isActive
                  ? "app-nav-bar__tab app-nav-bar__tab--active"
                  : "app-nav-bar__tab"
              }
              onClick={() => onTabChange(tab.id)}
            >
              <span
                className={
                  isUp === undefined
                    ? "app-nav-bar__dot app-nav-bar__dot--neutral"
                    : isUp
                      ? "app-nav-bar__dot app-nav-bar__dot--up"
                      : "app-nav-bar__dot app-nav-bar__dot--down"
                }
                aria-hidden="true"
              />
              <span className="app-nav-bar__label">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

export default AppNavBar;
