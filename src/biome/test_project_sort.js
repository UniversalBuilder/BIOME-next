const assert=require('node:assert/strict');
const {sortProjects}=require('./project_sort.js');
const statuses={Active:'En cours',Completed:'Terminé',Unknown:'Non renseigné'};
const rows=[
 {key:'a',title:'Projet 10',group:'',contact:'',status:'Unknown',created_at:null,last_activity:null},
 {key:'b',title:'Projet 2',group:'Zulu',contact:'Alice',status:'Completed',created_at:'2025-01-01',last_activity:'2025-03-01T12:00:00Z'},
 {key:'c',title:'Alpha',group:'Alpha',contact:'Bob',status:'Active',created_at:'2026-01-01',last_activity:'2025-03-01T12:30:00+01:00'},
];
const keys=(key,direction)=>sortProjects(rows,key,direction,statuses).map(p=>p.key).join('');
assert.equal(keys('title','asc'),'cba');
assert.equal(keys('created_at','desc'),'cba');
assert.equal(keys('created_at','asc'),'bca');
assert.equal(keys('last_activity','desc'),'bca'); // Real instants, including offsets.
assert.equal(keys('people','asc'),'cba');
assert.equal(keys('status','desc'),'bca'); // Unknown stays last in both directions.
assert.equal(keys('status','asc'),'cba');
assert.equal(rows[0].key,'a'); // Sorting must not mutate the source array.
console.log('Catalogue sorting: names, identities, dates, timezones, unknowns and immutability OK.');
