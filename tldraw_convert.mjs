#!/usr/bin/env node
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

async function main() {
  const [inputPath, outputPath] = process.argv.slice(2);
  if (!inputPath || !outputPath) {
    console.error('Usage: tldraw_convert.mjs <input.tldr> <output.png>');
    process.exit(1);
  }

  let convert;
  try {
    ({ convert } = await import('@tldraw/tldraw'));
  } catch (error) {
    console.error('Unable to load @tldraw/tldraw. Run `npm install @tldraw/tldraw` inside the repository.');
    console.error(String(error));
    process.exit(2);
  }

  let file;
  try {
    const raw = await readFile(inputPath, 'utf8');
    file = JSON.parse(raw);
  } catch (error) {
    console.error(`Failed to read ${inputPath}:`, error);
    process.exit(3);
  }

  let result;
  try {
    result = await convert({
      file,
      format: 'png',
      // Ensure relative asset paths resolve correctly for embedded assets.
      assetBaseUrl: new URL('./', `file://${resolve(dirname(inputPath))}/`).href,
    });
  } catch (error) {
    console.error('tldraw convert() failed:', error);
    process.exit(4);
  }

  const base64 = extractBase64(result);
  if (!base64) {
    console.error('tldraw convert() succeeded but returned no PNG data.');
    process.exit(5);
  }

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, Buffer.from(base64, 'base64'));
}

function extractBase64(result) {
  if (!result || typeof result !== 'object') return null;
  const queue = [result];
  while (queue.length) {
    const value = queue.shift();
    if (!value) continue;
    if (typeof value === 'string') {
      const maybe = extractFromString(value);
      if (maybe) return maybe;
      continue;
    }
    if (value instanceof Array) {
      queue.push(...value);
      continue;
    }
    if (typeof value === 'object') {
      const maybe = extractFromObject(value);
      if (maybe) return maybe;
      queue.push(...Object.values(value));
    }
  }
  return null;
}

function extractFromString(value) {
  if (typeof value !== 'string') return null;
  if (value.startsWith('data:image/png')) {
    const [, payload] = value.split(',', 2);
    if (payload) return payload;
  }
  if (/^[A-Za-z0-9+/=]+$/.test(value) && value.length > 100) {
    return value;
  }
  return null;
}

function extractFromObject(obj) {
  if (!obj || typeof obj !== 'object') return null;
  for (const key of ['src', 'dataURL', 'dataUrl', 'base64']) {
    const value = obj[key];
    const fromStr = extractFromString(value);
    if (fromStr) return fromStr;
  }
  return null;
}

main().catch((error) => {
  console.error('Unexpected failure:', error);
  process.exit(99);
});
