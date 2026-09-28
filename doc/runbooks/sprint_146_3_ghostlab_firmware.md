# Sprint 146.3 — firmware: wdrożenie i testy

Status: pakiet przygotowany lokalnie, 28 IX 2026. Odbiór gameplay/UI po wdrożeniu.
Bez commita i pusha w ramach przygotowania pakietu.

## Kontrakt

Nowy szablon `firmware_update`, uruchamiany na własnym pulpicie. Twórca ustala
całkowite wartości: powodzenie 20–80%, przyrost 50–200 MB i 10–100 m. Jeden zakup
opłaca jedną próbę; nie uruchamia jej automatycznie. Gracz potwierdza flashowanie
w aplikacji. Po obu wynikach obowiązuje dokładnie 24 h wspólnego cooldownu konta.

Sukces trwale zwiększa pojemność dysku i zasięg skanu od motocykla. Maksimum:
2 TB = 2 097 152 MB (jednostki binarne istniejącego dysku), 30 km = 30 000 m.
Przyrost jest przycinany do pozostałego miejsca. Jeden osiągnięty limit nie blokuje
drugiego przyrostu. Oba osiągnięte limity blokują zakup/próbę przed opłatą/zużyciem.
Istniejące parametry ponad limitem nie są obniżane. Zajętość dysku nie zmienia się
od sukcesu; instalator aplikacji ma zwykły koszt miejsca przy pierwszej instalacji.

Porażka zużywa próbę bez bonusów i zwrotu HC. Pulpit ciemnieje, pojawiają się
zakłócenia i pełnoekranowy ekran awarii. Tło jest nieaktywne również z klawiatury.
Po 8 s można nacisnąć restart; serwer weryfikuje identyfikator crasha i czas.
Odświeżenie/reconnect przywraca blokadę. Restart usuwa wyłącznie crash, bez
skrótów cooldownu. `prefers-reduced-motion` wyłącza animację zakłóceń.

Nie ma kasowania plików, utraty wcześniejszych bonusów ani dodatkowej kary HC.
Crash jest stanem konta, nie restartem globalnego GhostNetwork. Blokada obowiązuje
na wejściu do żądań i przed commitem zapisu. Odczyt crasha i lokalny restart działają
również przy areszcie; nie zdejmują jego ograniczeń. Inne sesje otrzymują zdarzenie,
a pulpit dodatkowo sprawdza stan po odzyskaniu widoczności i co 15 s.

## Zakup i wersje

- Googleplex potwierdza cenę, ryzyko i rzeczywiste możliwe przyrosty przed zakupem.
- Pierwszy zakup instaluje aplikację i tworzy opłaconą próbę atomowo z płatnością.
  Przychód trafia do twórcy; zakup własnego produktu stosuje dotychczasową zasadę
  bez transferu środków do samego siebie.
- Po zużyciu: kolejny zakup z przycisku w aplikacji, po 24 h. Reinstalacja zbędna.
- Na koncie może czekać jedna niewykorzystana próba rodziny. Chroni to przed
  przypadkowym ponownym płaceniem. Potwierdzenie może być anulowane bez zużycia.
- Próba jest przypisana do wersji i parametrów z chwili zakupu. Darmowa aktualizacja
  aplikacji nie zmienia opłaconej próby ani nie tworzy nowej. Następny zakup korzysta
  z aktualnej publikacji; aplikacja pokazuje parametry próby oddzielnie od wersji instalacji.
- Odinstalowanie nie usuwa próby/bonusów/cooldownu. Przywrócenie aplikacji z istniejącą
  opłaconą próbą nie pobiera drugiej opłaty. Wycofanie sprzedaży nie odbiera już zakupionej próby.
- Powtórzenie klucza zakupu odtwarza rozliczenie; powtórzenie identyfikatora próby
  odtwarza wynik. Awaria transakcji nie pozostawia częściowych skutków ani opłat.

## Wdrożenie

1. Wykonać standardową spójną kopię SQLite aplikacji przed zmianą wersji.
2. Po osobnym zatwierdzeniu i wysłaniu zmian pobrać wersję na serwerze.
3. `pm2 startOrRestart ecosystem.web.config.js --update-env`
4. Zweryfikować proces i logi. Konfiguracja zawiera
   `CHAOS_GHOSTLAB_FIRMWARE_RUNTIME_ENABLED: "true"` i istniejące
   `CHAOS_GHOSTLAB_RUNTIME_ACTORS: "*"` — dostęp dla wszystkich graczy.
5. Odświeżyć pulpit. Szablon ma być widoczny w GhostLab oraz panelu admina.

Schema powstaje idempotentnie przy starcie: `ghostlab_firmware_state` i
`ghostlab_firmware_attempts`, z unikatową oczekującą próbą na konto. Nie uruchamiać
migracji pełnych profili ani modyfikacji historycznych publikacji.

Wyłączenie: flaga runtime `false` i restart PM2 z `--update-env`. Nowe zakupy
i wykonania są blokowane, wcześniejsze bonusy zostają. Odczyt crasha i restart
pozostają dostępne przy wyłączonym runtime. Nie usuwać tabel z historią, cooldownami
ani stanem awarii. Preferować wyłączenie wykonawcy zamiast cofania kodu sprzed
146.3: stary kod nie egzekwuje nowego crasha i nie dolicza bonusu skanu.

## Skoordynowany test gameplayowy

Przygotować autora i co najmniej dwa inne konta kupujących, bez aresztu.
Jeden firmware 80% i drugi 20% zwiększają szansę obejrzenia obu wyników,
ale wynik nadal jest losowy. Nie wyłączać ani nie skracać produkcyjnego cooldownu.

1. Autor: utworzyć, walidować, skompilować i opublikować; sprawdzić granice pól.
2. Kupujący A: zanotować HC, pojemność, zajętość i zasięg. Kupić produkt:
   jeden debit/credit, jedna instalacja, jedna dostępna próba. Anulować pierwsze
   potwierdzenie flashowania — próba ma pozostać dostępna.
3. Uruchomić i zapisać wynik. Sukces: dokładny przyrost, po reconnectcie nadal jest;
   skan tuż poza starym zasięgiem działa. Podróż, ataki i radar służb bez bonusu.
4. Kupujący B: osobna próba. Porażka: brak bonusu, crash całego pulpitu,
   odświeżenie nie odblokowuje. Restart odzyskuje pulpit, cooldown pozostaje.
   Sprawdzić desktop, mobile i ograniczenie animacji. Jeśli oba konta mają ten sam
   wynik, drugi wynik odebrać na kolejnym koncie albo po 24 h.
5. W obu przypadkach drugi produkt tej rodziny i reinstalacja nie obchodzą 24 h.
   Po 24 h nowy zakup i nowa próba są możliwe; sukcesy kumulują bonusy.
6. Przed użyciem opłaconej próby autor publikuje nową wersję. Darmowo zaktualizować
   aplikację: próba zachowuje zakupione parametry. Po jej zużyciu aktualizacja
   nie daje następnej próby. Następny zakup stosuje nową wersję.
7. Sprawdzić przywrócenie odinstalowanej aplikacji z niewykorzystaną próbą oraz
   wykonanie wcześniej zakupionej próby po wycofaniu publikacji.

Granice 2 TB/30 km, transakcje, utrata odpowiedzi, współbieżność, wyłączenie runtime,
areszt i bezciężarowe ścieżki są sprawdzane lokalnie automatycznie. Nie trzeba
budować tysięcy sukcesów na koncie produkcyjnym, aby odebrać limity.

## Testy lokalne

28 IX 2026: 88 testów backendu z poniższego zestawu — PASS; pięć zestawów JS — PASS.
Kontrola składni JS oraz `git diff --check` — PASS. Testy backendu korzystały wyłącznie
z baz tymczasowych. Zmiany pozostają lokalne, bez wdrożenia na serwer.

Backend uruchamiać wyłącznie przez izolowany runner:

```text
python -B tools/run_isolated_tests.py tests.test_ghostlab_firmware tests.test_ghostlab_maintenance tests.test_ghostlab_registry tests.test_ghostlab_runtime tests.test_ghostlab_travel tests.test_ghostlab_mutation_runtime
node tests/js/test_ghostlab_firmware.js
node tests/js/test_ghostlab_maintenance.js
node tests/js/test_ghostlab_runtime.js
node tests/js/test_ghostlab_travel.js
node tests/js/test_googleplex_app_purchase_lock.js
```

Test JS weryfikuje interakcje, nie zastępuje wizualnego odbioru w przeglądarce.
Odbiór wyglądu crasha i układu mobile pozostaje w powyższej checkliście gameplayowej.
