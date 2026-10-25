# Heading home from GPS, Vacation from a calendar

Heading home used to need a hand-drawn "near home" zone or a switch, and Vacation was a number of
days ending at midnight of the return day. Both were clumsy and imprecise.

**Heading home** is now detected from the GPS position of tracked people (person or device tracker
attributes, as the mobile app reports them): the distance to home must shrink by at least 0.5 km at
walking pace or faster, and the estimated arrival must fall within the longest Room lead time. It
holds while they keep coming closer and ends at home, when they turn away (1 km further than their
closest point) or after twice the ETA without progress. Extra heading-home entities still work.
Away counts from when the house became empty, tracked by Smart Heating and kept across restarts,
instead of the person entity's `last_changed` (which a zone change or restart resets).

**Vacation** is a period with an exact return moment: from a calendar (events whose title or
description contains a keyword; all-day events end at local midnight of their end date), from the
return date-time entity plus switch, or from the `set_vacation` service. Each Room leaves Vacation
one lead time before the return, using the lead time for how far it has cooled.

## Consequences

- No zones to configure; phones without GPS fall back to home/away only.
- GPS positions stay in memory and never reach storage or diagnostics.
- Vacation ends per Room, not for the whole house at once.
