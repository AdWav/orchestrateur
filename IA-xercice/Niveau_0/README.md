# Niveau 0 — Mise en service d'un agent conversationnel

## Objectif pédagogique

Ce niveau introduit la notion la plus simple et la plus visible : **imposer une règle de forme** a un agent, ici la **langue de réponse**.

L'apprenant observe un comportement initial, modifie l'agent, puis valide le changement avec un protocole de test reproductible.

---

## Competences visées

- Formuler une hypothese de comportement ("avant/apres").
- Ajouter une contrainte explicite dans une fiche agent (ou un prompt systeme).
- Mesurer un resultat avec des cas de test simples.
- Distinguer fond (exactitude) et forme (langue, ton, format).

---

## Prérequis

- Avoir valide le quizz d'introduction.
- Savoir modifier un fichier de configuration simple.
- Savoir lancer le sandbox local.

---

## Livrables attendus

1. Un fichier de configuration agent modifie avec une regle de langue explicite.
2. Une trace de tests "avant/apres" (tableau ou notes).
3. Une courte conclusion (3 a 6 lignes) sur le comportement observe.

---

## Contenu du dossier

- `enonce.md` : version apprenant (consignes pas a pas).
- `corrige-formateur.md` : exemple de correction et points de vigilance.
- `grille-evaluation.md` : barème rapide sur 10 points.

---

## Temps indicatif

- Mise en route : 10 min
- Baseline (avant) : 10 min
- Modification : 10 min
- Retests et debrief : 15 min

**Total** : 45 min

---

## Critere de reussite du niveau

Le niveau est acquis si :

- l'agent repond en francais sur tous les prompts de validation ;
- la regle de langue est explicite et testable ;
- la conclusion distingue clairement ce qui releve de la langue et ce qui releve de la qualite du contenu.
