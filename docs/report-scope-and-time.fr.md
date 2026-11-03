# Temps de travail et périmètre du bilan

## Dans chaque projet : Temps & bilan

Le bouton **Temps & bilan**, près du temps total, ouvre le volet du projet. La coche **Exclure ce projet de tous les bilans** s’applique après **Enregistrer le périmètre**. Un motif est facultatif. Elle retire le projet de tous les indicateurs et exports statistiques, pour toutes les périodes. Le cahier, les données et les durées restent conservés ; décochez et enregistrez pour le réintégrer.

Cette exclusion convient par exemple au développement interne de BIOME, à un projet atypique ou à un historique trop incomplet pour la population étudiée. Elle relève d’un choix explicite ; un temps important n’est pas supprimé automatiquement.

## Saisir du temps sans note

**Saisir du temps** demande une date de rattachement, des heures et/ou des minutes, et un commentaire facultatif. Aucun texte de cahier n’est créé. Les durées autonomes s’ajoutent à celles du cahier : ne ressaisissez pas un total qui inclut déjà des séances enregistrées.

Une séance ordinaire accepte jusqu’à 24 heures. Cochez **Estimation historique** pour un temps cumulé rétrospectif, éventuellement supérieur à une journée. L’estimation reste identifiée comme telle. La date choisie détermine le mois et l’année du bilan ; répartissez une estimation en plusieurs saisies si elle couvre plusieurs périodes.

Le tableau des temps distingue les durées liées au cahier, les durées autonomes et les estimations. Une durée autonome peut être modifiée ou retirée, avec conservation de la version précédente dans l’historique. Une durée liée à une note se corrige depuis cette note, grâce à **Voir l’entrée**.

Une durée vide ne crée pas de saisie. Un zéro doit être saisi explicitement. Il est conservé comme une observation de durée nulle, plutôt que comme une donnée manquante.

## Règles de calcul

| Situation | Conséquence |
| --- | --- |
| Projet exclu volontairement | Retiré des totaux, graphiques, décomptes et moyennes. Présent séparément dans la traçabilité des exclusions. |
| Projet sans activité documentée ni temps dans la période | Hors de la population de cette période. |
| Projet présent, sans temps renseigné dans la période | Conservé dans le nombre de projets ; écarté des statistiques de durée et des répartitions en heures. |
| Zéro explicitement enregistré | Durée connue de zéro, comprise dans la population des projets avec temps renseigné. |
| Groupe ou contact manquant | Hors du nombre de groupes/contacts connus ; un groupe manquant est aussi hors de la répartition par groupe. Le temps total reste conservé. |
| Logiciel, modalité ou thématique manquant | Hors de la seule répartition concernée. |
| Estimation historique | Incluse à sa date de rattachement et signalée dans les détails et les exports. |
| Dossier illisible ou temps invalide | Signalé dans les avertissements, sans inventer de durée. |

Les moyennes utilisent les seuls projets dont le temps est connu, y compris les zéros saisis, après exclusion volontaire. Les catégories scientifiques comptent des projets, sans répartir artificiellement les heures entre plusieurs logiciels.

Les mois sans durée renseignée affichent **—**, avec une piste hachurée ; un zéro enregistré affiche **0 h 00 min**. Le bloc **Périmètre et qualité des données** distingue projets retenus, exclus, sans temps et zéros saisis. Les motifs de non-participation à chaque répartition peuvent se cumuler ; ils ne doivent pas être additionnés comme des populations distinctes.

## Exports et conservation

L’écran, le JSON, les CSV, le rapport HTML et le PDF emploient le même périmètre. `projects.csv` contient les projets retenus ; `excluded-projects.csv` liste séparément les exclusions et leurs motifs. `scope.csv` et `coverage.csv` explicitent les populations et exclusions. Les estimations sont un sous-ensemble du temps autonome, lui-même inclus dans le total : ces colonnes ne doivent pas être additionnées entre elles. Les colonnes restent distinctes ; une cellule de durée vide signifie non renseignée. Les « Sessions » du CSV et le champ technique `session_count` comptent les saisies de temps, y compris les estimations cumulées.

Les durées et le périmètre sont stockés dans le dossier du projet, dans `records/work-logs.json`, avec un historique des corrections. Le CSV de temps est une projection de ce document. Une transaction interrompue peut être reprise sans dupliquer le temps. Les enregistrements devenus obsolètes sont refusés au lieu d’écraser une autre correction. La sauvegarde et la restauration documentaires conservent le périmètre, les durées et leur historique.
