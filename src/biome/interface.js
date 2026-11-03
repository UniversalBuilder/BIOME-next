/* Context help and action descriptions are local and do not change application state. */
(() => {
  'use strict';
  const descriptions = {
    'nav-projects': 'Retrouver les projets du catalogue et reprendre un cahier.',
    'open-directory': 'Gérer les contacts, les groupes et les catégories proposés dans les projets.',
    'open-report': 'Consulter les heures et les projets sur une période, puis exporter le bilan.',
    'open-maintenance': 'Ouvrir ou créer un catalogue, sauvegarder, restaurer et vérifier les accès.',
    'context-help': 'Afficher les repères et les actions propres à cet écran.',
    'new-project': 'Ouvrir le formulaire de création : titre, contact et demande initiale.',
    'request-import-preview': 'Lire les champs explicitement nommés dans le message et préremplir les champs vides. À vérifier avant création.',
    'request-import-clear': 'Retirer le message préparé de cette création, avant son enregistrement.',
    'new-originals-pick': 'Sélectionner le dossier des images originales. Son contenu ne sera pas copié.',
    'new-originals-clear': 'Retirer ce choix de dossier du formulaire. Les images restent à leur place.',
    'create-project': 'Créer le dossier documentaire avec la demande, puis ouvrir le cahier du projet.',
    'cancel-project': 'Fermer le formulaire de création sans créer de projet.',
    'refresh-projects': 'Relire le catalogue pour afficher les projets et leurs dernières informations.',
    'back-directory': 'Revenir à la liste des projets du catalogue.',
    'directory-save': 'Enregistrer le contact ou le groupe saisi dans l’annuaire.',
    'directory-cancel': 'Quitter la modification de cette fiche sans enregistrer les changements saisis.',
    'vocabulary-save': 'Enregistrer cette valeur dans la liste de catégories sélectionnée.',
    'vocabulary-cancel': 'Quitter la modification de la catégorie sans enregistrer les changements saisis.',
    'back-report': 'Revenir à la liste des projets.',
    'refresh-report': 'Recalculer le bilan pour la période et les filtres actuellement sélectionnés.',
    'back-projects': 'Revenir au catalogue sans supprimer le projet ouvert.',
    'reload': 'Recharger le projet depuis son dossier. Enregistrez vos modifications en cours avant de continuer.',
    'edit-info': 'Corriger le titre, le contact, le groupe ou les dates du projet.',
    'edit-framing': 'Définir l’objectif, le livrable, le statut, l’intervention et les catégories scientifiques.',
    'delete-project': 'Préparer le retrait du projet vers la corbeille BIOME. Une confirmation sera demandée.',
    'info-date-suggest': 'Proposer une date à partir des informations disponibles ; vérifiez-la avant d’enregistrer.',
    'info-save': 'Enregistrer les informations corrigées dans le dossier du projet.',
    'info-cancel': 'Fermer les informations sans enregistrer les changements saisis.',
    'framing-save': 'Enregistrer le cadrage et actualiser la synthèse du projet.',
    'framing-cancel': 'Fermer le cadrage sans enregistrer les changements saisis.',
    'tab-notebook': 'Consulter les notes, les essais et les échanges ; saisir le temps de travail.',
    'tab-files': 'Retrouver les pièces jointes, les données copiées et les emplacements externes.',
    'tab-deliveries': 'Préparer une archive versionnée et retrouver les livraisons déjà produites.',
    'manual-time-cancel': 'Fermer la saisie autonome sans enregistrer la durée.',
    'compose': 'Ajouter une note, un essai, une réunion, un échange ou une décision au cahier.',
    'import-open': 'Préparer une entrée à partir d’un message Outlook, d’un email ou d’un texte.',
    'clear-search': 'Effacer la recherche et le filtre de type pour afficher tout le cahier.',
    'import-preview': 'Lire le message sélectionné et préparer une entrée à relire avant enregistrement.',
    'import-cancel': 'Fermer la préparation de l’échange sans l’ajouter au cahier.',
    'conflict-reload': 'Reprendre la version enregistrée sur disque ; votre variante reste conservée dans les fichiers de conflit.',
    'conflict-save': 'Remplacer la version sur disque par votre correction, après comparaison. La version remplacée est conservée dans l’historique.',
    'save': 'Enregistrer le texte, la date, le temps renseigné et les pièces jointes de cette entrée.',
    'cancel': 'Fermer l’éditeur sans enregistrer les changements en cours.',
    'data-folder-create-open': 'Préparer un nouveau dossier de données séparé du catalogue.',
    'data-folder-link': 'Choisir un dossier existant comme emplacement des données, sans le déplacer ni le copier.',
    'data-folder-parent-pick': 'Choisir l’emplacement où créer le dossier de données du projet.',
    'data-folder-create': 'Créer le dossier de données à l’emplacement préparé, puis le lier à ce projet.',
    'data-folder-cancel': 'Annuler la préparation du nouveau dossier de données.',
    'receive-open': 'Préparer la copie d’originaux reçus vers un stockage durable, avec un reçu de vérification.',
    'receive-file': 'Sélectionner un fichier source à copier. La copie ne commence pas encore.',
    'receive-folder': 'Sélectionner un dossier source à copier. La copie ne commence pas encore.',
    'receive-destination-pick': 'Choisir le stockage durable où copier les originaux sélectionnés.',
    'receive-preview': 'Calculer le nombre de fichiers, le volume et la destination avant de copier.',
    'receive-save': 'Copier les originaux, vérifier les empreintes et conserver le reçu. Les sources restent intactes.',
    'receive-cancel': 'Fermer la préparation de réception sans lancer une nouvelle copie.',
    'add-dataset': 'Ajouter ou corriger une référence vers un fichier ou un dossier externe.',
    'pick-file': 'Sélectionner un fichier externe à référencer. Son contenu ne sera pas copié.',
    'pick-folder': 'Sélectionner un dossier externe à référencer. Son contenu ne sera pas copié.',
    'dataset-save': 'Enregistrer le libellé, la catégorie et l’emplacement de cette référence.',
    'dataset-cancel': 'Fermer la référence sans enregistrer les changements saisis.',
    'new-delivery': 'Choisir les fichiers à figer dans une nouvelle archive ZIP versionnée.',
    'catalogue-new': 'Préparer une nouvelle collection de projets dans un nouveau dossier.',
    'workspace-choose': 'Ouvrir un catalogue documentaire existant sans déplacer les projets.',
    'catalogue-parent-pick': 'Choisir l’emplacement parent du nouveau catalogue.',
    'catalogue-create': 'Créer le nouveau catalogue, puis l’utiliser comme collection active.',
    'catalogue-create-cancel': 'Fermer la création sans créer de catalogue.',
    'workspace-apply': 'Afficher les projets du dossier sélectionné, sans déplacer le catalogue précédent.',
    'workspace-cancel': 'Conserver le catalogue actuel et annuler ce changement.',
    'relocate-pick': 'Choisir où copier le catalogue documentaire. Aucune copie ne commence encore.',
    'relocate-run': 'Copier le catalogue, vérifier la copie puis l’utiliser. Le catalogue source est conservé.',
    'demo-pick': 'Choisir l’emplacement du catalogue fictif de démonstration.',
    'demo-install': 'Installer les projets fictifs dans un catalogue séparé et l’ouvrir. Votre catalogue actuel reste dans les récents.',
    'run-diagnostics': 'Vérifier la structure des projets et l’accès actuel aux fichiers ou dossiers liés.',
    'trash-reload': 'Relire les projets retirés du catalogue et conservés dans la corbeille BIOME.',
    'backup-pick': 'Choisir où enregistrer l’archive de sauvegarde documentaire.',
    'backup-create': 'Créer et vérifier un ZIP du catalogue et des fichiers internes. Les données externes ne sont pas copiées.',
    'restore-pick-file': 'Choisir l’archive ZIP à vérifier puis à restaurer.',
    'restore-pick-folder': 'Choisir le dossier parent d’une nouvelle restauration, sans modifier le catalogue actif.',
    'restore-create': 'Vérifier l’archive et restaurer ses fichiers dans un nouveau dossier.',
    'restore-open': 'Utiliser le catalogue qui vient d’être restauré, à la place de la collection affichée.',
    'delete-project-confirm': 'Déplacer le dossier documentaire vers la corbeille BIOME. Les données externes restent à leur place.',
    'delete-project-cancel': 'Garder le projet dans le catalogue et fermer cette confirmation.',
    'close-image': 'Fermer l’aperçu et revenir aux pièces jointes.',
    'page-help-close': 'Fermer l’aide et retrouver votre écran, avec vos champs en cours de saisie.',
    'ds-clear': 'Retirer tous les éléments de la sélection de livraison, sans supprimer leurs fichiers.',
    'ds-review-button': 'Passer au récapitulatif pour vérifier les fichiers et les données externes avant de produire le ZIP.',
    'ds-back': 'Revenir à la sélection en conservant les fichiers déjà choisis.',
    'ds-create': 'Produire une nouvelle archive versionnée à partir de la sélection vérifiée.',
    'ds-image-close': 'Fermer l’aperçu de l’image et revenir à la sélection.',
    'ds-rename-open': 'Modifier le libellé affiché pour ce fichier dans la livraison, sans renommer le fichier source.',
    'ds-rename-save': 'Conserver ce libellé pour la livraison en cours de préparation.',
    'ds-rename-cancel': 'Fermer la correction du libellé sans enregistrer la nouvelle saisie.',
    'ds-preview-select': 'Ajouter ou retirer ce fichier de la sélection de livraison.',
    'ds-expand': 'Afficher l’image en grand pour vérifier son contenu.',
    'stop-biome': 'Arrêter le serveur local BIOME. Enregistrez votre travail avant de quitter.'
  };
  const screens = {
    projects: {title:'Retrouver et commencer un projet', intro:'Le catalogue rassemble vos dossiers documentaires. Les filtres changent la liste affichée ; les indicateurs comptent toujours le catalogue complet.', actions:[['Nouveau projet','Renseignez un titre, un contact et la demande. Le projet sera créé « À cadrer », puis ouvert dans le cahier.'],['Recherche + statut','Cherchez dans le titre, le contact ou le groupe, puis combinez avec un statut. Effacez la recherche pour élargir les résultats.'],['Titre d’un projet','Ouvre son cahier. Les fichiers et les livraisons sont accessibles dans les onglets du projet.']],note:'Actualiser relit les dossiers du catalogue. Les indicateurs « En cours » et « En validation » correspondent aux statuts enregistrés, pas à un calcul automatique d’avancement.'},
    accounting:{title:'Temps autonome et participation au bilan',intro:'Les durées s’ajoutent à celles du cahier. Le périmètre du bilan est un choix indépendant : exclure un projet ne supprime aucune saisie.',actions:[['Exclure ce projet','Cochez puis enregistrez pour le retirer de tous les bilans et exports, pour toutes les périodes. Décochez et enregistrez pour le réintégrer.'],['Saisir du temps','Choisissez une date et une durée sans créer de note. Une estimation historique peut cumuler plusieurs journées ; la date choisie détermine sa place dans le bilan.'],['Corriger / retirer','Modifiez les durées autonomes depuis leur tableau. Pour une durée liée à une note, utilisez Voir l’entrée. L’historique des corrections reste conservé.']],note:'Ne ressaisissez pas un total qui inclut déjà les séances du cahier. Une durée absente reste inconnue ; un zéro saisi est une donnée explicite. Les estimations restent identifiables dans les bilans.'},
    create:{title:'Créer le dossier du projet',intro:'Trois informations suffisent pour commencer : titre, contact et demande initiale. Le cadrage pourra être complété ensuite.',actions:[['Importer une demande','Les champs explicitement nommés d’un message peuvent préremplir les champs vides. Vérifiez toujours les valeurs proposées.'],['Dossier des originaux','Lie l’emplacement des images sans les copier. Ce choix peut attendre si les images ne sont pas encore disponibles.'],['Créer et ouvrir','Crée le dossier documentaire et conserve la demande dans le nouveau cahier.']],note:'L’email et le groupe sont facultatifs. Un mail libre ne permet pas de déduire automatiquement toutes les coordonnées.'},
    notebook:{title:'Tenir le cahier du projet',intro:'Chaque entrée conserve un événement de travail : note, essai, réunion, échange ou décision, avec sa date et ses fichiers éventuels.',actions:[['Ajouter une entrée','Choisissez le type, saisissez le texte et, si utile, le temps humain en minutes. L’enregistrement se fait dans le dossier du projet.'],['Importer un échange','Prépare une entrée à partir d’un message ou d’un texte. Relisez le contenu avant de l’enregistrer.'],['Rechercher / filtrer','Affiche les entrées correspondant au texte et au type choisis. « Effacer » rétablit le cahier complet.']],note:'Les minutes renseignées alimentent le bilan à la date de la séance. Une durée vide signifie « non renseignée », et non zéro minute.'},
    exchange:{title:'Conserver un échange dans le cahier',intro:'Importez un message Outlook, un email ou un texte pour préparer une entrée relisible et datée.',actions:[['Choisir le message','Sélectionnez le fichier ou collez le texte reçu.'],['Préparer l’entrée','Lit le contenu et le place dans l’éditeur, pour vérifier le texte, le type et la date.'],['Enregistrer ensuite','La préparation seule ne crée pas d’entrée. Relisez et enregistrez depuis l’éditeur du cahier.']],note:'Le message original peut contenir des informations personnelles. Vérifiez le texte et les pièces jointes avant de les conserver dans le projet.'},
    entry:{title:'Enregistrer une entrée du cahier',intro:'Cette entrée décrit un événement précis. Sa date détermine la période à laquelle le temps de travail est comptabilisé.',actions:[['Type, date et texte','Décrivez ce qui a été fait ou décidé. Les tags permettent de retrouver l’entrée ensuite.'],['Minutes','Saisissez le temps humain estimé. Laissez vide si la durée est inconnue ; le temps de calcul n’est pas du temps humain.'],['Pièces jointes','Les fichiers sélectionnés seront copiés dans le dossier documentaire lors de l’enregistrement.']],note:'Enregistrer conserve le texte et les métadonnées. Lors d’une correction, une version devenue obsolète est signalée pour comparaison, au lieu d’écraser silencieusement une autre modification.'},
    files:{title:'Distinguer fichiers et données',intro:'Une pièce jointe est conservée dans le projet. Une référence indique où trouver des données externes, sans en copier le contenu.',actions:[['Dossier de données','Crée ou lie le dossier séparé contenant les images du projet. Lier un dossier ne le déplace pas.'],['Recevoir les originaux','Prépare une copie des fichiers reçus. Vérifiez source, destination et volume avant de copier ; les sources restent intactes.'],['Ajouter des données','Enregistre une référence et sa catégorie. Pour conserver une copie, utilisez la réception ou une pièce jointe du cahier.']],note:'La sauvegarde du catalogue inclut les fichiers internes. Les données conservées sur un autre stockage doivent être sauvegardées séparément.'},
    receive:{title:'Préparer une copie vérifiée',intro:'La réception conserve les originaux sur le stockage choisi, avec un reçu permettant de retrouver les fichiers copiés.',actions:[['Source','Sélectionnez le fichier ou dossier reçu. La source n’est pas supprimée.'],['Destination','Choisissez l’emplacement durable. « Préparer la réception » affiche le nombre de fichiers et le volume à copier.'],['Copier et conserver','Lance la copie puis vérifie les empreintes. Attendez le résultat avant de considérer les données comme reçues.']],note:'Une référence externe n’est pas une copie de sécurité. Les originaux qui restent hors du catalogue demandent une sauvegarde distincte.'},
    dataset:{title:'Ajouter une référence externe',intro:'Cette fiche décrit un emplacement ; elle ne transfère pas les données dans BIOME.',actions:[['Fichier ou dossier','Choisissez un emplacement accessible depuis cet ordinateur.'],['Libellé et catégorie','Expliquez le rôle des données pour les retrouver dans le tableau.'],['Enregistrer','Conserve la référence dans le projet. Les fichiers sources restent à leur emplacement actuel.']],note:'Sur un stockage réseau, l’accès peut dépendre du VPN et des droits. Une référence enregistrée ne garantit pas que le stockage sera disponible plus tard.'},
    datafolder:{title:'Créer un dossier de données',intro:'Ce dossier est destiné aux images et aux résultats volumineux, séparément du catalogue documentaire.',actions:[['Dossier parent','Choisissez le stockage qui accueillera le dossier de données.'],['Préparation','Vérifiez le nom et le chemin proposés avant de créer le dossier.'],['Créer et lier','Crée le dossier puis enregistre son emplacement dans ce projet.']],note:'Cette opération ne déplace pas automatiquement les images déjà présentes ailleurs. Utilisez la réception des originaux pour copier les fichiers reçus.'},
    deliveries:{title:'Figer une version à transmettre',intro:'Une livraison conserve une sélection précise de fichiers dans une archive versionnée. Les corrections ultérieures du cahier ne la réécrivent pas.',actions:[['Préparer une livraison','Ouvre la sélection des fichiers à inclure. Filtrez les éléments, puis vérifiez la sélection conservée.'],['Données externes','Leur inclusion est facultative. Le volume peut être important ; vérifiez les emplacements et les fichiers sélectionnés.'],['Archive produite','Le ZIP contient les fichiers choisis, une synthèse, un manifeste et des empreintes de contrôle.']],note:'Pour transmettre des fichiers corrigés, produisez une nouvelle livraison. La précédente reste une trace de ce qui a été livré à cette date.'},
    framing:{title:'Définir le travail attendu',intro:'Le cadrage relie la demande aux prochaines étapes. Il peut être complété au fil des échanges, sans remplir tous les champs dès le départ.',actions:[['Objectif et livrable','Décrivez la question à traiter et ce qui devra être remis.'],['Statut et prochaine étape','Indiquez où en est le projet et ce qui doit suivre. Le statut est un choix enregistré, pas une estimation automatique.'],['Intervention et catégories','Précisent le type de travail, les logiciels, les modalités et les thématiques utilisés pour les filtres et le bilan.']],note:'Enregistrer actualise la synthèse du projet. Les catégories scientifiques comptent des projets dans le bilan ; elles ne répartissent pas automatiquement les heures entre catégories.'},
    info:{title:'Corriger les informations du projet',intro:'Ces champs identifient le projet et ses interlocuteurs. Ils sont distincts du cadrage scientifique et des séances de travail.',actions:[['Titre et contact','Corrigez les informations affichées dans le catalogue et l’en-tête du projet.'],['Groupe et email','Complétez les coordonnées si elles sont connues.'],['Dates du projet','Vérifiez les dates proposées avant d’enregistrer ; elles ne remplacent pas les dates des séances du cahier.']],note:'Les heures du bilan restent calculées aux dates des séances. Modifier une date de projet ne déplace pas toutes ses heures vers cette date.'},
    contacts:{title:'Maintenir l’annuaire et les catégories',intro:'Les contacts et groupes sont proposés lors de la création et de la correction des projets. Ce ne sont pas des comptes d’accès à BIOME.',actions:[['Ajouter / modifier','Crée ou corrige une fiche de contact ou de groupe. Les corrections sont historisées.'],['Supprimer','Prépare le retrait d’une fiche. Si des projets l’utilisent, l’écran demande de traiter leur réattribution.'],['Catégories','Gérez les valeurs proposées pour les logiciels, les modalités et les thématiques. Une valeur masquée n’est plus proposée.']],note:'Vérifiez la fiche existante avant d’en créer une autre avec un nom proche. Les catégories décrivent les projets, pas des résultats de mesure.'},
    report:{title:'Lire le bilan d’activité',intro:'Le bilan retient les projets avec une activité dans la période et non exclus volontairement. Les données manquantes sont écartées du seul calcul concerné.',actions:[['Période et filtres','Choisissez l’intervalle à analyser, puis actualisez le bilan.'],['Heures et répartition','Le temps vient des minutes saisies dans le cahier, à la date de chaque séance. Groupes et interventions répartissent ce temps.'],['Catégories et export','Logiciels, modalités et thématiques comptent des projets. Les tableaux détaillent les valeurs ; l’export conserve la période et les données.']],note:'Le bloc Périmètre distingue les projets exclus, les durées inconnues et les zéros saisis. Les estimations sont identifiées. Pour exclure un projet atypique ou le réintégrer, ouvrez son volet Temps & bilan.'},
    catalogue:{title:'Gérer la collection documentaire',intro:'Le catalogue contient les dossiers des projets et les listes communes. Les images originales peuvent rester sur un autre stockage.',actions:[['Créer / ouvrir','Change la collection affichée. Les catalogues récents permettent de retrouver les emplacements précédents.'],['Sauvegarder / restaurer','La sauvegarde copie les fichiers internes dans un ZIP vérifié. La restauration crée un nouveau dossier, puis propose de l’utiliser.'],['Diagnostic et corbeille','Vérifiez la structure et les accès ; retrouvez les projets retirés dans la corbeille BIOME.']],note:'Les références externes sont conservées dans la sauvegarde, mais pas les données auxquelles elles mènent. Un accès réussi ne certifie pas l’intégrité scientifique des images.'}
  };
  const dialog = document.querySelector('#page-help-dialog');
  const trigger = document.querySelector('#context-help');
  const tooltip = document.querySelector('#action-tooltip');
  const visible = selector => { const element = document.querySelector(selector); return element && element.getClientRects().length > 0; };
  function currentHelp() {
    if (visible('#new-project-form')) return screens.create;
    if (visible('#project-workspace')) {
      if(visible('#manual-time-form') || visible('#project-accounting[open] #report-scope-form')) return screens.accounting;
      for (const [selector, key] of [['#import-form','exchange'],['#info-form','info'],['#framing-form','framing'],['#receive-form','receive'],['#dataset-form','dataset'],['#data-folder-form','datafolder'],['#form','entry']]) if (visible(selector)) return screens[key];
      return screens[({files:'files',deliveries:'deliveries'})[document.body.dataset.projectView] || 'notebook'];
    }
    return screens[({contacts:'contacts',report:'report',maintenance:'catalogue'})[document.body.dataset.space] || 'projects'];
  }
  trigger.addEventListener('click', () => {
    hideTooltip();
    const screen = currentHelp();
    document.querySelector('#page-help-title').textContent = screen.title;
    document.querySelector('#page-help-intro').textContent = screen.intro;
    const actions = document.querySelector('#page-help-actions');
    actions.replaceChildren();
    for (const [label, detail] of screen.actions) {
      const row = document.createElement('div'); row.className = 'help-action';
      const name = document.createElement('strong'); name.textContent = label;
      const text = document.createElement('p'); text.textContent = detail;
      row.append(name, text); actions.append(row);
    }
    document.querySelector('#page-help-note').textContent = screen.note;
    dialog.showModal();
  });
  document.querySelector('#page-help-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { hideTooltip(); trigger.focus({preventScroll:true}); });
  dialog.addEventListener('click', event => { const bounds = dialog.getBoundingClientRect(); if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close(); });

  function description(button) {
    if (button.dataset.tooltip) return button.dataset.tooltip;
    if (descriptions[button.id]) return descriptions[button.id];
    if (button.classList.contains('project-link')) return 'Ouvrir le cahier de « '+button.textContent.trim()+' ».';
    if (button.classList.contains('recent-catalogue')) return 'Ouvrir ce catalogue sans déplacer la collection actuelle.';
    const label = button.getAttribute('aria-label') || button.textContent.trim() || button.title;
    if (button.classList.contains('sort-heading')) return label+'. Cliquez à nouveau pour inverser l’ordre.';
    if (button.classList.contains('remove')) return 'Retirer ce fichier de la sélection à joindre. Le fichier source reste intact.';
    if (/recevoir des images/i.test(label)) return 'Préparer une réception d’originaux vers le dossier 01_raw de ce projet.';
    if (/ouvrir le dossier/i.test(label)) return 'Ouvrir ce dossier dans l’explorateur de fichiers de cet ordinateur.';
    if (/modifier.*entrée/i.test(label)) return 'Reprendre le texte et les métadonnées de cette entrée ; la correction sera conservée dans l’historique.';
    if (/annuler/i.test(label)) return 'Fermer cette préparation sans enregistrer les changements saisis.';
    if (/supprimer|retirer/i.test(label)) return 'Préparer le retrait de cet élément. Vérifiez sa portée avant de confirmer.';
    if (/modifier/i.test(label)) return 'Ouvrir les informations de cet élément pour les corriger.';
    if (/restaurer/i.test(label)) return 'Replacer ce projet de la corbeille BIOME dans le catalogue actif.';
    if (/enregistrer/i.test(label)) return 'Enregistrer les informations saisies dans ce panneau.';
    if (/télécharger/i.test(label)) return 'Télécharger une copie du fichier conservé dans le projet.';
    if (/export|pdf/i.test(label)) return 'Produire le document à partir de la période et des données affichées.';
    if (/cahier/i.test(label)) return 'Retrouver dans le cahier l’entrée associée à ce fichier.';
    if (/ouvrir|afficher|voir/i.test(label)) return 'Afficher cet élément pour le consulter.';
    if (/fermer/i.test(label)) return 'Fermer ce panneau et revenir à l’écran précédent.';
    if (/sélectionner|cocher/i.test(label)) return 'Mettre à jour les fichiers sélectionnés pour cette livraison.';
    return label ? 'Action : '+label.replace(/[.…]+$/,'')+'.' : 'Consulter ou modifier cet élément.';
  }
  let activeButton = null, timer = null, closeTimer = null;
  function hideTooltip() {
    clearTimeout(timer); clearTimeout(closeTimer);
    tooltip.hidden = true;
    if (activeButton) {
      const ids=(activeButton.getAttribute('aria-describedby') || '').split(/\s+/).filter(id=>id && id!==tooltip.id);
      if(ids.length) activeButton.setAttribute('aria-describedby',ids.join(' ')); else activeButton.removeAttribute('aria-describedby');
    }
    activeButton=null;
  }
  function positionTooltip() {
    if (!activeButton || tooltip.hidden) return;
    const box=activeButton.getBoundingClientRect(), tip=tooltip.getBoundingClientRect();
    const left=Math.max(10,Math.min(innerWidth-tip.width-10,box.left+(box.width-tip.width)/2));
    const above=box.top-tip.height-8;
    const top=above>=10?above:Math.min(innerHeight-tip.height-10,box.bottom+8);
    tooltip.style.left=left+'px';tooltip.style.top=Math.max(10,top)+'px';
  }
  function showTooltip(button, delay) {
    if (activeButton===button && !tooltip.hidden) { clearTimeout(closeTimer); return; }
    hideTooltip(); activeButton=button;
    const text=description(button);
    // Avoid native title popups competing with the accessible tooltip.
    if(button.hasAttribute('title')) button.removeAttribute('title');
    timer=setTimeout(()=>{
      if(!button.isConnected || !button.getClientRects().length) { hideTooltip(); return; }
      (button.closest('dialog[open]') || document.body).append(tooltip);
      tooltip.textContent=text;tooltip.style.left='0px';tooltip.style.top='0px';tooltip.hidden=false;
      const ids=new Set((button.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean));ids.add(tooltip.id);button.setAttribute('aria-describedby',[...ids].join(' '));
      positionTooltip();
    }, delay);
  }
  function scheduleClose() { clearTimeout(closeTimer); closeTimer=setTimeout(()=>{ if(activeButton && (activeButton.matches(':hover') || document.activeElement===activeButton || tooltip.matches(':hover'))) return; hideTooltip(); },120); }
  document.addEventListener('pointerover', event=>{if(event.pointerType==='touch')return;const button=event.target.closest('button, a[download]');if(button)showTooltip(button,450);});
  document.addEventListener('pointerout', event=>{if(event.target.closest('button, a[download]'))scheduleClose();});
  document.addEventListener('focusin',event=>{const button=event.target.closest('button, a[download]');if(button && button.matches(':focus-visible'))showTooltip(button,250);});
  document.addEventListener('focusout',event=>{if(event.target.closest('button, a[download]'))scheduleClose();});
  tooltip.addEventListener('pointerenter',()=>clearTimeout(closeTimer));tooltip.addEventListener('pointerleave',scheduleClose);
  document.addEventListener('keydown',event=>{if(event.key==='Escape' && !tooltip.hidden){hideTooltip();event.preventDefault();event.stopPropagation();}},true);
  document.addEventListener('click',()=>hideTooltip());
  addEventListener('scroll',()=>hideTooltip(),true);addEventListener('resize',()=>hideTooltip());
})();
