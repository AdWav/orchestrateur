# Niveau 0 — Corrige formateur

> A diffuser apres passage ou pendant la correction collective.

## Intention pedagogique

Ce niveau ne cherche pas a prouver la veracite des faits sur `/sandbox`.  
Il valide que l'apprenant sait **contraindre la forme** d'une reponse agent (ici : la langue).

---

## Correction attendue (principe)

L'apprenant doit ajouter une instruction explicite, par exemple :

- "Reponds toujours en francais."
- "Ne change pas de langue meme si l'utilisateur ecrit en anglais."
- "Si la demande impose une autre langue, expliquer en francais que la politique de langue est le francais."

Cette instruction peut etre placee dans :

- la mission de l'agent,
- un guardrail,
- le prompt systeme du runner.

Les trois options sont valides si le comportement final est stable.

---

## Exemple de formulation robuste

Vous pouvez accepter des variantes proches de ce bloc :

```text
Langue de sortie obligatoire : francais.
Reponds toujours en francais, quelle que soit la langue du prompt utilisateur.
N'utilise une autre langue que sur instruction explicite du systeme (pas de l'utilisateur).
```

---

## Resultat attendu apres modification

Sur la batterie de 4 prompts de l'enonce :

- 4 reponses en francais ;
- pas de bascule automatique en anglais ;
- eventuellement une phrase de refus en francais si l'utilisateur force une autre langue.

---

## Erreurs frequentes

1. Contrainte trop faible : "prefere le francais" au lieu de "toujours en francais".
2. Contrainte placee dans un champ non utilise par le runtime.
3. Tests insuffisants : un seul prompt de verification.
4. Confusion entre langue et exactitude : une reponse en francais peut rester factuellement fausse.

---

## Barème rapide (reference)

- 3 pts : contrainte explicite et correctement placee.
- 3 pts : protocole avant/apres complete.
- 2 pts : 4/4 prompts conformes (FR).
- 2 pts : debrief clair sur "forme vs fond".

Total : 10 points.
