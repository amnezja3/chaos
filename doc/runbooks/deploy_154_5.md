# Wdrożenie przyrostowe 154.5.0 — kreatory i menu mapy PL/EN

718 kluczy, osiem domen. To przyrost sprintu 154, nie jego pełne zakończenie.
EN pozostaje testowe. Brak nowych zależności i migracji bazy. Nowe projekty
utrwalają `presentation_locale` w istniejącym JSON projektu; historyczne
produkty i teksty autorów pozostają zachowane. Nie zmieniaj flag rolloutów.

Komendy na VPS wykonuj po kolei; po błędzie zatrzymaj wdrożenie.

## Pobranie

```bash
cd ~/app/chaos
git status --short
git rev-parse HEAD > /tmp/chaos-before-154-5.commit
git pull --ff-only origin main
git log -1 --oneline
```

Oczekiwane: czyste repo przed pull; commit `feat: ship 154.5 creator and map localization`.
Nie nadpisuj lokalnych zmian ani danych. Nie uruchamiaj naprawy FM.

## Testy przed restartem

```bash
.venv/bin/python tools/run_isolated_tests.py tests.test_ghost_i18n tests.test_map_action_locale tests.test_creator_policy tests.test_creator_routes tests.test_creator_legacy tests.test_creator_migration tests.test_captured_object_menu tests.test_ghostlab_scanner
```

Oczekiwane: `Ran 78 tests`, końcowe `OK`. Testy używają katalogu tymczasowego, a testy skanera
kontrolowanych odpowiedzi Overpass, w tym symulowanych timeoutów.

```bash
for test in test_ghost_i18n test_ghost_i18n_runtime test_locale_frame test_registration_locale test_map_action_locale test_creator_ux_contract test_creator_picker_handoff test_ghostlab_scanner test_ghostlab_scanner_preview; do
  node "tests/js/$test.js" || break
done
```

Oczekiwane: dziewięć wyników PASS/OK; każdy błąd zatrzymuje odbiór.
Diagnostyka `missing_key` w testach fallbacku jest oczekiwana.

## Restart i kontrola HTTP

```bash
pm2 reload chaos
pm2 status
pm2 logs chaos --lines 60 --nostream
curl -fsS 'https://chaos.re/static/locales/manifest.json?v=154.5.0'
```

Oczekiwane: `chaos` online, brak nowych tracebacków, manifest `154.5.0`
z domenami `map_actions`, `creators`, `map_workspace` i pozostałymi pięcioma.
Worker terytoriów i Ollama nie wymagają restartu.

Sprawdzenie całego pakietu na publicznym adresie:

```bash
.venv/bin/python - <<'PY'
import json
from urllib.request import urlopen
base = 'https://chaos.re/static/locales/'
def read(path):
    with urlopen(base + path + '?v=154.5.0', timeout=20) as response:
        return json.load(response)
manifest = read('manifest.json')
assert manifest['content_version'] == '154.5.0', manifest['content_version']
for locale in ('pl', 'en'):
    keys = set()
    for domain in manifest['domains']:
        catalog = read(locale + '/' + domain + '.json')
        assert catalog['content_version'] == '154.5.0', (locale, domain)
        assert not keys.intersection(catalog['messages']), (locale, domain)
        keys.update(catalog['messages'])
    assert len(keys) == 718, (locale, len(keys))
    print(locale, '718 keys OK')
PY
```

Oczekiwane: `pl 718 keys OK` i `en 718 keys OK`. Przy rozbieżności sprawdź
cache statyków, nie mieszaj wersji manifestu i katalogów.

Po restarcie odśwież pulpity klientów. Odbiór: PL → EN → PL w otwartym
kreatorze zachowuje tekst i przeznaczenie; nowe projekty otrzymują domyślne
teksty wybranego języka; menu mapy i zabezpieczeń zmienia etykiety, zachowując
cel. Własne nazwy i logi skanera nie są tłumaczone. Panel oznaczonego celu,
część wyników backendu mapy, dalsze workspace'y i radio nie są ukończone w tym wydaniu.

## Cofnięcie kodu

Przy czystym repo, jeśli odbiór ujawni regresję:

```bash
git switch --detach "$(cat /tmp/chaos-before-154-5.commit)"
pm2 reload chaos
pm2 status
```

Bez cofania bazy. Odśwież klientów również po cofnięciu. Powrót do linii wydań
po przygotowaniu poprawki: `git switch main`.
