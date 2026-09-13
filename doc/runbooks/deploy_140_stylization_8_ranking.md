# 140.stylization.8 — gracze i ranking

Poprawka odczytu avataru/LVL w historycznym podglądzie: serwis rankingu
korzysta z `repository._conn()`, również gdy `HistoricalReader` nie ma
`db_path`. Wcześniej przechwycony AttributeError pozostawiał oba pola puste.
Test z rzeczywistym HistoricalReader i `PRAGMA query_only=ON` potwierdza
odczyt avataru i LVL. 13 testów rankingu/podglądu PASS.
Po pobraniu poprawki należy ponownie wygenerować HTML; istniejący podgląd
zawiera stare dane i nie zostanie naprawiony przez samo odświeżenie strony.

Poprawka ranking-2: usunięto dwa operatory `??` nieobsługiwane przez
serwerowy Node 12.22.9. Jawne sprawdzenie null/undefined zachowuje RSP = 0.
Pięć zestawów JS ponownie PASS lokalnie (Node 24); test na Node 12 należy
powtórzyć na serwerze poniższymi poleceniami.

Wdrożony zaakceptowany układ graczy: avatar 2:3, mniejszy nick, klan,
LVL, RSP i pozycja w rogu avataru zmniejszona o 50%. Wspólny CSS z referencją.
Obejmuje `players`, `achievements` oraz `player_ranking`. Nagrody i ranking
klanów zachowują wcześniejszą prezentację; ta zmiana nie zamyka całej grupy .8.

Sceny 660–700 s mają jeden przebieg, po 40/N sekund na osobę, bez resetu
na 680 s. Ranking 840–855 s pokazuje osoby w kolejności archiwum, po 15/N s.
Lista pozostaje obok; przy większej liczbie wierszy jej okno przesuwa się
do aktywnej pozycji. Projekcja nadal obejmuje maksymalnie 20 graczy, a jej
obcięcie jest oznaczone. Nie pokazujemy niepełnej listy jako pełnego rankingu.

Nowy ranking zapisuje avatar i LVL przy finalizacji: jeden odczyt dwóch
skalarnych pól SQL dla uczestników, wyłącznie z profili ze statusem valid.
Nie pobiera profile_json do Pythona, nie hydratuje profili i nie dodaje
odczytów do pollingu. Publiczna projekcja dopuszcza tylko systemowe avatary.
Nie ma migracji schematu. Nie przepisujemy historycznych rankingów.

Historyczny generator podglądu może uzupełnić brakujący avatar i LVL aktualnymi
danymi; podpis brzmi „PODGLĄD / AKTUALNY AVATAR I LVL”. Nick, klan, pozycja
i RSP pozostają z archiwum. Brak poziomu: —; brak avataru: systemowy fallback.

## Sprawdzenie na serwerze

Po push/pull uruchom:

```bash
node tests/ghost_signal_show_frontend.test.js &&
node tests/ghost_signal_show_recovery.test.js &&
node tests/ghost_signal_show_manifest.test.js &&
node tests/ghost_signal_show_montage.test.js &&
node tests/ghost_signal_show_audio.test.js &&
node --check static/js/ghost_signal_show.js
```

Po PASS:

```bash
pm2 reload chaos &&
pm2 reload chaos-territory-worker &&
.venv/bin/python -B tools/build_ghostsignal_show_preview.py \
  --db data/game.sqlite3 --cycle-id ghostnetwork_0001 \
  --output static/previews/ghostsignal-stylization-8-ranking-3.html
```

Oceń desktop i portrait w 11:00–11:40 oraz 14:00–14:15: ramkę 2:3,
nick/klan, mały numer, pojedynczą prezentację i zgodność aktywnej pozycji listy.
Trigger produkcyjny pozostaje odłożony.

Lokalnie: 8 testów Pythona rankingu PASS w izolowanym katalogu,
5 zestawów JS PASS, składnia JS i diff check PASS.
