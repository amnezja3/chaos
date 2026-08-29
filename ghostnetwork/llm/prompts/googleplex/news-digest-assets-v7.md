prompt-version: googleplex-news-assets-prompt-v7

Napisz po polsku bardzo krótki komunikat Googleplex News. Wybierz jeden fact_ref.
Jeżeli wybrany fakt zawiera lat i lng, opisz własnymi słowami przybliżoną
okolicę albo najbliższe znane miasto. To jest interpretacja narracyjna i nie
musisz kopiować technicznego title, label ani stat. Nie przepisuj fact ID,
receipt, task, event, signal ani token-like identifiers. Nie umieszczaj
współrzędnych w title/body. Backend zachowuje prawdziwy cel niezależnie od
Twojego opisu. CTA może użyć wyłącznie cta_ref przypisanego do wybranego
fact_ref; w przeciwnym razie zwróć null. asset_ref wybierz wyłącznie z
allowed_asset_refs. Zachowaj limity output_limits i code-owned JSON Schema.
