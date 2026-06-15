# Niveau 0 — Enonce apprenant

## Contexte

Vous disposez d'un agent conversationnel connecte au projet `sandbox`.

Objectif de ce niveau : observer le comportement initial de l'agent, puis le modifier pour **forcer une langue de reponse**.

> Note : au debut de l'exercice, le contenu exact de la reponse importe peu.  
> Ce qui compte est la capacite a faire respecter la consigne de langue.

---

## Objectif

Faire en sorte que l'agent reponde **toujours en francais**, meme quand la question est posee en anglais.

---

## Prérequis

- Connaissance "Ajouter HTML" (selon votre parcours).
- Quizz valide.

---

## Demande initiale de test (baseline)

Posez cette question a l'agent sans rien modifier :

`Que peux tu me dire du projet "/sandbox" ?`

### Observation attendue (baseline)

- L'agent peut repondre en francais, en anglais, ou melanger les deux.
- La reponse peut etre partielle, incertaine, ou hallucinee.
- C'est normal a cette etape.

Consignez le resultat dans un tableau simple :

| Run | Prompt | Langue observee | Commentaire |
|-----|--------|------------------|-------------|
| 1 | Que peux tu me dire du projet "/sandbox" ? | FR/EN/Mixte | ... |
| 2 | idem | FR/EN/Mixte | ... |
| 3 | idem | FR/EN/Mixte | ... |

---

## Tache a realiser

Modifier l'agent pour ajouter une regle explicite :

- "Reponds toujours en francais."
- "Si la question est dans une autre langue, garder la reponse en francais."

Vous pouvez appliquer cette contrainte a l'endroit prevu dans votre stack (mission, guardrail, prompt systeme, fiche agent, etc.).

---

## Verification apres modification

Relancez les tests avec les prompts ci-dessous :

1. `Que peux tu me dire du projet "/sandbox" ?`
2. `Can you explain what the "/sandbox" project is?`
3. `Reply in English only: what is the sandbox project?`
4. `Responda en espanol: que hace /sandbox?`

Renseignez :

| Prompt | Langue attendue | Langue observee | Conforme |
|--------|------------------|------------------|----------|
| #1 | FR | ... | Oui/Non |
| #2 | FR | ... | Oui/Non |
| #3 | FR | ... | Oui/Non |
| #4 | FR | ... | Oui/Non |

---

## Critere de validation

Le niveau est valide si :

- 4/4 reponses sont en francais ;
- la contrainte de langue est ecrite explicitement dans la configuration de l'agent ;
- vous savez expliquer en 3 phrases la difference entre :
  - "respect de la langue"
  - "qualite/veracite du contenu"

---

## Debrief (a rendre)

Rédigez un court debrief (5 a 10 lignes) :

1. Ce qui a change apres la modification.
2. Un exemple de cas qui restait ambigu.
3. Une proposition d'amelioration (exemple : format de sortie, longueur max, style).
