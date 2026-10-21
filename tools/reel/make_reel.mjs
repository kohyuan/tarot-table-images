#!/usr/bin/env node
// タロットテーブル リール（本物の動画）を1本作る。
//
// 使い方（リポジトリの根から）:
//   node tools/reel/make_reel.mjs --params reel.json --out reels/R0001.mp4
//
// reel.json の形（表 reels_post の1行分）:
//   {
//     "post_id": "R0001",
//     "headline": "明日からの7日間 10/23(金)~10/29(木)のお金・買い物",   // I列
//     "question": "お金の出入りや買い物は、この7日間でどう動きやすいでしょう。", // J列
//     "cards": [                                                         // G列・H列の左・中・右
//       { "id": "S02", "pos": "U", "keyword": "迷い", "reading": "…" },     // keyword と reading は無くてもよい（出さない）
//       { "id": "M17", "pos": "U" },
//       { "id": "S09", "pos": "R" }
//     ]
//   }
//
// カードの絵は、リポジトリの cards/<card_id>.jpg（.png・.webp も可）。無いカードは仮の表面で出す。
// 音は tools/reel/audio/<正逆3文字>.m4a（例：UUR.m4a）を重ねる。
// 出来上がり：MP4（H.264・AAC）、1080x1920、30fps、33.3秒。書き出したあと条件を自分で確かめ、外れていればエラーで止まる。
import fs from 'fs'; import path from 'path'; import http from 'http'; import os from 'os';
import { spawn, execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const die = m => { console.error('✗ ' + m); process.exit(1); };

const paramsPath = opt('--params'); const out = opt('--out');
if (!paramsPath || !out) die('使い方: node tools/reel/make_reel.mjs --params reel.json --out reels/R0001.mp4');
const FPS = +opt('--fps', 30), WK = +opt('--workers', Math.max(1, Math.min(3, os.cpus().length))), W = 1080, H = 1920;
const P = JSON.parse(fs.readFileSync(paramsPath, 'utf8'));

// —— 中身の確かめ ——
if (!P.headline || !P.question) die('headline と question が必要です');
if (!Array.isArray(P.cards) || P.cards.length !== 3) die('cards は左・中・右の3枚が必要です');
const ID = /^(M(0\d|1\d|2[01])|[WCSP](0[1-9]|1[0-4]))$/;
P.cards.forEach((c, i) => { if (!ID.test(c.id)) die(`cards[${i}].id「${c.id}」は card_id の形ではありません`); if (!/^[UR]$/.test(c.pos)) die(`cards[${i}].pos は U か R`); });
if (new Set(P.cards.map(c => c.id)).size !== 3) die('3枚は別のカードにしてください');

// —— カードの絵 ——
const CARD_DIR = path.join(ROOT, 'cards');
const artOf = id => { for (const ext of ['jpg', 'png', 'webp', 'jpeg']) { const f = path.join(CARD_DIR, `${id}.${ext}`); if (fs.existsSync(f)) return `/cards/${id}.${ext}`; } return null; };
P.cards.forEach(c => { c.art = artOf(c.id); });
const allArts = fs.existsSync(CARD_DIR) ? fs.readdirSync(CARD_DIR).filter(f => /^[MWCSP]\d\d\.(jpg|jpeg|png|webp)$/.test(f)).sort() : [];
P.ribbon = allArts.map(f => ({ id: f.slice(0, 3), art: `/cards/${f}` }));
const audio = path.join(HERE, 'audio', P.cards.map(c => c.pos).join('') + '.m4a');
if (!fs.existsSync(audio)) die('音のファイルがありません: ' + audio);

// —— ブラウザ（headless Chrome）——
let chromium;
try { ({ chromium } = await import('playwright-core')); } catch { die('playwright-core がありません。tools/reel で npm install を実行してください'); }
function findChrome() {
  if (process.env.PLAYWRIGHT_CHROME) return process.env.PLAYWRIGHT_CHROME;
  for (const base of ['/opt/pw-browsers', path.join(os.homedir(), '.cache/ms-playwright')]) {
    if (!fs.existsSync(base)) continue;
    for (const d of fs.readdirSync(base).sort().reverse()) {
      for (const rel of ['chrome-linux/headless_shell', 'chrome-headless-shell-linux64/chrome-headless-shell', 'chrome-linux/chrome', 'chrome-linux64/chrome']) {
        const f = path.join(base, d, rel); if (fs.existsSync(f)) return f;
      }
    }
  }
  return undefined;   // playwright の既定に任せる
}
const EXE = findChrome();

// —— 小さなファイル配信（リポジトリの根を配る。params.js だけはこの1本の中身を返す）——
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.woff2': 'font/woff2', '.woff': 'font/woff' };
const PARAMS_JS = 'window.PARAMS = ' + JSON.stringify(P) + ';';
const server = http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split('?')[0]);
  if (u === '/tools/reel/page/params.js') { r.writeHead(200, { 'Content-Type': TYPES['.js'] }); return r.end(PARAMS_JS); }
  const f = path.resolve(ROOT, '.' + u);
  if (!f.startsWith(ROOT + path.sep)) { r.writeHead(403); return r.end(); }
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream' }); r.end(d); });
}).listen(0, '127.0.0.1');
await new Promise(r => server.on('listening', r));
const URL_ = `http://127.0.0.1:${server.address().port}/tools/reel/page/index.html`;

const tmp = fs.mkdtempSync(path.join(HERE, '.render-'));
const cleanup = () => { try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {} server.close(); };
process.on('exit', cleanup);

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto(URL_);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 }).catch(() => die('画面の準備が終わりません: ' + errs.join(' / ')));
  if (errs.length) die('画面のエラー: ' + errs.join(' / '));
  return page;
}

const t0 = Date.now();
const browser = await chromium.launch({ executablePath: EXE, args: ['--font-render-hinting=none', '--disable-gpu'] });
const probe = await openPage(browser);
const DUR = await probe.evaluate(() => window.DUR);
const fitInfo = await probe.evaluate(() => window.CHECK());
await probe.close();
const TOTAL = Math.round(DUR * FPS), per = Math.ceil(TOTAL / WK);
console.log(`${P.post_id || ''}: ${DUR}秒 ${TOTAL}コマ を ${WK} 本で書き出し（絵：${P.cards.map(c => c.id + (c.art ? '' : '（仮）')).join(' / ')}）`);

await Promise.all([...Array(WK)].map(async (_, w) => {
  const a = w * per, b = Math.min(TOTAL, a + per); if (a >= b) return;
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS), path.join(tmp, `seg_${w}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
  const closed = new Promise(r => ff.on('close', r));
  for (let f = a; f < b; f++) {
    await page.evaluate(t => window.render(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); if ((await closed) !== 0) die(`書き出し ${w} が失敗しました`);
  await page.close();
}));
await browser.close();

// —— つなぐ → 音を重ねる ——
const list = path.join(tmp, 'list.txt');
fs.writeFileSync(list, [...Array(WK)].map((_, w) => path.join(tmp, `seg_${w}.mp4`)).filter(f => fs.existsSync(f)).map(f => `file '${f}'`).join('\n'));
const video = path.join(tmp, 'video.mp4');
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', video]);
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-i', audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', path.resolve(out)]);

// —— 条件を確かめる（MP4・H.264・AAC・1080x1920・3〜90秒・音声あり）——
const info = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height:format=duration', '-of', 'json', path.resolve(out)]).toString());
const v = info.streams.find(s => s.codec_type === 'video'), au = info.streams.find(s => s.codec_type === 'audio'), d = +info.format.duration;
const bad = [];
if (!v || v.codec_name !== 'h264') bad.push('映像が H.264 ではない');
if (!v || v.width !== W || v.height !== H) bad.push('大きさが 1080x1920 ではない');
if (!au || au.codec_name !== 'aac') bad.push('音声（AAC）が無い');
if (!(d >= 3 && d <= 90)) bad.push(`長さ ${d} 秒が 3〜90 秒に入らない`);
if (fitInfo.q > 270) bad.push('問いが長すぎて枠に収まらない');
fitInfo.reads.forEach((h, i) => { if (h > 230) bad.push(`${['左', '中', '右'][i]}の読みが長すぎて枠に収まらない`); });
if (bad.length) die(bad.join(' / '));
console.log(`✓ ${out}（${d.toFixed(1)}秒、${(fs.statSync(out).size / 1e6).toFixed(1)}MB、${((Date.now() - t0) / 1000).toFixed(0)}秒で作成）`);
process.exit(0);
