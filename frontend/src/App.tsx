import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  IonApp,
  IonRouterOutlet,
  setupIonicReact,
} from "@ionic/react";
import { IonReactRouter } from "@ionic/react-router";
import { Redirect, Route } from "react-router-dom";

import HomePage from "./pages/HomePage";

import "@ionic/react/css/core.css";
import "@ionic/react/css/normalize.css";
import "@ionic/react/css/structure.css";
import "@ionic/react/css/typography.css";
import "@ionic/react/css/padding.css";
import "@ionic/react/css/float-elements.css";
import "@ionic/react/css/text-alignment.css";
import "@ionic/react/css/text-transformation.css";
import "@ionic/react/css/flex-utils.css";
import "@ionic/react/css/display.css";
import "@ionic/react/css/palettes/dark.class.css";

import "./theme/variables.css";
import "./theme/app.css";
import {
  applyResolvedTheme,
  getInitialThemeMode,
  persistThemeMode,
} from "./theme/theme";
import { I18nProvider } from "./i18n/I18nProvider";

setupIonicReact();

const queryClient = new QueryClient();

const App = () => {
  const [themeMode, setThemeMode] = useState(() => getInitialThemeMode());

  useEffect(() => {
    persistThemeMode(themeMode);
  }, [themeMode]);

  useEffect(() => {
    applyResolvedTheme(themeMode);
  }, [themeMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <IonApp>
          <IonReactRouter>
            <IonRouterOutlet>
              <Route exact path="/home">
                <HomePage
                  themeMode={themeMode}
                  onThemeChange={setThemeMode}
                />
              </Route>
              <Route exact path="/">
                <Redirect to="/home" />
              </Route>
            </IonRouterOutlet>
          </IonReactRouter>
        </IonApp>
      </I18nProvider>
    </QueryClientProvider>
  );
};

export default App;
