const fs = require('fs');
const d3 = require('d3-geo');

// ── 1. XML ESCAPE UTILITY ─────────────────────────────────────────
function escapeXml(unsafe) {
  if (!unsafe) return '';
  return String(unsafe)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

// ── 2. READ INPUT GEOJSON ─────────────────────────────────────────
const rawData = fs.readFileSync('india_pc_2024_simplified.geojson', 'utf8');
const geojson = JSON.parse(rawData);

// ── 3. GEOGRAPHIC SANITY BOUNDS ────────────────────────────────────
// India's mainland + Andaman/Nicobar/Lakshadweep roughly span
// lng 68–98, lat 6–38. A little padding either side to be safe.
// Anything outside this is corrupted data (decimal shift, null
// island [0,0], stray duplicate outline, etc.) — the kind of thing
// that silently blows up fitSize()'s bounding box and squeezes the
// real map into a tiny corner of the canvas.
const INDIA_BOUNDS = { minLng: 60, maxLng: 100, minLat: 0, maxLat: 40 };

function hasValidBounds(feature) {
  try {
    const [[minLng, minLat], [maxLng, maxLat]] = d3.geoBounds(feature);
    return (
      minLng >= INDIA_BOUNDS.minLng &&
      maxLng <= INDIA_BOUNDS.maxLng &&
      minLat >= INDIA_BOUNDS.minLat &&
      maxLat <= INDIA_BOUNDS.maxLat
    );
  } catch {
    // geoBounds throws on totally malformed/empty geometry
    return false;
  }
}

// ── 4. FILTER OUT BACKGROUND / NON-CONSTITUENCY / CORRUPTED POLYGONS ─
const droppedFeatures = [];

const validFeatures = geojson.features.filter(f => {
  if (!f.geometry || !f.geometry.coordinates) {
    droppedFeatures.push({ reason: 'no geometry', props: f.properties });
    return false;
  }

  const props = f.properties || {};
  const pcName = String(props.pc_name || props.PC_NAME || props.NAME || '').toLowerCase();

  if (pcName.includes('background') || pcName.includes('ocean') || pcName.includes('bbox')) {
    droppedFeatures.push({ reason: 'name match (background/ocean/bbox)', name: props.pc_name || props.PC_NAME });
    return false;
  }

  if (!['Polygon', 'MultiPolygon'].includes(f.geometry.type)) {
    droppedFeatures.push({ reason: `unsupported geometry type: ${f.geometry.type}`, name: props.pc_name || props.PC_NAME });
    return false;
  }

  if (!hasValidBounds(f)) {
    const bounds = (() => { try { return d3.geoBounds(f); } catch { return 'unreadable'; } })();
    droppedFeatures.push({ reason: 'out-of-range coordinates', name: props.pc_name || props.PC_NAME, bounds });
    return false;
  }

  return true;
});

// ── 5. DIAGNOSTIC OUTPUT ──────────────────────────────────────────
if (droppedFeatures.length > 0) {
  console.warn(`\nDropped ${droppedFeatures.length} feature(s):`);
  droppedFeatures.forEach(d => console.warn(`  - ${d.name || '(unnamed)'}: ${d.reason}`, d.bounds ? d.bounds : ''));
  console.warn('');
}

if (validFeatures.length < 500) {
  console.error(`⚠ WARNING: only ${validFeatures.length} valid features — expected ~543 Lok Sabha constituencies. Check the drop reasons above.`);
}

// Build filtered collection specifically for D3 projection calculation
const filteredGeoJSON = {
  type: 'FeatureCollection',
  features: validFeatures
};

// ── 6. VIEWPORT DIMENSIONS ────────────────────────────────────────
const width = 1449.064;
const height = 1534.05;

// ── 7. D3 MERCATOR PROJECTION SETUP ───────────────────────────────
// Fits projection strictly to the valid constituency geometries
const projection = d3.geoMercator().fitSize([width, height], filteredGeoJSON);
const pathGenerator = d3.geoPath().projection(projection);

// ── 8. COLOR GENERATOR FOR DISTINCT FILLS ─────────────────────────
function getPaletteColor(id) {
  const palette = [
    '#1a4878', '#105652', '#332c54', '#432818', '#1e3a58',
    '#2d4030', '#5c2a38', '#0c3b43', '#4a2800', '#2b3a4a',
    '#3b1f42', '#184d47', '#483434', '#0d2640', '#2d3047'
  ];
  return palette[(parseInt(id) || 0) % palette.length];
}

// ── 9. TRANSFORM GEOJSON FEATURES TO SVG PATHS ────────────────────
const paths = validFeatures.map((feature) => {
  const p = feature.properties || {};
  const pathData = pathGenerator(feature);

  // Normalize property lookups across common GeoJSON property casings
  const rawPcName = p.pc_name || p.PC_NAME || p.NAME || '';
  const rawStName = p.st_name || p.ST_NAME || p.STATE || '';
  const rawPcId   = p.pc_id   || p.PC_ID   || p.ID    || '';
  const rawPcNo   = p.pc_no   || p.PC_NO   || '';

  const pcName = escapeXml(rawPcName);
  const stName = escapeXml(rawStName);
  const pcId   = escapeXml(rawPcId);
  const pcNo   = escapeXml(rawPcNo);

  const color = getPaletteColor(rawPcId);

  return `<path class="constituency" ` +
    `id="c${pcId}" ` +
    `data-index="${pcId}" ` +
    `data-name="${pcName}" ` +
    `data-state="${stName}" ` +
    `data-pc-no="${pcNo}" ` +
    `data-party="" ` +
    `data-color="${color}" ` +
    `data-coalition="" ` +
    `data-mp="" ` +
    `fill="${color}" ` +
    `d="${pathData}" />`;
});

// ── 10. ASSEMBLE SVG DOCUMENT ─────────────────────────────────────
const svgOutput = `<svg xmlns="http://www.w3.org/2000/svg" id="india-constituencies" viewBox="0 0 ${width} ${height}" style="width:100%;height:100%;display:block">
  <desc>India Lok Sabha Constituencies — 543 seats</desc>
  <g id="constituencies">
    ${paths.join('\n    ')}
  </g>
</svg>`;

// ── 11. SAVE OUTPUT FILE ──────────────────────────────────────────
fs.writeFileSync('india_constituencies.svg', svgOutput);
console.log(`Successfully generated SVG with ${validFeatures.length} constituencies!`);