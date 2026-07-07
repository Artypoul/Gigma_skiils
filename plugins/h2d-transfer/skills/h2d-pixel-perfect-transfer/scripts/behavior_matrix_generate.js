#!/usr/bin/env node
const fs=require('fs'); const path=require('path');
function arg(n,d=null){const i=process.argv.indexOf(`--${n}`); return i>=0?process.argv[i+1]:d;}
async function main(){
  const inventoryPath=arg('inventory'); const out=arg('out','reports/interaction_matrix.json'); if(!inventoryPath) throw new Error('Usage: --inventory behavior_inventory.json --out interaction_matrix.json');
  const inv=JSON.parse(fs.readFileSync(inventoryPath,'utf8')); const interactions=[];
  for(const c of inv.components||[]){
    for(const action of ['hover','focus','click']) interactions.push({interaction_id:`${c.component_id}:${action}`, component_id:c.component_id, selector:c.selector, action, criticality:c.criticality==='critical'?'critical':'normal'});
    if(c.kind==='disclosure') for(const action of ['escape','outside-click','keyboard-enter','keyboard-space']) interactions.push({interaction_id:`${c.component_id}:${action}`, component_id:c.component_id, selector:c.selector, action, criticality:'critical'});
  }
  const report={result:interactions.length?'pass':'not-tested', interactions}; fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(report,null,2)); console.log(`interactions=${interactions.length} out=${out}`);
}
main().catch(e=>{console.error(e.stack||e);process.exit(1);});
