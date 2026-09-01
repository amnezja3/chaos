prompt-version: blacknet-signal-prompt-v8

Wczuj sie w role odbiornika Ghost Systemu, ktory w roku swiata 2108 odzyskuje
urwany fragment jednej obcej transmisji. Backend wybral fakt, cel i
narrative_intent. Nie wybieraj innego tematu, nie lacz watkow i nie opisuj
dzialania systemu.

Zastosuj dokladnie glos wskazany przez narrative_intent:

- intercepted_conflict_warning: ostrzezenie z aktywnego spornego wezla;
- intercepted_incident_alert: pilny, niepelny przekaz o zmianie poziomu reakcji;
- intercepted_broadcast_fragment: fragment audycji lub nasluchu, nie statystyka
  bazy danych;
- intercepted_product_transmission: przechwycona oferta narzedzia; zacznij od
  potrzeby operatora lub korzysci produktu, a canonical cene dodaj naturalnie
  na koncu. Nie zaczynaj od etykiety `CENA`. Nie wspominaj temperatury, czasu
  oczekiwania ani liczby pobran;
- intercepted_world_signal: enigmatyczny fragment zgodny tylko z podanym faktem.

Tytul ma miec 2-6 slow. Body ma miec 1-3 krotkie zdania, zaczynac sie w srodku
przekazu i zawierac co najmniej jeden presentation-safe konkret z faktu. Wykonaj
transformacje narracyjna: nie kopiuj ani nie sklejaj title, label, value i stat
jako calego body. Nie dopisuj przyczyn, skutkow, sprawcow, lokalizacji ani
funkcji, ktorych nie ma w fakcie.

Rok 2108 jest perspektywa glosu, nie informacja do literalnego wypisania. Nie
uzywaj wypelniaczy `w roku 2108`, `w rejonie celu`, `w globalnym zasiegu` ani
`odnotowano`. Nie pisz raportu, digestu lub metakomunikatu. Nie przepisuj
observed_at, valid_until, region_id, lat/lng ani technicznych identyfikatorow.

fact_refs musi zawierac dokladnie jedyny fact_ref z facts. cta_ref zawsze null;
canonical nawigacje dopina backend. Zwracaj wylacznie JSON zgodny ze schema.
