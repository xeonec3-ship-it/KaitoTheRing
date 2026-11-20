// Видео-превью боссов T26–T28: покадровый рендер страницы превью (three.js) в Playwright → ffmpeg (H.264).
// Запуск — из tools/boss_video.py:  node tools/boss_video.js job.json
// job.json: { html, out, fps, w, h, frames: [ {actors:[...], cam:{...}, cap, sub, head, fade, flash} ] }
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: job.w, height: job.h }, deviceScaleFactor: 1 });
  const errs = [];
  pg.on('pageerror', e => errs.push(e.message));
  pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await pg.goto('file://' + job.html);
  await pg.waitForFunction('window.VID && typeof FxRun !== "undefined"', null, { timeout: 240000 });
  await pg.evaluate(() => VID.init());
  await pg.waitForTimeout(2500);                       // текстуры
  if (process.env.VID_DEBUG) console.log(await pg.evaluate(() => JSON.stringify({ cw: cv.width, ch: cv.height, cs: [cv.clientWidth, cv.clientHeight],
    st: [stage.clientWidth, stage.clientHeight], vp: renderer.getViewport(new THREE.Vector4()).toArray(), ar: cam.aspect })));
  const tmpOut = require('path').join(require('os').tmpdir(), 'boss_video_' + process.pid + '.mp4');   // в репозиторий — только готовый файл
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(job.fps), '-c:v', 'mjpeg', '-i', '-',
    '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', String(job.crf || 20), '-pix_fmt', 'yuv420p', '-r', String(job.fps),
    '-movflags', '+faststart', tmpOut], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise(r => ff.on('close', r));
  const t0 = Date.now();
  for (let i = 0; i < job.frames.length; i++) {
    await pg.evaluate(f => VID.render(f), job.frames[i]);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`  ${job.out.split('/').pop()}: ${i}/${job.frames.length} (${((Date.now() - t0) / 1000).toFixed(0)} с)`);
  }
  ff.stdin.end();
  const code = await done;
  if (!code) { fs.copyFileSync(tmpOut, job.out); fs.unlinkSync(tmpOut); }
  if (errs.length) console.log('page errors:', JSON.stringify(errs.slice(0, 5)));
  console.log(`  ${job.out.split('/').pop()}: ${job.frames.length} кадров, ffmpeg ${code}`);
  await b.close();
  process.exit(code ? 1 : 0);
})();
