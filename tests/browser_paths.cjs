// Each browser process owns its fictional downloads; no fixed Linux paths.
'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const evidence=process.env.AULA_BROWSER_EVIDENCE_DIR;
if(evidence)fs.mkdirSync(evidence,{recursive:true});
const root=fs.mkdtempSync(path.join(evidence||os.tmpdir(),'aula-browser-assets-'));
const scratch=name=>path.join(root,name);
const cleanup=()=>fs.rmSync(root,{recursive:true,force:true});
if(!evidence)process.once('exit',cleanup);
module.exports={scratch,cleanup};
