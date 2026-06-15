# Niveau 1 — Enonce apprenant

## Contexte

Au niveau 0, vous avez force la langue de reponse.

Au niveau 1, vous devez augmenter la **qualite factuelle** de la reponse en donnant a l'agent un tool pour lire le contenu du dossier `sandbox`.

---

## Objectif niveau 1

### Demande n1

`Que peux tu me dire du projet "/sandbox" ?`

### Reponse attendue (partielle minimale)

`Le projet sandbox est un livre d'or en python/react/SQLite.`

La formulation exacte peut varier, mais cette information doit apparaitre clairement.

---

## Prerequis

- Reussite du niveau 0.

---

## Etape 1 — Baseline (avant ajout tool)

Posez la demande n1 a l'agent actuel.

Consignez :

| Run | Prompt | Reponse utile ? | Niveau de certitude |
|-----|--------|------------------|---------------------|
| 1 | Demande n1 | Oui/Non/Partiel | faible/moyen/fort |
| 2 | Demande n1 | Oui/Non/Partiel | faible/moyen/fort |

Objectif : constater les limites sans tool (reponse vague ou hallucination possible).

---

## Etape 2 — Ajout du tool

Ajoutez a l'agent un tool de lecture/exploration du workspace (fichiers/dossiers), selon votre stack.

Le tool doit permettre au minimum :

- lister un dossier cible ;
- lire des fichiers cles (`README`, `package.json`, `requirements`, etc.).

---

## Etape 3 — Ajustement de la consigne agent

Ajoutez une consigne explicite du type :

- "Pour toute question sur un dossier/projet local, commence par explorer le dossier cible."
- "Ne reponds pas sur l'architecture technique sans avoir consulte au moins deux sources du dossier."
- "Si l'information est manquante, le dire explicitement."

---

## Etape 4 — Aide "skills" pour une reponse complete

Ajoutez une mini methode (dans mission/guardrails/prompt) qui guide la description d'un dossier :

1. Identifier l'objectif fonctionnel (quel produit ?).
2. Identifier le backend (langage/framework).
3. Identifier le frontend (langage/framework).
4. Identifier la persistence (base de donnees).
5. Donner une synthese en 2-4 phrases.

But : obtenir une reponse plus complete et structuree.

---

## Etape 5 — Retest

Rejouez :

`Que peux tu me dire du projet "/sandbox" ?`

Puis un prompt de robustesse :

`Decris "/sandbox" en citant les technologies detectees.`

Tableau de validation :

| Prompt | Mention "livre d'or" | Mention backend | Mention frontend | Mention DB | Conforme |
|--------|-----------------------|-----------------|------------------|------------|----------|
| n1 | Oui/Non | Oui/Non | Oui/Non | Oui/Non | Oui/Non |
| robustesse | Oui/Non | Oui/Non | Oui/Non | Oui/Non | Oui/Non |

---

## Critere de validation

Niveau valide si :

- l'agent utilise effectivement le tool (ou traces d'exploration disponibles) ;
- la reponse contient le noyau attendu : livre d'or + python/react/SQLite ;
- la reponse est globalement coherente avec les fichiers observes dans `sandbox`.

---

## Debrief a rendre

En 6 a 10 lignes :

1. Ce qui a change grace au tool.
2. Ce qui restait insuffisant avant l'aide "description de dossier".
3. Une amelioration proposee pour le niveau suivant (ex : citations de fichiers).
