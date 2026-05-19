# Couche 2 — Drift temporel, collapse, poids et entropie

*Maintien de la capacité sur plusieurs générations, entraînements ou sessions — pas seulement à un pas de décodage.*

← [Couche 1](./01-decodage-et-regulation.md) | [Index](./README.md)

---

## 1. Deuxième couche : quelle question ?

La couche 1 répond à : *« le texte sort-il d’un régime dégénéré **maintenant** ? »*

La couche 2 répond à :

- Le modèle **oublie-t-il** des tâches passées quand on le met à jour ?
- La distribution apprise **s’effondre-t-elle** si on réentraîne sur ses propres sorties ?
- Peut-on **allouer** dynamiquement la capacité (taille de modèle, compute) selon l’incertitude ?
- L’**alignement** (RLHF, DPO) maintient-il le modèle « dans les clous » sans le dégrader ?

---

## 2. Model collapse — boucle modèle ↔ données synthétiques

### 2.1 Shumailov et al. (fondateur)

**Shumailov et al., *The Curse of Recursion: Training on Generated Data Makes Models Forget*, 2023**  
https://arxiv.org/abs/2305.17493  
Version journal : *Nature* (2024) — https://www.nature.com/articles/s41586-024-07566-y

#### Problème

Entraîner la génération \(n+1\) sur des données produites par le modèle \(n\) : **effondrement** de la distribution apprise — disparition des **queues** (événements rares), puis convergence vers une loi à **faible variance** (modes confondus).

#### Formalisation (histogramme / échantillonnage fini)

- Taille d’échantillon \(M\) par génération.
- État \(i\) de probabilité \(q \leq 1/M\) : nombre attendu d’occurrences \(< 1\) → **perte d’information** sur les événements rares.
- Processus **distinct** de l’oubli catastrophique : ce n’est pas qu’on efface l’ancien ; on **réinterprète** une réalité déjà biaisée.

#### Risque

Bornes sur la distance de **Wasserstein** entre la vraie distribution et celle des modèles successifs (sections 3–4 du papier).

#### Conséquence opérationnelle

« Maintenir le modèle en capacité » exige des **données humaines / réelles** dans la boucle — pas uniquement du texte généré par LLM.

---

### 2.2 Accumulation vs remplacement (cadre linéaire tractable)

**Dohmatob et al., *Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data*, 2024**  
https://arxiv.org/abs/2404.01413

#### Remplacement des données (collapse)

Erreur de test quadratique **croît linéairement** avec le nombre d’itérations \(n\) :

\[
\mathbb{E}^{\text{Replace}}_{\text{test}}(\hat{w}_n)
= \frac{\sigma^2 d}{T - d - 1} \times n
\]

(\(d\) : dimension ; \(T\) : nombre d’échantillons ; \(\sigma^2\) : bruit.)

#### Accumulation (éviter la divergence)

\[
\mathbb{E}^{\text{Accum}}_{\text{test}}(\hat{w}_n)
\leq \frac{\sigma^2 d}{T - d - 1} \times \frac{\pi^2}{6}
\]

**Intuition** : à l’itération \(i\), la contribution au jeu d’entraînement est pondérée \(\propto 1/i\) ; l’effet sur le MSE est \(\propto 1/i^2\) ; \(\sum 1/i^2 < \infty\) → **borne finie** indépendante de \(n\).

#### Leçon

Maintenir la capacité dans une boucle auto-référente = **conserver l’ancre de données réelles** + accumuler plutôt que remplacer.

---

## 3. Oubli catastrophique — maintien des poids (continual learning)

### 3.1 EWC (référence classique)

**Kirkpatrick et al., *Overcoming catastrophic forgetting in neural networks*, PNAS 2017**  
https://arxiv.org/abs/1612.00796

#### Problème

Apprendre la tâche B en séquentiel **dégrade** la tâche A : les poids importants pour A sont écrasés.

#### Équation (tâche B, ancrage sur A)

\[
\mathcal{L}(\theta) = \mathcal{L}_B(\theta) + \sum_i \frac{\lambda}{2}\, F_i\, (\theta_i - \theta^*_{A,i})^2
\]

- \(\theta^*_A\) : solution après tâche A  
- \(F_i\) : élément diagonal de la **matrice d’information de Fisher** (importance du paramètre \(i\) pour A)  
- \(\lambda\) : compromis ancien / nouveau  

**Type** : ressort élastique sur les poids — maintien de la **performance passée** en région quadratique autour de \(\theta^*_A\).

#### Limite pour les LLM

Coût et approximations Fisher ; surtout pertinent pour **fine-tuning séquentiel**, pas pour le décodage Ollama live.

---

### 3.2 Distinction collapse vs forgetting

| | Model collapse | Catastrophic forgetting |
|--|----------------|-------------------------|
| **Unité** | Chaîne de **modèles** \(M_0, M_1, \ldots\) | Un **même** réseau, tâches successives |
| **Mécanisme** | Biais de la **distribution** d’entraînement | Écrasement des **poids** |
| **Symptôme** | Queues qui disparaissent, variance qui s’effondre | Perte de score sur tâche A |

---

## 4. Alignement — maintenir le modèle près du prior tout en optimisant une récompense

### 4.1 RLHF / PPO avec pénalité KL (schéma standard)

**Christiano et al. ; Ouyang et al. (InstructGPT / RLHF)**

Objectif typique (formulation usuelle) :

\[
\max_\pi \; \mathbb{E}_{\pi}\big[r(x,y)\big] - \beta\, \mathbb{E}_{\pi}\big[\mathrm{KL}(\pi(\cdot|x) \,\|\, \pi_{\text{ref}}(\cdot|x))\big]
\]

**Interprétation** : « capacité de fonctionnement » = rester **suffisamment proche** du modèle de base \(\pi_{\text{ref}}\) pour ne pas dégrader le langage, tout en montant la récompense humaine.

→ Formalisation détaillée côté décodage : [Controlled Decoding](./01-decodage-et-regulation.md#5-controlled-decoding--rl--ancrage-kl) (ICML 2024).

### 4.2 DPO (alternative sans RL explicite)

**Rafailov et al., *Direct Preference Optimization*, 2023**  
https://arxiv.org/abs/2305.18290

Réécrit l’objectif RLHF en **perte sur paires préférées**, avec \(\pi_{\text{ref}}\) dans la formule — même idée de **ancrage** implicite au modèle de référence.

---

## 5. Contrôle par entropie à l’inférence (couche 2 bis — compute & incertitude)

Signal commun : **entropie des logits** \(H_t = -\sum_i p_i \log p_i\) comme proxy d’« état difficile ».

### 5.1 EAD — commutation de modèles

**Simonds, *Entropy Adaptive Decoding: Dynamic Model Switching*, 2025**  
https://arxiv.org/abs/2502.06833

- Entropie lissée : \(\bar{H}_t = \frac{1}{w}\sum_{i=t-w+1}^{t} H_i\)
- Règle : si \(\bar{H}_t > \tau\) → modèle **large** \(M_L\), sinon \(M_S\)
- **Maintien** : performance proche du grand modèle avec **fraction réduite** de tokens sur \(M_L\)

### 5.2 CNTP — multi-échantillons si entropie haute

**Cautious Next Token Prediction** (ACL Findings 2025)  
https://aclanthology.org/2025.findings-acl.1318/

Nombre d’essais de décodage **anti-corrélé** à la confiance (entropie basse → un essai ; haute → plusieurs).

### 5.3 EAGER — budget de raisonnement adaptatif

**EAGER: Entropy-Aware GEneRation** (2025)  
https://arxiv.org/abs/2510.11170

Branchement / scaling d’inférence **uniquement** sur tokens à haute entropie — allocation de compute pour **maintenir** la qualité de raisonnement sous budget.

### 5.4 Politique de température apprise

**Adaptive Decoding via Latent Preference Optimization** (2024)  
https://arxiv.org/abs/2411.09661

Apprend une **politique de température** token ou séquence (proche en esprit de Mirostat, mais **apprise** par RL/préférences plutôt que régulateur analytique).

---

## 6. Synthèse couche 2 — quelle grandeur pour quel horizon ?

| Horizon | Référence clé | Grandeur contrôlée / bornée |
|---------|---------------|-----------------------------|
| Générations de modèles | Shumailov 2023 | Distance à la vraie loi ; queues |
| Itérations linéaires | Dohmatob 2024 | \(\mathbb{E}_{\text{test}}\) (borne vs linéaire en \(n\)) |
| Tâches séquentielles | Kirkpatrick EWC 2017 | \(\mathcal{L}_A\) via pénalité Fisher |
| Alignement | RLHF / DPO | KL à \(\pi_{\text{ref}}\) |
| Inférence adaptative | EAD, CNTP, EAGER | Entropie \(\bar{H}_t\), budget compute |
| Un pas (rappel) | Mirostat 2021 | Surprise \(S(X) \approx \tau\) |

---

## 7. Implications pour un orchestrateur d’agents

1. **Réglage live (couche 1)** : cadre la **qualité instantanée** de la sortie ; ne protège pas contre un modèle obsolète ou un fine-tune destructeur.
2. **Traces & réentraînement (couche 2)** : si des sorties LLM alimentent des corpus ou des fine-tunes, penser **accumulation + données réelles** (Dohmatob), pas remplacement pur.
3. **Agents multiples / workflows** : l’équivalent EWC serait des **versions figées** de modèles par rôle + pénalité de dérive explicite lors d’un update — peu documenté sous cette forme pour LLM, mais l’analogie formelle tient.
4. **Budget** : EAD/EAGER formalisent le maintien **performance / coût** via l’entropie — pertinent si l’orchestrateur route entre SLM et LLM.

---

## 8. Bibliographie rapide (couche 2)

| Titre court | Année | Lien |
|-------------|-------|------|
| Curse of Recursion (model collapse) | 2023 | https://arxiv.org/abs/2305.17493 |
| Is Model Collapse Inevitable? | 2024 | https://arxiv.org/abs/2404.01413 |
| EWC / catastrophic forgetting | 2017 | https://arxiv.org/abs/1612.00796 |
| Controlled Decoding | 2024 | https://arxiv.org/abs/2310.17022 |
| DPO | 2023 | https://arxiv.org/abs/2305.18290 |
| Entropy Adaptive Decoding | 2025 | https://arxiv.org/abs/2502.06833 |
| EAGER | 2025 | https://arxiv.org/abs/2510.11170 |

---

*Document généré pour le projet orchestrateur — complément de [`EXPLAIN.md`](../EXPLAIN.md).*
