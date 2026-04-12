#!/usr/bin/env node
/**
 * Capture carousel slides as JPEGs via Playwright.
 *
 *   node scripts/export-slides.js --validate <carousel-dir>
 *   node scripts/export-slides.js --export --confirm <carousel-dir>
 *
 * --validate → slide-01-preview.jpg (does not write slide-XX.jpg)
 * --export    → slide-01.jpg … only runs with --confirm (after user approves)
 */

const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const WIDTH = 768;
const HEIGHT = 1376;
const JPEG_QUALITY = 92;

function printUsage() {
  console.error(`Usage:
  node scripts/export-slides.js --validate <carousel-folder>
  node scripts/export-slides.js --export --confirm <carousel-folder>

  --export requires --confirm so final JPGs are only written after explicit approval.`);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  let mode = null;
  let exportConfirmed = false;
  const rest = [];
  for (const a of args) {
    if (a === '--validate') mode = 'validate';
    else if (a === '--export') mode = 'export';
    else if (a === '--confirm') exportConfirmed = true;
    else if (a === '--help' || a === '-h') mode = 'help';
    else if (!a.startsWith('-')) rest.push(a);
  }
  return { mode, exportConfirmed, carouselDir: rest[0] };
}

function listSlideHtmls(dir) {
  const files = fs.readdirSync(dir);
  return files
    .filter((f) => /^slide-\d+\.html$/i.test(f))
    .sort((a, b) => {
      const na = parseInt(a.match(/slide-(\d+)/i)[1], 10);
      const nb = parseInt(b.match(/slide-(\d+)/i)[1], 10);
      return na - nb;
    });
}

async function main() {
  const { mode, exportConfirmed, carouselDir: rawDir } = parseArgs(
    process.argv
  );

  if (mode === 'help' || !mode) {
    printUsage();
    process.exit(mode === 'help' ? 0 : 1);
  }

  if (!rawDir) {
    console.error('Error: missing carousel folder path.');
    printUsage();
    process.exit(1);
  }

  if (mode !== 'validate' && mode !== 'export') {
    printUsage();
    process.exit(1);
  }

  if (mode === 'export' && !exportConfirmed) {
    console.error(
      'Export aborted: writing slide-XX.jpg requires explicit user approval.'
    );
    console.error(
      'After the user confirms, run: node scripts/export-slides.js --export --confirm <carousel-folder>'
    );
    process.exit(1);
  }

  const carouselDir = path.resolve(process.cwd(), rawDir);
  if (!fs.existsSync(carouselDir) || !fs.statSync(carouselDir).isDirectory()) {
    console.error(`Error: not a directory: ${carouselDir}`);
    process.exit(1);
  }

  const slides = listSlideHtmls(carouselDir);
  if (slides.length === 0) {
    console.error(`Error: no slide-NN.html files in ${carouselDir}`);
    process.exit(1);
  }

  let chromium;
  try {
    ({ chromium } = require('playwright'));
  } catch (e) {
    console.error(
      'Error: playwright is not installed. Run: npm install playwright && npx playwright install chromium'
    );
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  try {
    for (const file of slides) {
      const filePath = path.join(carouselDir, file);
      const url = pathToFileURL(filePath).href;
      await page.goto(url, { waitUntil: 'load', timeout: 60_000 });

      const base = path.basename(file, path.extname(file));
      const outName =
        mode === 'validate' ? `${base}-preview.jpg` : `${base}.jpg`;
      const outPath = path.join(carouselDir, outName);

      await page.screenshot({
        path: outPath,
        type: 'jpeg',
        quality: JPEG_QUALITY,
      });

      console.log('Wrote', outPath);
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
