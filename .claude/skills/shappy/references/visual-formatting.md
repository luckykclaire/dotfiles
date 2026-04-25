# OT Law Visual Formatting Specification

This file documents the **exact** format of an OT Law proposal, based on direct inspection of the OTLaw-AteneoPathways-4_22_2026.docx source. Get this right — the format is what makes it look like OT Law.

---

## The one rule above all others: edit the template, don't rebuild

**Shappy NEVER rebuilds an OT Law proposal from scratch using docx-js or python-docx.** The format uses floating/anchored drawings, a page-one-only banner with negative `posOffset`, a Word header for interior pages only, a two-footer setup (`<w:titlePg/>` trick), embedded custom fonts (Source Sans Pro, Gill Sans Light, Myriad Pro), and a footer text-box that contains both a page number and a white-on-blue address block overlaid on a background image. Rebuilding this from scratch with a docx library will produce something that *looks roughly right but isn't OT Law*.

**The correct workflow:**
1. Copy `assets/OTLaw-Proposal-Template.docx` (the Ateneo Pathways proposal, which is the canonical template) to the working directory.
2. Unpack it with `python /mnt/skills/public/docx/scripts/office/unpack.py template.docx unpacked/`.
3. Edit `unpacked/word/document.xml` to replace the content — keep all the `<w:rPr>`, `<w:pPr>`, table, and drawing structures intact; only swap the text inside `<w:t>` elements and adjust table rows where the number/names of Included Services differ.
4. Leave `header1.xml`, `footer1.xml`, `footer2.xml`, `styles.xml`, `numbering.xml`, and the three media images completely alone unless you have a specific reason to change them.
5. Repack with `python /mnt/skills/public/docx/scripts/office/pack.py unpacked/ output.docx --original template.docx`.

This is a template-edit workflow, not a template-build workflow. Treat the template .docx as read-only source-of-truth for everything formatting-related.

---

## Page setup (from the file's `<w:sectPr>`)

```xml
<w:pgSz w:w="12240" w:h="15840"/>
<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" 
         w:header="0" w:footer="0" w:gutter="0"/>
<w:titlePg/>
```

- **Page size:** US Letter (12,240 × 15,840 DXA = 8.5" × 11")
- **Margins:** 1 inch on all sides (1440 DXA)
- **`<w:titlePg/>` flag is REQUIRED** — this is what makes page 1 use `footer1.xml` (blank page number only) and pages 2+ use `footer2.xml` (branded with the blue band, address, and page number). Without this flag, every page uses the same footer and page 1's layout breaks.

---

## Page 1 (cover page) layout

Page 1 is unique in three ways:

### 1. The big banner is NOT a Word header. It's a floating drawing anchored in the body.

The banner at the top of page 1 — blue rectangle with "OT | LAW" wordmark, address, and `consult@otlaw.ph` — is `image1.png` placed as a `<w:drawing>` element inside the **third body paragraph** (not in the Word header).

Key XML characteristics:
```xml
<w:drawing>
  <wp:anchor behindDoc="1" relativeHeight="251658240" allowOverlap="1" ...>
    <wp:positionH relativeFrom="margin"><wp:posOffset>-989970</wp:posOffset></wp:positionH>
    <wp:positionV relativeFrom="margin"><wp:posOffset>-967299</wp:posOffset></wp:positionV>
    <wp:extent cx="8304530" cy="1752600"/>  <!-- ~9.08" × ~1.92" full-bleed -->
    ...
    <a:blip r:embed="rId7"/>  <!-- image1.png -->
  </wp:anchor>
</w:drawing>
```

- **`behindDoc="1"`** — image sits behind text.
- **Negative `posOffset` values** — push the image up and left past the margin so it bleeds to the page edges. Don't change these values.
- **`relativeFrom="margin"`** — positions the image relative to the top margin, not the page.
- **Anchored, not inline** — this is a floating object. `wrapNone`. Text flows underneath it.

### 2. The first-page top spacing ("there has to be space from above")

Page 1 has **two empty paragraphs before the banner paragraph**:

```xml
<!-- Body paragraph 1: empty with just a tab. Creates ~14pt of vertical space. -->
<w:p><w:pPr>...</w:pPr><w:r><w:tab/></w:r></w:p>

<!-- Body paragraph 2: completely empty. Another ~14pt. -->
<w:p><w:pPr>...</w:pPr></w:p>

<!-- Body paragraph 3: contains the floating banner drawing + starts "Private & Confidential" -->
<w:p><w:pPr>...</w:pPr><w:r>...<w:drawing>...</w:drawing>...</w:r>...</w:p>
```

**Why:** the banner image floats with a negative `posOffset`, so it bleeds up to the page edge. But the body text flow starts at the top margin. The two leading empty paragraphs push the first real text (the "Private & Confidential" line) down past where the banner ends, so text doesn't collide with the banner.

**Shappy rule:** When editing the template, **preserve these two leading empty paragraphs**. Never delete them. If page 1 text starts creeping up into the banner, the cause is almost always that these empties got removed.

### 3. Page 1 footer is intentionally minimal

Page 1 uses `footer1.xml`, which is just a centered page number using the built-in `PageNumber` style. No blue band, no address, no `consult@otlaw.ph`. This is correct — the cover page's branding comes from the banner at the top, so repeating the address in a footer would be visual noise.

---

## Interior pages (page 2+) layout

### Interior header: THIS is the Word header

`header1.xml` contains `image2.png` (the diagonal chevron + small "OT | LAW" wordmark on ivory background) placed as an **inline drawing** inside a single paragraph with `<w:ind w:left="-1418"/>` (negative left indent so the image bleeds past the left margin).

```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="Header"/>
    <w:ind w:left="-1418"/>
  </w:pPr>
  <w:r><w:drawing><wp:inline>
    <wp:extent cx="7783736" cy="674478"/>  <!-- ~8.5" × ~0.74" full-width bleed -->
    ...
    <a:blip r:embed="rId1"/>  <!-- image2.png -->
  </wp:inline></w:drawing></w:r>
</w:p>
```

This is an **inline** drawing (not anchored like the page-1 banner). It's loaded via `header1.xml` with `<w:headerReference w:type="default" r:id="rId8"/>`, and because `<w:titlePg/>` is set, Word automatically suppresses this header on page 1.

### Interior footer: `footer2.xml`

`footer2.xml` is the sophisticated branded footer. It combines three elements:

**(a) A framed page number** (upper-left of the footer, positioned with `<w:framePr>`). Uses Myriad Pro bold, white text (`<w:color w:val="FFFFFF"/>`) — white because it sits on the blue band.

```xml
<w:framePr w:h="321" w:hRule="exact" w:wrap="none" 
           w:vAnchor="text" w:hAnchor="page" w:x="417" w:y="578"/>
```

**(b) A text box** (`<mc:AlternateContent>` with `<w:drawing><wp:anchor>` holding a `wps:wsp` shape) containing the right-aligned address in Gill Sans Light, white text, 9pt. The text box is floated over the blue band background.

```
5F Phinma Plaza 39 Drive, Rockwell Center,
Makati City, Metro Manila, Philippines
consult@otlaw.ph                              [bold]
```

**(c) The blue band with rose-gold rule** is `image3.png`, placed as an anchored drawing behind the text.

### "ONGCANGCO TINGSON LAW" micro-text in the footer

The footer also contains "ONGCANGCO TINGSON LAW" in small caps to the right of the page number. This is a separate text run, also in white, Gill Sans Light-style.

---

## Fonts (from the actual file)

These are the fonts the proposal references. If any aren't installed on the editing environment, the file will still validate but may render with substitutes — which is a silent failure mode.

| Usage | Font | Where |
|---|---|---|
| Body text | **Source Sans Pro** | Main document body (most `<w:rFonts w:ascii="Source Sans Pro"/>`) |
| Footer address | **Gill Sans Light** | footer2.xml text box |
| Footer page number | **Myriad Pro** | footer2.xml page number |
| Headers/titles | (inherits from Source Sans Pro default) | — |

**Shappy rule:** Don't change fonts unless explicitly asked. The template references these specific faces and the file has been reviewed to look right with them.

---

## Colors

- **Bleu Encre** `#1D3C72` — letterhead band, section numbering/headings, table header backgrounds, footer blue band background (via image3.png)
- **Ivory** `#FAF6EE` — interior header background (via image2.png)
- **Rose Gold** `#B76E79` — thin horizontal rule at the top/bottom of the letterhead band and the footer band (baked into images 1 and 3)
- **White** `#FFFFFF` — text color for all footer content (page number, address, email) since it sits on the blue band
- **Black** — body text

---

## Tables (from observed structure)

- Header row: dark blue (`#1D3C72` Bleu Encre) background, white text, bold
- Body rows: white background, black text
- Borders: thin gray or black
- Column widths in the Included Services summary table (page 2): approximately 3150 DXA (left) + 6210 DXA (right) = 9360 DXA total (fits 1" margins on US Letter)
- Installment table (page 10): 6 columns — Installment | VAT Exclusive (PHP) | 12% VAT (PHP) | VAT Inclusive (PHP) | % of Total | Billing
- **Signature treatment on totals**: the "VAT Inclusive Total" cell has a solid **black** fill with **white** text. This is an OT Law visual signature — keep it.

---

## Defined styles in `styles.xml` (don't redefine)

The template already has all the styles it needs. Notably:
- Paragraph styles tied to Source Sans Pro
- `PageNumber` character style (used in both footers)
- `Header` and `Footer` paragraph styles
- Table styles including the dark-blue-header treatment

When editing via the template workflow, these come along for free. Don't attempt to redefine them.

---

## Known typography traps

These issues showed up in the PDF render of the Ateneo Pathways v1 draft. Shappy should sweep for them before finalizing:

1. **"fl" and "fi" ligature drops.** "filing" rendered as "fling"; "first" as "frst." If the template is edited with a tool that drops characters on ligature handling, affected words include: filing, first, financial, efficient, sufficient, fiduciary, confidential. Do a find for "fl" and "fr" in body text after editing to catch these.

2. **"ini/a/ve" artifact.** "initiative" rendered as "ini/a/ve" in a prior draft. This was a font-substitution character-set issue. Search for `/a/` in the body after editing.

3. **Collapsed spaces.** "without independent" rendering as "withoutindependent." Search for common compound-word candidates (without, between, throughout, under, over) followed by no-space-then-letter.

4. **Em dash vs en dash vs hyphen.** OT Law uses **em dash (—)** for inline pauses and section lead-ins (e.g., "A. Cooperation — Ateneo Pathways..."). Use **en dash (–)** for date ranges and degree entries (e.g., "Juris Doctor, 2016"). Never use double hyphens (--).

---

## File naming convention

```
OTLaw-[ClientShortName]-[M_DD_YYYY].docx
```

Examples:
- `OTLaw-AteneoPathways-4_22_2026.docx`
- `OTLaw-VisayaKPO-3_15_2026.docx`
- `OTLaw-ARIBohol-11_08_2025.docx`

Underscores for the date separator. PascalCase client short name (no spaces).

---

## Quick-reference: what NOT to touch in the template

| File | Leave alone? | Notes |
|---|---|---|
| `word/header1.xml` | ✅ Yes | Interior page header — never changes |
| `word/footer1.xml` | ✅ Yes | Page 1 footer — just a page number |
| `word/footer2.xml` | ✅ Yes | Interior footer — blue band, address, email |
| `word/media/image1.png` | ✅ Yes | Page-1 banner |
| `word/media/image2.png` | ✅ Yes | Interior header graphic |
| `word/media/image3.png` | ✅ Yes | Interior footer background band |
| `word/styles.xml` | ✅ Yes | All styles already defined |
| `word/numbering.xml` | ✅ Yes | List numbering presets |
| `word/theme/theme1.xml` | ✅ Yes | Theme colors |
| `word/document.xml` | ❌ This is what you edit | Replace body text; keep `<w:sectPr>`, `<w:titlePg/>`, leading empty paragraphs, and the banner drawing XML structure intact |
