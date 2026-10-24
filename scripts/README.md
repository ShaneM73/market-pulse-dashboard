`build_states_geo.mjs` regenerates `data/states_geo.json`:

```bash
npm install us-atlas topojson-client topojson-simplify d3-geo
node build_states_geo.mjs   # writes states.json; add postal abbreviations and copy to ../data/states_geo.json
```
