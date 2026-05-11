# Operations et prochaines etapes

## Objectif de la base actuelle

La base actuelle doit prouver trois choses:

- qu'un orchestrateur central peut piloter plusieurs agents specialises
- que les handoffs sont explicites et verifiables
- que la topologie Docker est assez propre pour evoluer

## Verification rapide

Quand la stack tourne, verifier:

1. `GET /health`
2. `GET http://localhost:11434/api/tags`
3. `GET /v1/team`
4. `GET /v1/use-cases`
5. `POST /v1/runtime/recommendation`
6. `POST /v1/workflows/specification`
7. `POST /v1/workflows/repo-audit`

## Profil de validation ultra-legere

Le compose courant est calibre pour un laptop de `16 Go` de RAM avec le modele:

- `qwen2.5:0.5b`

Le but est de valider le comportement global, pas la qualite finale.

## Exemple de payload pour le workflow

```json
{
  "objective": "Produire un protocole de benchmark pour trois modeles locaux",
  "context": {
    "machine": "128 Go RAM",
    "scope": "local only"
  },
  "constraints": [
    "Tout doit rester en local",
    "Chaque handoff doit etre explicite"
  ],
  "success_criteria": [
    "Le plan doit etre actionnable",
    "Le verdict final doit mentionner les manques eventuels"
  ],
  "use_case_id": "local-model-benchmark"
}
```

## Reponse attendue

Le workflow doit renvoyer:

- la requete normalisee
- les sorties des quatre roles
- la memoire du workflow
- un verdict `verification_passed`

## Exemple de payload pour le repo audit

```json
{
  "objective": "Auditer ce depot en lecture seule",
  "repo_path": ".",
  "analysis_axes": [
    "architecture",
    "docs",
    "dependencies"
  ]
}
```

La reponse attendue inclut alors:

- la requete normalisee `RepoAuditRequest`
- un `inventory` du depot audite
- des `findings` relies a des preuves
- un `validation_report`
- la memoire d'execution et les evenements de capacites

## Extensions naturelles

Les prochaines etapes coherentes sont:

1. changer `OLLAMA_DEFAULT_MODEL` pour monter en qualite
2. ajouter une trace persistante des handoffs
3. isoler certains agents dans des images plus specialisees
4. connecter une UI `TypeScript`
5. introduire un stockage memoire partage externe
6. permettre l'audit d'un repo monte explicitement via Docker

## Regle de croissance

Ne pas ajouter une nouvelle equipe d'agents tant que:

- les contrats de handoff ne sont pas stables
- les checks du `Verifier` ne sont pas juges suffisants
- le runtime modele n'est pas valide sur la machine cible
