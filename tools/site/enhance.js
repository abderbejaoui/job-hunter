/* The layer on top: a three.js field of CV sheets behind the hero, and Motion
   springs on the things a pointer touches.

   Everything here is optional. The page is complete without it - app.js does
   the typing, the arrivals and the picker - so this module only ever adds.
   It stands down on reduced motion, on a machine with no WebGL, and if either
   CDN fails to load, and in every one of those cases the page is exactly the
   page it was before this file existed.

   Motion is Framer Motion's engine without React (same authors, `motion` on
   npm). This page is generated HTML, not a React app, so that is the version
   that fits. */

const MOTION = "https://cdn.jsdelivr.net/npm/motion@11.11.13/+esm";
const THREE = "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.min.js";

const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const fine = window.matchMedia("(pointer: fine)").matches;

if (!still) {
  motionLayer().catch(() => {});
  whenIdle(() => sheets().catch(() => {}));
}

function whenIdle(run) {
  const go = () => ("requestIdleCallback" in window
    ? requestIdleCallback(run, { timeout: 1500 }) : setTimeout(run, 300));
  if (document.readyState === "complete") go();
  else window.addEventListener("load", go, { once: true });
}

// --- Motion -----------------------------------------------------------------

async function motionLayer() {
  const { animate, inView, spring } = await import(MOTION);
  const soft = { type: spring, stiffness: 170, damping: 18, mass: 0.9 };
  const snappy = { type: spring, stiffness: 420, damping: 26 };

  // The hero lifts away as the page scrolls past it. The children carry the
  // CSS arrival transforms, so this moves their wrapper and never them.
  //
  // A plain scroll listener, not Motion's `scroll()`. That one is driven from
  // requestAnimationFrame, and a throttled frame loop (a background tab, a
  // headless check) leaves it frozen at 0 while the page has scrolled - the
  // same trap app.js removed rAF to escape.
  const field = document.querySelector(".field");
  const hero = document.querySelector(".hero");
  if (field && hero) {
    const lift = () => {
      const p = Math.min(1, Math.max(0, window.scrollY / field.offsetHeight));
      hero.style.opacity = String(1 - p * 0.9);
      hero.style.translate = "0 " + (-90 * p).toFixed(1) + "px";
    };
    window.addEventListener("scroll", lift, { passive: true });
    lift();
  }

  // The two CVs lean toward the pointer. Tilt only where there is a real
  // pointer: on a phone this would fire on scroll-touches and read as jitter.
  if (fine) {
    for (const card of document.querySelectorAll(".cv")) {
      card.style.transformStyle = "preserve-3d";
      card.addEventListener("pointermove", (ev) => {
        const box = card.getBoundingClientRect();
        const px = (ev.clientX - box.left) / box.width - 0.5;
        const py = (ev.clientY - box.top) / box.height - 0.5;
        animate(card, { rotateY: px * 9, rotateX: -py * 7,
                        transformPerspective: 900 }, soft);
      });
      card.addEventListener("pointerleave", () =>
        animate(card, { rotateX: 0, rotateY: 0 }, soft));
    }

    // Buttons lean after the pointer a little, and give when pressed.
    for (const btn of document.querySelectorAll(".btn")) {
      btn.addEventListener("pointermove", (ev) => {
        const box = btn.getBoundingClientRect();
        animate(btn, { x: (ev.clientX - box.left - box.width / 2) * 0.22,
                       y: (ev.clientY - box.top - box.height / 2) * 0.3 }, snappy);
      });
      btn.addEventListener("pointerleave", () =>
        animate(btn, { x: 0, y: 0, scale: 1 }, snappy));
      btn.addEventListener("pointerdown", () => animate(btn, { scale: 0.95 }, snappy));
      btn.addEventListener("pointerup", () => animate(btn, { scale: 1 }, snappy));
    }

    for (const chip of document.querySelectorAll(".board")) {
      chip.addEventListener("pointerenter", () =>
        animate(chip, { y: -4, scale: 1.05 }, snappy));
      chip.addEventListener("pointerleave", () =>
        animate(chip, { y: 0, scale: 1 }, snappy));
    }
  }

  // The tailored CV arrives with a little overshoot - the one card on the
  // page that is supposed to feel like it landed.
  inView(".cv.best", (card) => {
    animate(card, { scale: [0.94, 1], y: [18, 0] },
            { type: spring, stiffness: 260, damping: 15 });
  }, { amount: 0.4 });
}

// --- three.js: the same CV, over and over ------------------------------------

async function sheets() {
  const field = document.querySelector(".field");
  if (!field || !webgl()) return;
  const T = await import(THREE);

  const canvas = document.createElement("canvas");
  canvas.className = "sheets";
  canvas.setAttribute("aria-hidden", "true");
  field.prepend(canvas);

  const renderer = new T.WebGLRenderer({ canvas, alpha: true, antialias: true,
                                         powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setClearColor(0x000000, 0);

  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(42, 1, 0.1, 60);
  camera.position.set(0, 0, 9);

  // Every sheet is the same CV. That is the point being made.
  const map = new T.CanvasTexture(page());
  map.colorSpace = T.SRGBColorSpace;
  map.anisotropy = 4;
  const material = new T.MeshBasicMaterial({
    map, transparent: true, opacity: 0.16, side: T.DoubleSide, depthWrite: false,
  });
  const small = window.innerWidth < 760;
  const count = small ? 26 : 56;
  const mesh = new T.InstancedMesh(new T.PlaneGeometry(0.78, 1.1), material, count);
  scene.add(mesh);

  // Kept out of a band down the middle, where the headline is. A sheet
  // floating behind the words is a sheet making them harder to read.
  //
  // The band is measured on screen, not in the world: with perspective, a
  // sheet at x = 3 is well clear of the words up close and dead behind them
  // twenty units back. So x is picked as a share of the half-width visible at
  // the sheet's own depth - between 55% and 95% of the way out, either side.
  // The headline itself reaches about 47%, and a close sheet is wide.
  const green = new T.Color(0x0d5238);
  const white = new T.Color(0xffffff);
  const halfWidthPerUnit = Math.tan((42 / 2) * Math.PI / 180) *
                           (field.clientWidth / field.clientHeight);
  const drift = [];
  for (let i = 0; i < count; i++) {
    const z = -Math.random() * 14 + 2;
    const out = (0.55 + Math.random() * 0.4) * (9 - z) * halfWidthPerUnit;
    const x = (i % 2 ? 1 : -1) * out;
    drift.push({
      x, y: (Math.random() - 0.5) * 9, z,
      rx: Math.random() * 0.8 - 0.4, ry: Math.random() * 1.2 - 0.6,
      rz: Math.random() * 0.6 - 0.3,
      speed: 0.12 + Math.random() * 0.22, spin: (Math.random() - 0.5) * 0.25,
      phase: Math.random() * Math.PI * 2,
    });
    // Far sheets sink into the field colour rather than fading to grey.
    mesh.setColorAt(i, white.clone().lerp(green, Math.min(1, (2 - z) / 16)));
  }
  mesh.instanceColor.needsUpdate = true;

  const size = () => {
    const w = field.clientWidth, h = field.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(size).observe(field);
  size();

  // Follow the pointer, and push forward as the field scrolls away.
  const aim = { x: 0, y: 0 };
  window.addEventListener("pointermove", (ev) => {
    aim.x = (ev.clientX / window.innerWidth - 0.5) * 1.2;
    aim.y = -(ev.clientY / window.innerHeight - 0.5) * 0.8;
  }, { passive: true });

  // Only while the field is on screen and the tab is visible. A WebGL loop
  // left running under the rest of the page is a laptop fan for nothing.
  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(field);

  const dummy = new T.Object3D();
  const clock = new T.Clock();
  canvas.classList.add("on");

  renderer.setAnimationLoop(() => {
    if (!visible || document.hidden) return;
    const t = clock.getElapsedTime();
    const through = Math.min(1, Math.max(0, -field.getBoundingClientRect().top /
                                                 field.clientHeight));
    camera.position.x += (aim.x - camera.position.x) * 0.04;
    camera.position.y += (aim.y - camera.position.y) * 0.04;
    camera.position.z = 9 - through * 3.5;
    camera.lookAt(0, 0, -3);

    for (let i = 0; i < count; i++) {
      const s = drift[i];
      // Rise, and wrap back to the bottom: the stream never runs out.
      const y = ((s.y + t * s.speed + 4.5) % 9 + 9) % 9 - 4.5;
      dummy.position.set(s.x + Math.sin(t * 0.3 + s.phase) * 0.25, y, s.z);
      dummy.rotation.set(s.rx + Math.sin(t * 0.4 + s.phase) * 0.15,
                         s.ry + t * s.spin, s.rz);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
    renderer.render(scene, camera);
  });
}

function webgl() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch (e) {
    return false;
  }
}

/* One CV page, drawn once: a name bar, a contact line, and three sections of
   text lines. Abstract on purpose - legible text at this size and opacity
   would just be noise the eye tries to read. */
function page() {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 362;
  const g = c.getContext("2d");
  g.fillStyle = "#ffffff";
  g.beginPath();
  g.roundRect(0, 0, 256, 362, 10);
  g.fill();
  g.fillStyle = "#1c3a2e";
  g.fillRect(22, 26, 120, 14);
  g.fillStyle = "#8fa39a";
  g.fillRect(22, 48, 168, 5);
  let y = 76;
  for (let s = 0; s < 3; s++) {
    g.fillStyle = "#3f7d62";
    g.fillRect(22, y, 64, 6);
    y += 16;
    g.fillStyle = "#b5c2bc";
    for (let l = 0; l < 5; l++) {
      g.fillRect(22, y, 212 - ((l * 37) % 70), 4);
      y += 12;
    }
    y += 14;
  }
  return c;
}
