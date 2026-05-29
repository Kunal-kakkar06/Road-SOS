import fs from 'fs';
import path from 'path';

const distPath = path.resolve('dist');
const assetsPath = path.resolve('dist/assets');

if (fs.existsSync(assetsPath)) {
  const files = fs.readdirSync(assetsPath);
  const assetUrls = files.map(file => `/assets/${file}`);
  assetUrls.push('/', '/index.html', '/favicon.svg');

  const swPath = path.resolve('dist/sw.js');
  if (fs.existsSync(swPath)) {
    let swContent = fs.readFileSync(swPath, 'utf8');
    const replaceTarget = "c.addAll(['/', '/index.html'])";
    const replacement = `c.addAll(${JSON.stringify(assetUrls)})`;
    swContent = swContent.replace(replaceTarget, replacement);
    fs.writeFileSync(swPath, swContent, 'utf8');
    console.log('[PWA Build] Injected assets into sw.js:', assetUrls);
  }
}
