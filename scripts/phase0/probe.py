#!/usr/bin/env python3
"""Phase 0 probes (ADR-0004). Stdlib only. Talks to Home Assistant REST API.

Config via env: HA_URL, HA_TOKEN, EASY_CLIMATE, BURNER_ENTITY (optional),
TRV_CLIMATE, TRV_Z2M_NAME, TRV_ENTITIES (comma list), LOW_SETPOINT, HIGH_SETPOINT.
Each probe appends JSON lines to results/<probe>-<timestamp>.jsonl.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

E = os.environ
URL = E["HA_URL"].rstrip("/")
HDR = {"Authorization": f"Bearer {E['HA_TOKEN']}", "Content-Type": "application/json"}
OUT = None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def log(kind, **kw):
    rec = {"t": now(), "kind": kind, **kw}
    print(json.dumps(rec), flush=True)
    OUT.write(json.dumps(rec) + "\n"); OUT.flush()


def api(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method, headers=HDR,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or "null"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace"), dict(e.headers)
    except Exception as e:  # network
        return 0, repr(e), {}


def state(eid):
    s, b, _ = api("GET", f"/api/states/{eid}")
    return b if s == 200 else {"state": f"ERR{s}", "attributes": {}}


def set_temp(eid, temp):
    t0 = time.time()
    s, b, h = api("POST", "/api/services/climate/set_temperature", {"entity_id": eid, "temperature": temp})
    log("write", entity=eid, temp=temp, status=s, body=b if s != 200 else None,
        retry_after=h.get("Retry-After"), took_s=round(time.time() - t0, 2))
    return s


def snap(eids):
    return {e: {"s": (st := state(e))["state"], "a": {k: v for k, v in st["attributes"].items()
            if k in ("temperature", "current_temperature", "hvac_action", "hvac_mode", "preset_mode")}}
            for e in eids}


def watch(eids, cond, timeout, every=5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        sn = snap(eids)
        log("sample", elapsed=round(time.time() - t0), **{"states": sn})
        if cond(sn):
            return round(time.time() - t0)
        time.sleep(every)
    return None


def p_latency():
    """Setpoint write -> burner start. Needs BURNER_ENTITY (flame/heating binary_sensor or climate hvac_action)."""
    easy, burner = E["EASY_CLIMATE"], E.get("BURNER_ENTITY") or E["EASY_CLIMATE"]
    lo, hi = float(E["LOW_SETPOINT"]), float(E["HIGH_SETPOINT"])
    runs = int(E.get("RUNS", 4))
    for i in range(runs):
        log("run", i=i, phase="drop")
        set_temp(easy, lo)
        watch([burner], lambda s: s[burner]["s"] in ("off", "idle") or s[burner]["a"].get("hvac_action") == "idle", 900)
        time.sleep(60)
        log("run", i=i, phase="raise")
        set_temp(easy, hi)
        d = watch([burner, easy], lambda s: s[burner]["s"] in ("on", "heating") or s[burner]["a"].get("hvac_action") == "heating", 1800)
        log("result", i=i, seconds_to_burner=d)
    set_temp(easy, lo)


def p_persist():
    """Does a raised setpoint persist or revert? Samples every 5 min for HOURS."""
    easy = E["EASY_CLIMATE"]
    hrs = float(E.get("HOURS", 4))
    log("start", before=snap([easy]))
    set_temp(easy, float(E["HIGH_SETPOINT"]))
    watch([easy], lambda s: False, hrs * 3600, every=300)
    log("end", after=snap([easy])); set_temp(easy, float(E["LOW_SETPOINT"]))


def p_ratelimit():
    """Controlled bursts alternating 0.5 degC steps. Stops at first non-200 and records shape."""
    easy = E["EASY_CLIMATE"]
    base = float(E["LOW_SETPOINT"])
    for gap in (60, 30, 15, 10, 5, 2, 1):
        log("burst", gap_s=gap, count=12)
        for n in range(12):
            if set_temp(easy, base + 0.5 * (n % 2)) != 200:
                log("limited", gap_s=gap, n=n)
                log("hint", msg="Also copy the HA log lines mentioning bosch_pointt / 429 into findings")
                set_temp_later(easy, base); return
            time.sleep(gap)
    set_temp(easy, base)


def set_temp_later(eid, t):
    time.sleep(900); set_temp(eid, t)


def p_trv_report():
    """Passive: log changes of TRV entities with 1s polling. Change setpoint/ warm the TRV meanwhile."""
    eids = E["TRV_ENTITIES"].split(","); mins = float(E.get("MINUTES", 60)); last = {}
    t0 = time.time()
    while time.time() - t0 < mins * 60:
        for e in eids:
            st = state(e)
            key = (st["state"], json.dumps(st["attributes"], sort_keys=True, default=str))
            if last.get(e) != key:
                last[e] = key
                log("change", entity=e, state=st["state"], last_updated=st.get("last_updated"),
                    attrs={k: v for k, v in st["attributes"].items() if k in ("temperature", "current_temperature", "local_temperature", "valve_position", "pi_heating_demand")})
        time.sleep(1)


def mqtt_push(temp):
    s, b, _ = api("POST", "/api/services/mqtt/publish",
                  {"topic": f"zigbee2mqtt/{E['TRV_Z2M_NAME']}/set", "payload": json.dumps({"external_temperature": temp})})
    log("push", temp=temp, status=s)


def p_trv_ext():
    """Push external temps; measure arrival (TRV local temp / valve reacts). Then stop pushing; observe fallback."""
    eids = E["TRV_ENTITIES"].split(",")
    pushes = int(E.get("PUSHES", 6)); gap = int(E.get("GAP_S", 300)); quiet_h = float(E.get("QUIET_HOURS", 3))
    log("start", before=snap(eids))
    for i in range(pushes):
        mqtt_push(round(float(E["LOW_SETPOINT"]) + 6 + (i % 3), 1))  # fake room temp, varied to see valve effect
        t0 = time.time()
        while time.time() - t0 < gap:
            log("sample", since_push=round(time.time() - t0), states=snap(eids)); time.sleep(15)
    log("phase", name="pushes_stopped")
    watch(eids, lambda s: False, quiet_h * 3600, every=120)
    log("end", after=snap(eids))


PROBES = {"latency": p_latency, "persist": p_persist, "ratelimit": p_ratelimit,
          "trv-report": p_trv_report, "trv-ext": p_trv_ext}

if __name__ == "__main__":
    name = sys.argv[1]
    os.makedirs("results", exist_ok=True)
    OUT = open(f"results/{name}-{datetime.now():%Y%m%d-%H%M%S}.jsonl", "a")
    try:
        PROBES[name]()
    except KeyboardInterrupt:
        log("interrupted")
        if name != "trv-report" and E.get("EASY_CLIMATE"):
            set_temp(E["EASY_CLIMATE"], float(E["LOW_SETPOINT"]))
