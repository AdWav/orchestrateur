# Niveau 2 — Corrige formateur

> Correction ciblee sur "faits verifies" et "preuves citees".

## Intention pedagogique

Faire passer l'apprenant d'une logique de reponse probable a une logique de reponse **justifiee**.

Le point central est la regle :

`pas de fait sans source`.

---

## Attendus minimaux

Pour la demande n2, la reponse doit :

- decrire le projet `sandbox` ;
- mentionner la stack principale ;
- inclure des chemins de fichiers en preuve.

Exemples de preuves acceptables (selon contenu local) :

- `IA-xercice/sandbox/README.md`
- `IA-xercice/sandbox/backend/requirements.txt`
- `IA-xercice/sandbox/frontend/package.json`
- `IA-xercice/sandbox/backend/app/main.py`

---

## Formulation de guardrail acceptable

```text
Chaque affirmation technique doit etre appuyee par au moins un chemin de fichier consulte.
Si aucune preuve n'est trouvee, indiquer explicitement "non observe".
Ne pas extrapoler au-dela des fichiers lus.
```

---

## Erreurs frequentes

1. Le chemin est cite mais ne prouve pas reellement le fait.
2. Une seule preuve globale pour plusieurs affirmations differentes.
3. Format de reponse trop libre, difficile a auditer.
4. L'agent oublie de declarer les inconnues.

---

## Barème de reference (10 points)

- 3 pts : regle de preuve correctement ajoutee.
- 3 pts : au moins 3 citations pertinentes et exploitables.
- 2 pts : distinction claire "observe" / "non observe".
- 2 pts : test anti-hallucination reussi (question piege).

Total : 10 points.
