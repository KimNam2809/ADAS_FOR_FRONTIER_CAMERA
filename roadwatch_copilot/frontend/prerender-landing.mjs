import { readFile, writeFile } from 'node:fs/promises';
import { render } from './.landing-ssr/landing-prerender.js';

const target = new URL('./dist-landing/landing.html', import.meta.url);
const shell = await readFile(target, 'utf8');
if (!shell.includes('<div id="root"></div>')) throw new Error('Unexpected landing shell');
const html = shell.replace('<div id="root"></div>', `<div id="root">${render()}</div>`);
await writeFile(target, html);
await writeFile(new URL('./dist-landing/index.html', import.meta.url), html);
console.log('Prerendered landing content; no inference server required.');
