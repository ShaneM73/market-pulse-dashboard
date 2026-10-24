import fs from 'node:fs';
import * as topojson from 'topojson-client';
import { presimplify, simplify, quantile } from 'topojson-simplify';
import { geoPath } from 'd3-geo';
let topo = JSON.parse(fs.readFileSync('node_modules/us-atlas/states-albers-10m.json'));
topo = presimplify(topo);
topo = simplify(topo, quantile(topo, 0.08));
const fc = topojson.feature(topo, topo.objects.states);
const path = geoPath(null).digits(1);
const rows = fc.features.map(f => {
  const [cx, cy] = path.centroid(f);
  return { id: f.id, name: f.properties.name, path: path(f), cx: +cx.toFixed(1), cy: +cy.toFixed(1) };
});
fs.writeFileSync('states.json', JSON.stringify(rows));
console.log(rows.length, 'states; bytes', fs.statSync('states.json').size);
console.log(rows.map(r => r.name).sort().join(', '));
