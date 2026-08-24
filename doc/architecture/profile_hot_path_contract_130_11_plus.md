# Profile Hot-Path Contract — Sprinty 130.11–138

Data ustanowienia bramki: 2026-08-23.

Status: `BINDING FOR ALL IMPLEMENTATION FROM SPRINT 130.11 ONWARD`.

## Powód

Manual po Sprintach 130.10.1–130.10.2 potwierdził odzyskanie płynności gry.
Regresja wynikała z podpinania pełnego `profile_json` pod małe operacje runtime:
zwykły odczyt parsował wielomegabajtowy profil, mała mutacja przepisywała go
przez integrity/CAS/LKG, a fan-out potrafił powielać ten koszt dla wielu kont.

Realny profil `main` miał około `34,6 MB`. Od tej chwili brak ciężkiego profilu
w hot pathach jest warunkiem correctness i wydajności, nie opcjonalną
optymalizacją wykonywaną po sprincie.

## Twardy zakaz runtime

Endpoint gameplayowy, mapowy, desktopowy, snapshot/delta/recovery, event hook,
publisher i worker nie mogą w swojej zwykłej ścieżce:

- wywoływać `sync_session_profile()`;
- wywoływać `UserStore.get_profile()` albo `get_profile_with_revision()` tylko
  po to, aby pobrać identity, klan, profesję, target, inventory, operację,
  wiadomość, wallet, terytorium albo stan GN;
- tworzyć `UserProfileManager` dla małej runtime mutation;
- parsować lub kopiować pełnego `users.profile_json`;
- używać `list_profiles()` ani pętli `get_profile()` dla audience fan-out;
- wykonywać JSON projection wszystkich profili per event/request, jeżeli koszt
  nadal wymaga parsowania wielkich rekordów;
- wkładać pełnego profilu do sesji, cache, joba, delty, outboxu albo payloadu
  modelu;
- wykonywać schema init, global reconcile ani pełny profile overlay per request,
  event lub claimed job.

Zakaz dotyczy także ścieżek „tylko raz”, fallbacków oraz error recovery. Fallback
nie może po cichu wracać do ciężkiego profilu.

## Wymagany model

Implementacja najpierw wybiera najmniejszy istniejący source of truth:

- identity/klan/profesja: integrity-gated, wąska projekcja lub dedykowany indeks;
- targety: `PlayerTargetRuntimeStore` i `PlayerMarkedTargetStore`;
- aplikacje/narzędzia/storage: canonical inventory stores;
- wallet: canonical wallet balance/ledger;
- operacje i wiadomości: ich runtime stores;
- terytoria, ownership i konflikty: territory stores/snapshoty;
- GhostNetwork: viewer projection z tabel GN;
- audience fan-out: trwały indeks odbiorców/klanów albo bounded sparse lookup,
  nigdy pełne profile wszystkich graczy.

Jeżeli potrzebnej lekkiej projekcji nie ma, sprint ma ją najpierw dodać i
zmigrować. Nie wolno implementować funkcji przez tymczasowy full-profile path z
obietnicą późniejszej optymalizacji.

## Jedyny wyjątek

Pełna ścieżka profilu jest dopuszczalna tylko dla:

1. jawnego audit/forensics/recovery dokładnie jednego wskazanego konta;
2. rzeczywistej trwałej mutacji pól, które nadal kanonicznie należą do profilu;
3. jawnego verify/checksum/LKG/promotion.

Wyjątek wymaga nazwanego call site i testu. Przy write przygotowanie, overlay,
walidacja, serializacja, checksum i LKG odbywają się przed `BEGIN IMMEDIATE`;
pod writer-lockiem pozostają revision/checksum recheck, session precommit,
CAS, właściwy zapis, atomowy LKG i commit. Nie wolno skanować innych kont.

Sprint 130.11 może korzystać z heavy path wyłącznie w operatorskim narzędziu
repair dla exact canonical `Trollu2`. Jego status/audit/plan/verify nie stają się
endpointem runtime ani helperem używanym przez worker.

## Obowiązkowa bramka każdego sprintu

Przed implementacją:

1. zinwentaryzować wszystkie nowe i dotknięte call sites profilu;
2. przypisać każde wymagane pole do canonical store/projection;
3. wskazać jawnie, czy istnieje dozwolony heavy call site; domyślnie: nie;
4. zmierzyć baseline `[HOT_PATH]` dla dotkniętych endpointów lub metryki workera.

Testy muszą wymuszać:

- `profile_full_read=0` i `profile_full_write=0` dla zwykłego requestu/eventu;
- `profile_bytes=0` dla ścieżek, które nie zwracają pełnego `/api/profile`;
- zero `sync_session_profile`, `UserProfileManager`, `list_profiles` i
  per-recipient `get_profile` w snapshot/delta/fan-out/worker;
- ten sam wynik dla małego konta oraz syntetycznego profilu co najmniej 35 MB;
- bounded query count niezależny od rozmiaru profilu;
- brak pełnego profilu w logach, sesji, cache, delcie, outboxie i tasku Ollamy;
- brak dodatkowej pracy pod SQLite writer-lockiem.

Jeżeli ścieżka wykonuje dozwolony pełny write, test ma udowodnić dokładnie jeden
heavy read/write, przygotowanie przed lockiem i brak skanu innych użytkowników.

## Bramka GO

Każdy Sprint 130.11–138 kończy się zestawieniem:

```text
PROFILE HOT PATH AUDIT
new runtime call sites: <n>
profile_full_read: 0
profile_full_write: 0
profile_bytes: 0
list_profiles/all-user scans: 0
per-recipient profile reads: 0
allowed heavy recovery/write call sites: <jawna lista albo none>
```

Niespełnienie któregokolwiek z zer dla zwykłego runtime daje `NO-GO`, nawet gdy
funkcja gameplayowo działa. Nie podnosimy timeoutów i nie maskujemy regresji
animacją, cachem ani retry.
