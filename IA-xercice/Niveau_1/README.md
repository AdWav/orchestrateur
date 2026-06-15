# Niveau 1 — Ajout puis utilisation d'un tool

## Objectif pedagogique

Ce niveau introduit une capacite cle : connecter l'agent a un **tool de lecture/exploration** pour qu'il puisse decrire un dossier reel au lieu de repondre de memoire.

Ici, l'objectif cible est le dossier `sandbox`.

---

## Prerequis

- Niveau 0 valide.
- Agent operationnel dans votre environnement local.

---

## Competences visees

- Ajouter un tool a un agent.
- Formuler une consigne qui force l'usage du tool avant reponse.
- Verifier qu'une reponse est fondee sur des elements observes dans le dossier.

---

## Livrables attendus

1. Configuration agent mise a jour avec un tool d'exploration de fichiers.
2. Prompt/mission ajuste pour imposer un parcours "lire puis repondre".
3. Trace de test montrant la progression :
   - avant tool,
   - apres ajout tool,
   - apres consigne "reponse complete".

---

## Contenu du dossier

- `enonce.md` : instructions apprenant.
- `corrige-formateur.md` : correction type et points de vigilance.
- `grille-evaluation.md` : notation sur 10 points.

---

## Critere de reussite

Le niveau est acquis si la reponse a :

`Que peux tu me dire du projet "/sandbox" ?`

contient au minimum le noyau attendu :

`Le projet sandbox est un livre d'or en python/react/SQLite.`

et s'appuie sur des elements verifies dans le dossier (pas uniquement une supposition).
