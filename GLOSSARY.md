# Glossary

**Room**: A heated space in the home with its own target temperature (living room left, living room right, sunroom, working room, bedroom, kitchen, bathroom).

**Smart TRV**: A Shelly BLU TRV radiator valve controllable from Home Assistant. Present in living room left, living room right, sunroom, working room, bedroom.

**Dumb TRV**: A manual radiator valve kept near frost-protection. Never drives heating.

**Call for heat**: The signal that makes the boiler fire. Today only the Bosch EasyControl (living room right) can raise it.

**Living area**: Living room left, living room right and sunroom. Connected by ensuite doors that can be closed, so they can act as one space or as separate rooms.

**Manual-room override**: A button that tells the boiler to heat because someone wants a dumb-TRV room warm (the radiator valve is turned by hand).

**Heat demand**: A room's need for heat at a moment, decided by schedule, presence, work-from-home calendar, or manual boost.

**Comfort temperature**: The target a room holds while it has heat demand.

**Away**: No tracked person is home. All rooms drop to setback; a long absence drops to frost-hold.

**Vacation mode**: A user-set period of several days during which all rooms hold frost-hold temperature.

**Frost-hold**: The lowest temperature held during a long absence, only to protect the house.

**Pre-heat**: Starting to heat before a room's scheduled demand so it is at comfort temperature on time; lead time is learned per room.

**Open-window detection**: Treating a sharp temperature drop in a room as an open window and pausing its heating briefly.

**Floor heating**: Kitchen and bathroom loops on a mixing valve with a lower fixed flow temperature. Slow to respond, so needs long pre-heat. Deferred to a later phase.

**Boost**: A manual one-tap request to heat a room now.

**Setback**: The lower target temperature a room holds when it has no heat demand.
