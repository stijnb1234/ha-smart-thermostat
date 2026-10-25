# Smart Heating – Handleiding

*English version: [manual.en.md](manual.en.md)*

Smart Heating regelt de verwarming per kamer: elke kamer wordt warm wanneer dat nodig is, en de cv-ketel brandt alleen als een kamer echt warmte vraagt. Je hoeft er meestal niets voor te doen; deze handleiding legt uit wat er gebeurt en wat je ziet op het scherm Overzicht.

## In het kort

In huis is één cv-ketel en hangen verschillende radiatoren. Normaal stookt de ketel voor het hele huis tegelijk. Smart Heating kijkt per kamer: alleen een kamer die op dat moment warm moet zijn, krijgt warmte. Kamers waar niemand is, blijven koeler. Zo bespaar je gas zonder dat je het koud hebt.

Dat werkt zo:

- **Slimme radiatorkranen** op de radiatoren openen en sluiten vanzelf. Elke kraan krijgt van Smart Heating te horen hoe warm zijn kamer moet zijn.
- **De cv-ketel** gaat alleen branden als minstens één kamer warm moet zijn en nog duidelijk te koud is. Op het scherm heet de ketel ‘boiler’.
- **Elke kamer heeft een schema**: de tijden waarop het daar warm moet zijn. Buiten die tijden zakt de kamer naar een lagere temperatuur.
- **Het systeem let op wat er in huis gebeurt**: is iedereen weg, staat er een raam open, ben je met vakantie? Dan past het de temperatuur vanzelf aan.
- **Het leert je huis kennen.** Elke kamer warmt en koelt op zijn eigen manier. Smart Heating merkt hoe, en gebruikt dat om op tijd te beginnen, een open raam sneller te herkennen en de ketel uit te zetten voordat de kamer te warm wordt.
- **Kamers zonder slimme kraan doen ook mee.** Zolang niet elke radiator een slimme kraan heeft, nemen die kamers toch deel, en zorgen ze ervoor dat het huis niet warmer wordt dan je wilt.

Je hoeft er dus meestal niets voor te doen. Wil je het eens anders, dan zijn er een paar knoppen, zoals **Boost** om een kamer nu meteen warm te stoken.

## Het scherm Overzicht

Klik in de zijbalk van Home Assistant op **Smart Heating**. Je komt dan meteen op het Overzicht: het eerste icoontje linksboven, het huisje. Hier zie je in één keer wat de verwarming doet, en hier staan alle knoppen die je nodig hebt. De andere icoontjes (een radiator, een ketel en een vraagteken) zijn de tabbladen Verwarming, Boiler en Help. Die zijn bedoeld voor de beheerder; je kunt ze gewoon laten liggen.

Links staat het blok **Nu**, rechts staan de knoppen. Is er iets mis, dan verschijnt er ook een blok **Meldingen**. Op een telefoon staan de blokken onder elkaar in plaats van naast elkaar.

### Nu

Bovenaan staat één korte zin over het hele huis, bijvoorbeeld:

> Verwarmen: Woonkamer, Slaapkamer. Boiler aan.

- **Verwarmen:** de kamers die nu nog te koud zijn en waar de radiator dus open staat. Staat er *Er wordt niets verwarmd*, dan zijn alle kamers op temperatuur.
- **Boiler aan / Boiler uit:** of de cv-ketel op dit moment gevraagd wordt om te branden.
- Soms staat er nog iets achter: *Niemand is thuis.* of *Vakantiemodus staat aan.*

Daaronder staat *Geen meldingen.* Is er iets mis, dan staat daar bijvoorbeeld **2 meldingen hebben aandacht nodig**.

Dan volgt een tabel met één regel per kamer:

| Kolom | Wat je ziet |
| --- | --- |
| Ruimte | De naam van de kamer. |
| Nu | Hoe warm het nu in de kamer is. Een streepje (–) betekent dat de temperatuur even niet bekend is. |
| Doel | De temperatuur waar de kamer nu naartoe werkt. |
| Wat gebeurt er | Een korte zin, zoals *Warm tot 23:00*. Wat al die zinnen betekenen, staat in de volgende paragraaf. |

### Meldingen

Dit blok verschijnt alleen als er iets aandacht nodig heeft, bijvoorbeeld een bijna lege batterij. Zie je het niet, dan is alles in orde. Elke melding staat er als gewone zin; verderop in deze handleiding lees je wat je ermee kunt.

### Bediening

Hier staan de knoppen:

- **Terug van vakantie** (een datum en tijd) en **Vakantiemodus** (een aan/uit-schakelaar): voor als je een paar dagen weg bent.
- **Handmatige ruimte-override** en **Handmatige ruimte-override annuleren**: voor kamers zonder slimme kraan.
- In een apart blok **Boost**: voor elke kamer een knop **Boost** en een knop **Boost annuleren**, bijvoorbeeld *Slaapkamer: Boost*.
- Onderaan een link naar de Smart Heating-opties (schema’s en temperaturen per kamer). Die is bedoeld voor de beheerder.

Hoe je de knoppen gebruikt, staat bij [De knoppen](#de-knoppen) verderop.

## Wat de zin bij een kamer betekent

In de kolom *Wat gebeurt er* staat per kamer één zin. De tijden en temperaturen hieronder zijn voorbeelden. Ligt een tijdstip niet vandaag, dan staat de dag erbij, bijvoorbeeld *ma 07:00*.

| Je ziet | Wat het betekent |
| --- | --- |
| Warm tot 23:00 | Het schema zegt dat het hier nu warm moet zijn, tot 23:00. |
| Warm | Het is hier warm en er staat geen eindtijd gepland. |
| Warm vanaf 07:00 | Nu staat de kamer lager. Om 07:00 begint de volgende warme periode. |
| Op 16 graden gehouden | De kamer staat op de lagere temperatuur en er is niets gepland. |
| Opwarmen, warm tot 17:00 | De kamer is al eerder begonnen met opwarmen, zodat hij op tijd warm is. |
| Boost tot 14:00 | Iemand heeft op Boost gedrukt. De kamer is warm tot 14:00, of tot je de Boost annuleert. |
| Raam lijkt open, verwarming gepauzeerd tot 14:20 | De kamer koelde heel snel af. Waarschijnlijk staat er een raam open, dus de verwarming wacht even. |
| Niemand thuis, op 16 graden gehouden | Iedereen is weg. Na twee dagen weg zakt dit naar 12 graden. |
| Persoon van deze ruimte is weg, op 16 graden gehouden | Deze kamer hoort bij iemand die nu weg is, dus het schema wordt overgeslagen. De kamer warmt weer op als die persoon thuis of onderweg is. |
| Wacht tot de vloerverwarming is opgewarmd, op 12 graden gehouden | De vloerverwarming warmt eerst op. Kamers die nu niet gebruikt worden, houden hun radiator zolang dicht. |
| Handmatig ingesteld op 22 graden, tot 17:00 | Iemand heeft de kraan zelf verdraaid. Die stand blijft tot 17:00, daarna neemt het schema het weer over. |
| Vakantie tot za 16:20, op 12 graden gehouden | De vakantiemodus staat aan. De kamer blijft net boven het vriespunt tot die tijd en warmt dan op, zodat het aangenaam is als je terug bent. |

## Wanneer wordt een kamer warm?

Elke kamer kent drie temperaturen. De beheerder kan ze per kamer aanpassen; dit zijn de standaardwaarden:

| Temperatuur | Standaard | Wanneer |
| --- | --- | --- |
| Comfort | 19,5 °C | Als het volgens het schema warm moet zijn, of na een Boost. |
| Lager | 16 °C | Buiten het schema, of als niemand thuis is. |
| Vorstbeveiliging | 12 °C | Bij vakantie, als je langer dan twee dagen weg bent, of als er een raam open lijkt te staan. Net warm genoeg om het huis te beschermen. |

### Het schema

In het schema staat wanneer een kamer warm moet zijn. De beheerder kiest er per kamer een, bijvoorbeeld:

- **Woonruimte:** elke dag van 06:00 tot 23:00.
- **Werkkamer:** maandag, woensdag en vrijdag van 08:00 tot 17:00.
- **Slaapkamer:** tijdens de werkuren, plus even opwarmen voor het slapengaan (21:30 tot 22:30).

Het schema aanpassen doet de beheerder in de instellingen.

### Op tijd warm

Een kamer begint al voor de geplande tijd met opwarmen, zodat hij op tijd warm is. Hoe vroeg hangt af van hoe koud de kamer nu is: een kamer die flink is afgekoeld (na een weekend weg bijvoorbeeld) begint eerder dan een kamer die nog redelijk warm is. In het begin schat het systeem dat; daarna leert het per kamer hoe snel opwarmen echt gaat, ook afhankelijk van hoe koud het buiten is. Is het opwarmen eenmaal begonnen, dan gaat het door tot het schema begint. Je ziet dan *Opwarmen* bij de kamer staan. Meer daarover bij [Het systeem leert](#het-systeem-leert).

### Wie wint er?

Soms gelden er meerdere dingen tegelijk. Dan wint de bovenste uit dit rijtje:

1. **Boost**: je wilt het nu warm.
2. **Open raam**: de verwarming pauzeert even.
3. **Vakantie**: het hele huis op vorstbeveiliging.
4. **Niemand thuis**: alle kamers op de lagere temperatuur.
5. **Het schema**, met op tijd opwarmen. Hoort de kamer bij iemand die weg is, dan wordt het schema overgeslagen.
6. Anders: **de lagere temperatuur**.

## Wat het systeem vanzelf doet

Deze dingen gebeuren automatisch. Je hoeft er niets voor te doen.

- **Raam open:** koelt een kamer ineens sneller af dan hij normaal doet, dan gaat het systeem ervan uit dat er een raam open staat. De verwarming in die kamer pauzeert dan een kwartier tot een half uur, zodat je niet de straat verwarmt. Het systeem kijkt hiervoor naar de thermometer in de radiatorkraan, want die zit meestal dicht bij het raam en merkt tocht als eerste. Vlak na het verwarmen koelt de radiator zelf nog af en daalt die thermometer mee; dat uur telt alleen de thermometer van de kamer zelf, zodat dit niet voor een open raam wordt aangezien. Wat ‘ineens’ is, leert het systeem per kamer, zie [Het systeem leert](#het-systeem-leert).
- **Niemand thuis:** is iedereen de deur uit, dan gaan alle kamers naar de lagere temperatuur (16 °C). Ben je langer dan twee dagen weg, dan zakt het huis naar vorstbeveiliging (12 °C). Die twee dagen tellen vanaf het moment dat de laatste persoon vertrok.
- **Kamer van iemand die weg is:** een kamer kan bij bepaalde personen horen, bijvoorbeeld een werkkamer. Zijn die allemaal weg, dan blijft die kamer op de lagere temperatuur, ook als het schema iets anders zegt. Een Boost werkt wel gewoon.
- **Onderweg naar huis:** staat de Home Assistant-app met locatie op je telefoon, dan ziet het systeem dat je dichterbij komt en schat het wanneer je thuis bent. Op tijd om op te warmen begint het huis te verwarmen, zodat het warm is als je binnenkomt. Niets in te stellen, geen zones.
- **Vloerverwarming:** vloerverwarming is traag. Een kamer met vloerverwarming begint daarom al een paar uur voor de geplande tijd. Zolang die opwarmt, blijven de radiatoren in kamers die niet gebruikt worden dicht, zodat de warmte naar de vloer gaat.
- **Kamers zonder slimme kranen:** die vragen om warmte als het er koud is en zetten de ketel uit zodra het warm genoeg is. Zie [Kamers zonder slimme kranen](#kamers-zonder-slimme-kranen).
- **Een kamer die niet warmer wordt:** vraagt een kamer al driekwartier om warmte en is hij nauwelijks warmer geworden, dan krijg je een melding. Zie [Meldingen](#meldingen-1).
- **Kraan uitgezet:** staat een slimme radiatorkraan uit, dan zet het systeem hem vanzelf weer aan.
- **Weekrapport:** elke maandag om 08:00 krijg je een bericht in Home Assistant (bij het belletje). Daarin staat hoeveel gas er is gebruikt vergeleken met vorig jaar, rekening houdend met hoe koud het was, hoeveel uur elke kamer verwarmd is en of er problemen waren. Heeft het systeem een gewoonte van je opgemerkt, dan staat er ook een suggestie voor het schema in.

## Kamers zonder slimme kranen

Misschien heeft nog niet elke kamer een slimme kraan. De radiatoren daar staan de hele tijd open (of je draait ze met de hand), dus Smart Heating kan ze niet dichtdoen.

Dat geeft een probleem. Vraagt een andere kamer, bijvoorbeeld de slaapkamer, om warmte, dan slaat de ketel aan en worden die open radiatoren ook warm. Die kamer wordt dan veel warmer dan je wilde.

De beheerder lost dit op door die kamers toe te voegen als kamer met **open radiatoren**. Zo’n kamer heeft een temperatuursensor nodig en volgt zijn schema zoals elke andere kamer. Voor de ketel werkt het zo:

- **Hij vraagt om warmte als het koud is.** Is de kamer meer dan 0,3 graden onder zijn comforttemperatuur, dan wordt de ketel gevraagd te branden.
- **Hij zet de ketel uit als het warm genoeg is.** Zodra de kamer zijn comforttemperatuur haalt, gaat de ketel uit. Dat geldt voor alle kamers: ook als de slaapkamer nog koud is, wacht de ketel tot die kamer weer iets is afgekoeld (0,3 graden). Zo wordt het huis nooit warmer dan die kamer mag worden.

Goed om te weten:

- **Eén sensor, één kamer.** Dekt één thermometer meerdere verbonden kamers, voeg ze dan toe als één kamer in plaats van meerdere kamers op dezelfde thermometer. Dat werkt even goed en is makkelijker bij te houden.
- **Een koude kamer moet soms wachten.** Zolang de kamer met open radiatoren warm is, blijft de ketel uit, ook als een andere kamer wat te koud is. Dat is de prijs van de open radiatoren. Twee manieren eromheen: draai een radiator met de hand dicht, of gebruik de **Handmatige ruimte-override**, die de ketel altijd aanzet.
- **Zijn de kranen er eenmaal,** dan zet de beheerder *open radiatoren* uit, voegt hij de kamers toe als gewone kamers met hun kranen, en haalt hij de gecombineerde kamer weg als die er was. De begrenzing verdwijnt dan vanzelf, omdat elke kraan zijn eigen radiator dichtdraait.

## Het systeem leert

Smart Heating begint met verstandige standaardwaarden en leert daarna elke kamer kennen. Dat gebeurt per kamer, het blijft bewaard na een herstart, en zolang er nog te weinig gegevens zijn, gelden gewoon de standaardwaarden. Je hoeft er niets voor te doen.

- **Hoe snel opwarmen gaat.** Het systeem onthoudt hoe snel een kamer opwarmt en hoe koud het toen buiten was. Samen met hoe koud de kamer nu is, weet het zo hoe vroeg het moet beginnen voordat het schema start (zie [Op tijd warm](#op-tijd-warm)).
- **Wat een open raam is.** Elke kamer koelt een beetje anders af: een kamer met een groot raam daalt sneller dan een kleine slaapkamer. Na ongeveer drie uur rustige metingen weet het systeem wat voor een kamer normaal is en wat niet. Een kamer die normaal nauwelijks verandert, herkent een open raam sneller. De instelling van de beheerder voor de temperatuurdaling is het maximum: het systeem kan de kamer alerter maken dan dat, nooit minder alert.
- **Hoever een kamer blijft opwarmen.** Een radiator blijft nog even warm nadat de ketel stopt. Het systeem meet hoeveel verder de kamer opwarmt, en zet de ketel zoveel eerder uit. Zo komt de kamer precies op zijn doel tot rust in plaats van er iets boven, wat gas bespaart. Dit leert het na minstens drie keer verwarmen, en de correctie is nooit meer dan één graad.
- **Hoe de thermometers verschillen.** De thermometer in een radiatorkraan meet een andere waarde dan de losse thermometer midden in de kamer. Het systeem vergelijkt de twee zolang de radiator uit staat. Wordt de losse thermometer ooit stil, dan gebruikt het de waarde van de kraan, gecorrigeerd met dat verschil, in plaats van er een stukje naast te zitten. Heeft de beheerder zelf een correctie ingesteld, dan geldt die.
- **Wat je met de hand doet.** Druk je regelmatig rond dezelfde tijd op **Boost** of draai je een kraan omhoog, buiten het schema, dan merkt het systeem dat. Is dat op minstens drie verschillende dagen binnen vier weken gebeurd, dan staat het in het maandagrapport, bijvoorbeeld *je vraagt vaak om warmte op di, do rond 07:10, overweeg dit aan het schema toe te voegen*. Het systeem past het schema nooit zelf aan, dat doe jij of de beheerder.

## De knoppen

Alle knoppen staan op het Overzicht, aan de rechterkant. Een knop gebruik je door op **Klik** ernaast te tikken.

### Boost: nu even warm

Is het koud in een kamer en wil je niet wachten op het schema? Druk dan bij die kamer op **Boost**. De kamer gaat meteen naar de comforttemperatuur en de ketel springt aan als dat nodig is. Eén uitzondering: is een kamer met open radiatoren (zie [Kamers zonder slimme kranen](#kamers-zonder-slimme-kranen)) al warm, dan blijft de ketel uit. De **Handmatige ruimte-override** heeft die beperking niet. Een Boost duurt standaard een uur. Daarna gaat de kamer vanzelf terug naar het schema.

Wil je eerder stoppen, druk dan op **Boost annuleren**. Bij de kamer zie je zolang *Boost tot 14:00* staan.

### Vakantie: het huis op een laag pitje

Ga je een paar dagen weg? Zo zet je het huis op vorstbeveiliging:

1. Zet **Terug van vakantie** op de dag en tijd dat je thuis verwacht te zijn.
2. Zet **Vakantiemodus** aan.

Alle kamers gaan dan naar 12 °C. Elke kamer begint precies op tijd op te warmen, zodat het aangenaam is als je terug bent. Ben je eerder terug, zet de vakantiemodus dan gewoon uit; het huis merkt ook zelf als je onderweg naar huis bent.

Heeft de beheerder een vakantieagenda gekoppeld, dan heb je de knoppen niet eens nodig: zet een afspraak zoals *Vakantie* in die agenda, met de tijd dat je vertrekt en de tijd dat je terug bent, en de vakantiemodus volgt die vanzelf.

### Handmatige ruimte-override: voor kamers zonder slimme kraan

Sommige kamers hebben een gewone radiatorkraan die je met de hand draait. Die kamers kunnen de ketel zelf niet laten aanslaan. Wil je zo’n kamer toch warm hebben:

1. Draai de radiatorkraan in die kamer open.
2. Druk op **Handmatige ruimte-override**.

De ketel blijft dan twee uur lang branden. Ben je eerder klaar, druk dan op **Handmatige ruimte-override annuleren**, en vergeet niet de kraan weer dicht te draaien.

## Meldingen

Een melding verschijnt alleen als er echt iets aandacht nodig heeft. Heeft de beheerder het ingesteld, dan komen meldingen die even duren ook op je telefoon binnen, met een bericht zodra ze zijn opgelost. Hij verdwijnt vanzelf zodra het probleem is opgelost. In de meldingen staat de naam van de kamer; hieronder staat *de kamer*.

| Melding | Wat je kunt doen |
| --- | --- |
| De batterij van de radiatorkraan in de kamer is bijna leeg. | Vervang de batterijen binnenkort. De kraan werkt tot die tijd gewoon door. |
| De radiatorkraan in de kamer reageert niet. | Kijk of de batterij leeg is of de kraan los zit. Helpt dat niet, laat het de beheerder weten. |
| De radiatorkraan in de kamer staat uit en gaat niet weer aan. | Het systeem probeerde de kraan aan te zetten, maar dat lukte niet. Kijk op de kraan zelf of laat het de beheerder weten. |
| De radiatorkraan in de kamer neemt zijn temperatuur niet over. | De kraan kreeg een paar keer een temperatuur, maar nam die niet over. Vaak helpt nieuwe batterijen plaatsen. |
| De temperatuursensor in de kamer meldt niets meer. | De losse thermometer in die kamer is stil. Kijk of de batterij leeg is. Tot die tijd gebruikt het systeem de thermometer in de radiatorkraan. |
| De kamer vraagt steeds om warmte maar wordt niet warmer. | Mogelijk staat een raam open of werkt de radiator niet. Controleer beide. |
| De kamer is al lange tijd te koud en haalt zijn doel niet. | Kijk of er een raam of deur openstaat en of de radiator warm wordt. Blijft het zo, laat het de beheerder weten. |
| De ketelthermostaat is onbereikbaar. | De ketel kan even niet betrouwbaar worden aangestuurd. De radiatorkranen volgen gewoon het schema. Meestal lost dit zichzelf op. |

## Zelf iets verstellen

Je mag gewoon aan de knoppen in huis draaien. Smart Heating houdt daar rekening mee.

- **Aan een slimme radiatorkraan draaien:** de stand die je kiest, blijft staan tot het schema van die kamer de volgende keer verandert. Daarna neemt het systeem het weer over. Zet je de kraan hoger dan de lagere temperatuur en is de kamer kouder dan wat je instelde, dan slaat de ketel ook aan. Bij de kamer staat zolang *Handmatig ingesteld op …*.
- **Aan de ketelthermostaat draaien** (de thermostaat die de ketel aanzet): je instelling wordt ongeveer twee uur gerespecteerd. Daarna gaat Smart Heating weer verder.
- **In Home Assistant de temperatuur van een kamer veranderen:** dat kan niet. Je krijgt dan de melding dat het doel door Smart Heating wordt bepaald. Gebruik in plaats daarvan **Boost**, of vraag de beheerder het schema of de temperaturen aan te passen.

## Veelgestelde vragen

**Er staat ‘Verwarmen’, maar ook ‘Boiler uit’. Klopt dat?**
Ja. ‘Verwarmen’ betekent dat de radiator in die kamer open staat omdat het er nog iets te koud is. De ketel slaat alleen aan voor kamers die volgens het schema of een Boost echt warm moeten zijn. Een kamer die op de lagere temperatuur staat, krijgt alleen de warmte die nog in de leidingen zit.

**Mijn kamer wordt niet warm. Wat nu?**
Kijk eerst naar de zin bij de kamer op het Overzicht. Staat er bijvoorbeeld *Warm vanaf 17:00* of *Persoon van deze ruimte is weg*, dan doet het systeem precies wat het moet doen. Wil je het toch warm, druk dan op **Boost**. Staat er een melding, lees dan bij [Meldingen](#meldingen-1) wat je ermee kunt.

**Kan ik de tijden of temperaturen aanpassen?**
Ja, maar dat doet de beheerder in de instellingen. Vraag het gerust als een schema niet bij je dag past.

**Waarom staat er ‘Raam lijkt open’, terwijl alles dicht is?**
De kamer koelde ineens snel af, bijvoorbeeld door een deur die openstond. Na hooguit een half uur gaat de verwarming vanzelf weer verder. Wil je niet wachten, druk dan op **Boost**. Gebeurt het te vaak? Vraag de beheerder om de temperatuurdaling voor open raam bij die kamer hoger te zetten.

**Waarom slaat de ketel niet aan, terwijl een kamer koud is?**
Waarschijnlijk omdat een kamer met open radiatoren (een kamer zonder slimme kranen) al warm genoeg is. Zolang die kamer op zijn comforttemperatuur is, blijft de ketel voor het hele huis uit, zodat niets te warm wordt. Zie [Kamers zonder slimme kranen](#kamers-zonder-slimme-kranen). Heb je haast? Gebruik de **Handmatige ruimte-override**.

**Past het systeem mijn schema zelf aan?**
Nee. Het leert hoe je huis zich gedraagt en kan in het maandagrapport een schematijd voorstellen, maar het verandert het schema nooit zelf.

**Hoe lang duurt het voor het mijn huis kent?**
De eerste dingen, zoals een open raam, werken na een paar uur. Op tijd opwarmen en de ketel op tijd uitzetten worden beter in de eerste weken. Tot die tijd gelden de standaardwaarden, dus je zit er niet slechter mee.

**Moet ik de vakantiemodus na mijn vakantie zelf uitzetten?**
Nee. Het huis warmt op tijd op voor het terugkeermoment dat je instelde, en de knop gaat uit zodra er iemand thuis is.
