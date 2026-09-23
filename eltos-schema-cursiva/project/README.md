# Eltos Schema Cursiva Font Build

Make sure you have fontforge CLI installed using eg. `brew install fontforge`.

Don't edit `eltos-schema-cursiva-v1.sfd` and `glyphs.js` manually, instead:

- Add SVGs to the `glyphs` directory
- Update `scripts/kerning.txt` and `scripts/spacing.txt` if necessary
- Run `scripts/build.py`
