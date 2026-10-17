"""Pure weekly gas-savings report. No Home Assistant imports.

Gas use is normalised as m3 per heating-degree-day (HDD) so a cold week and a
mild week compare fairly, and this week is compared with the same period last year.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from .engine import Alert
from .i18n import DEFAULT_LANGUAGE, tr
from .status import alert_sentence

DEFAULT_HDD_BASE = 18.0


def heating_degree_days(daily_mean_temps: Sequence[float], base: float = DEFAULT_HDD_BASE) -> float:
    return sum(max(0.0, base - t) for t in daily_mean_temps)


def m3_per_hdd(gas_m3: float | None, temps: Sequence[float], base: float) -> float | None:
    """None when gas is unknown or there were no heating degree-days."""
    if gas_m3 is None:
        return None
    hdd = heating_degree_days(temps, base)
    if hdd <= 0:
        return None
    return gas_m3 / hdd


def heated_hours(samples: Sequence[tuple[datetime, bool]], end: datetime) -> float:
    """Hours heating, from chronological (time, is_heating) state changes up to `end`."""
    total = 0.0
    for i, (start, heating) in enumerate(samples):
        stop = samples[i + 1][0] if i + 1 < len(samples) else end
        if heating and stop > start:
            total += (stop - start).total_seconds() / 3600
    return total


@dataclass(frozen=True)
class Report:
    gas_m3: float | None
    hdd: float
    m3_per_hdd: float | None
    last_year_m3_per_hdd: float | None
    room_hours: Mapping[str, float] = field(default_factory=dict)
    issues: Sequence[str] = ()

    @property
    def change_pct(self) -> float | None:
        if self.m3_per_hdd is None or not self.last_year_m3_per_hdd:
            return None
        return (self.m3_per_hdd / self.last_year_m3_per_hdd - 1) * 100

    def format(self, lang: str = DEFAULT_LANGUAGE) -> str:
        lines = [tr(lang, "report.title"), ""]
        if self.m3_per_hdd is None:
            lines.append(tr(lang, "report.no_gas"))
        else:
            line = tr(
                lang, "report.gas",
                gas=f"{self.gas_m3:.1f}", hdd=f"{self.hdd:.1f}", per=f"{self.m3_per_hdd:.2f}",
            )
            if self.last_year_m3_per_hdd is None:
                line += tr(lang, "report.no_last_year")
            else:
                line += tr(
                    lang, "report.vs_last_year",
                    last=f"{self.last_year_m3_per_hdd:.2f}", pct=f"{self.change_pct:+.0f}",
                )
            lines.append(line)
        lines += ["", tr(lang, "report.heated_hours")]
        lines += [
            tr(lang, "report.room_hours", room=n, hours=f"{h:.1f}") for n, h in self.room_hours.items()
        ] or [tr(lang, "report.no_data")]
        lines += ["", tr(lang, "report.issues")]
        lines += [f"- {i}" for i in self.issues] or [tr(lang, "report.no_issues")]
        return "\n".join(lines)


def build_report(
    *,
    gas_m3: float | None,
    temps: Sequence[float],
    last_gas_m3: float | None,
    last_temps: Sequence[float],
    room_hours: Mapping[str, float],
    issues: Sequence[str],
    base: float = DEFAULT_HDD_BASE,
) -> Report:
    return Report(
        gas_m3=gas_m3,
        hdd=heating_degree_days(temps, base),
        m3_per_hdd=m3_per_hdd(gas_m3, temps, base),
        last_year_m3_per_hdd=m3_per_hdd(last_gas_m3, last_temps, base),
        room_hours=dict(room_hours),
        issues=list(issues),
    )


def alert_issues(
    history: Sequence[tuple[datetime, Alert]],
    active: Sequence[Alert],
    since: datetime,
    lang: str = DEFAULT_LANGUAGE,
) -> list[str]:
    """Report lines for alerts raised since `since` or still active, one per (code, room)."""
    still_active = {(a.code, a.room) for a in active}
    seen: dict[tuple[str, str | None], Alert] = {}
    for at, alert in history:
        if at >= since:
            seen[(alert.code, alert.room)] = alert
    for alert in active:
        seen.setdefault((alert.code, alert.room), alert)
    return [
        alert_sentence(a, lang) + tr(lang, "report.still_active" if key in still_active else "report.resolved")
        for key, a in seen.items()
    ]
