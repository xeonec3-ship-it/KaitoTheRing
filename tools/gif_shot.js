const { chromium } = require('playwright');
// Кадры для гифок из tools/sigil_preview.html (собрать превью: python3 tools/build_sigil_preview.py).
// Склейка: ffmpeg -framerate 15 -i out/f%04d.png -vf "scale=480:-1,split[a][b];[a]palettegen[p];[b][p]paletteuse" x.gif
// node gif_shot.js page.html outDir "Scene" view seconds fps — steps preview time by hand, so frames are exact
(async () => {
  const [,, file, out, scene, view, secS, fpsS, orbitS] = process.argv;
  const orbit = +(orbitS || 0);
  const secs = +secS, fps = +fpsS;
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 760, height: 700 }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + file); await p.waitForTimeout(400);
  await p.evaluate(({ scene, view }) => { const s = document.querySelector('#scene'); s.value = scene; s.dispatchEvent(new Event('change'));
    document.querySelectorAll('[data-view="' + view + '"]').forEach(b => b.click()); document.querySelector('#play').click(); speed = 0; t = 0;
    if (view.includes(',')) { [yaw, pitch, dist, tgtY] = view.split(',').map(Number); } }, { scene, view });
  const n = Math.round(secs * fps);
  for (let i = 0; i < n; i++) {
    const restarted = await p.evaluate(([fps, orbit]) => new Promise((res) => {
      const D = TPS / fps, k = 4;
      let r = false;
      for (let j = 0; j < k; j++) { t += D / k; INST.forEach((s) => s.update(t, D / k)); if (INST.length && INST.every((s) => s.done(t))) { r = true; } }
      yaw += orbit / fps;
      requestAnimationFrame(() => requestAnimationFrame(() => res(r)));
    }), [fps, orbit]);
    if (restarted) { console.log('cycle ends at frame', i); break; }
    await p.locator('#stage').screenshot({ path: `${out}/f${String(i).padStart(4, '0')}.png` });
  }
  console.log('frames', n, 'time', await p.evaluate(() => document.querySelector('#time').textContent), 'errors', JSON.stringify(errs));
  await b.close();
})();
