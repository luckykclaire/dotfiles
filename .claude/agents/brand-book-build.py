#!/usr/bin/env python3
"""
Brand book builder — reads a JSON config, fills the template, writes HTML.

Usage:
    python3 brand-book-build.py <config.json> <output.html>

The config.json shape is documented in brand-book.md. Image paths in
config["logos"] and config["pegs"] are read from disk and base64-encoded
into data URIs by this script — the agent never has to handle base64.
"""
from __future__ import annotations
import sys, json, base64, datetime, urllib.parse, pathlib, mimetypes

TEMPLATE = pathlib.Path.home() / ".claude/agents/brand-book-template.html"

def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def encode_image(path_str: str) -> str:
    """Read an image file, return a data: URI."""
    p = pathlib.Path(path_str).expanduser()
    if not p.exists():
        die(f"Image not found: {p}")
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    if p.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    b = p.read_bytes()
    return f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"

def gfont(font: dict) -> str:
    fam = urllib.parse.quote(font["family"])
    weights = ";".join(str(w) for w in font.get("weights", [400]))
    return f"family={fam}:wght@{weights}"

def main() -> None:
    if len(sys.argv) != 3:
        die("Usage: brand-book-build.py <config.json> <output.html>")
    cfg_path, out_path = sys.argv[1], sys.argv[2]

    if not TEMPLATE.exists():
        die(f"Template missing: {TEMPLATE}")

    cfg = json.loads(pathlib.Path(cfg_path).read_text())

    # --- defaults ---
    cfg.setdefault("competitors", [])
    cfg.setdefault("values", [])
    cfg.setdefault("pegDescription", "")
    cfg.setdefault("personality", {"playful":5,"luxurious":5,"innovative":5,"bold":5,"warm":5})
    cfg.setdefault("palette", {})
    palette = cfg["palette"]
    palette.setdefault("primary",   [{"name":"Ink","hex":"#111111"}])
    palette.setdefault("secondary", [])
    palette.setdefault("accent",    [{"name":"Signal","hex":"#FF5A1F"}])
    palette.setdefault("neutral",   [
        {"name":"Paper","hex":"#FFFFFF"},
        {"name":"Bone","hex":"#EDEAE4"},
        {"name":"Graphite","hex":"#6B6B6B"},
        {"name":"Ink","hex":"#111111"},
    ])
    fonts = cfg.setdefault("fonts", {})
    fonts.setdefault("display", {"family":"Instrument Serif","category":"Serif","weights":[400]})
    fonts.setdefault("body",    {"family":"Inter","category":"Sans-serif","weights":[400,500,600]})
    fonts.setdefault("mono",    {"family":"JetBrains Mono","category":"Monospace","weights":[400,500]})
    fonts.setdefault("rationale", "")

    # --- archetype defaults if missing ---
    arch = cfg.setdefault("archetype", {})
    arch.setdefault("primary", {"name":"[CUSTOMIZE]","voice":"[CUSTOMIZE]","desire":"[CUSTOMIZE]","peers":"[CUSTOMIZE]"})
    arch.setdefault("shadow",  {"name":"[CUSTOMIZE]","voice":"[CUSTOMIZE]","desire":"[CUSTOMIZE]","peers":"[CUSTOMIZE]"})

    # --- theme defaults (optional; backwards compat) ---
    theme = cfg.setdefault("theme", {})
    theme.setdefault("canvas", "#FAFAFA")
    theme.setdefault("ink", "#111111")
    theme.setdefault("heroStyle", "solid-primary")  # solid-primary | golden-hour | ivory-editorial
    theme.setdefault("topbarLogoIndex", 0)
    # default gradient stops: primary -> secondary (or accent) -> canvas
    if "gradientStops" not in theme:
        p_hex = palette["primary"][0]["hex"]
        s_hex = (palette["secondary"][0]["hex"] if palette["secondary"]
                 else (palette["primary"][1]["hex"] if len(palette["primary"]) > 1
                       else palette["accent"][0]["hex"] if palette["accent"] else p_hex))
        theme["gradientStops"] = [p_hex, s_hex, theme["canvas"]]
    stops = theme["gradientStops"]
    if len(stops) < 2:
        die("theme.gradientStops must have at least 2 colors")
    # build the gradient CSS string
    if len(stops) == 2:
        gradient_css = f"linear-gradient(135deg, {stops[0]} 0%, {stops[1]} 100%)"
    else:
        gradient_css = f"linear-gradient(135deg, {stops[0]} 0%, {stops[1]} 45%, {stops[2]} 100%)"
    # rule color derived from ink
    ink = theme["ink"].lstrip("#")
    r_, g_, b_ = int(ink[0:2],16), int(ink[2:4],16), int(ink[4:6],16)
    rule_css = f"rgba({r_},{g_},{b_},.12)"

    # --- encode images (paths -> data URIs) ---
    logos_in = cfg.get("logos", []) or []
    pegs_in  = cfg.get("pegs",  []) or []
    cfg["logos"] = [encode_image(p) if not str(p).startswith("data:") else p for p in logos_in]
    cfg["pegs"]  = [encode_image(p) if not str(p).startswith("data:") else p for p in pegs_in]

    # --- google fonts href ---
    gfonts_href = (
        "https://fonts.googleapis.com/css2?"
        + "&".join([gfont(fonts["display"]), gfont(fonts["body"]), gfont(fonts["mono"])])
        + "&display=swap"
    )

    # --- positioning fallback ---
    positioning = cfg.get("positioningStatement") or (
        f"For {cfg.get('customer','[CUSTOMIZE: target]')} who {cfg.get('customerNeed','[CUSTOMIZE: need]')}, "
        f"{cfg.get('name','[Brand]')} is the {cfg.get('category','[CUSTOMIZE: category]')} that "
        f"{cfg.get('differentiator','[CUSTOMIZE: differentiator]')}, because "
        f"{cfg.get('reasonToBelieve','[CUSTOMIZE: proof]')}."
    )

    # --- customize block (optional bespoke content; falls back to visible TODO cards) ---
    customize = cfg.setdefault("customize", {})

    def _cust_card(body_html: str) -> str:
        """Wrap arbitrary filled content in the shared card shell."""
        return f'<div style="font-size:14px; line-height:1.6;">{body_html}</div>'

    def _cust_todo(hint: str) -> str:
        """Visible `Customize` placeholder card for when no content is supplied."""
        return f'<div class="customize"><span class="tag">Customize</span><div>{hint}</div></div>'

    def cust(key: str, hint: str, wrapper=_cust_card) -> str:
        """Return the filled HTML for a customize key, or a visible fallback card."""
        val = customize.get(key)
        if not val:
            return _cust_todo(hint)
        return wrapper(val)

    # Origin + Manifesto reuse the same styled "big prose block" shell
    def _prose_block(title: str, body: str) -> str:
        # The template already colors the section; we render a simple prose block
        return (
            f'<div style="max-width:72ch; font-size:16px; line-height:1.65;">'
            f'{body}</div>'
        )

    origin_html = (
        _prose_block("Origin Narrative", customize["originNarrative"])
        if customize.get("originNarrative")
        else _cust_todo(
            'Origin Narrative (150–250 words). Tell the brand\'s origin as a short story — name a specific moment, a specific person, a specific decision. No founder-deck platitudes.'
        )
    )
    manifesto_html = (
        _prose_block("Manifesto", customize["manifesto"])
        if customize.get("manifesto")
        else _cust_todo(
            'Manifesto (200–300 words). Open with a provocation, name the tension in the category, stake a belief, end with a line you\'d hang on the wall.'
        )
    )

    # Persona cards — render inline (already inside a .card)
    def _inline(val: str) -> str:
        return f'<p style="font-size:14px; line-height:1.6; margin:8px 0 0;">{val}</p>'

    primary_detail_html = (
        _inline(customize["primaryPersonaDetail"])
        if customize.get("primaryPersonaDetail")
        else _cust_todo("Add a day-in-the-life vignette, jobs-to-be-done, and the publications/podcasts/social accounts they consume.")
    )
    secondary_html = (
        _inline(customize["secondaryPersona"])
        if customize.get("secondaryPersona")
        else _cust_todo("The secondary audience — partners, influencers, or enterprise buyers — and what they care about differently.")
    )
    anti_html = (
        _inline(customize["antiPersona"])
        if customize.get("antiPersona")
        else _cust_todo('The customer you are NOT for. Be specific. Saying "everyone" here means you have no brand.')
    )

    # Customer journey — inline strings after "— "
    journey = customize.get("customerJourney") or {}
    j_awareness = journey.get("awareness") or "[where and how they first hear about you]"
    j_consideration = journey.get("consideration") or "[what they compare you against]"
    j_purchase = journey.get("purchase") or "[the trigger moment and friction points]"
    j_loyalty = journey.get("loyalty") or "[what brings them back]"
    j_advocacy = journey.get("advocacy") or "[what makes them refer you]"

    # We Say — intro text (table itself is JS-rendered)
    wesay_intro_html = (
        f'<p style="font-size:14px; opacity:.8; max-width:68ch;">{customize["weSayIntro"]}</p>'
        if customize.get("weSayIntro")
        else _cust_todo("Fill in 20 pairs covering product, pricing, support, social, and crisis tone. 3 starters provided.")
    )

    # Power words — inline mono row
    if customize.get("powerWords"):
        pw = customize["powerWords"]
        if isinstance(pw, list):
            pw = " · ".join(pw)
        power_words_html = f'<p class="mono" style="font-size:13px; opacity:.85; margin-top:8px;">{pw}</p>'
    else:
        power_words_html = _cust_todo("List 10 words your brand owns. Not adjectives — nouns and verbs that carry your POV.")

    # Taglines — display-font list
    if customize.get("taglines"):
        tl = customize["taglines"]
        if isinstance(tl, list):
            items = "".join(
                f'<li style="font-family:var(--f-display); font-size:clamp(22px,2.4vw,30px); line-height:1.2; letter-spacing:-0.01em; margin:8px 0;">{t}</li>'
                for t in tl
            )
            taglines_html = f'<ol style="padding-left:1.2em; margin:0;">{items}</ol>'
        else:
            taglines_html = f'<p style="font-family:var(--f-display); font-size:clamp(22px,2.4vw,30px); line-height:1.2;">{tl}</p>'
    else:
        taglines_html = _cust_todo("Draft 5 tagline candidates. Under 6 words; no category clichés; readable as both headline and sign-off.")

    # Photography + illustration
    photo_direction_html = (
        _inline(customize["photoDirection"])
        if customize.get("photoDirection")
        else _cust_todo('3–5 adjectives describing photography mood — e.g., "quiet, textural, morning light."')
    )
    photo_color_html = (
        _inline(customize["photoColor"])
        if customize.get("photoColor")
        else _cust_todo('Describe the post-processing signature — e.g., "warm highlights, lifted shadows, slight grain."')
    )
    photo_subject_html = (
        _inline(customize["photoSubject"])
        if customize.get("photoSubject")
        else _cust_todo("What we shoot — real customers, real environments, real products in use.")
    )
    illustration_html = (
        _inline(customize["illustration"])
        if customize.get("illustration")
        else _cust_todo("Line weight, color usage, geometric vs. organic, human figures vs. abstract.")
    )

    # Social hook (plain text rendered in big display type)
    social_hook_html = customize.get("socialHook") or "[CUSTOMIZE: the hook that stops the scroll.]"

    # Hashtag bank
    if customize.get("hashtagBank"):
        hb = customize["hashtagBank"]
        if isinstance(hb, dict):
            lines = []
            for label in ("branded", "community", "industry", "campaign"):
                if hb.get(label):
                    vals = hb[label]
                    if isinstance(vals, list):
                        vals = " ".join(vals)
                    lines.append(f'<div style="margin:6px 0;"><strong style="font-size:12px; text-transform:uppercase; letter-spacing:.12em; opacity:.7;">{label.title()}</strong><br><span class="mono" style="font-size:12px;">{vals}</span></div>')
            hashtag_html = f'<div style="margin-top:8px;">{"".join(lines)}</div>'
        else:
            hashtag_html = f'<p class="mono" style="font-size:12px; margin-top:8px;">{hb}</p>'
    else:
        hashtag_html = _cust_todo("Branded · Community · Industry · Campaign (rotate).")

    # Influencer brief
    influencer_html = (
        _inline(customize["influencerBrief"])
        if customize.get("influencerBrief")
        else _cust_todo("One-page brief: brand one-liner, product context, what to show, what NOT to say, deadlines, deliverables.")
    )

    # Packaging / vehicle wrap / merch / asset library
    packaging_html = (
        _inline(customize["packagingNote"])
        if customize.get("packagingNote")
        else _cust_todo("If you don't sell a physical product, delete this section. If you do, specify the unboxing sequence, label hierarchy, sustainable material palette, printing method, and required regulatory placements.")
    )
    vehicle_html = (
        _inline(customize["vehicleWrap"])
        if customize.get("vehicleWrap")
        else _cust_todo("If applicable, specify logo placement, vehicle classes, and approval workflow.")
    )
    merch_html = (
        _inline(customize["merchApproved"])
        if customize.get("merchApproved")
        else _cust_todo("List the merch your brand actually stands behind. If you wouldn't wear it, don't make it.")
    )
    asset_lib_html = (
        _inline(customize["assetLibraryLocation"])
        if customize.get("assetLibraryLocation")
        else _cust_todo("DAM, Drive, Notion, or Figma link. One source of truth.")
    )

    # --- the BRAND data block (consumed by template JS) ---
    brand_data = {
        "name": cfg.get("name","[Brand]"),
        "competitors": cfg.get("competitors", []),
        "values": cfg.get("values", []),
        "pegDescription": cfg.get("pegDescription",""),
        "personality": cfg["personality"],
        "palette": cfg["palette"],
        "fonts": cfg["fonts"],
        "logos": cfg["logos"],
        "pegs":  cfg["pegs"],
        "theme": theme,
        "customize": customize,
    }

    # --- text substitutions ---
    name = cfg.get("name","[Brand]")
    subs = {
        "{{BRAND_NAME}}": name,
        "{{BRAND_SLUG}}": "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-") or "brand",
        "{{DATE}}": datetime.date.today().isoformat(),
        "{{ESSENCE_LINE}}": cfg.get("essenceLine") or "The definitive source of truth for how this brand looks, sounds, and behaves.",
        "{{CATEGORY}}": cfg.get("category","[CUSTOMIZE]"),
        "{{PRICE_POSITIONING}}": cfg.get("pricePositioning","[CUSTOMIZE]"),
        "{{OWNER}}": cfg.get("owner","[CUSTOMIZE]"),
        "{{CONTACT}}": cfg.get("contact","[CUSTOMIZE]"),
        "{{MISSION}}": cfg.get("mission","[CUSTOMIZE: one sentence on what you do and for whom.]"),
        "{{VISION}}": cfg.get("vision","[CUSTOMIZE: one sentence on the future you are building toward.]"),
        "{{PROMISE}}": cfg.get("promise","[CUSTOMIZE: one sentence promise.]"),
        "{{ESSENCE}}": cfg.get("essence","[one word]"),
        "{{VOICE_LINE}}": cfg.get("voiceLine","[CUSTOMIZE: one sentence naming the voice archetype.]"),
        "{{CUSTOMER}}": cfg.get("customer","[CUSTOMIZE: demographics + psychographics.]"),
        "{{POSITIONING_STATEMENT}}": positioning,
        "{{ARCHETYPE_PRIMARY_NAME}}":   arch["primary"]["name"],
        "{{ARCHETYPE_PRIMARY_VOICE}}":  arch["primary"]["voice"],
        "{{ARCHETYPE_PRIMARY_DESIRE}}": arch["primary"]["desire"],
        "{{ARCHETYPE_PRIMARY_PEERS}}":  arch["primary"]["peers"],
        "{{ARCHETYPE_SHADOW_NAME}}":    arch["shadow"]["name"],
        "{{ARCHETYPE_SHADOW_PEERS}}":   arch["shadow"]["peers"],
        "{{GOOGLE_FONTS_HREF}}": gfonts_href,
        "{{F_DISPLAY}}": fonts["display"]["family"],
        "{{F_BODY}}":    fonts["body"]["family"],
        "{{F_MONO}}":    fonts["mono"]["family"],
        "{{C_PRIMARY}}":   palette["primary"][0]["hex"],
        "{{C_SECONDARY}}": palette["secondary"][0]["hex"] if palette["secondary"] else "#FAFAFA",
        "{{C_ACCENT}}":    palette["accent"][0]["hex"]    if palette["accent"]    else "#FF5A1F",
        "{{C_CANVAS}}":    theme["canvas"],
        "{{C_INK}}":       theme["ink"],
        "{{C_RULE}}":      rule_css,
        "{{HERO_STYLE}}":  theme["heroStyle"],
        "{{HERO_GRADIENT_CSS}}": gradient_css,
        # Customize-object substitutions (fill-your-own-content block)
        "{{CUSTOMIZE_ORIGIN}}":                   origin_html,
        "{{CUSTOMIZE_MANIFESTO}}":                manifesto_html,
        "{{CUSTOMIZE_PRIMARY_PERSONA_DETAIL}}":   primary_detail_html,
        "{{CUSTOMIZE_SECONDARY_PERSONA}}":        secondary_html,
        "{{CUSTOMIZE_ANTI_PERSONA}}":             anti_html,
        "{{CUSTOMIZE_JOURNEY_AWARENESS}}":        j_awareness,
        "{{CUSTOMIZE_JOURNEY_CONSIDERATION}}":    j_consideration,
        "{{CUSTOMIZE_JOURNEY_PURCHASE}}":         j_purchase,
        "{{CUSTOMIZE_JOURNEY_LOYALTY}}":          j_loyalty,
        "{{CUSTOMIZE_JOURNEY_ADVOCACY}}":         j_advocacy,
        "{{CUSTOMIZE_WESAY_INTRO}}":              wesay_intro_html,
        "{{CUSTOMIZE_POWER_WORDS}}":              power_words_html,
        "{{CUSTOMIZE_TAGLINES}}":                 taglines_html,
        "{{CUSTOMIZE_PHOTO_DIRECTION}}":          photo_direction_html,
        "{{CUSTOMIZE_PHOTO_COLOR}}":              photo_color_html,
        "{{CUSTOMIZE_PHOTO_SUBJECT}}":            photo_subject_html,
        "{{CUSTOMIZE_ILLUSTRATION}}":             illustration_html,
        "{{CUSTOMIZE_SOCIAL_HOOK}}":              social_hook_html,
        "{{CUSTOMIZE_HASHTAG_BANK}}":             hashtag_html,
        "{{CUSTOMIZE_INFLUENCER_BRIEF}}":         influencer_html,
        "{{CUSTOMIZE_PACKAGING}}":                packaging_html,
        "{{CUSTOMIZE_VEHICLE_WRAP}}":             vehicle_html,
        "{{CUSTOMIZE_MERCH}}":                    merch_html,
        "{{CUSTOMIZE_ASSET_LIBRARY}}":            asset_lib_html,
        # The data block is injected last because it's huge and contains JSON
        "{{BRAND_DATA_JSON}}": json.dumps(brand_data, separators=(",", ":")),
    }

    html = TEMPLATE.read_text()
    for k, v in subs.items():
        html = html.replace(k, v)

    # sanity: any unsubstituted placeholders?
    leftover = []
    i = 0
    while True:
        j = html.find("{{", i)
        if j < 0: break
        k = html.find("}}", j)
        if k < 0: break
        leftover.append(html[j:k+2])
        i = k + 2
    if leftover:
        print(f"WARNING: unsubstituted placeholders: {set(leftover)}", file=sys.stderr)

    out = pathlib.Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"Wrote {out}  ({out.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
