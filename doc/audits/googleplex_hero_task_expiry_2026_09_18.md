# 142.3 — hero znika po zakończeniu terminu zadania

Odczyt produkcyjny: sześć slotów redakcyjnych pozostaje active; world-grid
jest invalidated z powodem task_expired. Nie jest to zastąpienie hero przez
produkt. Pięć kart ma nadal datę publikacji 5 września, produkt 17 września;
status active nie dowodzi, że wszystkie odświeżenia Stage II już przeszły.

Przyczyna: maintain_narrative_freshness wygaszało także zakończone,
opublikowane taski blacknet_world, ukrywając ich medium records.
Termin wykonania zadania mógł minąć, chociaż incydent nadal był aktualny.

Mała poprawka: opublikowane intercepted_incident_alert nie są usuwane przez
deadline generacji. Nadal podlegają kanonicznej wersji narracji, zamknięciu
incydentu i końcowi cooling. Nieopublikowane wyniki nadal wygasają przed
generacją i przed commit. Pozostałe typy narracji zachowują obecny lifecycle.
Nie przywracamy historycznych, już unieważnionych wpisów.

Walidacja: 19 testów incident_narrative_retirement i narrative_freshness PASS
(18,183 s); osobny test coexistence produktu oraz dwóch kolejnych hero PASS.
Izolowane bazy, brak modyfikacji produkcji. Odbiór po deployu: świeży hero
nie znika wyłącznie z powodu terminu taska, ale znika po zamknięciu źródła.
