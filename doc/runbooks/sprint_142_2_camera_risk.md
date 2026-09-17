# 142.2 — kamery a publiczne ryzyko

Reguły zatwierdzone przez autora 17 IX 2026. Implementacja lokalna: **46 testów PASS**;
odbiór produkcyjny tego etapu jeszcze nie został wykonany.

## Kontrakt

- Kamera przy obiekcie dodaje osobny składnik +4. Co najmniej jeden ważny
  shutdown zeruje składnik, również gdy pozostałe kamery nadal działają.
  Wyłączenie dwóch nie daje dodatkowej zniżki.
- Zakres: własne operacje gracza przy obiekcie wskazanym przez serwerowy
  parent_target_id. Inni gracze i inne obiekty nie korzystają z osłony.
- Pozostałe składniki, w tym alarm i aktywne zdolności, nadal działają.
  Przy znanej ekspozycji security.camera nie jest liczona drugi raz.
- Istniejący incydent otrzymuje niższy wkład, nie znika po zejściu poniżej
  progu inicjacji. Nie cofamy kar. Timeout/cancel ostatniej operacji oraz
  pełna trwałość publikacji pozostają osobnym zakresem 142.3.

## Dane i koszt

Builder zapisuje camera_exposure z serwerowego player_scan_snapshots:
zweryfikowane współrzędne obiektu, owner, scan_id, scope i ID kamer.
Nie korzysta z klientowego camera_disabled ani deklarowanej liczby kamer.
Dowód zostaje w operation_json po nowym scanie, TTL, reconnect i restarcie.
Brak aktualnej obserwacji oznacza known=false, nie dowód braku kamer.
Stare operacje bez ekspozycji zachowują dotychczasowy kalkulator; do odbioru
użyć nowego scanu i nowych operacji. camera_shutdown nie nalicza sobie +4.

Worker pobiera jednym indeksowanym SELECT-em maksymalnie 512 aktywnych
shutdown danego gracza, wyłącznie z dowodem camera_evidence.schema=1.
Nie czyta archiwum terminalnych operacji ani pełnych profili. Stan wygaśnięcia
liczony jest z expires_at; anulowanie usuwa osłonę przy następnym ticku.
Nie ma dodatkowego odczytu per kamera/per operacja w ticku. Zmiana ryzyka
i map.operations_changed zapisują się w tej samej transakcji CAS.
Awaria delty wycofuje zapis; kolejny tick ponawia projekcję.
Istniejący handler map.operations_changed odświeża listę operacji.

## Weryfikacja

17 IX 2026: poniższy zestaw zakończył się wynikiem **46/46 PASS** (15,880 s).
`git diff --check` bez błędów. Nie wykonywano odbioru UI ani deployu.

Uruchomienie w izolowanym katalogu, na tymczasowych bazach:

```powershell
python -B tools/run_isolated_tests.py test_camera_exposure test_camera_shutdown_contract test_operation_risk_meter test_incident_initializer test_camera_incident_audit
```

Nowe przypadki: canonical shutdown → 62 do 58 heat, brak kumulacji,
incydent poniżej progu, wspólny incydent i częściowy batch, reset scanu/TTL,
odtworzenie ze store, expiry/cancel, obcy gracz/obiekt, niezweryfikowany
shutdown, brak kamer/obserwacji, sfałszowane pola, profil 35 MB bez pełnego
I/O, delta live oraz rollback i ponowienie po awarii delty.

## Deploy i odbiór

Brak migracji danych. Standardowy deploy i restart procesu `chaos` po nazwie.
To nie jest zamknięcie całego 142 ani odbiór publikacji/kar z kolejnych etapów.

1. Nowy scan obiektu z kamerami; uruchomić operację przy tym obiekcie.
   W odpowiedzi summary operacji sprawdzić operation_risk_meter.camera_modifier=4
   i camera_state.detected>0.
2. Wyłączyć jedną kamerę. Po ticku camera_modifier=0, disabled=1;
   lista operacji powinna odświeżyć się bez zamykania mapy.
3. Druga kamera nie zmniejsza składnika poniżej zera. Operacja drugiego
   gracza i innego obiektu zachowuje swój składnik.
4. Nowy scan/reconnect nie resetuje osłony. Po końcu wszystkich shutdown
   składnik wraca do 4. Porównywać ten składnik, ponieważ time_heat rośnie
   niezależnie i całkowite ryzyko nie musi spaść dokładnie o 4 między odczytami.
