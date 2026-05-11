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
  IonItem,
  IonLabel,
  IonList,
  IonNote,
  IonPage,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from "@ionic/react";
import { useQuery } from "@tanstack/react-query";

import {
  apiBaseUrl,
  fetchHealth,
  fetchTeam,
  fetchUseCases,
} from "../lib/api";

import "./HomePage.css";

const HomePage = () => {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    staleTime: 30_000,
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

  const error =
    healthQuery.error ?? teamQuery.error ?? useCasesQuery.error ?? null;
  const isLoading =
    healthQuery.isLoading || teamQuery.isLoading || useCasesQuery.isLoading;

  return (
    <IonPage>
      <IonHeader translucent>
        <IonToolbar>
          <IonTitle>Orchestrateur Local</IonTitle>
          <IonButtons slot="end">
            <IonButton href={`${apiBaseUrl}/docs`} target="_blank">
              API
            </IonButton>
          </IonButtons>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <div className="home-shell">
          <section className="hero-card">
            <IonChip color="primary">Mobile-first</IonChip>
            <h1>Socle web-native pour piloter tes agents locaux.</h1>
            <p>
              Cette base Ionic React est deja branchee sur ton API FastAPI et
              prete pour une evolution vers Android et iOS via Capacitor.
            </p>
            <IonNote color="medium">API cible: {apiBaseUrl}</IonNote>
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
              ) : error ? (
                <div className="error-box">
                  {(error as Error).message}
                </div>
              ) : (
                <div className="status-grid">
                  <div>
                    <span className="eyebrow">Service</span>
                    <strong>{healthQuery.data?.service}</strong>
                  </div>
                  <div>
                    <span className="eyebrow">Etat</span>
                    <IonBadge color="success">
                      {healthQuery.data?.status}
                    </IonBadge>
                  </div>
                  <div>
                    <span className="eyebrow">Equipe</span>
                    <strong>{teamQuery.data?.roles.length ?? 0} roles</strong>
                  </div>
                  <div>
                    <span className="eyebrow">Use cases</span>
                    <strong>{useCasesQuery.data?.length ?? 0} exposes</strong>
                  </div>
                </div>
              )}
            </IonCardContent>
          </IonCard>

          <IonCard>
            <IonCardHeader>
              <IonCardSubtitle>Equipe actuelle</IonCardSubtitle>
              <IonCardTitle>{teamQuery.data?.name ?? "Specification Team"}</IonCardTitle>
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
