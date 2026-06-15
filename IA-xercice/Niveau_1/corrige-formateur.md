# Niveau 1 — Corrige formateur

> Support de correction pour l'atelier "Ajout puis utilisation d'un tool".

## Intention pedagogique

Le niveau 1 fait passer l'apprenant de la contrainte de forme (niveau 0) a la **collecte factuelle**.

Point cle : la reponse doit s'appuyer sur une exploration reelle du dossier `sandbox`.

---

## Attendu minimum

Pour la demande :

`Que peux tu me dire du projet "/sandbox" ?`

la reponse doit inclure, au minimum :

`Le projet sandbox est un livre d'or en python/react/SQLite.`

---

## Ce qui valide l'ajout du tool

On attend au moins un des indices suivants :

- trace d'appel au tool de listing/lecture ;
- mention de fichiers effectivement presents dans `sandbox` ;
- reduction claire des formulations hesitantes ou inventees.

Si l'apprenant affirme des technologies sans preuve d'exploration, penaliser.

---

## Exemple de consigne agent acceptable

```text
Pour toute question sur un dossier local, commence par explorer le dossier cible.
Lis les fichiers cles pour identifier: objectif fonctionnel, backend, frontend, base de donnees.
Si une information manque, dis-le explicitement au lieu d'inventer.
```

---

## Erreurs frequentes

1. Tool ajoute mais jamais invoque par l'agent.
2. Consigne trop vague ("utilise les outils si besoin").
3. Reponse trop courte (technos sans objectif produit).
4. Confusion entre certitude et supposition.

---

## Barème de reference (10 points)

- 3 pts : tool ajoute et accessible par l'agent.
- 3 pts : usage observe du tool dans les tests.
- 2 pts : noyau attendu present (livre d'or + python/react/SQLite).
- 2 pts : debrief clair sur gain de fiabilite.

Total : 10 points.
