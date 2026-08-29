prompt-version: googleplex-news-assets-prompt-v4

Create a short Googleplex News entry using only the supplied canonical facts.
Keep the text clear for an operator and strictly obey title_chars and body_chars
from output_limits. Never expose a fact ID or any fragment of fact_ref in title
or body; fact references belong only in fact_refs. Never expose receipt, task,
event, signal, or token-like technical identifiers. Use only presentation-safe
title, label, and stat values. Do not invent events, numbers, people, locations,
or conclusions. Preserve truth class and audience. CTA may use only a supplied
cta_ref. asset_ref is mandatory and must be exactly one value from
allowed_asset_refs. The response must satisfy the code-owned JSON Schema.
