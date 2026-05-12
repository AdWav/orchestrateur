# Demos entreprise

Cette page presente l'orchestrateur comme une petite cellule projet d'entreprise.
L'idee n'est plus "quatre agents abstraits", mais une equipe missionnee pour traiter un dossier concret.

Le point d'entree installe est `orchestrateur`.

## Scenarios disponibles

La demo peut maintenant etre jouee avec deux mises en scene:

- `delivery-mission`: un cabinet ou une direction delivery prepare un pre-audit technique client
- `tech-due-diligence`: un comite d'investissement evalue une cible avant acquisition ou integration

Le moteur reste le meme, mais le sens metier change.

## Scenario 1

Imagine une entreprise comme `Atlas Conseil`.
Elle doit analyser rapidement le depot d'un nouveau client, clarifier les risques, puis dire au management si la mission est faisable.

Dans cette lecture:

- `Planner` devient le directeur de mission
- `Researcher` devient l'analyste senior
- `Executor` devient le responsable delivery
- `Verifier` devient le controle qualite

La demo simule exactement ce type de fonctionnement.

## Scenario 2

Autre exemple plus marquant: un comite d'investissement technique.
Une organisation comme `Northbridge Capital` veut evaluer `BlueVector` avant acquisition ou integration.

Dans cette lecture:

- `Planner` devient le partner investissement tech
- `Researcher` devient l'analyste due diligence
- `Executor` devient l'operating partner integration
- `Verifier` devient le risk officer

Le livrable attendu n'est plus un simple dossier de mission, mais une recommandation go/no-go appuyee par des red flags et un plan d'integration.

## Installation

```bash
pip install -e ".[dev]"
```

Par defaut, la CLI execute les workflows localement avec le backend `dry-run`.
Pour utiliser `Ollama`, il suffit de positionner `MODEL_BACKEND=ollama` et les variables associees.

## Demo complete en local

La commande suivante construit une histoire metier complete avec le scenario par defaut `delivery-mission`:

- une entreprise pilote la mission
- un client est audite
- l'equipe produit un brief de mission
- le depot est inspecte en lecture seule
- un verdict exploitable remonte au management

```bash
orchestrateur demo --repo-path .
```

Tu peux aussi personnaliser le scenario:

```bash
orchestrateur demo \
  --repo-path . \
  --company-name "Nova Conseil" \
  --client-name "Studio Helios"
```

Et voici l'exemple alternatif de mon choix:

```bash
orchestrateur demo \
  --repo-path . \
  --company-name "Northbridge Capital" \
  --client-name "BlueVector" \
  --scenario tech-due-diligence
```

La sortie JSON contient notamment:

- `business_story` pour le contexte entreprise
- `business_story.scenario` pour la mise en scene choisie
- `team` pour l'equipe technique sous-jacente
- `specification_request` pour le brief de mission
- `specification` pour le dossier produit par la cellule projet
- `repo_audit_request` pour le mandat d'analyse
- `repo_audit` pour le rapport final

## Lecture metier des roles

Pour `delivery-mission`:

- le directeur de mission cadre l'objectif, les contraintes et la definition du succes
- l'analyste senior collecte les signaux du depot et les zones d'incertitude
- le responsable delivery transforme cela en plan d'action operable
- le controle qualite decide si le dossier est defendable et assez trace

Pour `tech-due-diligence`:

- le partner investissement tech pose la these et les criteres de decision
- l'analyste due diligence identifie les red flags et les angles morts
- l'operating partner integration prepare la trajectoire d'integration ou de remediations
- le risk officer arbitre si la recommandation est suffisamment solide pour le comite

Autrement dit, l'orchestrateur peut ressembler soit a une mini equipe de cabinet, soit a une cellule d'investissement technique.

## Commandes CLI utiles

Afficher l'equipe:

```bash
orchestrateur team
```

Lancer seulement le brief de mission:

```bash
orchestrateur specification \
  --objective "Pour Nova Conseil, cadrer une mission de pre-audit technique pour Studio Helios" \
  --context company_name="Nova Conseil" \
  --context client_name="Studio Helios" \
  --context business_context="qualification avant engagement commercial" \
  --constraint "Le dossier doit etre lisible par la direction de mission" \
  --success-criterion "Les risques doivent etre explicites." \
  --success-criterion "Le plan doit etre actionnable." \
  --use-case-id operator-runbook
```

Lancer seulement l'audit du depot:

```bash
orchestrateur repo-audit \
  --objective "Pour Nova Conseil, auditer le depot de Studio Helios en lecture seule" \
  --repo-path . \
  --analysis-axis architecture \
  --analysis-axis docs \
  --analysis-axis tests \
  --analysis-axis security \
  --analysis-axis dependencies
```

## Utilisation via l'API

Demarrer l'API:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Puis rejouer le meme scenario en HTTP:

```bash
orchestrateur demo \
  --repo-path . \
  --company-name "Nova Conseil" \
  --client-name "Studio Helios" \
  --api-url http://127.0.0.1:8000
```

Ou avec le scenario `tech-due-diligence`:

```bash
orchestrateur demo \
  --repo-path . \
  --company-name "Northbridge Capital" \
  --client-name "BlueVector" \
  --scenario tech-due-diligence \
  --api-url http://127.0.0.1:8000
```

Tu peux aussi appeler directement les endpoints.

Equipe:

```bash
curl http://127.0.0.1:8000/team
```

Brief de mission:

```bash
curl -X POST http://127.0.0.1:8000/workflows/specification \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Pour Nova Conseil, cadrer une mission de pre-audit technique pour Studio Helios",
    "context": {
      "company_name": "Nova Conseil",
      "client_name": "Studio Helios",
      "business_context": "qualification avant engagement commercial"
    },
    "constraints": [
      "Le dossier doit etre lisible par la direction de mission"
    ],
    "success_criteria": [
      "Les risques doivent etre explicites.",
      "Le plan doit etre actionnable."
    ],
    "use_case_id": "operator-runbook"
  }'
```

Audit du depot:

```bash
curl -X POST http://127.0.0.1:8000/workflows/repo-audit \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Pour Nova Conseil, auditer le depot de Studio Helios en lecture seule",
    "repo_path": ".",
    "analysis_axes": ["architecture", "tests", "docs", "security", "dependencies"]
  }'
```

## Quand utiliser quoi

- `demo` si tu veux montrer le systeme comme une equipe projet complete
- `--scenario delivery-mission` si tu veux un angle cabinet, PMO ou delivery
- `--scenario tech-due-diligence` si tu veux un angle acquisition, risque et investissement
- `specification` si tu veux produire un brief de mission sans encore ouvrir le depot
- `repo-audit` si tu veux faire la due diligence technique du depot
- `--company-name` et `--client-name` si tu veux rendre la demo plus credibile en contexte entreprise
- `--api-url` si tu veux piloter une instance FastAPI deja demarree
