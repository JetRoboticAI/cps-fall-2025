"""
Simple pump driver using RPi.GPIO.

Design assumptions
------------------
- The relay board for the pump is **active-low**:
    GPIO.LOW  -> pump ON
    GPIO.HIGH -> pump OFF
  Many low-level relay modules for Raspberry Pi use this convention.

- Pin numbering uses **BCM mode** (GPIO numbers, not BOARD header numbers).

- A small "settle" delay (default 5 ms) is applied after each ON/OFF to give
  the relay time to physically switch and to reduce relay chatter in rapid calls.

What this class provides
------------------------
- on() / off()        : explicit ON/OFF with debouncing delay
- pulse(seconds)      : ON for a duration, then OFF (guaranteed OFF via finally)
- toggle()            : convenience flip between states
- is_on property      : current software state (best-effort, not latched feedback)
- destroy()           : return the pin to a safe OFF state and cleanup()
- __repr__            : human-readable status, including the current GPIO level
"""

import RPi.GPIO as GPIO
import time

# Use BCM numbering globally for this module (idempotent if called again)
GPIO.setmode(GPIO.BCM)


class Pump:
    def __init__(self, channel: int, gpio_pin: int, settle_ms: int = 5):
        """
        Initialize one pump bound to a single GPIO output (active-low).

        Parameters
        ----------
        channel : int
            Logical channel/index for your own bookkeeping (e.g., "zone" number or sensor channel).
            It is not used by GPIO; only stored for diagnostics and __repr__.
        gpio_pin : int
            BCM GPIO pin number that drives the relay controlling this pump.
        settle_ms : int
            Milliseconds to sleep after switching ON/OFF. Helps relay modules settle and
            avoids rapid back-to-back transitions in calling code.

        Notes
        -----
        - The implementation assumes an **active-low** relay: LOW means ON, HIGH means OFF.
        - We explicitly set the initial output level to GPIO.HIGH (OFF) for safety.
        - GPIO.setmode(GPIO.BCM) is called at module import and again here for robustness;
          RPi.GPIO treats repeated setmode to the same scheme as a no-op.
        """
        self.channel = channel
        self.gpio_pin = gpio_pin
        self.settle_ms = max(0, int(settle_ms))
        self._is_on = False  # software-side bookkeeping flag

        # Ensure we remain in BCM mode (safe if already set)
        GPIO.setmode(GPIO.BCM)

        # Configure the pin as output and default it to OFF (HIGH) for active-low relays
        GPIO.setup(self.gpio_pin, GPIO.OUT, initial=GPIO.HIGH)

    def on(self) -> None:
        """
        Turn the pump ON (active-low -> drive pin LOW).
        No-ops if already ON.
        """
        if self._is_on:
            return
        GPIO.output(self.gpio_pin, GPIO.LOW)
        self._is_on = True
        if self.settle_ms:
            time.sleep(self.settle_ms / 1000.0)

    def off(self) -> None:
        """
        Turn the pump OFF (active-low -> drive pin HIGH).
        No-ops if already OFF.
        """
        if not self._is_on:
            return
        GPIO.output(self.gpio_pin, GPIO.HIGH)
        self._is_on = False
        if self.settle_ms:
            time.sleep(self.settle_ms / 1000.0)

    def pulse(self, seconds: float) -> None:
        """
        Turn the pump ON for 'seconds' and then OFF, even if an exception occurs.

        Parameters
        ----------
        seconds : float
            Duration in seconds. Negative values are treated as 0.
        """
        self.on()
        try:
            time.sleep(max(0.0, float(seconds)))
        finally:
            # Ensure we always leave the pump OFF
            self.off()

    def toggle(self) -> None:
        """Toggle the pump state (OFF->ON or ON->OFF)."""
        if self._is_on:
            self.off()
        else:
            self.on()

    @property
    def is_on(self) -> bool:
        """
        Return the last commanded state tracked by software.

        Note
        ----
        - This does not read back any latching/feedback from the relay.
          For most relay boards there is no true state feedback, so we expose the
          software-tracked state for convenience.
        """
        return self._is_on

    def destroy(self) -> None:
        """
        Safely release GPIO resources for this pin:
        - drives the pin to OFF (HIGH) if possible,
        - calls GPIO.cleanup(self.gpio_pin) to free the channel.
        Use this when permanently disposing of the instance.
        """
        try:
            GPIO.output(self.gpio_pin, GPIO.HIGH)  # best effort: ensure OFF
        except Exception:
            pass
        GPIO.cleanup(self.gpio_pin)

    def __repr__(self):
        """
        Human-friendly representation including:
        - logical channel and GPIO pin
        - software-tracked state (ON/OFF)
        - current GPIO input reading for the pin (0/1) which reflects the
          last output level set (for outputs, reading is usually the same level).
        """
        str_out = ""
        str_out += f"Pump(channel={self.channel}, gpio_pin={self.gpio_pin})"
        str_out += f"    state={'ON' if self._is_on else 'OFF'}, gpioState={GPIO.input(self.gpio_pin)}"
        return str_out


if __name__ == "__main__":
    # Minimal interactive test harness:
    # - Creates four pumps on common relay pins (adjust to your wiring)
    # - Allows toggling one or all via console commands
    try:
        p1 = Pump(channel=1, gpio_pin=17)
        p2 = Pump(channel=2, gpio_pin=18)
        p3 = Pump(channel=3, gpio_pin=15)
        p4 = Pump(channel=4, gpio_pin=14)
        pumps = [p1, p2, p3, p4]

        while True:
            cmd = input("1/2/3/4 = toggle, a = toggle all, q = quit: ").strip().lower()
            if cmd in ('1', '2', '3', '4'):
                idx = int(cmd) - 1
                p = pumps[idx]
                print(p)
                p.toggle()
                print(p, "\n")
            elif cmd == 'a':
                for p in pumps:
                    print(p)
                    p.toggle()
                    print(p, "\n")
            elif cmd == 'q':
                print("Exit")
                break
    except KeyboardInterrupt:
        # Ensure pins are released on Ctrl+C
        GPIO.cleanup()
    finally:
        # Always perform a final cleanup to avoid leaving pins exported
        GPIO.cleanup()
