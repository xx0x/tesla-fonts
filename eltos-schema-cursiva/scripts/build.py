"""Rebuild the Eltos Schema Cursiva font project from the SVG glyphs.

Usage (from anywhere):
    fontforge -lang=py -script eltos-schema-cursiva/scripts/build.py

What it does:
  * re-imports every glyphs/<name>.v.svg into project/eltos-schema-cursiva-v1.sfd
    (outlines edited in the FontForge GUI are overwritten, edit the SVGs instead)
  * sets side bearings measured on the upright (de-slanted) outline, adjusted by spacing.txt
  * makes lowercase letters references to the uppercase ones
  * builds the kerning from kerning.txt
  * writes font/EltosSchemaCursiva-Regular.otf + .woff and the glyph list for project/
"""
import datetime, fontforge, glob, json, os, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SFD = os.path.join(ROOT, "project", "eltos-schema-cursiva-v1.sfd")
GLYPHS = os.path.join(ROOT, "glyphs")
SPACING = os.path.join(HERE, "spacing.txt")
KERNING = os.path.join(HERE, "kerning.txt")
FONT_DIR = os.path.join(ROOT, "font")
FONT_BASENAME = "EltosSchemaCursiva-Regular"
PREVIEW_GLYPHS = os.path.join(ROOT, "project", "glyphs.js")

SB = 55           # default side bearing (font units, em = 1000)
SLANT = 0.5       # tan of the lettering slant (~27 deg), spacing is measured upright
SPACE_WIDTH = 400
VERSION = "1.000"
BUILD = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def read_table(path):
    """Yield whitespace-split rows of a config file, skipping blanks and # comments."""
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            row = line.split("#", 1)[0].split()
            if row:
                yield lineno, row


def glyph_name(token):
    """Accept either a glyph name (Tcaron, period) or the character itself (Ť, .)."""
    if len(token) == 1:
        return fontforge.nameFromUnicode(ord(token))
    return token


def is_accented(g):
    return g.unicode > 0 and len(unicodedata.normalize("NFD", chr(g.unicode))) > 1


def base_name(g):
    """Glyph name of the unaccented uppercase form (Ťť -> T, a -> A, period -> period)."""
    if g.unicode < 0:
        return g.glyphname
    base = unicodedata.normalize("NFD", chr(g.unicode))[0].upper()
    return fontforge.nameFromUnicode(ord(base))


def body_bbox(f, g):
    """Upright bbox of the base letter only (accent contours sitting high up are ignored)."""
    tmp = f.createChar(-1, "__tmp")
    lay = fontforge.layer()
    for c in g.foreground:
        if not is_accented(g) or c.boundingBox()[1] < 500:
            lay += c
    tmp.foreground = lay
    tmp.transform((1, 0, -SLANT, 1, 0, 0))
    bb = tmp.boundingBox()
    f.removeGlyph(tmp)
    return bb


def set_names(f):
    f.encoding = "UnicodeBmp"
    f.fontname = "EltosSchemaCursiva-Regular"
    f.familyname = "Eltos Schema Cursiva"
    f.fullname = "Eltos Schema Cursiva"
    f.weight = "Regular"
    f.os2_weight = 400
    f.copyright = "Copyright (c) 2026, Václav Mach (https://github.com/xx0x)"
    # head.fontRevision must be numeric, the build timestamp goes into the version string
    f.version = VERSION
    for key, val in [("Family", "Eltos Schema Cursiva"), ("SubFamily", "Regular"),
                     ("Fullname", "Eltos Schema Cursiva"),
                     ("PostScriptName", "EltosSchemaCursiva-Regular"),
                     ("Designer", "Václav Mach"), ("Manufacturer", "Václav Mach"),
                     ("Version", "Version %s; %s" % (VERSION, BUILD)),
                     ("UniqueID", "EltosSchemaCursiva-Regular; %s" % BUILD),
                     ("License", "This Font Software is licensed under the SIL Open Font License, "
                                 "Version 1.1. This license is available with a FAQ at: "
                                 "https://openfontlicense.org"),
                     ("License URL", "https://openfontlicense.org")]:
        f.appendSFNTName("English (US)", key, val)
    # Line spacing: 1350 units, accents are tall so leave room above the caps.
    # Win metrics follow the real bbox (Windows clips anything outside them).
    f.os2_typoascent, f.os2_typoascent_add = 1100, 0
    f.os2_typodescent, f.os2_typodescent_add = -250, 0
    f.os2_typolinegap = 0
    f.hhea_ascent, f.hhea_ascent_add = 1100, 0
    f.hhea_descent, f.hhea_descent_add = -250, 0
    f.hhea_linegap = 0
    f.os2_winascent, f.os2_winascent_add = 0, 1
    f.os2_windescent, f.os2_windescent_add = 0, 1


def import_glyphs(f):
    spacing = {}
    for lineno, row in read_table(SPACING):
        name, left, right = row
        spacing[glyph_name(name)] = (int(left), int(right))

    for svg in sorted(glob.glob(os.path.join(GLYPHS, "*.v.svg"))):
        name = os.path.basename(svg)[:-len(".v.svg")]
        if fontforge.unicodeFromName(name) < 0:
            sys.exit("%s: not a standard glyph name (see the Adobe Glyph List)" % os.path.basename(svg))
        g = f.createChar(fontforge.unicodeFromName(name), name)
        g.clear()
        g.importOutlines(svg)
        # accented glyphs take the spacing of their base letter
        left, right = spacing.get(name, spacing.get(base_name(g), (0, 0)))
        xmin, _, xmax, _ = body_bbox(f, g)
        g.transform((1, 0, 0, 1, SB + left - xmin, 0))
        g.width = round(xmax - xmin + 2 * SB + left + right)

    f.createChar(0x20, "space").width = SPACE_WIDTH
    f.createChar(0xA0, "uni00A0").width = SPACE_WIDTH


def make_lowercase(f):
    for g in list(f.glyphs()):
        if g.unicode < 0 or not chr(g.unicode).isupper():
            continue
        lu = ord(chr(g.unicode).lower())
        lg = f.createChar(lu, fontforge.nameFromUnicode(lu))
        lg.clear()
        lg.addReference(g.glyphname)
        lg.width = g.width


def make_kerning(f):
    """kerning.txt rows are `LEFT RIGHT VALUE`.

    A plain base letter (T) means the whole group: T, Ť, t, ť.
    An accented letter (Ť or Tcaron) means just that letter and its lowercase.
    Later rows override earlier ones, so exceptions go below the general rule.
    """
    groups = {}
    for g in f.glyphs():
        if g.unicode > 0 and g.glyphname not in ("space", "uni00A0"):
            groups.setdefault(base_name(g), []).append(g.glyphname)

    def expand(token, lineno):
        name = glyph_name(token)
        if name not in f:
            sys.exit("kerning.txt:%d: unknown glyph %r" % (lineno, token))
        g = f[name]
        if not is_accented(g) and base_name(g) == name:
            return groups[name]
        lower = chr(g.unicode).lower()
        names = [name]
        if lower != chr(g.unicode):
            names.append(fontforge.nameFromUnicode(ord(lower)))
        return names

    pairs = {}
    for lineno, row in read_table(KERNING):
        left, right, value = row
        for a in expand(left, lineno):
            for b in expand(right, lineno):
                pairs[(a, b)] = int(value)

    if "kern" in f.gpos_lookups:
        f.removeLookup("kern")
    f.addLookup("kern", "gpos_pair", None,
                (("kern", (("DFLT", ("dflt",)), ("latn", ("dflt",)))),))
    f.addLookupSubtable("kern", "kern-1")
    for (a, b), value in sorted(pairs.items()):
        if value:
            f[a].addPosSub("kern-1", b, 0, 0, value, 0, 0, 0, 0, 0)
    return len(pairs)


def write_preview_glyphs(f):
    """project/glyphs.js: every encoded glyph, so the preview table stays in sync."""
    rows = []
    for g in sorted(f.glyphs(), key=lambda g: g.unicode):
        if g.unicode > 0x20 and g.unicode != 0xA0:
            rows.append('  {"char": %s, "name": "%s", "code": "U+%04X", "width": %d}'
                        % (json.dumps(chr(g.unicode), ensure_ascii=False), g.glyphname, g.unicode, g.width))
    with open(PREVIEW_GLYPHS, "w", encoding="utf-8") as fh:
        fh.write("// Generated by scripts/build.py, do not edit.\nwindow.FONT_BUILD = \"%s\";\nwindow.GLYPHS = [\n%s\n];\n"
                 % (BUILD, ",\n".join(rows)))


def main():
    f = fontforge.open(SFD)
    set_names(f)
    import_glyphs(f)
    make_lowercase(f)
    npairs = make_kerning(f)
    f.save(SFD)
    os.makedirs(FONT_DIR, exist_ok=True)
    for ext in ("otf", "woff"):
        f.generate(os.path.join(FONT_DIR, "%s.%s" % (FONT_BASENAME, ext)))
    write_preview_glyphs(f)
    print("saved %s + font/%s.otf/.woff, build %s (%d glyphs, %d kerning pairs)"
          % (os.path.relpath(SFD, ROOT), FONT_BASENAME, BUILD, sum(1 for _ in f.glyphs()), npairs))


main()
