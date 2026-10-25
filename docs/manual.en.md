# Smart Heating – Manual

*Nederlandse versie: [manual.nl.md](manual.nl.md)*

Smart Heating controls the heating room by room: each room gets warm when it needs to, and the boiler only fires when a room actually asks for heat. Most of the time you don't have to do anything. This manual explains what happens and what you see on the Overview screen.

## In short

The house has one boiler and several radiators. Normally the boiler heats the whole house at once. Smart Heating looks at each room separately: only a room that should be warm right now gets heat. Rooms nobody is using stay cooler. That saves gas without leaving you cold.

This is how it works:

- **Smart radiator valves** on the radiators open and close by themselves. Smart Heating tells each valve how warm its room should be.
- **The boiler** only fires when at least one room should be warm and is still clearly too cold.
- **Each room has a schedule**: the times when it should be warm there. Outside those times the room drops to a lower temperature.
- **The system keeps an eye on what is going on**: is everyone out, is a window open, are you on holiday? Then it adjusts the temperature by itself.

So most of the time you don't have to do anything. If you want something different, there are a few buttons, such as **Boost** to heat a room right away.

## The Overview screen

In the Home Assistant sidebar, click **Smart Heating**. You land straight on the Overview: the first icon at the top left, the little house. Here you see at a glance what the heating is doing, and here are all the buttons you need. The other icons (a radiator, a boiler and a question mark) are the Heating, Boiler and Help tabs. Those are meant for the administrator; you can safely ignore them.

On the left is the **Right now** block, on the right are the buttons. If something is wrong, an **Alerts** block appears as well. On a phone the blocks are stacked instead of side by side.

### Right now

At the top is one short sentence about the whole house, for example:

> Heating: Living room, Bedroom. Boiler on.

- **Heating:** the rooms that are still too cold, so their radiator is open. If it says *Nothing is heating*, every room is at its temperature.
- **Boiler on / Boiler off:** whether the boiler is being asked to fire right now.
- Sometimes there is more after it: *Nobody is home.* or *Vacation mode is on.*

Below that it says *No alerts.* If something is wrong, it says for example **2 alerts need attention**.

Then follows a table with one line per room:

| Column | What you see |
| --- | --- |
| Room | The name of the room. |
| Now | How warm the room is right now. A dash (–) means the temperature is briefly unknown. |
| Aiming for | The temperature the room is working towards. |
| What is happening | A short sentence, such as *Warm until 23:00*. What all these sentences mean is explained in the next section. |

### Alerts

This block only appears when something needs attention, for example a nearly empty battery. If you don't see it, everything is fine. Each alert is a plain sentence; further on in this manual you can read what to do about it.

### Controls

These are the buttons:

- **Vacation mode** (an on/off switch) and **Vacation days** (a slider): for when you are away for a few days.
- **Manual room override** and **Cancel manual room override**: for rooms without a smart valve.
- In a separate **Boost** block: for each room a **Boost** button and a **Cancel boost** button, for example *Study: Boost*.
- At the bottom, a link to the Smart Heating options (schedules and temperatures per room). That is meant for the administrator.

How to use the buttons is explained under [The buttons](#the-buttons) further on.

## What the sentence for a room means

The *What is happening* column has one sentence per room. The times and temperatures below are examples. If a time is not today, the day is shown too, for example *Mon 07:00*.

| You see | What it means |
| --- | --- |
| Warm until 23:00 | The schedule says it should be warm here now, until 23:00. |
| Warm | It is warm here and no end time is planned. |
| Warm from 07:00 | The room is lower for now. The next warm period starts at 07:00. |
| Kept at 16 degrees | The room is at the lower temperature and nothing is planned. |
| Warming up, warm until 17:00 | The room started warming up early so it is warm on time. |
| Boost until 14:00 | Someone pressed Boost. The room stays warm until 14:00, or until you cancel the Boost. |
| Window seems open, heating paused until 14:20 | The room cooled down very quickly. A window is probably open, so the heating waits for a bit. |
| Nobody home, kept at 16 degrees | Everyone is out. After two days away this drops to 12 degrees. |
| Room's person is away, kept at 16 degrees | This room belongs to someone who is away right now, so its schedule is skipped. It warms up again once that person is home or on their way. |
| Waiting for the floor heating to warm up first, kept at 12 degrees | The floor heating is warming up first. Rooms not in use keep their radiator closed meanwhile. |
| Set by hand to 22 degrees, until 17:00 | Someone turned the valve by hand. That setting stays until 17:00, then the schedule takes over again. |
| Vacation until Sat 00:00, kept at 12 degrees | Vacation mode is on. The house is kept just above freezing and warms up again in time. |

## When does a room get warm?

Every room has three temperatures. The administrator can change them per room; these are the defaults:

| Temperature | Default | When |
| --- | --- | --- |
| Comfort | 19.5 °C | When the schedule says it should be warm, or after a Boost. |
| Lower | 16 °C | Outside the schedule, or when nobody is home. |
| Frost protection | 12 °C | On holiday, when you have been away for more than two days, or when a window seems to be open. Just warm enough to protect the house. |

### The schedule

The schedule says when a room should be warm. By default:

- **Living room:** every day from 06:00 to 23:00.
- **Study:** Monday, Wednesday and Friday from 08:00 to 17:00.
- **Bedroom:** during working hours, plus a short warm-up before bedtime (21:30 to 22:30).

Changing the schedule is done by the administrator in the settings.

### Warm on time

A room starts warming up before the scheduled time, so it is warm when it should be. At first that is a bit more than an hour in advance. After that the system learns per room how long warming up really takes, also depending on how cold it is outside. You then see *Warming up* next to the room.

### What wins?

Sometimes several things apply at once. Then the highest one in this list wins:

1. **Boost**: you want it warm now.
2. **Open window**: the heating pauses for a bit.
3. **Vacation**: the whole house at frost protection.
4. **Nobody home**: every room at the lower temperature.
5. **The schedule**, including warming up on time. If the room belongs to someone who is away, the schedule is skipped.
6. Otherwise: **the lower temperature**.

## What the system does by itself

These things happen automatically. You don't need to do anything.

- **Window open:** if a room suddenly cools down very quickly, the system assumes a window is open. The heating in that room then pauses for fifteen minutes to half an hour, so you are not heating the street.
- **Nobody home:** when everyone has left, all rooms go to the lower temperature (16 °C). If you are away for more than two days, the house drops to frost protection (12 °C).
- **Room of someone who is away:** a room can belong to certain people, for example a study. If they are all away, that room stays at the lower temperature, even if the schedule says otherwise. A Boost still works.
- **On the way home:** if the administrator has set this up, the system notices you are on your way, for example when you get close to home. The house then starts warming up, so it is warm when you walk in.
- **Floor heating:** floor heating is slow. A room with floor heating therefore starts a few hours before the scheduled time. While it warms up, the radiators in rooms not in use stay closed, so the heat goes to the floor.
- **Rooms without smart valves yet:** a room marked *open radiators* asks for heat when it is cold, and stops the boiler as soon as it is warm enough, so the whole house is not heated past that room.
- **Learning:** per room the system learns how much the temperature normally fluctuates (so an open window is recognised sooner), how far the room keeps warming after the boiler stops (so the boiler stops early enough), and how its thermometer differs from the valve's. In the Monday report it suggests schedule times if you often press Boost or turn the valve up around the same time outside the schedule. It never changes the schedule by itself.
- **Valve switched off:** if a smart radiator valve is switched off, the system switches it back on.
- **Weekly report:** every Monday at 08:00 you get a notification in Home Assistant (under the bell). It shows how much gas was used compared to last year, taking into account how cold it was, how many hours each room was heated, and whether there were any problems.

## The buttons

All buttons are on the Overview, on the right-hand side. To use a button, tap **Press** next to it.

### Boost: warm right now

Is a room cold and you don't want to wait for the schedule? Press **Boost** for that room. The room goes straight to its comfort temperature and the boiler fires if needed. A Boost lasts one hour by default. After that the room goes back to its schedule by itself.

To stop earlier, press **Cancel boost**. While it lasts, the room shows *Boost until 14:00*.

### Vacation: the house on a low flame

Going away for a few days? This is how you put the house on frost protection:

1. Set the **Vacation days** slider to the number of days you will be away (1 to 60, default 7). Count the nights: if you leave on Saturday and come back the next Saturday, choose 7.
2. Switch **Vacation mode** on.

All rooms then go to 12 °C. On the day you come back, the house follows its normal schedule again from midnight, so it is warm when you get home. Back early? Just switch vacation mode off. If 'on the way home' is set up, vacation also ends by itself as you approach.

### Manual room override: for rooms without a smart valve

Some rooms have an ordinary radiator valve that you turn by hand. Those rooms cannot make the boiler fire on their own. To heat such a room anyway:

1. Turn the radiator valve in that room open.
2. Press **Manual room override**.

The boiler then keeps firing for two hours. Done earlier? Press **Cancel manual room override**, and don't forget to turn the valve back down.

## Alerts

An alert only appears when something really needs attention. It disappears by itself once the problem is solved. Alerts mention the room by name; below it says *the room*.

| Alert | What you can do |
| --- | --- |
| The battery of the radiator valve in the room is low. Replace it soon. | Replace the batteries soon. The valve keeps working until then. |
| The radiator valve in the room is not responding. | Check whether the battery is empty or the valve has come loose. If that doesn't help, let the administrator know. |
| The radiator valve in the room is switched off and does not turn back on. | The system tried to switch the valve on but could not. Check the valve itself or let the administrator know. |
| The radiator valve in the room does not accept its temperature. | The valve was sent a temperature a few times but did not take it. New batteries often help. |
| The temperature sensor in the room stopped reporting. | The separate thermometer in that room has gone quiet. Check whether its battery is empty. Until then the system uses the thermometer in the radiator valve. |
| The room keeps asking for heat but is not warming up. | A window may be open, or the radiator is not working. Check both. |
| The room has been too cold for a long time and is not reaching its target. | Check whether a window or door is open and whether the radiator gets warm. If it stays this way, let the administrator know. |
| The Bosch cloud cannot be reached. | The boiler cannot be controlled reliably for now. The radiator valves keep following the schedule. This usually sorts itself out. |

## Changing things yourself

You are free to turn the knobs in the house. Smart Heating takes that into account.

- **Turning a smart radiator valve:** the setting you choose stays until that room's schedule changes next. Then the system takes over again. If you set the valve above the lower temperature and the room is colder than what you set, the boiler fires too. Meanwhile the room shows *Set by hand to …*.
- **Turning the EasyControl** (the Bosch thermostat on the wall): your setting is respected for about two hours. After that Smart Heating carries on.
- **Changing a room's temperature in Home Assistant:** that is not possible. You get a message saying the target is set by Smart Heating. Use **Boost** instead, or ask the administrator to change the schedule or the temperatures.

## Frequently asked questions

**It says 'Heating', but also 'Boiler off'. Is that right?**
Yes. 'Heating' means the radiator in that room is open because it is still a little too cold there. The boiler only fires for rooms that really should be warm, because of the schedule or a Boost. A room at the lower temperature only gets the heat that is still in the pipes.

**My room is not getting warm. What now?**
First look at the room's sentence on the Overview. If it says, for example, *Warm from 17:00* or *Room's person is away*, the system is doing exactly what it should. Want it warm anyway? Press **Boost**. If there is an alert, see [Alerts](#alerts-1) for what to do.

**Can I change the times or temperatures?**
Yes, but the administrator does that in the settings. Just ask if a schedule doesn't fit your day.

**Why does it say 'Window seems open' when everything is closed?**
The room suddenly cooled down quickly, for example because a door was open. After at most half an hour the heating carries on by itself. Don't want to wait? Press **Boost**.

**Do I have to switch vacation mode off myself after my holiday?**
No. On the day you come back, the house follows its normal schedule again, and the switch turns off as soon as someone is home.
