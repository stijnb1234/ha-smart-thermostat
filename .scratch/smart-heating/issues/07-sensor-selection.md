# 07: Sensor selection

**What to build:** Rooms with an external sensor use it as truth; others use the TRV sensor with a calibration offset. External temperature is pushed to the TRV.

**Blocked by:** 00, 02

**Status:** ready-for-agent

- [ ] External sensor preferred when configured
- [ ] TRV sensor plus offset used otherwise
- [ ] External temperature pushed to the TRV, tolerating slow delivery

Parent spec: `.scratch/smart-heating/spec.md`
