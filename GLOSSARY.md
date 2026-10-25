# Glossary

Terms as Smart Heating uses them in code, docs and the UI.

## Rooms and hardware

**Room**: A heated space with its own comfort, setback and frost-hold temperatures and its own
schedule. Has a stable **Room id** (set once from the name, kept on rename) that keys its entities
and learned data; the name is only what people read.

**Smart TRV**: A radiator valve Home Assistant can set (any `climate` entity). Extras found on its
device are used when present: a battery sensor, a number entity that takes an **external
temperature**, valve position and heating demand. Over Zigbee2MQTT without such a number, the
external temperature goes over MQTT.

**External temperature**: A separate room sensor's reading, pushed to the TRV so it regulates on
the room temperature instead of its own sensor next to the radiator.

**Open radiators**: A Room whose radiators have no smart valve yet and stay open. It has a sensor,
calls the boiler when cold, and stops every boiler call once it reaches comfort (until it has
cooled by the demand hysteresis) so the house does not overheat.

**Floor heating**: A Room heated by always-open floor loops: no TRV, a sensor, and a long pre-heat
because it responds slowly.

**Manual room**: A Room with a hand-turned (dumb) valve. Smart Heating does not control it; it only
matters through the **Manual-room override**.

## The boiler

**Boiler thermostat**: The thermostat that makes the boiler fire. Smart Heating calls for heat by
raising its setpoint (**boiler high**) and ends the call by lowering it (**boiler low**). Reached through a **boiler adapter**; other kinds of boiler call (a relay,
OpenTherm) are further adapters.

**Call for heat**: The signal that makes the boiler fire: raised while a Room heating to comfort
is colder than its target by more than the **demand hysteresis**, or while a Manual-room override
runs.

**Demand hysteresis**: How far below its target a Room must be before it calls for heat, widened
by its learned **coast**.

**Manual hold**: A setpoint changed by hand on the boiler thermostat, respected for a while before
Smart Heating writes again. If the hand-set value is what Smart Heating wants anyway when the hold
ends, it is adopted.

## Targets

**Heat demand**: A Room's need for heat at a moment, decided by schedule, presence, Boost or a
hand-set valve.

**Comfort temperature**: The target a Room holds while it has heat demand.

**Setback**: The lower target a Room holds when it has no heat demand. Rooms at setback never call
for heat; they may drift below it.

**Frost-hold**: The lowest target, held during a long absence or Vacation, only to protect the house.

**Boost**: A manual request to heat a Room to comfort now, for a set time (button or the
`smart_heating.boost` service with a duration).

**Manual-room override**: A button that calls the boiler for a while because someone wants a
manual room warm.

## Presence

**Away**: No tracked person is home or heading home. All Rooms drop to setback; after a long
absence (counted from when the house became empty, kept across restarts and zone changes) to
frost-hold.

**Heading home**: A tracked person on the way home, detected from their phone's GPS: the distance
to home shrinks at travel speed and the estimated arrival is within the time the house needs to warm
up. Ends Away early and warms their Rooms. Extra heading-home entities (a switch, a zone) can add to it.

**Room occupants**: The people a Room is for. While all of them are away its schedule is skipped.

**Vacation**: A period during which the house holds frost-hold, set by hand (return moment and
switch, or the `set_vacation` service) or by matching events in a vacation calendar. Each Room is
released one lead time before the return, so it is warm then.

## Timing and learning

**Pre-heat**: Starting to heat before a scheduled comfort period so the Room is at comfort on
time. The **lead time** is the Room's current shortfall (comfort minus its temperature) divided by
its learned heating rate at the current outdoor temperature; it is frozen once pre-heat starts.

**Coast**: How far a Room keeps warming after its call ends; learned per Room so the call can end
earlier.

**Open-window detection**: Treating a sharp temperature drop as an open window and pausing the
Room at frost-hold for a while. While a radiator is hot or **cooling down** after heating, the TRV's
own sensor falls anyway, so only the external room sensor is trusted then.

**Schedule suggestion**: A recurring Boost or hand-set valve at a time the schedule does not cover,
reported weekly. The schedule is never changed by itself.
