# Finitions visuelles et aide contextuelle

BIOME-next conserve son thème sombre Pandora et ses accents cyan et violet.

## Typographie et surfaces

Roboto est embarquée avec l’application : le rendu ne dépend pas d’une police système ou d’un service en ligne. Le corps emploie la graisse 400, les titres et les libellés de navigation la graisse 500, les actions principales la graisse 600. Les titres, les valeurs et les informations secondaires ont une échelle distincte, sans appliquer le gras à tous les éléments.

Les cartes utilisent des dégradés légers, des contours translucides et des ombres diffuses. Les états survolé, actif et sélectionné partagent les mêmes règles. Les tableaux du catalogue s’adaptent aux largeurs intermédiaires ; le défilement horizontal reste disponible sur les petits écrans. Les indicateurs décrivent le catalogue complet, indépendamment des filtres.

## Aide au moment de l’action

La page d’aide globale et le bouton « Comprendre cet écran » ont été retirés.

- Les infobulles expliquent l’effet des actions. Elles apparaissent au survol ou au focus clavier, restent visibles lorsque le pointeur passe sur leur texte et se ferment avec Échap. Le texte utilise `aria-describedby`.
- Le bouton « ? » ouvre une modale courte pour l’écran ou le formulaire en cours : création, cahier, édition d’entrée, informations, cadrage, fichiers, réception, référence, dossier de données, livraison, contacts, bilan ou catalogue.
- L’aide conserve le projet, l’onglet et les champs saisis. Le dialogue natif contient le focus ; Échap ou le bouton de fermeture le ferme, puis le focus revient au déclencheur.
- Polices et aide sont incluses dans la version portable Windows ; aucune requête vers un service de polices externe n’est nécessaire.

Les interactions s’appuient sur les repères WAI pour les [infobulles](https://www.w3.org/WAI/ARIA/apg/patterns/tooltip/) et les [dialogues modaux](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/). Le motif WAI des infobulles est encore présenté comme un travail en cours ; il ne constitue pas à lui seul une certification d’accessibilité.

## Vérification

Les 91 tests Python existants passent sous Python 3.12 avec les dépendances de BIOME. Le parcours `tools/check_interface.cjs` vérifie, sur un catalogue synthétique, le chargement de la police, les infobulles souris et clavier, les actions dynamiques, Échap, le retour du focus, le contenu contextuel, la conservation d’un brouillon et d’un onglet, la largeur du tableau et le dialogue sur mobile. Les captures ont été examinées.

Ce contrôle navigateur utilise Playwright et un navigateur installé localement. Il doit cibler une prévisualisation contenant un seul projet créé par `synthetic_fixture.create_fixture`, sans données utilisateur. Les modules et le navigateur peuvent être fournis par les variables `BIOME_PLAYWRIGHT` et `BIOME_CHROMIUM` ; sinon le script utilise l’installation Playwright habituelle.

```text
node tools/check_interface.cjs http://127.0.0.1:PORT/
```

Les captures sont conservées dans `test-tmp/interface`. Ces vérifications ne constituent pas un audit complet d’accessibilité.

## Références visuelles

Les captures fournies par l’utilisateur et [ThreatLens de DIGIMARIX](https://dribbble.com/shots/27543906-ThreatLens-Enterprise-Cybersecurity-SaaS-Dashboard) servent de références pour la hiérarchie visuelle et la subtilité des surfaces. Les données affichées restent celles du catalogue BIOME.
