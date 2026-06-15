# Niveau 2 — Enonce apprenant

## Contexte

Au niveau 1, vous avez appris a utiliser un tool pour explorer `/sandbox`.

Au niveau 2, vous devez rendre la reponse **audit-able** : chaque information importante doit etre accompagnee d'une source fichier.

---

## Objectif niveau 2

### Demande n2

`Que peux tu me dire du projet "/sandbox" ? Reponds avec les preuves.`

### Attendu

Une reponse qui contient :

1. Une synthese (fonction du projet + stack principale).
2. Une section "Preuves" avec chemins de fichiers.
3. Un signal explicite des zones incertaines (si besoin).

---

## Prerequis

- Niveau 1 reussi.

---

## Etape 1 — Baseline

Sans ajouter la contrainte de preuve, posez la demande n2.

Notez si la reponse contient :

| Critere | Oui/Non |
|---------|---------|
| Fonction du projet | |
| Technologies (backend/frontend/DB) | |
| Sources de preuve (fichiers) | |
| Distinction "observe" vs "suppose" | |

---

## Etape 2 — Renforcement de l'agent

Ajoutez une regle explicite dans mission/guardrails/prompt :

- "Pas de fait sans source fichier."
- "Chaque affirmation technique doit etre reliee a un chemin."
- "Si une information n'est pas trouvee, ecrire 'non observe dans les fichiers consultes'."

Vous pouvez imposer un format de sortie :

1. Resume (2-4 lignes)
2. Faits verifies
3. Preuves (liste de chemins)
4. Inconnues / limites

---

## Etape 3 — Verification guidee

Relancez la demande n2 et un prompt de controle :

`Decris /sandbox et cite les fichiers qui prouvent chaque technologie mentionnee.`

Puis completez :

| Fait annonce | Preuve fournie | Chemin valide ? | Commentaire |
|--------------|----------------|-----------------|-------------|
| ... | ... | Oui/Non | ... |
| ... | ... | Oui/Non | ... |
| ... | ... | Oui/Non | ... |

---

## Etape 4 — Test anti-hallucination

Posez une question piege :

`Le projet sandbox utilise-t-il PostgreSQL et Next.js ? Justifie.`

Comportement attendu :

- L'agent verifie les fichiers ;
- il refuse les affirmations non observees ;
- il repond avec prudence et preuves.

---

## Critere de validation

Le niveau est valide si :

- la reponse cite au moins 3 fichiers pertinents ;
- chaque fait principal est lie a une preuve ;
- l'agent indique explicitement ce qu'il ne peut pas confirmer.

---

## Debrief a rendre (6 a 10 lignes)

1. Ce que la contrainte de preuve a change dans la qualite de reponse.
2. Un exemple de fait retire/corrige grace aux preuves.
3. Une proposition d'evolution pour le niveau 3 (ex : format JSON des preuves).
