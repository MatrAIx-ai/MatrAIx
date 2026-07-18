/**
 * NASA-panel holographic Earth: shaded globe + land point-cloud + soft aura.
 * Two palettes: muted slate-blue on dark, ink-on-paper on light.
 */
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useIsLightTheme } from "../../hooks/useIsLightTheme";

/**
 * Cloudless Blue Marble: land/ocean split by color, so lowland plains
 * (Amazon basin, Ganges plain, …) are kept — unlike an elevation map.
 */
const EARTH_URL = "/earth/day.jpg";

/** Same axes as the land point-cloud: north up, negative z so east is right. */
function latLonToVec3(latDeg: number, lonDeg: number): THREE.Vector3 {
  const lat = (latDeg * Math.PI) / 180;
  const lon = (lonDeg * Math.PI) / 180;
  const cl = Math.cos(lat);
  return new THREE.Vector3(
    cl * Math.cos(lon),
    Math.sin(lat),
    -cl * Math.sin(lon),
  );
}

/** Global AI / innovation hub cities: [lat, lon]. */
const CITIES: Record<string, [number, number]> = {
  sanFrancisco: [37.77, -122.42], // Bay Area — OpenAI, Anthropic, Google
  seattle: [47.61, -122.33], // Microsoft, AWS
  toronto: [43.65, -79.38], // Vector Institute
  newYork: [40.71, -74.01],
  london: [51.51, -0.13], // DeepMind
  paris: [48.86, 2.35], // Mistral
  telAviv: [32.09, 34.78],
  bangalore: [12.97, 77.59],
  singapore: [1.35, 103.82],
  shenzhen: [22.54, 114.06],
  beijing: [39.9, 116.41],
  seoul: [37.57, 126.98],
  tokyo: [35.68, 139.69],
};

/** Innovation corridor: a ring linking the hubs around the globe. */
const CITY_LINKS: Array<[keyof typeof CITIES, keyof typeof CITIES]> = [
  ["seattle", "sanFrancisco"],
  ["sanFrancisco", "newYork"],
  ["toronto", "newYork"],
  ["newYork", "london"],
  ["london", "paris"],
  ["paris", "telAviv"],
  ["telAviv", "bangalore"],
  ["bangalore", "singapore"],
  ["singapore", "shenzhen"],
  ["shenzhen", "beijing"],
  ["beijing", "seoul"],
  ["seoul", "tokyo"],
  ["tokyo", "sanFrancisco"],
];

interface GlobePalette {
  coreDeep: number;
  coreMid: number;
  coreLit: number;
  atmosColor: number;
  atmosStrength: number;
  landColor: number;
  landOpacity: number;
  latticeColor: number;
  latticeOpacity: number;
  markerColor: number;
  markerHaloColor: number;
  markerHaloOpacity: number;
  arcColor: number;
  arcOpacity: number;
  ringColor: number;
  ringOpacity: number;
  /** Additive glow reads well on dark; normal blending on light. */
  glowBlending: THREE.Blending;
}

const DARK_PALETTE: GlobePalette = {
  coreDeep: 0x05070b,
  coreMid: 0x0b1219,
  coreLit: 0x16202b,
  atmosColor: 0x5d7f96,
  atmosStrength: 0.55,
  landColor: 0xaec9d9,
  landOpacity: 0.8,
  latticeColor: 0x3c4d5e,
  latticeOpacity: 0.35,
  markerColor: 0xd9e8f2,
  markerHaloColor: 0x5d7f96,
  markerHaloOpacity: 0.16,
  arcColor: 0x6d8ea4,
  arcOpacity: 0.42,
  ringColor: 0x33485c,
  ringOpacity: 0.2,
  glowBlending: THREE.AdditiveBlending,
};

const LIGHT_PALETTE: GlobePalette = {
  coreDeep: 0xccd6e0,
  coreMid: 0xe3e9ef,
  coreLit: 0xf6f9fb,
  atmosColor: 0x8ba3b6,
  atmosStrength: 0.35,
  landColor: 0x2b5876,
  landOpacity: 0.75,
  latticeColor: 0x93a8ba,
  latticeOpacity: 0.5,
  markerColor: 0x1f639b,
  markerHaloColor: 0x1f639b,
  markerHaloOpacity: 0.14,
  arcColor: 0x3d6f92,
  arcOpacity: 0.5,
  ringColor: 0x7d94a6,
  ringOpacity: 0.35,
  glowBlending: THREE.NormalBlending,
};

function sampleLandPoints(
  image: HTMLImageElement,
  count: number,
): Float32Array {
  const w = 1024;
  const h = 512;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(image, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);

  const positions: number[] = [];
  let attempts = 0;
  const maxAttempts = count * 40;

  while (positions.length / 3 < count && attempts < maxAttempts) {
    attempts += 1;
    const u = Math.random();
    const v = Math.random();
    // Equal-area-ish latitude sampling
    const lat = Math.asin(2 * v - 1);
    const lon = u * Math.PI * 2 - Math.PI;
    const x = Math.floor(u * w);
    const y = Math.floor((1 - (lat / Math.PI + 0.5)) * h);
    const idx = (Math.min(h - 1, Math.max(0, y)) * w + Math.min(w - 1, Math.max(0, x))) * 4;
    const r8 = data[idx];
    const g8 = data[idx + 1];
    const b8 = data[idx + 2];
    // Ocean on the Blue Marble is blue-dominant; everything else (green,
    // tan, snow/ice) counts as land so full continents render.
    const isOcean = b8 > r8 + 14 && b8 > g8 + 8;
    if (isOcean) continue;

    const r = 1.001;
    const cl = Math.cos(lat);
    // Negative z so east appears to the right when viewed from outside
    // (positive z would render a mirror image of Earth).
    positions.push(r * cl * Math.cos(lon), r * Math.sin(lat), -r * cl * Math.sin(lon));
  }

  return new Float32Array(positions);
}

export function DigitalGlobe({ className = "" }: { className?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const isLight = useIsLightTheme();

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const palette = isLight ? LIGHT_PALETTE : DARK_PALETTE;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 20);
    camera.position.set(0, 0, 3.15);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    host.appendChild(renderer.domElement);

    const root = new THREE.Group();
    // Match reference tilt
    root.rotation.z = -0.18;
    root.rotation.x = 0.22;
    scene.add(root);

    // Shaded sphere — soft light from upper-left, darker toward the limb
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.98, 64, 64),
      new THREE.ShaderMaterial({
        uniforms: {
          lightDir: { value: new THREE.Vector3(-0.6, 0.5, 0.62).normalize() },
          deep: { value: new THREE.Color(palette.coreDeep) },
          mid: { value: new THREE.Color(palette.coreMid) },
          lit: { value: new THREE.Color(palette.coreLit) },
        },
        vertexShader: `
          varying vec3 vNormalW;
          void main() {
            vNormalW = normalize(mat3(modelMatrix) * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 lightDir;
          uniform vec3 deep;
          uniform vec3 mid;
          uniform vec3 lit;
          varying vec3 vNormalW;
          void main() {
            float ndl = clamp(dot(normalize(vNormalW), normalize(lightDir)), 0.0, 1.0);
            vec3 color = mix(deep, mid, smoothstep(0.0, 0.55, ndl));
            color = mix(color, lit, smoothstep(0.45, 1.0, ndl) * 0.8);
            gl_FragColor = vec4(color, 1.0);
          }
        `,
      }),
    );
    root.add(core);

    // Atmosphere halo (backside fresnel) — tight so it fades well inside the canvas
    const atmos = new THREE.Mesh(
      new THREE.SphereGeometry(1.08, 64, 64),
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: palette.glowBlending,
        side: THREE.BackSide,
        uniforms: {
          color: { value: new THREE.Color(palette.atmosColor) },
          strength: { value: palette.atmosStrength },
        },
        vertexShader: `
          varying vec3 vNormal;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 color;
          uniform float strength;
          varying vec3 vNormal;
          void main() {
            float i = pow(0.62 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.6) * strength;
            gl_FragColor = vec4(color, i);
          }
        `,
      }),
    );
    root.add(atmos);

    const pointsMat = new THREE.PointsMaterial({
      size: 0.0085,
      color: palette.landColor,
      transparent: true,
      opacity: palette.landOpacity,
      depthWrite: false,
      blending: palette.glowBlending,
      sizeAttenuation: true,
    });
    let points: THREE.Points | null = null;

    // Faint dot lattice over the whole sphere (reference has subtle dots on oceans too)
    const latticeCount = 9000;
    const latticePos = new Float32Array(latticeCount * 3);
    for (let i = 0; i < latticeCount; i++) {
      const y = 1 - (i / (latticeCount - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = Math.PI * (3 - Math.sqrt(5)) * i;
      latticePos[i * 3] = r * Math.cos(th) * 0.995;
      latticePos[i * 3 + 1] = y * 0.995;
      latticePos[i * 3 + 2] = r * Math.sin(th) * 0.995;
    }
    const latticeGeo = new THREE.BufferGeometry();
    latticeGeo.setAttribute("position", new THREE.BufferAttribute(latticePos, 3));
    const latticeMat = new THREE.PointsMaterial({
      size: 0.0065,
      color: palette.latticeColor,
      transparent: true,
      opacity: palette.latticeOpacity,
      depthWrite: false,
      blending: palette.glowBlending,
      sizeAttenuation: true,
    });
    root.add(new THREE.Points(latticeGeo, latticeMat));

    const cityDirs = new Map(
      Object.entries(CITIES).map(([name, [lat, lon]]) => [
        name,
        latLonToVec3(lat, lon),
      ]),
    );
    const markerGeo = new THREE.SphereGeometry(0.014, 12, 12);
    const markerMat = new THREE.MeshBasicMaterial({
      color: palette.markerColor,
      transparent: true,
      opacity: 0.95,
    });
    for (const dir of cityDirs.values()) {
      const m = new THREE.Mesh(markerGeo, markerMat);
      m.position.copy(dir).multiplyScalar(1.015);
      root.add(m);
      const haloDot = new THREE.Mesh(
        new THREE.SphereGeometry(0.04, 12, 12),
        new THREE.MeshBasicMaterial({
          color: palette.markerHaloColor,
          transparent: true,
          opacity: palette.markerHaloOpacity,
          depthWrite: false,
          blending: palette.glowBlending,
        }),
      );
      haloDot.position.copy(m.position);
      root.add(haloDot);
    }

    const arcMat = new THREE.LineBasicMaterial({
      color: palette.arcColor,
      transparent: true,
      opacity: palette.arcOpacity,
    });
    const arcs: THREE.Line[] = [];
    for (const [from, to] of CITY_LINKS) {
      const a = cityDirs.get(from)!.clone().multiplyScalar(1.015);
      const b = cityDirs.get(to)!.clone().multiplyScalar(1.015);
      // Arc apex height grows with great-circle distance so short hops hug
      // the surface and transoceanic routes swing well clear of it.
      const apex = 1.06 + 0.5 * (a.angleTo(b) / Math.PI);
      const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(apex);
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(48)),
        arcMat,
      );
      root.add(line);
      arcs.push(line);
    }

    // Thin latitude rings
    const ringMat = new THREE.LineBasicMaterial({
      color: palette.ringColor,
      transparent: true,
      opacity: palette.ringOpacity,
    });
    for (const lat of [-0.45, 0, 0.45]) {
      const pts: THREE.Vector3[] = [];
      for (let i = 0; i <= 96; i++) {
        const t = (i / 96) * Math.PI * 2;
        const r = Math.cos(lat);
        pts.push(new THREE.Vector3(Math.cos(t) * r, Math.sin(lat), Math.sin(t) * r).multiplyScalar(1.01));
      }
      root.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), ringMat));
    }

    const loader = new THREE.ImageLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(
      EARTH_URL,
      (image) => {
        const pos = sampleLandPoints(image, 32000);
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
        points = new THREE.Points(geo, pointsMat);
        root.add(points);
      },
      undefined,
      () => {
        // Fallback fibonacci land-ish cloud
        const fallback = new Float32Array(9000);
        let n = 0;
        for (let i = 0; i < 3000; i++) {
          const y = 1 - (i / 2999) * 2;
          const r = Math.sqrt(1 - y * y);
          const th = Math.PI * (3 - Math.sqrt(5)) * i;
          if (Math.sin(th * 2.1) * Math.cos(y * 3) < 0.1) continue;
          fallback[n++] = r * Math.cos(th);
          fallback[n++] = y;
          fallback[n++] = r * Math.sin(th);
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.BufferAttribute(fallback.subarray(0, n), 3));
        points = new THREE.Points(geo, pointsMat);
        root.add(points);
      },
    );

    const setSize = () => {
      const w = Math.max(1, host.clientWidth);
      const h = Math.max(1, host.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.display = "block";
    };
    setSize();
    const ro = new ResizeObserver(setSize);
    ro.observe(host);

    let raf = 0;
    const tick = () => {
      root.rotation.y += 0.0016;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.dispose();
      core.geometry.dispose();
      (core.material as THREE.Material).dispose();
      atmos.geometry.dispose();
      (atmos.material as THREE.Material).dispose();
      markerGeo.dispose();
      markerMat.dispose();
      arcMat.dispose();
      ringMat.dispose();
      pointsMat.dispose();
      latticeGeo.dispose();
      latticeMat.dispose();
      points?.geometry.dispose();
      for (const line of arcs) line.geometry.dispose();
      if (renderer.domElement.parentElement === host) {
        host.removeChild(renderer.domElement);
      }
    };
  }, [isLight]);

  return <div ref={hostRef} className={`h-full w-full ${className}`} aria-hidden />;
}
