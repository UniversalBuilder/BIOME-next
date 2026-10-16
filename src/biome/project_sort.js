/* Shared by the catalogue and the sorting checks. Missing values stay last. */
(function(scope){
  function sortProjects(projects,key,direction,statusNames){
    const collator=new Intl.Collator('fr',{numeric:true,sensitivity:'base'});
    const value=p=>key==='status'?(p.status==='Unknown'?'':(statusNames[p.status]||p.status)):
      key==='people'?([p.group,p.contact].filter(Boolean).join(' · ')):
      ['created_at','last_activity'].includes(key)?(p[key]&&Number.isFinite(Date.parse(p[key]))?Date.parse(p[key]):null):p[key];
    return [...projects].sort((a,b)=>{
      let av=value(a),bv=value(b);
      const missing=v=>v===null||v===undefined||v==='';
      if(missing(av)||missing(bv)){if(missing(av)&&!missing(bv))return 1;if(!missing(av)&&missing(bv))return -1;}
      const comparison=typeof av==='number'&&typeof bv==='number'?av-bv:collator.compare(av||'',bv||'');
      return (direction==='desc'?-comparison:comparison)||collator.compare(a.title,b.title)||collator.compare(a.key,b.key);
    });
  }
  scope.sortProjects=sortProjects;
  if(typeof module!=='undefined')module.exports={sortProjects};
})(typeof globalThis!=='undefined'?globalThis:this);
