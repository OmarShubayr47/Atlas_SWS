"""Template schematics by voice (T-004 phase 4).

Owner decision 2026-10-01: schematics are DIAGRAMS FROM TEMPLATES. The
language model only picks a template and fills in values from what the user
said; every number on the drawing is computed here, deterministically, and
anything that would otherwise be a guessed datasheet value is either given by
the user or printed as a labelled assumption. That follows the project rule
"never invent electrical values" — a model asked to "design an LED circuit"
freehand will happily invent a forward voltage.

    values.py     parse "4k7" / "100 nF" / "5 V"; format; E12/E24/E96 series
    templates.py  the circuits: parameters, formulas, drawings (schemdraw)
    render.py     drawing + title + caption -> SVG bytes
    store.py      save each revision as rN.json (the spec) + rN.svg

The spec JSON is the shared format: a future sketch-to-schematic step (T-004
phase 5) would produce the same spec and reuse everything here.
"""
