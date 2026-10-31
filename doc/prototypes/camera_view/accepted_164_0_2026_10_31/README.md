# Zaakceptowany wzorzec Camera Street View — 31.10.2026

Operator nadał PASS głównemu podglądowi, standardowemu oknu, efektom zakłóceń
i braku sygnału. Ten niezmienny snapshot zabezpiecza warstwę prezentacji przed
dalszą implementacją sprintów 164–166. Nie jest osobnym demonstratorem.

`manifest.json` zawiera listę plików, rozmiary i SHA-256. Kopie odczytano ponownie
i sprawdzono po zapisie. Odtworzenie wybranego pliku musi być świadome;
nie przywracać całego katalogu nad bieżącym kodem. Skrypt tworzący checkpoint
`tools/freeze_camera_presentation.js` odmawia nadpisania istniejącego snapshotu.

Zakres: renderer i CSS, linki CHAOS, ikona, trzy zdjęcia, sześć efektów, testy UI,
zrzuty oraz ówczesna tablica i audit. Historyczne testy zawierają dawny reopen;
to materiał porównawczy, nie kontrakt nowego gameplayu. Baza i sekrety wyłączone.

Snapshot nie zawiera backendu ani kompletnego środowiska uruchomieniowego.
`camera_visual.py` był już w trakcie przebudowy po nowej decyzji operatora.
Nie wolno przypisywać jego zmianom PASS prezentacji. Nowy kontrakt: rzeczywisty
czas operacji z Super Powers, ręczne zamknięcie zużywa dostęp; kolejny feed
wymaga nowego hakowania i pobrania. Zdjęcia graczy nadal wyłączone.
