/* Dated standalone time and explicit report scope, independent of notebook editors. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  let state=null, projectId=null, editingId=null, editRevision=null, scopeRevision=null, scopeDirty=false;
  const panel=$('#project-accounting'), form=$('#manual-time-form');
  function feedback(text,error=false){$('#accounting-error').textContent=error?text:'';$('#accounting-feedback').textContent=error?'':text;}
  function resetEditor(){form.reset();editingId=null;editRevision=null;form.hidden=true;}
  function openEditor(log=null){
    if(!state)return;
    editingId=log?.id||null;editRevision=state.work_revision;
    form.reset();$('#manual-time-title').textContent=log?'Corriger une durée autonome':'Saisir du temps sans entrée de cahier';
    $('#manual-time-date').value=log?.date||new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Zurich'}).format(new Date());
    $('#manual-time-hours').value=log?Math.floor(log.minutes/60):'';
    $('#manual-time-minutes').value=log?log.minutes%60:'';
    $('#manual-time-estimate').checked=log?.estimate===true;$('#manual-time-description').value=log?.description||'';
    panel.open=true;form.hidden=false;feedback('');$('#manual-time-date').focus();form.scrollIntoView({block:'nearest'});
  }
  async function post(payload){
    if(!state || state.project_key!==projectKey)throw new Error('Attendez la fin du chargement du projet.');
    const targetKey=state.project_key;
    const route='/api/accounting'+(targetKey?'?project='+encodeURIComponent(targetKey):'');
    const response=await fetch(route,{method:'POST',headers:{'Content-Type':'application/json','X-Biome-Token':token},body:JSON.stringify(payload)});
    const result=await response.json();if(projectKey!==targetKey || data.project_key!==targetKey)return null;if(!response.ok)throw new Error(result.error||'Enregistrement impossible.');
    if(scopeDirty && scopeRevision===payload.base_revision && payload.action!=='scope')scopeRevision=result.work_revision;
    if(!form.hidden && editRevision===payload.base_revision && payload.action==='scope')editRevision=result.work_revision;
    Object.assign(data,result);return result;
  }
  function renderLogs(){
    const area=$('#accounting-logs');area.replaceChildren();
    if(!state.logs.length){const empty=document.createElement('p');empty.className='muted';empty.textContent='Aucune durée renseignée. Ce projet ne contribue pas aux statistiques de temps.';area.append(empty);return;}
    const table=document.createElement('table'),head=document.createElement('thead'),header=document.createElement('tr');
    for(const label of ['Date','Durée','Origine / commentaire','Actions']){const th=document.createElement('th');th.textContent=label;header.append(th);}head.append(header);table.append(head);const body=document.createElement('tbody');
    for(const log of [...state.logs].sort((a,b)=>b.date.localeCompare(a.date))){
      const row=document.createElement('tr');
      for(const value of [log.date,duration(log.minutes)+(log.minutes===0?' · zéro saisi':''),(log.entry_ids?.length?'Lié au cahier':log.estimate?'Estimation historique':'Saisie autonome')+(log.description?' · '+log.description:'')]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}
      const cell=document.createElement('td');cell.className='accounting-actions';
      if(log.entry_ids?.length){
        const view=document.createElement('button');view.type='button';view.textContent='Voir l’entrée';view.dataset.tooltip='Corriger cette durée dans l’entrée du cahier à laquelle elle est rattachée.';
        view.onclick=()=>{showView('notebook');$('#filter').value='all';$('#notebook-search').value='';render(false);const entry=document.getElementById('item-'+log.entry_ids[0]);if(entry){entry.tabIndex=-1;entry.focus();entry.scrollIntoView({block:'center'});}};cell.append(view);
      }else{
        const edit=document.createElement('button');edit.type='button';edit.textContent='Modifier';edit.dataset.tooltip='Corriger cette durée autonome ; la version précédente reste dans l’historique.';edit.onclick=()=>openEditor(log);
        const remove=document.createElement('button');remove.type='button';remove.textContent='Retirer';remove.dataset.tooltip='Retirer cette durée des totaux. La saisie retirée reste dans l’historique du projet.';
        remove.onclick=()=>{
          remove.textContent='Confirmer le retrait';remove.classList.add('danger');
          const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Annuler';cancel.onclick=renderLogs;cell.append(cancel);
          const base=state.work_revision;
          remove.onclick=async()=>{remove.disabled=true;try{const result=await post({action:'delete',id:log.id,base_revision:base});if(!result)return;window.renderProjectAccounting({...data,...result});if(editingId===log.id)resetEditor();feedback('Durée retirée ; la saisie précédente reste conservée dans l’historique.');}catch(error){feedback(error.message,true);}finally{remove.disabled=false;}};
        };cell.append(edit,remove);
      }
      row.append(cell);body.append(row);
    }table.append(body);area.append(table);
  }
  window.renderProjectAccounting = project => {
    if(!project)return;
    const changed=projectId!==project.project.id;projectId=project.project.id;
    if(changed){resetEditor();scopeDirty=false;panel.open=false;feedback('');}
    state=project;
    if(!scopeDirty){$('#report-project-excluded').checked=state.reporting.excluded;$('#report-exclusion-reason').value=state.reporting.reason;scopeRevision=state.work_revision;}
    $('#report-project-badge').hidden=!state.reporting.excluded;
    $('#accounting-summary').textContent=(state.time_recorded?duration(state.total_minutes):'Temps non renseigné')+' · '+(state.reporting.excluded?'Hors bilan':'Inclus dans les bilans');
    $('#total').textContent=state.time_recorded?'Temps renseigné : '+duration(state.total_minutes):'Temps non renseigné';
    $('#accounting-time-summary').textContent=(state.time_recorded?duration(state.total_minutes)+' au total · '+duration(state.manual_minutes)+' sans entrée liée'+(state.estimated_minutes?' (dont '+duration(state.estimated_minutes)+' d’estimations historiques).':'.'):'Sans saisie, la durée reste inconnue.');
    $('#work').replaceChildren();for(const log of state.logs){const line=document.createElement('p');line.textContent=log.date+' · '+duration(log.minutes)+' · '+(log.estimate?'Estimation historique · ':'')+(log.description||'Saisie de temps');$('#work').append(line);}
    renderLogs();
  };
  $('#open-project-accounting').onclick=()=>{panel.open=!panel.open;if(panel.open)panel.scrollIntoView({block:'nearest'});};
  $('#manual-time-add').onclick=()=>openEditor();$('#manual-time-cancel').onclick=()=>{resetEditor();feedback('');};
  for(const selector of ['#report-project-excluded','#report-exclusion-reason'])$(selector).addEventListener('input',()=>{if(!scopeDirty)scopeRevision=state.work_revision;scopeDirty=true;});
  $('#report-scope-form').onsubmit=async event=>{
    event.preventDefault();const button=$('#report-scope-save');button.disabled=true;feedback('');
    try{const result=await post({action:'scope',excluded:$('#report-project-excluded').checked,reason:$('#report-exclusion-reason').value,base_revision:scopeRevision});if(!result)return;scopeDirty=false;window.renderProjectAccounting({...data,...result});feedback(result.reporting.excluded?'Projet exclu des bilans pour toutes les périodes. Ses temps restent conservés.':'Projet réintégré dans les bilans.');}
    catch(error){feedback(error.message,true);}finally{button.disabled=false;}
  };
  form.onsubmit=async event=>{
    event.preventDefault();const button=$('#manual-time-save');feedback('');
    const hours=$('#manual-time-hours').value,minutes=$('#manual-time-minutes').value;
    if(hours===''&&minutes===''){feedback('Saisissez une durée. Pour une durée inconnue, ne créez pas de saisie.',true);return;}
    const total=Number(hours||0)*60+Number(minutes||0);
    if(!Number.isSafeInteger(total)||Number(minutes||0)>59||total<0){feedback('Utilisez des heures entières et 0 à 59 minutes.',true);return;}
    button.disabled=true;
    try{const result=await post({action:'save',id:editingId,base_revision:editRevision,date:$('#manual-time-date').value,minutes:total,estimate:$('#manual-time-estimate').checked,description:$('#manual-time-description').value});if(!result)return;resetEditor();window.renderProjectAccounting({...data,...result});feedback(result.reporting.excluded?'Durée enregistrée et conservée. Ce projet reste exclu des bilans.':'Durée enregistrée. Elle s’ajoute aux temps du cahier et sera comptée à la date choisie.');}
    catch(error){feedback(error.message,true);}finally{button.disabled=false;}
  };
  if(typeof data!=='undefined'&&data)window.renderProjectAccounting(data);
})();
