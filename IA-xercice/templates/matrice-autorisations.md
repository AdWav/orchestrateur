# Matrice d'autorisations — modèle

À remplir pour chaque agent de l'atelier (niveaux 2+).

**Nom de l'agent :** _______________________  
**Niveau atelier :** _______________________

| Colonne | Votre réponse |
|---------|---------------|
| **Périmètre** | Chemins / services / APIs autorisés : |
| **Actions** | Cocher : ☐ R (lecture) ☐ W? (proposition) ☐ W (écriture) ☐ D (suppression) ☐ exec (commandes) |
| **Preuve** | Comment vérifier le respect (citations, logs, diff review…) : |
| **Arrêt** | Conditions d'échec ou escalade humaine : |

## Exemple rempli — `doc_inventory`

| Colonne | Réponse |
|---------|---------|
| Périmètre | Arborescence du dépôt cible ; `docs/`, `README.md`, `compose.yaml`, dossiers services |
| Actions | R uniquement |
| Preuve | Chaque fait = chemin relatif cité |
| Arrêt | Arrêt si source manquante ; pas d'inférence sur ports/services sans fichier |
