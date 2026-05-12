# Lexique pratique IA, agents et Cursor

## Objectif

Ce document sert a parler proprement d'IA, d'agents et de Cursor sans melanger les couches.

Le but n'est pas d'accumuler du jargon. Le but est de savoir dire precisement:

- ce qu'est un `modele`
- ce qu'est un `agent`
- ce qu'est un `outil`
- ce qu'est un `skill`
- ce qu'est `MCP`
- et ou chaque terme se place dans l'ensemble

## Regle rapide

Quand tu bloques sur un mot, pose-toi cette question:

- est-ce que je parle du moteur ?
- de l'instruction ?
- de l'organisation ?
- de l'action ?
- ou de l'integration ?

En pratique:

- moteur = `modele`, `LLM`
- instruction = `prompt`, `system prompt`, `contexte`
- organisation = `agent`, `subagent`, `workflow`, `orchestration`
- action = `outil`, `tool call`
- integration = `API`, `MCP`, `serveur MCP`

## 1. Les couches a ne pas melanger

### Modele

Un `modele` est le moteur statistique qui produit une sortie a partir d'une entree.

Ce n'est pas:

- une application complete
- un agent

Phrase correcte:

- "Le modele genere la reponse, mais il ne pilote pas tout le workflow."

### LLM

Un `LLM` est un grand modele de langage.

Ce n'est pas:

- un orchestrateur
- un outil

Phrase correcte:

- "Le LLM redige, reformule ou raisonne sur du texte."

### Inference

L'`inference` est l'execution du modele.

Ce n'est pas:

- l'entrainement

Phrase correcte:

- "On fait l'inference localement via tel runtime."

### Prompt

Le `prompt` est l'instruction ou l'ensemble d'informations envoyees au modele.

Ce n'est pas:

- le modele lui-meme

Phrase correcte:

- "Le prompt est mal cadre, donc la sortie part dans tous les sens."

### System prompt

Le `system prompt` fixe le cadre general: role, ton, limites, priorites, comportements attendus.

Ce n'est pas:

- la requete ponctuelle de l'utilisateur

Phrase correcte:

- "Le system prompt impose les garde-fous et le role de l'assistant."

### User prompt

Le `user prompt` est la demande specifique de l'utilisateur.

Phrase correcte:

- "Le user prompt donne l'objectif, le system prompt donne le cadre."

### Contexte

Le `contexte` est tout ce qu'on fournit pour cette execution: historique, documents, exemples, variables, contraintes.

Ce n'est pas:

- la memoire persistante du systeme

Phrase correcte:

- "Le modele manque de contexte, pas forcement d'intelligence."

### Context window

La `context window` est la quantite maximale d'information que le modele peut prendre en compte sur une execution.

Ce n'est pas:

- une memoire infinie

Phrase correcte:

- "Le probleme vient de la fenetre de contexte, pas du prompt seul."

## 2. Agents et organisation du travail

### Agent

Un `agent` est un systeme qui utilise un modele pour poursuivre un objectif, raisonner en plusieurs etapes et, souvent, appeler des outils.

Ce n'est pas:

- un simple modele nu

Phrase correcte:

- "L'agent decide quand lire, chercher, executer ou verifier."

### Subagent

Un `subagent` est un agent delegue a une sous-tache precise.

Ce n'est pas:

- un simple appel d'outil

Phrase correcte:

- "Je lance un subagent pour explorer une partie du code."

### Workflow

Un `workflow` est une suite d'etapes organisees pour arriver a un resultat.

Phrase correcte:

- "Le workflow enchaine planification, recherche, execution et verification."

### Orchestration

L'`orchestration` est la logique qui coordonne agents, outils, etapes et handoffs.

Ce n'est pas:

- la generation de texte elle-meme

Phrase correcte:

- "Le probleme vient de l'orchestration, pas du modele."

### Handoff

Un `handoff` est le passage du contexte ou du travail d'une etape a une autre.

Phrase correcte:

- "Le handoff entre recherche et verification est mal defini."

## 3. Outils, skills, rules, hooks

### Outil

Un `outil` est une capacite executable: lire un fichier, lancer une commande, appeler une API, modifier du code, etc.

Ce n'est pas:

- une methode generale de travail

Phrase correcte:

- "L'agent appelle un outil pour lire le fichier."

### Tool call

Un `tool call` est l'appel effectif d'un outil par l'agent.

Phrase correcte:

- "Le modele propose une action, puis l'agent fait un tool call."

### Skill

Un `skill` est un savoir-faire reutilisable. Il encapsule une methode, des regles de travail, des conventions et parfois un enchainement recommande.

Dans Cursor, un `skill` aide l'agent a bien traiter une famille de taches.

Ce n'est pas:

- l'action concrete elle-meme
- un outil

Phrase correcte:

- "Le skill explique comment faire correctement, l'outil execute."

Formule simple:

- `outil` = ce que je peux faire
- `skill` = comment je m'y prends bien

### Rule

Une `rule` est une regle persistante qui guide le comportement de l'agent dans un projet ou un contexte donne.

Dans Cursor, une rule sert a imposer des conventions, des garde-fous, ou des preferences de travail.

Ce n'est pas:

- un skill specialise
- un hook

Phrase correcte:

- "La rule impose les conventions du depot."

### Hook

Un `hook` est un mecanisme d'automatisation declenche autour d'un evenement.

Dans Cursor, un hook peut servir a lancer une verification ou une action en reaction a un moment donne.

Ce n'est pas:

- une consigne redactionnelle
- un skill

Phrase correcte:

- "Le hook automatise telle action apres tel evenement."

### Mode

Un `mode` designe le cadre d'interaction de l'agent.

Exemples typiques:

- `Agent`: execution et edition
- `Plan`: reflexion et conception
- `Ask`: exploration en lecture seule

Ce n'est pas:

- un sous-agent

Phrase correcte:

- "Ici, le bon mode est Plan, pas Agent."

## 4. MCP et integrations

### API

Une `API` est l'interface technique d'un service ou d'une application.

Phrase correcte:

- "Github expose une API."

### MCP

`MCP` signifie `Model Context Protocol`.

C'est un protocole standard qui permet de brancher des ressources et des actions externes a un assistant ou a un agent.

Ce n'est pas:

- une API particuliere
- un outil unique

Phrase correcte:

- "MCP standardise la facon de connecter des services a l'agent."

### Serveur MCP

Un `serveur MCP` expose des ressources et/ou des outils via le protocole MCP.

Phrase correcte:

- "Le serveur MCP donne acces a Linear, Github ou a la doc interne."

### Ressource MCP

Une `ressource MCP` est une information exposee a la lecture: document, schema, fichier, page, donnee.

Phrase correcte:

- "Le serveur expose cette documentation comme ressource MCP."

### Tool MCP

Un `tool MCP` est une action executable exposee via un serveur MCP.

Phrase correcte:

- "Creer un ticket ou lancer une requete peut etre un tool MCP."

### Provider

Un `provider` est le fournisseur d'un modele ou d'un service.

Exemples:

- OpenAI
- Anthropic
- Ollama

Phrase correcte:

- "On change de provider sans changer toute l'architecture."

### Runtime

Le `runtime` est l'environnement qui execute effectivement le modele.

Exemples:

- Ollama
- vLLM
- llama.cpp

Phrase correcte:

- "Le provider et le runtime ne sont pas toujours la meme chose."

## 5. Memoire, recherche et connaissance

### Memoire

La `memoire` est ce que le systeme conserve entre les tours, les etapes ou les sessions.

Ce n'est pas:

- le simple contexte du tour en cours

Phrase correcte:

- "La memoire permet de conserver un etat de travail."

### RAG

`RAG` signifie `Retrieval-Augmented Generation`.

On cherche des sources pertinentes, puis on les injecte dans le contexte avant la generation.

Ce n'est pas:

- du fine-tuning

Phrase correcte:

- "Ici, du RAG suffit peut-etre; pas besoin de re-entrainer le modele."

### Embedding

Un `embedding` est une representation vectorielle d'un contenu.

Phrase correcte:

- "On compare des embeddings pour retrouver les passages proches semantiquement."

### Base vectorielle

Une `base vectorielle` stocke et recherche des embeddings.

### Retriever

Le `retriever` retrouve les documents potentiellement pertinents.

### Reranker

Le `reranker` reclasse les resultats du retriever pour garder les plus utiles.

## 6. Entrainement et specialisation

### Entrainement

L'`entrainement` ajuste les poids du modele a partir de donnees.

Ce n'est pas:

- le prompting
- l'inference

Phrase correcte:

- "L'entrainement change le modele; le prompt, non."

### Fine-tuning

Le `fine-tuning` specialise un modele deja pre-entraine.

Ce n'est pas:

- du simple RAG

Phrase correcte:

- "Le fine-tuning change le comportement du modele de facon plus structurelle."

### Parametre

Un `parametre` est une valeur interne apprise par le modele pendant l'entrainement.

### Hyperparametre

Un `hyperparametre` est un reglage choisi par les humains ou le systeme.

Exemples:

- learning rate
- batch size
- temperature

### Temperature

La `temperature` regle le niveau de variabilite en generation.

Phrase correcte:

- "On baisse la temperature pour rendre la sortie plus stable."

## 7. Qualite, securite et evaluation

### Eval

Une `eval` est une evaluation structuree d'un systeme, d'un agent ou d'un prompt.

Phrase correcte:

- "On a besoin d'une eval avant de conclure que le systeme marche."

### Benchmark

Un `benchmark` est un test comparatif normalise ou semi-standardise.

Phrase correcte:

- "Le benchmark compare plusieurs modeles sur la meme tache."

### Guardrails

Les `guardrails` sont les garde-fous qui limitent les comportements non souhaites.

Phrase correcte:

- "Les guardrails ne remplacent pas une bonne orchestration."

### Hallucination

Une `hallucination` est une sortie plausible mais fausse, inventee ou non fondee.

Phrase correcte:

- "Le modele hallucine des sources inexistantes."

### Prompt injection

Une `prompt injection` est une tentative de detourner le systeme en manipulant les instructions via des contenus fournis.

Phrase correcte:

- "Le systeme doit resister aux prompt injections dans les documents lus."

## 8. Confusions frequentes

### `modele` vs `agent`

- Le modele produit une sortie.
- L'agent organise un comportement autour du modele.

### `outil` vs `skill`

- L'outil execute.
- Le skill guide la methode.

### `rule` vs `skill`

- La rule impose un cadre durable.
- Le skill apporte un savoir-faire specialise.

### `hook` vs `rule`

- Le hook automatise un evenement.
- La rule guide un comportement.

### `API` vs `MCP`

- L'API est l'interface d'un service donne.
- MCP est un protocole standard pour brancher des services a un agent.

### `contexte` vs `memoire`

- Le contexte est fourni pour ce tour.
- La memoire dure au-dela du tour.

### `RAG` vs `fine-tuning`

- Le RAG apporte des sources a l'execution.
- Le fine-tuning modifie le modele en amont.

### `prompting` vs `entrainement`

- Le prompting guide.
- L'entrainement transforme le modele.

## 9. Formulations utiles

Tu peux dire:

- "Ce n'est pas une fonction du modele, c'est une capacite de l'agent."
- "Le skill decrit la bonne methode; l'outil execute l'action."
- "La rule fixe un cadre durable; le hook automatise un declenchement."
- "Le MCP sert de couche d'integration standard entre l'agent et des services externes."
- "Le probleme vient peut-etre de l'orchestration ou du contexte, pas du modele seul."
- "Ici, on n'a pas besoin de fine-tuning; un meilleur prompt ou du RAG peut suffire."
- "Le system prompt cadre le comportement global, le user prompt donne la demande locale."
- "Le handoff entre deux etapes est mal defini."

## 10. Mini pense-bete

- `modele`: moteur de generation
- `LLM`: modele de langage
- `prompt`: instruction envoyee au modele
- `system prompt`: cadre global
- `contexte`: informations du tour courant
- `context window`: taille max de contexte exploitable
- `agent`: systeme organise autour du modele
- `subagent`: agent delegue a une sous-tache
- `workflow`: suite d'etapes
- `orchestration`: coordination des etapes et outils
- `outil`: action executable
- `tool call`: appel effectif d'un outil
- `skill`: methode reutilisable
- `rule`: regle persistante
- `hook`: automatisation sur evenement
- `MCP`: protocole standard de connexion
- `serveur MCP`: composant qui expose ressources et tools
- `memoire`: etat conserve
- `RAG`: recherche de sources avant generation
- `eval`: evaluation structuree
- `guardrails`: garde-fous

## 11. Idee directrice

Pour parler avec precision, separe toujours:

- le moteur: `modele`, `LLM`
- le cadrage: `prompt`, `system prompt`, `contexte`
- l'organisation: `agent`, `subagent`, `workflow`, `orchestration`
- l'action: `outil`, `tool call`
- l'integration: `API`, `MCP`, `serveur MCP`
- la persistence: `memoire`
- l'apport documentaire: `RAG`

Si tu tiens cette separation, tu sonnes deja beaucoup plus precis et beaucoup plus "a egalite" dans la discussion.
