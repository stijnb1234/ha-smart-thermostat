# Control TRVs over Zigbee2MQTT and push external room temperature

Shelly BLU TRV Gen3 is paired to Zigbee2MQTT (not the Shelly integration). Room temperature from external sensors (living right, kitchen, bedroom) is pushed to the TRV `external_temperature`; other rooms use the TRV sensor with a calibration offset. Z2M does not expose open-window detection, so window-open is detected from temperature drop in our own logic.

## Consequences

- External temperature is delivered to the sleepy device with retries (up to 1 hour), so it cannot be a tight control loop.
- Fallback behaviour when pushes stop is unverified and must be probed in Phase 0.
