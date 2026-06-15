# Niveau 0 — Grille d'evaluation (10 points)

## A. Mise en place de la contrainte (3 pts)

| Critere | Points |
|---------|--------|
| Regle de langue explicite ("toujours en francais") | 1 |
| Regle placee dans une zone effectivement lue par l'agent | 1 |
| Formulation non ambigue (pas "si possible", pas "de preference") | 1 |

---

## B. Protocole de test (3 pts)

| Critere | Points |
|---------|--------|
| Baseline avant modification (au moins 3 runs) | 1 |
| Batterie apres modification (au moins 4 prompts incluant anglais) | 1 |
| Tableau de suivi present (attendu vs observe) | 1 |

---

## C. Resultat observe (2 pts)

| Critere | Points |
|---------|--------|
| Toutes les reponses de verification sont en francais | 2 |

Si 1 seul ecart de langue : 1 point.  
Si plusieurs ecarts : 0 point.

---

## D. Analyse et recul (2 pts)

| Critere | Points |
|---------|--------|
| L'apprenant distingue clairement forme (langue) et fond (veracite) | 1 |
| Propose une amelioration pertinente pour l'etape suivante | 1 |

---

## Seuil indicatif

- **8 a 10** : acquis
- **6 a 7** : partiellement acquis (retester la robustesse)
- **0 a 5** : a retravailler (reprendre baseline + reformulation des regles)
