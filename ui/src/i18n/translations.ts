export type Language = "fr" | "en";

const LANGUAGE_STORAGE_KEY = "orchestrateur:language";

function isLanguage(value: string | null): value is Language {
  return value === "fr" || value === "en";
}

function detectBrowserLanguage(): Language {
  if (typeof navigator === "undefined") {
    return "fr";
  }

  return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
}

const translations = {
  fr: {
    app: {
      title: "Orchestrateur Local",
    },
    header: {
      apiDocs: "API",
      languageSwitcher: "Changer la langue",
      switchToLight: "Basculer vers le mode clair",
      switchToDark: "Basculer vers le mode sombre",
      ollamaListAria: "Lister les modeles installes avec Ollama",
      ollamaListButton: "Modèles",
      ollamaListTitle: "Modeles disponibles sur la machine",
      ollamaListSubtitle: "(equivalent CLI : ollama list)",
      ollamaListEmpty: "Aucun modele. Utiliser `ollama pull <nom>` puis reessayer.",
      ollamaListErrorTitle: "Indisponible",
      ollamaRoutingInactive:
        "`MODEL_BACKEND=ollama` est requis pour appliquer le routage depuis l'UI.",
      ollamaRuntimeHeading: "Routage pour les prochains workflows",
      ollamaRuntimeDefaultLabel: "Modele par defaut",
      ollamaRuntimeRunnerHelp: "Modele utilise pour l'etape",
      ollamaSaveRuntime: "Enregistrer la configuration",
      ollamaRuntimeSaved: "Configuration Ollama enregistree.",
      ollamaRuntimeSettingsFetchError:
        "Les reglages runtime n'ont pas pu etre lus depuis l'API (GET /v1/runtime/ollama/settings).",
      ollamaPersistPathPrefix: "Fichier de persistance :",
      ollamaWarm: "Precharger",
      ollamaUnload: "Decharger",
      ollamaWarmOk: (name: string) => `Prechargement termine pour ${name}.`,
      ollamaUnloadOk: (name: string) => `Dechargement demande pour ${name}.`,
      ollamaModelsInstalledTitle: "Tags installes",
    },
    common: {
      none: "aucun",
      notAvailable: "n/a",
      unavailable: "indisponible",
      unreachable: "injoignable",
      unknown: "inconnu",
      noReasonProvided: "Aucune raison fournie",
      createInProgress: "Creation...",
      execute: "Executer",
      close: "Fermer",
      remove: "Retirer",
      addStep: "Ajouter une etape",
    },
    status: {
      passed: "reussi",
      blocked: "bloque",
      approved: "approuve",
      inFlow: "en cours",
    },
    runtime: {
      roleLabels: {
        plan: "Planification",
        research: "Recherche",
        execute: "Execution",
        verify: "Verification",
        Planner: "Planification",
        Researcher: "Recherche",
        Executor: "Execution",
        Verifier: "Verification",
      },
    },
    errors: {
      invalidContextLine: (line: string) =>
        `La ligne "${line}" doit respecter le format cle=valeur.`,
      emptyContextKey: "Chaque ligne de contexte doit avoir une cle non vide.",
      createAgentFallback: "Impossible de creer l'agent.",
      createWorkflowFallback: "Impossible de creer le workflow.",
      httpFallback: (status: number, path: string) => `HTTP ${status} sur ${path}`,
    },
    memory: {
      updated: (key: string) => `Memoire mise a jour : ${key}`,
    },
    hero: {
      internalDescription:
        "L'orchestrateur expose l'API sur :8000 et enchaine les etapes locales plan → research → execute → verify dans le meme processus.",
      externalDescription:
        "L'orchestrateur sonde un mesh HTTP d'executants dedies et un runtime modele Ollama partage.",
    },
    apiHealth: {
      subtitle: "Orchestrateur central",
      title: "Sante de l'API",
      loading: "Chargement des informations de demarrage...",
      service: "Service",
      execution: "Execution",
      state: "Etat",
      team: "Equipe",
      useCases: "Cas d'usage",
      internalRole: "role interne",
      internalRoles: "roles internes",
      httpMesh: "mesh HTTP",
      rolesCount: (count: number) => `${count} executants declares`,
      useCasesCount: (count: number) => `${count} exposes`,
    },
    catalog: {
      subtitle: "Catalogue",
    },
    mesh: {
      serviceLabels: {
        po: "Orchestrateur",
        plan: "Planification",
        research: "Recherche",
        execute: "Execution",
        verify: "Verification",
        ollama: "Ollama",
      },
    },
    agentForm: {
      title: "Creer une fiche agent",
      id: "Identifiant",
      displayName: "Nom affiche",
      businessRole: "Role metier",
      mission: "Mission",
      capabilities: "Capacites (une par ligne)",
      inputs: "Entrees attendues (une par ligne)",
      outputs: "Sorties produites (une par ligne)",
      guardrails: "Guardrails (une par ligne)",
      create: "Creer l'agent",
      persistedNote: "La fiche est persistee dans le catalogue du repo.",
      actionDescription:
        "Ouvre une fiche modale pour creer un agent sans allonger la page principale.",
      openAction: "Ouvrir la fiche agent",
      idPlaceholder: "directeur-mission",
      displayNamePlaceholder: "Directeur de mission",
      businessRolePlaceholder: "Direction de mission",
      missionPlaceholder: "Explique le mandat de cet agent.",
    },
    agentList: {
      title: "Agents definis",
      empty: "Aucune fiche agent pour l'instant.",
    },
    workflowForm: {
      title: "Creer un workflow",
      id: "Identifiant",
      name: "Nom du workflow",
      goal: "Objectif",
      context: "Contexte (cle=valeur par ligne)",
      constraints: "Contraintes (une par ligne)",
      successCriteria: "Criteres de succes (une par ligne)",
      step: (index: number) => `Etape ${index}`,
      stepId: "Identifiant d'etape",
      stepName: "Nom de l'etape",
      linkedAgent: "Agent associe",
      selectAgent: "Selectionne un agent",
      objective: "Objectif",
      expectedDeliverables: "Livrables attendus (une par ligne)",
      stepSuccessCriteria: "Criteres de succes de l'etape (une par ligne)",
      dependsOn: "Depend de (ids, une par ligne)",
      create: "Creer le workflow",
      actionDescription:
        "Le builder de workflow s'ouvre en modale, avec ses etapes et dependances.",
      openAction: "Ouvrir le builder workflow",
      actionNote: "Le workflow est enregistre comme preset dans le catalogue.",
      idPlaceholder: "audit-pre-mission",
      namePlaceholder: "Audit pre-mission",
      goalPlaceholder: "Explique le resultat final attendu.",
      contextPlaceholder: "company=Atlas Conseil\nclient=Maison Orion",
    },
    workflowList: {
      title: "Workflows definis",
      empty: "Aucun workflow defini pour l'instant.",
      steps: "Etapes",
      agent: "Agent",
    },
    repoAudit: {
      subtitle: "Trace observable",
      title: "Lancer un repo audit depuis `:8000`",
      objective: "Objectif",
      repoPath: "Chemin du repo",
      analysisAxes: "Axes d'analyse",
      run: "Lancer le repo audit",
      running: "Execution du workflow en cours...",
      note:
        "La vue affiche une trace structuree, pas la pensee brute cachee.",
      defaultObjective:
        "Auditer ce depot pour exposer les signaux d'architecture, de tests, de documentation et de securite.",
      objectivePlaceholder: "Decris le type d'audit a demander a l'orchestrateur.",
      axisLabels: {
        architecture: "Architecture",
        tests: "Tests",
        docs: "Documentation",
        security: "Securite",
        dependencies: "Dependances",
      },
    },
    report: {
      summarySubtitle: "Resume d'execution",
      summaryTitle: "Etat global du workflow",
      verification: "Verification",
      filesScanned: "Fichiers analyses",
      findings: "Constats",
      evidenceCount: "Nombre de preuves",
      detectedLanguages: "Langages detectes",
      timelineSubtitle: "Chronologie du pipeline",
      timelineTitle: "Reflexion observable par etape de pipeline",
      agent: "Etape",
      journalSubtitle: "Journal du workflow",
      journalTitle: "Evenements traces par l'orchestrateur",
      jsonToggleCaption: "json",
      viewModeToggleAria:
        "Vue classique lorsque desactive ; affiche la sortie JSON lorsque active.",
    },
    artifacts: {
      searchPlan: "Plan de recherche",
      acceptanceCriteria: "Criteres d'acceptation",
      importantFiles: "Fichiers importants",
      coverageMap: "Carte de couverture",
      evidenceExcerpts: "Extraits de preuves",
      repositorySummary: "Resume du depot",
      findings: "Constats",
      recommendedActions: "Actions recommandees",
      unknowns: "Inconnues",
      validationStatus: "Statut de validation",
      approved: "Approuve",
      evidenceCount: "Nombre de preuves",
      coveredAxes: "Axes couverts",
      policyCompliance: "Conformite aux politiques",
      missingRequirements: "Exigences manquantes",
      unsupportedClaims: "Affirmations non prises en charge",
      capabilities: "Capacites",
      inputs: "Entrees",
      outputs: "Sorties",
      guardrails: "Guardrails",
      constraints: "Contraintes",
      successCriteria: "Criteres de succes",
      expectedDeliverables: "Livrables attendus",
      stepSuccessCriteria: "Criteres de succes de l'etape",
      dependsOn: "Depend de",
      nextActions: "Actions suivantes",
    },
    team: {
      subtitleLive: (roleCount: number) =>
        `Equipe actuelle — ${roleCount} role${roleCount > 1 ? "s" : ""}`,
      fallbackName: "Equipe de specification",
      fallbackPurpose:
        "Le frontend affiche les quatre etapes standard (plan · research · execute · verify) et les contrats de handoff fournis par l'API.",
      capabilities: "Capacites",
      handoffsTitle: "Contrats de handoff",
      guardrailsTitle: "Guardrails",
      loadingRoles: "Chargement de l'equipe...",
    },
    useCases: {
      subtitleLive: (count: number) => `Workflows exposes — ${count} cas`,
      title: "Cas d'usage disponibles",
      expectedOutcome: "Resultat attendu",
      loading: "Chargement des cas...",
      empty: "Aucun cas expose pour cette equipe.",
    },
  },
  en: {
    app: {
      title: "Local Orchestrator",
    },
    header: {
      apiDocs: "API",
      languageSwitcher: "Change language",
      switchToLight: "Switch to light mode",
      switchToDark: "Switch to dark mode",
      ollamaListAria: "List installed models from Ollama",
      ollamaListButton: "Models",
      ollamaListTitle: "Models available on this machine",
      ollamaListSubtitle: "(CLI equivalent: ollama list)",
      ollamaListEmpty: "No models. Run `ollama pull <name>` and try again.",
      ollamaListErrorTitle: "Unavailable",
      ollamaRoutingInactive: "`MODEL_BACKEND=ollama` is required to apply routing from the UI.",
      ollamaRuntimeHeading: "Routing for upcoming workflows",
      ollamaRuntimeDefaultLabel: "Default model",
      ollamaRuntimeRunnerHelp: "Model for step",
      ollamaSaveRuntime: "Save configuration",
      ollamaRuntimeSaved: "Saved Ollama routing settings.",
      ollamaRuntimeSettingsFetchError:
        "Runtime settings could not be read from the API (GET /v1/runtime/ollama/settings).",
      ollamaPersistPathPrefix: "Persistence file:",
      ollamaWarm: "Preload",
      ollamaUnload: "Unload",
      ollamaWarmOk: (name: string) => `Preload complete for ${name}.`,
      ollamaUnloadOk: (name: string) => `Unload triggered for ${name}.`,
      ollamaModelsInstalledTitle: "Installed tags",
    },
    common: {
      none: "none",
      notAvailable: "n/a",
      unavailable: "unavailable",
      unreachable: "unreachable",
      unknown: "unknown",
      noReasonProvided: "No reason provided",
      createInProgress: "Creating...",
      execute: "Run",
      close: "Close",
      remove: "Remove",
      addStep: "Add step",
    },
    status: {
      passed: "passed",
      blocked: "blocked",
      approved: "approved",
      inFlow: "in flow",
    },
    runtime: {
      roleLabels: {
        plan: "Planner",
        research: "Researcher",
        execute: "Executor",
        verify: "Verifier",
        Planner: "Planner",
        Researcher: "Researcher",
        Executor: "Executor",
        Verifier: "Verifier",
      },
    },
    errors: {
      invalidContextLine: (line: string) =>
        `The line "${line}" must follow the key=value format.`,
      emptyContextKey: "Each context line must have a non-empty key.",
      createAgentFallback: "Unable to create the agent.",
      createWorkflowFallback: "Unable to create the workflow.",
      httpFallback: (status: number, path: string) => `HTTP ${status} on ${path}`,
    },
    memory: {
      updated: (key: string) => `Memory updated: ${key}`,
    },
    hero: {
      internalDescription:
        "The orchestrator exposes the API on :8000 and runs the local stages plan → research → execute → verify in the same process.",
      externalDescription:
        "The orchestrator probes an HTTP mesh of dedicated runners and a shared Ollama model runtime.",
    },
    apiHealth: {
      subtitle: "Central orchestrator",
      title: "API health",
      loading: "Loading bootstrap information...",
      service: "Service",
      execution: "Execution",
      state: "State",
      team: "Team",
      useCases: "Use cases",
      internalRole: "internal role",
      internalRoles: "internal roles",
      httpMesh: "HTTP mesh",
      rolesCount: (count: number) => `${count} runners declared`,
      useCasesCount: (count: number) => `${count} exposed`,
    },
    catalog: {
      subtitle: "Catalog",
    },
    mesh: {
      serviceLabels: {
        po: "Orchestrator",
        plan: "Planning",
        research: "Research",
        execute: "Execution",
        verify: "Verification",
        ollama: "Ollama",
      },
    },
    agentForm: {
      title: "Create an agent definition",
      id: "Identifier",
      displayName: "Display name",
      businessRole: "Business role",
      mission: "Mission",
      capabilities: "Capabilities (one per line)",
      inputs: "Expected inputs (one per line)",
      outputs: "Produced outputs (one per line)",
      guardrails: "Guardrails (one per line)",
      create: "Create agent",
      persistedNote: "The definition is persisted in the repository catalog.",
      actionDescription:
        "Open a modal form to create an agent without making the main page longer.",
      openAction: "Open agent form",
      idPlaceholder: "engagement-director",
      displayNamePlaceholder: "Engagement director",
      businessRolePlaceholder: "Mission leadership",
      missionPlaceholder: "Explain this agent's mandate.",
    },
    agentList: {
      title: "Defined agents",
      empty: "No agent definitions yet.",
    },
    workflowForm: {
      title: "Create a workflow",
      id: "Identifier",
      name: "Workflow name",
      goal: "Goal",
      context: "Context (key=value per line)",
      constraints: "Constraints (one per line)",
      successCriteria: "Success criteria (one per line)",
      step: (index: number) => `Step ${index}`,
      stepId: "Step id",
      stepName: "Step name",
      linkedAgent: "Assigned agent",
      selectAgent: "Select an agent",
      objective: "Objective",
      expectedDeliverables: "Expected deliverables (one per line)",
      stepSuccessCriteria: "Step success criteria (one per line)",
      dependsOn: "Depends on (ids, one per line)",
      create: "Create workflow",
      actionDescription:
        "The workflow builder opens in a modal with its steps and dependencies.",
      openAction: "Open workflow builder",
      actionNote: "The workflow is saved as a preset in the catalog.",
      idPlaceholder: "pre-engagement-audit",
      namePlaceholder: "Pre-engagement audit",
      goalPlaceholder: "Explain the expected final outcome.",
      contextPlaceholder: "company=Atlas Consulting\nclient=Orion House",
    },
    workflowList: {
      title: "Defined workflows",
      empty: "No workflows defined yet.",
      steps: "Steps",
      agent: "Agent",
    },
    repoAudit: {
      subtitle: "Observable trace",
      title: "Run a repo audit from `:8000`",
      objective: "Objective",
      repoPath: "Repo path",
      analysisAxes: "Analysis axes",
      run: "Run repo audit",
      running: "Running workflow...",
      note: "This view shows a structured trace, not the hidden raw reasoning.",
      defaultObjective:
        "Audit this repository to surface architecture, testing, documentation, and security signals.",
      objectivePlaceholder: "Describe the audit you want the orchestrator to run.",
      axisLabels: {
        architecture: "Architecture",
        tests: "Tests",
        docs: "Documentation",
        security: "Security",
        dependencies: "Dependencies",
      },
    },
    report: {
      summarySubtitle: "Run summary",
      summaryTitle: "Overall workflow status",
      verification: "Verification",
      filesScanned: "Files scanned",
      findings: "Findings",
      evidenceCount: "Evidence count",
      detectedLanguages: "Detected languages",
      timelineSubtitle: "Pipeline timeline",
      timelineTitle: "Observable reasoning per pipeline stage",
      agent: "Stage",
      journalSubtitle: "Workflow journal",
      journalTitle: "Events traced by the orchestrator",
      jsonToggleCaption: "json",
      viewModeToggleAria:
        "Structured view when off; shows raw JSON output when on.",
    },
    artifacts: {
      searchPlan: "Search plan",
      acceptanceCriteria: "Acceptance criteria",
      importantFiles: "Important files",
      coverageMap: "Coverage map",
      evidenceExcerpts: "Evidence excerpts",
      repositorySummary: "Repository summary",
      findings: "Findings",
      recommendedActions: "Recommended actions",
      unknowns: "Unknowns",
      validationStatus: "Validation status",
      approved: "Approved",
      evidenceCount: "Evidence count",
      coveredAxes: "Covered axes",
      policyCompliance: "Policy compliance",
      missingRequirements: "Missing requirements",
      unsupportedClaims: "Unsupported claims",
      capabilities: "Capabilities",
      inputs: "Inputs",
      outputs: "Outputs",
      guardrails: "Guardrails",
      constraints: "Constraints",
      successCriteria: "Success criteria",
      expectedDeliverables: "Expected deliverables",
      stepSuccessCriteria: "Step success criteria",
      dependsOn: "Depends on",
      nextActions: "Next actions",
    },
    team: {
      subtitleLive: (roleCount: number) =>
        roleCount <= 1
          ? `Current team — ${roleCount} runner`
          : `Current team — ${roleCount} runners`,
      fallbackName: "Specification Team",
      fallbackPurpose:
        "The frontend displays the four standard stages (plan · research · execute · verify) and the handoff contracts exposed by the API.",
      capabilities: "Capabilities",
      handoffsTitle: "Handoff contracts",
      guardrailsTitle: "Guardrails",
      loadingRoles: "Loading team...",
    },
    useCases: {
      subtitleLive: (count: number) =>
        count <= 1
          ? `Exposed workflows — ${count} use case`
          : `Exposed workflows — ${count} use cases`,
      title: "Available use cases",
      expectedOutcome: "Expected outcome",
      loading: "Loading use cases...",
      empty: "No use cases exposed for this team.",
    },
  },
} as const;

export type I18nCopy = (typeof translations)[Language];

let activeLanguage: Language = "fr";

export function getInitialLanguage(): Language {
  if (typeof window === "undefined") {
    return "fr";
  }

  const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return isLanguage(storedLanguage) ? storedLanguage : detectBrowserLanguage();
}

export function getI18nCopy(language: Language = activeLanguage): I18nCopy {
  return translations[language];
}

export function getActiveI18nCopy(): I18nCopy {
  return getI18nCopy(activeLanguage);
}

export function applyLanguage(language: Language) {
  activeLanguage = language;

  if (typeof window !== "undefined") {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }

  if (typeof document !== "undefined") {
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    document.title = translations[language].app.title;
  }
}

export function translateRuntimeRoleLabel(role: string): string {
  const copy = getActiveI18nCopy();
  return copy.runtime.roleLabels[role as keyof typeof copy.runtime.roleLabels] ?? role;
}

export function translateMeshServiceLabel(key: string): string {
  const copy = getActiveI18nCopy();
  return copy.mesh.serviceLabels[key as keyof typeof copy.mesh.serviceLabels] ?? key;
}

export function translateApprovalState(approved: boolean | null): string {
  const copy = getActiveI18nCopy();

  if (approved === true) {
    return copy.status.approved;
  }

  if (approved === false) {
    return copy.status.blocked;
  }

  return copy.status.inFlow;
}

export function translatePassState(passed: boolean): string {
  const copy = getActiveI18nCopy();
  return passed ? copy.status.passed : copy.status.blocked;
}

export function translateAnalysisAxis(axis: string): string {
  const copy = getActiveI18nCopy();
  return copy.repoAudit.axisLabels[axis as keyof typeof copy.repoAudit.axisLabels] ?? axis;
}
