# What Became of the Abbeys?

What stands today on the sites of the religious houses that Henry VIII closed between 1536 and 1540, and did the Cistercians really choose remote, empty places?

**Interactive version:** https://tristan-hotham.github.io/after-the-abbeys/

**Paper and data (Zenodo):** https://doi.org/10.5281/zenodo.23677173

This repository holds the interactive page, the house-level dataset, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- {{n_houses|int}} religious houses in England ({{n_england|int}}) and Wales ({{n_wales|int}}) closed between 1536 and 1540 are in the dataset, {{n_with_coords|int}} with coordinates. Closures peaked in 1538 ({{by_year.1538|int}} houses, including {{friars_1538|int}} friaries).
- Of the {{afterlife_known_n|int}} houses whose present state the lists record, {{afterlife_known_share.house|pct0}} have a house or hotel on the site, {{afterlife_known_share.church|pct0}} a church in use, {{afterlife_known_share.ruin|pct0}} are ruins and {{afterlife_known_share.nothing|pct0}} have nothing visible left; {{afterlife.cathedral|int}} are cathedrals. {{standing_share_of_known|pct0}} still have something standing.
- The orders differ: {{afterlife_known_share_by_order.Benedictine.church|pct0}} of Benedictine sites with a recorded fate have a church in use, {{afterlife_known_share_by_order.Cistercian.ruin|pct0}} of Cistercian sites are ruins, and {{afterlife_known_share_by_order.Friars.nothing|pct0}} of friary sites have nothing visible.
- {{kept_name_n|int}} of the {{house_n|int}} houses built on monastic sites carry a monastic word in their recorded name ({{kept_name_abbey_n|int}} "Abbey").
- Against random points in the same county, the typical Cistercian monastery site had as many 1086 households within 5 km as an ordinary spot (median {{setting.Cistercian monks.pct_median|f1}}th percentile), against the {{setting.Benedictine monks.pct_median|f1}}th for Benedictine monks and the {{setting.Friars.pct_median|f1}}th for friars.
- With county fixed effects, Cistercian monks' sites had {{regression.effects.Cistercian monks.pct_change|f1}}% households within 5 km relative to Benedictine monks' (95% interval {{regression.effects.Cistercian monks.ci.0|f1}}% to {{regression.effects.Cistercian monks.ci.1|f1}}%). Quieter, not empty. The emptiest sites belong to the Carthusians ({{setting.Carthusian.pct_median|f1}}th percentile, n = {{setting.Carthusian.n|int}}).
- Cistercian sites sit on higher, hillier ground: median relief within 1 km {{setting.Cistercian monks.relief_median|f1}} m against {{setting.Benedictine monks.relief_median|f1}} m for Benedictine monks.

## Files

- `index.html`: the interactive page (Leaflet map, charts). Data embedded.
- `header.png`: social card (1200 by 630).
- `data/houses.csv`: one row per house closed 1536 to 1541: name, county, coordinates and their source, order and group, the list's community text, year and words of dissolution, the list's status mark and later-use notes (verbatim), afterlife class and all components found, the phrase that decided the class, any kept monastic name, Wikidata QID, Wikipedia link and source page.
- `data/house_settings.csv`: for each mapped house, whether it lies in the Domesday comparison area, distance to the nearest Domesday place, Domesday places and 1086 households within 5 and 10 km, the county percentile, height, relief and distance to the nearest watercourse.
- `data/baseline_points.csv`: the 400 random points per county used as the comparison, with the same measures.
- `data/houses.geojson`: the mapped houses as points.
- `data/audit_sample.csv`: the random check of 40 classified houses.
- `data/wikipedia_lists/`: one text file per English county list, the fields copied row by row from Wikipedia (name ## mark ## communities ## dissolved ## later use ## coordinates). Wales and Lancashire are parsed from raw wikitext; `Lancashire.txt` is the reader's copy kept for the extraction check.
- `data/local_notes.json`: quoted sentences about Whalley and Sawley from their Wikipedia articles.
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `code/`: run in order (`figlib.py` holds shared drawing helpers). `01_extract.py` (Wikidata rows to one record per house), `02_lists.py` (Wikipedia lists to one table, from `data/wikipedia_lists/*.txt`, the row-by-row copies of the county lists), `03_build.py` (join, order, afterlife rules), `04_setting.py` (Domesday, terrain and river measures), `05_analyse.py` (results and data files), `06_build_site.py` (page and README), `07_header.py` (social card).

## Method in brief

- Houses: the English Wikipedia county lists of monastic houses (46 English county pages read with a web reader that copied each row's fields verbatim, and the Wales and Lancashire pages parsed from raw wikitext; the reader agreed with the raw wikitext on all {{extraction_check.matched_names|int}} Lancashire rows), joined to Wikidata by name and distance. {{n_wikidata_only|int}} houses come from Wikidata alone.
- Afterlife: fixed rules on the list's later-use text and status marks, with Wikidata types and designations where the list is silent. Classes in priority order: cathedral, monastery again, church, house or hotel, school or college, farm, other use, ruin, earthworks only, nothing visible, protected (use unrecorded), unclear. A random check of {{audit.n|int}} classified houses found {{audit.consistent|int}} consistent with their source text.
- Setting: 1086 households of located Domesday places within 5 km, ranked against 400 random points in the same county; OLS of log(1 + households) on group with county fixed effects and robust errors; bootstrap intervals for medians.

## Known limits

- The lists are uneven and often silent on the present: {{afterlife.unclear|int}} houses are unclear and {{afterlife.protected|int}} only "protected". Rules read words, not buildings.
- My {{n_england|int}} English houses are about {{share_of_900|pct0}} of the "nearly 900" religious houses Wikipedia gives for England. Rows without a dissolution date are left out, and the Isle of Wight list could not be read.
- Domesday is not a census, is thin in Yorkshire after the harrying of the north, and gives no usable household counts for Wales, the far north, Lancashire, Greater Manchester, Merseyside, London or Winchester; {{dom_area_n|int}} houses are in the comparison.

## How to rerun

Python 3 with pandas, numpy, scipy, statsmodels, shapely, pyproj and playwright. Shared inputs (not included): the Wikidata and Wikipedia extracts, the domesday-destiny data, the AWS Terrain Tiles extract read by `within-sight/code/dem.py`, OS Open Rivers and the ONS county outlines from how-roman-is-your-road. Then `python3 code/01_extract.py` and so on to `07_header.py`.

## Sources and licences

- Wikipedia lists of monastic houses and articles (CC BY-SA 4.0), https://en.wikipedia.org/wiki/List_of_monastic_houses_in_England
- Wikidata (CC0), https://www.wikidata.org/
- Domesday data: Hull Domesday Project, Professor J.J.N. Palmer, George Slater and the University of Hull (CC BY-NC-SA), via https://github.com/embabel-worlds/realm-domesday and Open Domesday (https://opendomesday.org/)
- County outlines: Office for National Statistics (OGL v3). OS Open Rivers (OGL v3). Contains OS data © Crown copyright and database right.
- Elevation: AWS Terrain Tiles by Mapzen/Tilezen (sources include SRTM, GMTED2010, ETOPO1 and national datasets), https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Base map tiles: © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

Licences of this work: `data/houses.csv`, `data/houses.geojson`, `data/audit_sample.csv`, `data/wikipedia_lists/` and `data/local_notes.json` derive from Wikipedia and Wikidata and are CC BY-SA 4.0. `data/house_settings.csv`, `data/baseline_points.csv`, `data/results.json`, the page text and the paper use the Domesday figures and are CC BY-NC-SA 4.0. Code (`code/`) is MIT. See `LICENSE`.

## Citation

Hotham, T. (2026) *What Became of the Abbeys? The afterlives and settings of the religious houses closed 1536 to 1540.* Zenodo. https://doi.org/10.5281/zenodo.23677173

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
