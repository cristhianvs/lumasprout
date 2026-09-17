// Curated public demo: never copy telemetry exports, research PDFs or local context.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'dist');
fs.mkdirSync(path.join(out,'play'),{recursive:true});
for(const file of ['index.html','styles.css','usability.css','app.js','engine.js','admin.html','admin.css','admin.js','simulation.js'])fs.copyFileSync(path.join(root,file),path.join(out,'play',file));
for(const file of ['index.html','site.css'])fs.copyFileSync(path.join(root,'site',file),path.join(out,file));
fs.cpSync(path.join(root,'assets'),path.join(out,'assets'),{recursive:true});
fs.writeFileSync(path.join(out,'.nojekyll'),'');
console.log('Public demo built in dist/');
