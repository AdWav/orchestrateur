# Module Cours — Échantillonnage LLM (théorie ↔ réglages)

Corrélation entre les **équations de décodage** (un token à la fois) et les **libellés de l’UI** « Échantillonnage live » de l’orchestrateur.

**Terminologie.** Dans l’interface et la doc courte, on parle de **réglages** (curseurs, champs numériques, listes). Le mot familier **potard** (comme sur une console audio) peut servir d’image pour les mêmes contrôles, mais ce ne sont que des paramètres exposés à l’API — pas du matériel.

- UI : barre d'onglets **Orchestrateur local** / **Échantillonnage** (réglages live, aperçu streamé) / **Cours** (module théorie ↔ formules)
- Code catalogue : `frontend/src/course/samplingCourseCatalog.ts`
- Guide pratique : [`EXPLAIN.md`](./EXPLAIN.md)
- Streaming, calque tokens, BPE : [`sampling-runtime.md`](./sampling-runtime.md)
- Littérature : [`litterature-maintien-capacite-modele/`](./litterature-maintien-capacite-modele/README.md)

---

## 1. Chaîne de calcul (ordre d’application)

| Étape | Étape (UI Cours) | Réglages concernés |
|------:|------------------|-------------------|
| 1 | Logits bruts | *(aucun — sortie du modèle)* |
| 2 | Biais ciblé | `logit_bias` |
| 3 | Anti-répétition | `repeat_penalty`, `repeat_last_n`, `presence_penalty`, `frequency_penalty` |
| 4 | Hasard / régulation | `temperature`, `mirostat`, `mirostat_eta`, `mirostat_tau` |
| 5 | Filtres du vivier | `top_k`, `top_p`, `min_p` |
| 6 | Échantillonnage | *(tirage stochastique)* |
| 7 | Contraintes globales | `num_predict`, `stop` |

---

## 2. Tableau réglage ↔ symboles ↔ formule ↔ groupe UI

| Clé API / réglage | Libellé UI | Symboles | Formule (résumé) | Groupe rôle | Impact |
|------------------|------------|----------|-----------------|-------------|--------|
| `logit_bias` | Logit bias | \(z_i\), `bias_i` | \(z'_i = z_i + \text{bias}_i\) | E. Chirurgie | Ciblé |
| `repeat_penalty` | Repeat penalty | \(z_i\), historique | Pénalise les tokens déjà vus dans la fenêtre | D. Anti-répétition | Très fort |
| `repeat_last_n` | Repeat last N | \(N\) | \(N\) = nombre de tokens passés considérés | D. Anti-répétition | Moyen |
| `presence_penalty` | Presence penalty | \(\alpha_{\text{pres}}\) | Pénalise les **sujets** déjà présents | D. Anti-répétition | Moyen |
| `frequency_penalty` | Frequency penalty | \(\alpha_{\text{freq}}\) | Pénalise les **mots** trop fréquents | D. Anti-répétition | Moyen |
| `temperature` | Temperature | \(T\), \(P(i)\) | \(P(i) \propto \exp(z'_i / T)\) | B. Créativité | Très fort |
| `mirostat` | Mirostat (0/1/2) | \(k\), \(\tau\), \(\mu\) | Active la boucle de régulation (voir ci-dessous) | B. Créativité | Fort |
| `mirostat_eta` | Mirostat eta | \(\eta\) | \(\mu \leftarrow \mu - \eta\, e\) | B. Créativité | Fort |
| `mirostat_tau` | Mirostat tau | \(\tau\), \(S(X)\) | Cible de surprise ; \(e = S(X) - \tau\) | B. Créativité | Fort |
| `top_k` | Top-k | \(k\), \(V^{(k)}\) | Ne garder que les \(k\) tokens les plus probables | C. Vivier | Fort |
| `top_p` | Top-p (nucleus) | \(p\), \(V^{(p)}\) | \(\sum_{i \in V^{(p)}} P(i) \geq p\) | C. Vivier | Très fort |
| `min_p` | Min-p | \(p_{\min}\) | Éligible si \(P(i) \geq p_{\min}\) | C. Vivier | Fort |
| `num_predict` | Max tokens | \(T_{\max}\) | Arrêt si \(t \geq T_{\max}\) | A. Longueur | Très fort |
| `stop` | Stop sequences | \(s\) | Arrêt si suffixe contient \(s\) | A. Longueur | Ciblé |

Plages UI (min–max) : définies dans `frontend/src/components/samplingFieldSpecs.ts`.

---

## 3. Boucle Mirostat (seul régulateur fermé documenté)

Référence : [Basu et al., ICLR 2021](https://arxiv.org/abs/2007.14966).

| Symbole | Réglage Ollama | Rôle |
|---------|---------------|------|
| \(S(X) = -\log P_M(X)\) | — | Surprise du token tiré |
| \(\tau\) | `mirostat_tau` | Surprise cible |
| \(\eta\) | `mirostat_eta` | Gain de correction |
| \(\mu\) | *(interne)* | Paramètre de top-k adaptatif |
| mode | `mirostat` | 0 = off ; 1 ou 2 = algorithme actif |

**Rétroaction (chaque token)** : \(e = S(X) - \tau\), puis \(\mu \leftarrow \mu - \eta\, e\), et ajustement de \(k\) pour le top-k suivant.

**Interaction** : si Mirostat est actif, `temperature` compte moins — ne pas pousser les deux au maximum (voir [`EXPLAIN.md` §5](./EXPLAIN.md)).

---

## 4. Nucleus sampling (top-p)

Référence : [Holtzman et al., ICLR 2020](https://arxiv.org/abs/1904.09751).

\[
V^{(p)} = \arg\min_{V} |V| \quad \text{s.t.} \quad \sum_{x \in V} P(x) \geq p
\]

**Réglage** : **`top_p`**. Souvent suffisant seul (~0,85–0,95) avant d’empiler `top_k` et `min_p`.

---

## 5. Voir les tokens en pratique (UI)

Après un **essai du profil live** (section en bas de l’onglet Échantillonnage) :

| Mode UI | Ce que vous voyez |
|---------|-------------------|
| **Flux** | Fragments tels qu’Ollama les envoie dans le stream HTTP (approximation visuelle) |
| **BPE** | Tokens du vocabulaire du modèle (GGUF), via `POST /v1/runtime/sampling/tokenize` |

Activer **Tokens**, puis choisir **Flux** ou **BPE**. En BPE, chaque pastille = un id tokenizer ; le survol affiche l’index et l’`id`.

Détails techniques : [`sampling-runtime.md`](./sampling-runtime.md).

---

## 6. Références projet

| Document | Contenu |
|----------|---------|
| [`EXPLAIN.md`](./EXPLAIN.md) | Mind maps, parcours pratique, interactions |
| [`sampling-runtime.md`](./sampling-runtime.md) | Preview streamé, tokenisation BPE, API |
| [`litterature-maintien-capacite-modele/01-decodage-et-regulation.md`](./litterature-maintien-capacite-modele/01-decodage-et-regulation.md) | Couche 1 — papiers et équations |
| [`litterature-maintien-capacite-modele/02-drift-temps-collapse-et-entropie.md`](./litterature-maintien-capacite-modele/02-drift-temps-collapse-et-entropie.md) | Couche 2 — collapse, EWC, entropie |

---

*Dernière mise à jour : module Cours UI, calque tokens Flux/BPE, doc sampling-runtime.*
