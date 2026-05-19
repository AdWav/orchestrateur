# Couche 1 — Décodage et régulation token par token

*Maintien d’un régime de génération « viable » à chaque pas d’inférence.*

---

## 1. Problème tel que la littérature le formule

Les LM ouverts ne « tombent en panne » pas au sens logiciel : ils **dégénèrent** — répétitions, incohérence, texte hors distribution humaine. La question devient :

> Comment contraindre ou réguler la chaîne de génération pour que des **statistiques de sortie** restent dans une zone où le modèle reste utile ?

Il n’existe **pas** un système d’équations canonique unique ; il existe des **cas d’étude** par paradigme.

---

## 2. Mirostat — boucle fermée sur la surprise (référence principale)

**Basu et al., *Mirostat: A Neural Text Decoding Algorithm that Directly Controls Perplexity*, ICLR 2021**  
https://arxiv.org/abs/2007.14966

### Problème

- **Boredom trap** : top-k / top-p trop bas → perplexité qui **chute** avec la longueur → répétitions.
- **Confusion trap** : paramètres trop hauts → perplexité qui **monte** → incohérence.

### Variables

| Symbole | Rôle |
|---------|------|
| \(S(X) = -\log P_M(X)\) | Surprise du token \(X\) |
| \(\tau\) | Surprise cible |
| \(\mu\) | Paramètre interne (init. \(2\tau\)) |
| \(k\) | Taille du top-k **adaptatif** |
| \(\eta\) | Gain (`mirostat_eta` dans Ollama) |

### Algorithme (rétroaction)

À chaque token :

1. Estimer l’exposant Zipf \(\hat{s}\) sur les logits récents.
2. Calculer \(k\) à partir de \(\hat{s}\), \(\mu\), \(\tau\) (éq. (2) du papier).
3. Échantillonner \(X\) par top-k.
4. Erreur : \(e = S(X) - \tau\).
5. Mise à jour : \(\mu \leftarrow \mu - \eta\, e\).

C’est le travail le plus proche d’un **régulateur** explicite (« maintenir la perplexité à \(\tau\) »).

### Analyse théorique (section 3)

Sous loi de Zipf, le papier relie l’entropie croisée \(H(P_{M_k}, P_M)\) à \(k\) et \(p\) (théorèmes 1–4) — explique **pourquoi** les réglages fixes dérivent.

---

## 3. Holtzman et al. — diagnostic + contrainte nucleus

**Holtzman et al., *The Curious Case of Neural Text Degeneration*, ICLR 2020**  
https://arxiv.org/abs/1904.09751

### Problème

Maximiser la vraisemblance (beam search) ou sampler naïvement produit des textes **statistiquement** éloignés du texte humain.

### Équation opérationnelle (nucleus / top-p)

À chaque pas, \(V^{(p)}\) = plus petit ensemble tel que :

\[
\sum_{x \in V^{(p)}} P(x) \geq p
\]

puis échantillonnage dans \(V^{(p)}\).

**Type** : contrainte dynamique (boucle **ouverte**), pas de rétroaction sur une grandeur cible.

---

## 4. SimCTG + Contrastive Search — score de décodage

**Su et al., *A Contrastive Framework for Neural Text Generation*, NeurIPS 2022**  
https://arxiv.org/abs/2202.06417

### Problème

Dégénérescence liée à des **représentations anisotropes** (tokens trop similaires dans l’espace latent).

### Entraînement

\[
\mathcal{L}_{\text{SimCTG}} = \mathcal{L}_{\text{MLE}} + \mathcal{L}_{\text{CL}}
\]

(\(\mathcal{L}_{\text{CL}}\) : objectif contrastif avec marge \(\rho\) sur les représentations de tokens.)

### Décodage

Parmi les \(k\) candidats les plus probables, choisir celui qui maximise un score combinant **vraisemblance** et **pénalité de dégénérescence** (similarité au contexte — éq. (5), hyperparamètre \(\alpha\)).

**Type** : optimisation locale par token ; maintien de la **discriminabilité** du texte généré.

---

## 5. Controlled Decoding — RL + ancrage KL

**Mudgal et al., *Controlled Decoding from Language Models*, ICML 2024**  
https://arxiv.org/abs/2310.17022

### Problème

Diriger un LM **gelé** vers une récompense sans « casser » le comportement linguistique.

### Objets formels

- Politique de décodage \(\pi\), référence \(\pi_{\text{ref}}\)
- Récompense \(r([\mathbf{x}, \mathbf{y}])\), valeur \(V^\*\), avantage \(A\)
- Divergence KL tokenwise \(D([\mathbf{x}, y^t]; \pi)\)

### Idée

Objectif **RL régularisé par KL** : maximiser la récompense tout en pénalisant l’écart à \(\pi_{\text{ref}}\) — « maintenir » le modèle **proche du prior** tout en satisfaisant une contrainte métier (sécurité, style, etc.).

---

## 6. Unlikelihood — correction de la distribution apprise

**Welleck et al., *Neural Text Generation with Unlikelihood Training*, ICML 2020**  
https://arxiv.org/abs/1908.04319

### Problème

L’objectif MLE **surpondère** les séquences répétitives ; le modèle reste « bon » en perplexité mais **dégénère** en génération.

### Type

Réentraînement de \(p_\theta\) pour **abaisser** la probabilité de séquences indésirables — maintien au niveau **distribution**, pas au décodage live.

---

## 7. Inférence active — cadre génératif bayésien

**Friston et al. ; Parr et al., *Active Inference* (MIT Press)**

### Problème (hors NLP strict)

Maintenir la cohérence entre **modèle génératif** et **observations**.

### Équations (schéma)

- Modèle génératif : \(p(y, \vartheta) = p(y \mid \vartheta)\, p(\vartheta)\)
- **Énergie libre variationnelle** \(F\) comme borne sur l’evidence
- Mises à jour des croyances (et actions) par minimisation de \(F\)

**Parallèle conceptuel** avec Mirostat : les deux utilisent une **erreur** (surprise observée vs cible) pour corriger le comportement — mais à des échelles différentes (croyances vs paramètre \(k\)).

---

## 8. Tableau récapitulatif (couche 1)

| Référence | Grandeur « maintenue » | Mécanisme |
|-----------|------------------------|-----------|
| Mirostat | Surprise \(\approx \tau\) | Boucle \(e,\ \mu,\ k\) |
| Holtzman (nucleus) | Masse dans le noyau | Contrainte \(V^{(p)}\) |
| Contrastive Search | Cohérence + diversité | Score de décodage |
| Controlled Decoding | Récompense + proximité KL | RL tokenwise |
| Unlikelihood | Proba. des mauvaises séq. | Réentraînement |
| Active inference | Erreur de prédiction / \(F\) | Dynamiques continues |

---

## 9. Lien projet orchestrateur

- Paramètres live documentés dans [`EXPLAIN.md`](../EXPLAIN.md).
- **Mirostat** est le seul aligné sur un papier à **boucle fermée** explicite ; les autres potards correspondent surtout aux lignes « contrainte ouverte » ou « heuristique » du tableau ci-dessus.

→ Suite : [02-drift-temps-collapse-et-entropie.md](./02-drift-temps-collapse-et-entropie.md)
