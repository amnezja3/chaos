# Sprint 160 — porównanie transportów VK

Operator potwierdził pełne zapytanie curl: HTTP 200 / 16,437 s, 679 obiektów,
417 node + 262 way, remark=null, IP 95.163.216.90. Kolejna próba przez Python
przekroczyła odczyt 25 s. Próby w różnym czasie nie rozstrzygają, czy przyczyną
jest transport, wybrany adres czy obciążenie operatora.

## Narzędzie

`tools/poi_transport_compare.py` wykonuje najwyżej dwa sekwencyjne żądania:
Python, następnie curl. Oba używają:

- tego samego zapytania 300 m, stały publiczny punkt Warszawy, pełne filtry;
- identycznych bajtów formularza, User-Agent i Accept/Accept-Encoding;
- HTTP/1.1, tego samego publicznego IP, pierwotnej nazwy hosta/SNI i weryfikacji TLS;
- QL timeout 25 s i limitu całkowitego 35 s na transport;
- braku proxy środowiskowego, przekierowań i automatycznych powtórzeń.

Python dostaje odczyt do pozostałego deadline (maksymalnie 35 s), a nie osobny
limit 25 s wcześniejszego narzędzia. Curl ma max-time=35. Pomiar czasu curl
zaczyna się wewnątrz curl; Python total obejmuje start procesu potomnego.
Curl connect-timeout=3 obejmuje zestawienie połączenia; Python zachowuje
istniejące osobne limity TCP i TLS po 3 s. Są to jawne różnice semantyki,
nie obietnica identycznego zachowania dwóch bibliotek we wszystkich fazach.

Pinning jest dopuszczany tylko do IPv4 z aktualnego, sprawdzonego publicznego
DNS hosta. Python ponownie weryfikuje przypięty adres w procesie potomnym.
Nie dodano opcji wyłączenia certyfikatu ani dowolnego prywatnego IP.

Trace Pythona zawiera IP, etap, czas zestawienia TCP/TLS, otrzymania nagłówków,
liczbę bajtów i ukończenie body. Wyjątek zachowuje trace. Twarde zabicie procesu
przy deadline może zwrócić trace_unavailable=true. Czas nagłówków Pythona to
odbiór całych nagłówków, a time_starttransfer curl mierzy pierwszy bajt — nie
należy traktować ich jako dokładnie tego samego zdarzenia.

## Ograniczenia operacyjne

Istniejąca konfiguracja i zakresy registry nie są modyfikowane. Wymagany ważny
udany small_probe. Świadome --execute dotyczy tylko tej pary diagnostycznej.
Oba wywołania używają wspólnego slotu, circuit oraz tej samej blokady 15 minut
co controlled_scan. Każda próba ponownie sprawdza rewizję kandydata. Przy 429
lub Retry-After druga próba jest pomijana, a cooldown respektowany w bazie.
Raporty trafiają do obserwacji zdrowia. Curl przechowuje body tylko w usuwanym
katalogu tymczasowym. Nie zapisuje POI do cache/world ani nie aktywuje gry.

Domyślne uruchomienie bez --execute sprawdza DNS i konfigurację, ale nie wysyła
zapytań Overpass. Po wygaśnięciu limitu diagnostyki na VPS:

```bash
cd ~/app/chaos
git pull --ff-only
.venv/bin/python tools/poi_transport_compare.py --db data/poi_cache.sqlite3 --execute
```

Bez restartu. Wynik może pojawić się po około 70 sekundach. Sekwencja i cache
dostawcy mogą wpływać na wynik; pojedyncza para nie daje dowodu przyczynowego.

Walidacja lokalna: 2 testy narzędzia (curl mockowany), 10 secure transport,
2 wire contract na lokalnym serwerze — PASS. Nie wykonano publicznych zapytań
VK w ramach testów lokalnych. Wynik porównania na VPS pozostaje do zebrania.
