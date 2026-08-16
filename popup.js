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
  const els = [];
  const seen = new Set();

  const push = (el, src, natural_w, natural_h, rect, kind) => {
    if (!src || src.startsWith('data:')) return;
    const key = src + '|' + Math.round(rect.width) + 'x' + Math.round(rect.height);
    if (seen.has(key)) return;
    seen.add(key);
    // `ref` is an index into els[], which stays in this isolated world for revealImage() to look up
    // later. Deliberately not a data-attribute on the element: writing to the page's DOM could trip
    // a framework's diffing or a MutationObserver, and we are a read-only audit tool.
    out.push({
      src,
      natural_w: natural_w || 0,
      natural_h: natural_h || 0,
      rendered_w: Math.round(rect.width),
      rendered_h: Math.round(rect.height),
      visible: rect.width > 0 && rect.height > 0,
      kind,
      ref: els.length,
    });
    els.push(el);
  };

  document.querySelectorAll('img').forEach((img) => {
    push(img, img.currentSrc || img.src, img.naturalWidth, img.naturalHeight, img.getBoundingClientRect(), 'img');
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
    bg.push({ el, src: new URL(match[1], location.href).href, rect });
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
    resolved.forEach((r) => push(r.el, r.src, r.w, r.h, r.rect, 'css'));
    window.__imgdimEls = els;
    return { url: location.href, title: document.title, dpr, images: out };
  });
}

/*
 * Also injected. Scrolls the clicked image into view and rings it for a couple of seconds.
 *
 * The ring is position:fixed and re-placed every frame rather than drawn once, because the scroll
 * is smooth and because sticky/fixed images move under the viewport rather than with the document.
 * Re-reading getBoundingClientRect each frame is the one approach that is correct for all three.
 *
 * Appended to documentElement, not body: an ancestor with a transform becomes the containing block
 * for position:fixed, and `body { transform }` is common enough to matter while `html { transform }`
 * is not. Nothing else about the page is touched, and the ring removes itself.
 */
function revealImage(ref, oversized) {
  const el = (window.__imgdimEls || [])[ref];
  // The isolated world is torn down on navigation, so a missing array means the page moved on.
  if (!window.__imgdimEls) return { ok: false, reason: 'stale' };
  if (!el || !el.isConnected) return { ok: false, reason: 'gone' };

  const first = el.getBoundingClientRect();
  if (!first.width || !first.height) return { ok: false, reason: 'hidden' };

  if (window.__imgdimClear) window.__imgdimClear();

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ block: 'center', inline: 'center', behavior: reduced ? 'auto' : 'smooth' });

  const line = oversized ? '#b45309' : '#2563eb';
  const glow = oversized ? 'rgba(180,83,9,.25)' : 'rgba(37,99,235,.25)';
  const ring = document.createElement('div');
  ring.style.cssText =
    'position:fixed;z-index:2147483647;pointer-events:none;border-radius:2px;' +
    `border:2px solid ${line};box-shadow:0 0 0 3px ${glow};` +
    `top:${first.top}px;left:${first.left}px;width:${first.width}px;height:${first.height}px;` +
    'transition:opacity 240ms ease-out;opacity:1';
  document.documentElement.appendChild(ring);

  let raf = 0;
  const clear = () => {
    cancelAnimationFrame(raf);
    ring.remove();
    window.__imgdimClear = null;
  };
  const place = (now, start = now) => {
    if (!el.isConnected) return clear();
    const r = el.getBoundingClientRect();
    ring.style.top = r.top + 'px';
    ring.style.left = r.left + 'px';
    ring.style.width = r.width + 'px';
    ring.style.height = r.height + 'px';
    if (now - start < 2400) raf = requestAnimationFrame((t) => place(t, start));
    else {
      ring.style.opacity = '0';
      setTimeout(clear, 280);
    }
  };
  window.__imgdimClear = clear;
  raf = requestAnimationFrame((t) => place(t));

  return { ok: true };
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

/* The subline doubles as the place we report a failed jump, so render() hands it over here. */
let subline = null;
let sublineText = '';
let sublineTimer = 0;

const CANT_REACH = {
  gone: 'That image has left the page. Press Re-check.',
  hidden: 'That image is hidden right now, so there is nothing to point at.',
  stale: 'The page has changed since this was measured. Press Re-check.',
};

function note(reason) {
  if (!subline) return;
  clearTimeout(sublineTimer);
  subline.textContent = CANT_REACH[reason] || CANT_REACH.gone;
  subline.classList.add('subline--note');
  sublineTimer = setTimeout(() => {
    subline.textContent = sublineText;
    subline.classList.remove('subline--note');
  }, 3200);
}

async function reveal(img) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return note('gone');
    const [res] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: revealImage,
      args: [img.ref, img.ratio > OVERSIZED_AT],
    });
    if (!res?.result?.ok) note(res?.result?.reason);
  } catch {
    note('stale');
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
  sub.textContent =
    (oversized.length
      ? `Measured against what your ${dpr}× display actually needs. Worst first.`
      : `Every measurable image suits your ${dpr}× display.`) +
    ' Click a row to jump to it on the page.';
  summary.append(headline, sub);
  subline = sub;
  sublineText = sub.textContent;
  clearTimeout(sublineTimer);

  const list = document.createElement('ul');
  list.className = 'list';

  measurable.slice(0, 60).forEach((img) => {
    const li = document.createElement('li');
    const row = document.createElement('button');
    row.type = 'button';
    row.className = 'row';
    row.title = 'Jump to this image on the page';
    row.addEventListener('click', () => reveal(img));

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

    row.append(thumb, meta, badge);
    li.append(row);
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
