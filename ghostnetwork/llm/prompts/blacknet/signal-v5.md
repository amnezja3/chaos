prompt-version: blacknet-signal-prompt-v5

Przeksztalc jedyny przekazany fakt w krotki, polski fragment transmisji z roku
2108 przechwycony przez Ghost System. Backend wybral juz temat, medium i cel;
nie wybieraj innego faktu i nie lacz kilku watkow.

Tytul powinien miec 2-6 slow. Body powinno miec 1-3 krotkie zdania i brzmiec
jak urwany, dramatyczny, enigmatyczny przekaz, a nie raport techniczny ani
streszczenie. Zachowaj konkret z title, label, value lub stat, ale nie dopisuj
przyczyn, skutkow, sprawcow ani lokalizacji, ktorych nie ma w fakcie.

Akcja dzieje sie w swiecie roku 2108. Daty observed_at i valid_until sa
technicznym czasem runtime: nigdy nie przepisuj ich roku ani nie pisz "w roku
2026". Nie przepisuj surowych lat/lng. Pola region_id oraz inne techniczne
prefiksy nie sa nazwami miejsc: nigdy nie wypisuj "world-", "world_" ani
"world:". Gdy nie ma canonical nazwy miejsca, pomin lokalizacje.

Nie kopiuj gotowych sloganow. Nie uzywaj sformulowan: "wydajny komunikat",
"oto najwazniejsze informacje", "BlackNet Digest", "zarejestrowano incydent"
ani "wiecej informacji nie jest dostepnych". Googleplex jest platforma, nie
podmiotem zdarzenia.

fact_refs musi zawierac dokladnie jedyny fact_ref z facts. cta_ref zawsze null;
nawigacje i canonical target dopina backend. Zwracaj wylacznie JSON zgodny ze
schema.
