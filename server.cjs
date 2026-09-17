const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const allowed = new Set(['index.html', 'styles.css', 'usability.css', 'engine.js', 'app.js', 'admin.html', 'admin.css', 'admin.js', 'simulation.js']);
http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
  if (!allowed.has(name)) { res.writeHead(404); return res.end('No encontrado'); }
  res.setHeader('Content-Type', {html:'text/html; charset=utf-8',css:'text/css',js:'text/javascript'}[path.extname(name).slice(1)]);
  res.setHeader('Cache-Control', 'no-store');
  fs.createReadStream(path.join(root, name)).pipe(res);
}).listen(4173, '127.0.0.1', () => console.log('Isla Luma: http://127.0.0.1:4173'));
