const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const shots = JSON.parse(fs.readFileSync(process.argv[2]));
  const outDir = process.argv[3];
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  p.on('console', m => { if (m.type() === 'error') console.log('ERR', m.text()); });
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  await p.goto('http://localhost:8123/view.html');
  await p.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
  for (const s of shots) {
    const t = Date.now();
    await p.evaluate(c => window.frame(c), s);
    await p.locator('canvas').screenshot({ path: outDir + '/' + s.name + '.png' });
    console.log(s.name, Date.now() - t, 'ms');
  }
  await b.close();
})();
