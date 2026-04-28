"""
IoT Device Control Service
Abstracts GPIO control so the rest of the app doesn't need to know
whether it's running on a Raspberry Pi or a development PC.

On Raspberry Pi:  Set GPIO_ENABLED=true in .env to use real GPIO pins.
On Windows/Mac:   GPIO is simulated in-memory (state stored in _device_state).
"""

import logging
import os

logger = logging.getLogger(__name__)

# ── Simulated device state (used when GPIO is not available) ──────────────────
_device_state: dict[str, bool] = {
    "lights": False,
    "fans": False,
    "personDetected": False,
}

# ── Optional GPIO import ──────────────────────────────────────────────────────
GPIO_ENABLED = os.getenv("GPIO_ENABLED", "false").lower() == "true"
GPIO_LIGHTS_PIN = int(os.getenv("GPIO_LIGHTS_PIN", 17))
GPIO_FANS_PIN = int(os.getenv("GPIO_FANS_PIN", 27))

gpio = None
if GPIO_ENABLED:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_LIGHTS_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(GPIO_FANS_PIN, GPIO.OUT, initial=GPIO.LOW)
        gpio = GPIO
        logger.info("GPIO initialized: lights pin=%d, fans pin=%d", GPIO_LIGHTS_PIN, GPIO_FANS_PIN)
    except ImportError:
        logger.warning("RPi.GPIO not available — falling back to simulated GPIO.")
        GPIO_ENABLED = False
    except Exception as exc:
        logger.error("GPIO setup failed: %s — falling back to simulation.", exc)
        GPIO_ENABLED = False


# ── Public API ─────────────────────────────────────────────────────────────────

def set_device_state(device: str, on: bool) -> None:
    """
    Turn a device ON or OFF.
    device: 'lights' | 'fans'
    on: True = ON, False = OFF
    """
    _device_state[device] = on

    if gpio and GPIO_ENABLED:
        pin = GPIO_LIGHTS_PIN if device == "lights" else GPIO_FANS_PIN
        gpio.output(pin, gpio.HIGH if on else gpio.LOW)
        logger.debug("GPIO pin %d set to %s", pin, "HIGH" if on else "LOW")
    else:
        logger.debug("Simulated: %s → %s", device, "ON" if on else "OFF")


def get_device_states() -> dict:
    """Return current state of all devices."""
    return {
        "lights": _device_state["lights"],
        "fans": _device_state["fans"],
        "personDetected": _device_state["personDetected"],
        "autoMode": True,  # TODO: persist auto-mode preference in DB
        "gpioEnabled": GPIO_ENABLED,
    }


def set_person_detected(detected: bool) -> None:
    """Update the person detection state."""
    _device_state["personDetected"] = detected


def cleanup_gpio() -> None:
    """Call on application shutdown to release GPIO pins."""
    if gpio and GPIO_ENABLED:
        gpio.cleanup()
        logger.info("GPIO cleaned up.")
