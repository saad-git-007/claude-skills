# Sourcing 3D models

Order of preference for each BOM line:

1. **KiCad official library** (`kicad-packages3D` + `kicad-footprints` on GitLab, raw URLs built by
   `kicad_map.urls`). Covers passives, SOT/SOIC/TSSOP/QFN, radial caps, pin headers and sockets, SMA,
   tact switches, crystals, many inductors. Names are exact: check
   `https://gitlab.com/kicad/libraries/kicad-packages3D/-/tree/master/<Lib>.3dshapes` when a fetch 404s.
   Past 404 fixes: `D_SOD-123F`, `TSSOP-28_4.4x9.7mm_P0.65mm`, `L_Coilcraft_XAL6060-XXX`, `SOT-323_SC-70`.
2. **Manufacturer download without login.** Worked: Same Sky / CUI terminal blocks (product page "3D model"),
   Mean Well (`/upload/pdf/<SERIES>/<SERIES>-3D.zip`), Würth Elektronik (`we-online.com/components/products/download/…stp`).
   Put the URL in `maker_urls`; zips are unpacked by `fetch_models.py`. If a site blocks curl, fetch once in a
   browser and drop the file in `models/maker/`.
3. **Community / CC0 model** (GitHub, GrabCAD-style mirrors with a clear licence) into `models/third_party/`,
   credited in `maker_sources`. E.g. a Zettler AZ943 relay, a Raspberry Pi 4 board.
4. **KiCad equivalent** of the same package (e.g. a generic 2.54 mm socket for a Samtec part). Say so in the report.
5. Otherwise leave the extruded box from the Altium body and list it for the user.

Never: create accounts, log in, accept terms for the user, or send their e-mail (SnapEDA, Ultra Librarian,
SamacSys/Component Search Engine, most DigiKey/Mouser "3D model" links). Use a generic User-Agent.

Check every stand-in against the BOM line and report mismatches, e.g. a right-angle terminal block model where
the BOM says vertical, a 22×50 mm capacitor on a 22×40 footprint, a relay model of a sibling coil-voltage variant.

Keep files small: delete the models folder with `setup.sh --clean` after the 3D build. The models are baked into
the HTML as compressed GLB.
