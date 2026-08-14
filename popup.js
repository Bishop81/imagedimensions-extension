/*
 * ImageDimensions popup.
 *
 * Why this exists as an extension at all: the hosted scanner loads a page in a headless browser,
 * which cannot reach anything behind a login, behind bot protection, or on localhost — and about
 * 10% of scans fail silently for exactly those reasons. This measures the page you are already
 * looking at, as you are seeing it.
 *
 * Oversized shares the site's shape — AREA overshoot, threshold 4 — but is measured against what
 * the real display needs rather than raw CSS pixels. See the note on `overshoot()` below for why
 * that differs from mcp-server/src/analyze.js, and why the difference is a fix rather than a drift.
 */

const OVERSIZED_AT = 4;
const SITE = 'https://imagedimensions.com';

const view = document.getElementById('view');
const hostEl = document.getElementById('host');
const recheckBtn = document.getElementById('recheck');

/* ---------------------------------------------------------------------------
 * Injected into the page. Must be entirely self-contained: it is serialised
 * across the process boundary, so it can close over nothing.
 * ------------------------------------------------------------------------- */
function measurePage() {
  const out = [];
  const seen = new Set();

  const push = (src, natural_w, natural_h, rect, kind) => {
    if (!src || src.startsWith('data:')) return;
    const key = src + '|' + Math.round(rect.width) + 'x' + Math.round(rect.height);
    if (seen.has(key)) return;
    seen.add(key);
    out.push({
      src,
      natural_w: natural_w || 0,
      natural_h: natural_h || 0,
      rendered_w: Math.round(rect.width),
      rendered_h: Math.round(rect.height),
      visible: rect.width > 0 && rect.height > 0,
      kind,
    });
  };

  document.querySelectorAll('img').forEach((img) => {
    push(img.currentSrc || img.src, img.naturalWidth, img.naturalHeight, img.getBoundingClientRect(), 'img');
  });

  // CSS backgrounds are ~20% of images on a typical page and most audits miss them entirely.
  // Their intrinsic size has to be loaded separately, so it is filled in asynchronously below.
  const bg = [];
  document.querySelectorAll('*').forEach((el) => {
    const value = getComputedStyle(el).backgroundImage;
    if (!value || value === 'none') return;
    const match = /url\(["']?(.*?)["']?\)/.exec(value);
    if (!match || !match[1] || match[1].startsWith('data:')) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return;
    bg.push({ src: new URL(match[1], location.href).href, rect });
  });

  const dpr = window.devicePixelRatio || 1;

  return Promise.all(
    bg.slice(0, 60).map(
      (b) =>
        new Promise((resolve) => {
          const probe = new Image();
          const done = () => resolve({ ...b, w: probe.naturalWidth, h: probe.naturalHeight });
          probe.onload = done;
          probe.onerror = () => resolve({ ...b, w: 0, h: 0 });
          probe.src = b.src;
          setTimeout(done, 2500);
        }),
    ),
  ).then((resolved) => {
    resolved.forEach((r) => push(r.src, r.w, r.h, r.rect, 'css'));
    return { url: location.href, title: document.title, dpr, images: out };
  });
}

/* ------------------------------------------------------------------------ */

/*
 * Overshoot measured against what THIS display actually needs, not against CSS pixels.
 *
 * The hosted scanner runs headless at devicePixelRatio 1, so it can only compare natural area to
 * rendered CSS area — which means a 400x400 file shown in a 200x200 slot reads as exactly 4x, even
 * though on a 2x screen that is textbook-correct retina serving.
 * Running in a real browser we know the actual DPR, so we compare against the pixels the display
 * genuinely wants. Same image now reads 1.0x on a retina screen and 4.0x on a 1x screen, and both
 * are true.
 *
 * This is deliberately BETTER than site/mcp-server behaviour rather than merely consistent with it.
 * Writing it exposed an off-by-one at exactly 4.0 in those, since fixed (2026-08-14): everything now
 * uses a strict `> 4`, matching the OVERSIZED_AT comparison here.
 */
const overshoot = (i, dpr) =>
  i.natural_w && i.natural_h && i.rendered_w && i.rendered_h
    ? (i.natural_w * i.natural_h) / (i.rendered_w * dpr * i.rendered_h * dpr)
    : null;

function fileName(src) {
  try {
    const path = new URL(src).pathname;
    return decodeURIComponent(path.slice(path.lastIndexOf('/') + 1)) || src;
  } catch {
    return src;
  }
}

function state(strong, detail) {
  view.innerHTML = '';
  const p = document.createElement('p');
  p.className = 'state';
  const s = document.createElement('strong');
  s.textContent = strong;
  p.append(s, document.createTextNode(detail));
  view.append(p);
}

function render(data) {
  const dpr = data.dpr || 1;
  const measurable = data.images
    .filter((i) => i.visible && overshoot(i, dpr) !== null)
    .map((i) => ({ ...i, ratio: overshoot(i, dpr) }))
    .sort((a, b) => b.ratio - a.ratio);

  if (data.images.length === 0) {
    state('No images on this page', 'Nothing to measure here. Try a page with photos or graphics.');
    return;
  }

  if (measurable.length === 0) {
    state(
      'Images found, but none measurable',
      'They may still be loading, or be hidden. Let the page finish and re-check.',
    );
    return;
  }

  const oversized = measurable.filter((i) => i.ratio > OVERSIZED_AT);
  view.innerHTML = '';

  const summary = document.createElement('div');
  summary.className = 'summary';
  const headline = document.createElement('p');
  headline.className = 'headline ' + (oversized.length ? 'headline--warn' : 'headline--ok');
  headline.innerHTML = oversized.length
    ? `<strong>${oversized.length} of ${measurable.length} images are oversized</strong>`
    : `<strong>All ${measurable.length} images are sized well</strong>`;
  const sub = document.createElement('p');
  sub.className = 'subline';
  sub.textContent = oversized.length
    ? `Measured against what your ${dpr}× display actually needs. Worst first.`
    : `Every measurable image suits your ${dpr}× display.`;
  summary.append(headline, sub);

  const list = document.createElement('ul');
  list.className = 'list';

  measurable.slice(0, 60).forEach((img) => {
    const li = document.createElement('li');
    li.className = 'row';

    const thumb = document.createElement('img');
    thumb.className = 'thumb';
    thumb.src = img.src;
    thumb.alt = '';
    thumb.loading = 'lazy';
    thumb.onerror = () => {
      thumb.style.visibility = 'hidden';
    };

    const meta = document.createElement('div');
    meta.className = 'meta';
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = fileName(img.src);
    name.title = img.src;
    const sizes = document.createElement('span');
    sizes.className = 'sizes';
    sizes.innerHTML =
      `${img.natural_w}×${img.natural_h}` +
      `<span class="arrow">→</span>` +
      `${img.rendered_w}×${img.rendered_h}`;
    meta.append(name, sizes);

    const badge = document.createElement('span');
    const over = img.ratio > OVERSIZED_AT;
    badge.className = 'badge' + (over ? '' : ' badge--ok');
    badge.textContent = `${img.ratio < 10 ? img.ratio.toFixed(1) : Math.round(img.ratio)}×`;
    badge.title = over
      ? 'Pixels downloaded versus pixels displayed'
      : 'Within a sensible retina allowance';

    li.append(thumb, meta, badge);
    list.append(li);
  });

  view.append(summary, list);
}

async function run() {
  recheckBtn.disabled = true;
  state('Measuring images…', '');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error('no-tab');

    try {
      hostEl.textContent = new URL(tab.url).hostname;
    } catch {
      hostEl.textContent = '';
    }

    // Chrome refuses injection into its own pages and the Web Store. Say so plainly rather
    // than showing an empty result that looks like a bug.
    if (/^(chrome|edge|about|devtools|view-source):/.test(tab.url || '') ||
        /^https:\/\/chromewebstore\.google\.com/.test(tab.url || '')) {
      state('Browser pages can’t be measured', 'Open a normal web page and try again.');
      return;
    }

    const [result] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: measurePage,
    });

    if (!result?.result) throw new Error('no-result');
    render(result.result);
  } catch {
    state('Couldn’t read this page', 'Reload the page, then open this again.');
  } finally {
    recheckBtn.disabled = false;
  }
}

recheckBtn.addEventListener('click', run);
document.getElementById('site-link').href = `${SITE}/?utm_source=chrome-extension`;
run();
