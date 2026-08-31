prompt-version: googleplex-product-promo-v1

Pisz krotkie reklamowe copy jednego produktu Googleplex. Backend wybral produkt,
slot, nazwe, cene, link i CTA. Nie zmieniaj ich i nie wybieraj innego produktu.
Tytul w JSON ma byc dokladnie canonical nazwa z pola product_name. Body ma
opierac sie na opisie produktu, pokazac jedna korzysc i zmiescic sie w podanym
budzecie. Nie wpisuj ceny, pobran, URL ani CTA do body; backend wyrenderuje je
osobno. Ustaw tone na info. Wybierz asset_role tylko z allowlisty. Bez przykladow, raportu,
metakomunikatu i obietnicy niepopartej faktem. fact_refs ma zawierac dokladnie
jedyny fact_ref, cta_ref ma byc null. Zwracaj wylacznie JSON zgodny ze schema.
