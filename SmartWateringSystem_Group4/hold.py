"""
Timed, thread-safe pump holding manager.

Overview
--------
This helper coordinates ON/OFF timing for multiple pump objects (e.g., relay-driven
water pumps). Each pump can be "held" ON for a given duration. If a new hold arrives
for the same pump before the timer expires, the hold is *extended* (the old timer is
canceled and replaced by a new one). When a hold expires, the pump is turned OFF.

Key ideas
---------
- One `threading.Timer` per pump index manages the scheduled OFF event.
- A per-pump unique `token` guards against stale timers: only the *latest* token
  is allowed to switch the pump OFF. If an older timer fires, it does nothing.
- A single `threading.Lock` protects shared state (`_timers`, `_tokens`, `_deadlines`).
- Two callbacks are injected:
    * on_begin(): called when a pump transitions from idle to ON (the caller may
      internally track global "first pump ON" semantics if needed).
    * on_end():   called when a pump transitions from ON to OFF (the caller may
      track "last pump OFF" semantics externally).

Typical usage
-------------
    manager = PumpHoldManager(pumps, on_begin=..., on_end=...)
    manager.hold(idx=0, duration=3.0)   # turn pump 0 ON for 3s (or extend if already ON)
    manager.remaining(0)                 # seconds remaining
    manager.off(0)                       # force OFF now
    manager.off_all()                    # force OFF all
"""

import threading
import time
from typing import Callable, List, Optional, Any


class PumpHoldManager:
    def __init__(
        self,
        pumps: List[Any],
        on_begin: Callable[[], None],
        on_end: Callable[[], None]
    ) -> None:
        """
        Create a timed hold manager for a sequence of pump-like objects.

        Parameters
        ----------
        pumps : list of Any
            Sequence of pump instances. Each pump is expected to expose:
              - on()  -> None : turn the pump ON
              - off() -> None : turn the pump OFF
        on_begin : Callable[[], None]
            Callback invoked when a pump transitions from idle to ON.
            (If you need "global first pump ON" semantics, implement that inside
             the callback using your own counters/locks.)
        on_end : Callable[[], None]
            Callback invoked when a pump transitions from ON to OFF.
            (Likewise, "global last pump OFF" can be implemented in the callback.)

        Internal structures
        -------------------
        - _timers[i]    : the active Timer for pump i, or None
        - _tokens[i]    : a unique object marking the *current* scheduled-off cycle
        - _deadlines[i] : POSIX timestamp (float) when pump i is expected to switch OFF
        """
        self.pumps = pumps
        n = len(pumps)
        self._lock = threading.Lock()
        self._timers: List[Optional[threading.Timer]] = [None] * n
        self._tokens: List[Optional[object]] = [None] * n
        self._deadlines: List[float] = [0.0] * n
        self._on_begin = on_begin
        self._on_end = on_end

    # ---- public API ----------------------------------------------------------

    def hold(self, idx: int, duration: float, *, source: str = "manual") -> str:
        """
        Start or extend a timed hold for pump `idx`.

        If the pump is currently idle (no active hold), it is turned ON and
        a timer is scheduled to turn it OFF after `duration` seconds.
        If the pump is already ON (an active hold exists), the existing timer
        is canceled and replaced, effectively **extending** the hold.

        Parameters
        ----------
        idx : int
            Pump index in the provided `pumps` list.
        duration : float
            Seconds to keep the pump ON from *now*. Must be >= 0.
        source : str
            Optional tag for logging/diagnostics.

        Returns
        -------
        str
            "started" if the pump transitioned from idle to ON,
            "extended" if the pump was already ON and its timer was extended.

        Thread-safety
        -------------
        This method acquires the internal lock while updating shared state
        and scheduling the new timer.

        Raises
        ------
        Exception
            Any exception raised by the underlying pump's `on()` will
            be propagated after invoking `on_end()` as a rollback.
        """
        with self._lock:
            # Cancel any existing timer for this pump
            if self._timers[idx] is not None:
                try:
                    self._timers[idx].cancel()
                except Exception:
                    pass  # Best-effort cancel; timer might have just fired

            is_idle = (self._tokens[idx] is None)

            # If idle, turn the pump ON and notify via callback
            if is_idle:
                self._on_begin()
                try:
                    self.pumps[idx].on()
                    print(f"[{source}] ON  pump zone={idx+1}")
                except Exception:
                    # If the pump failed to turn ON, roll back begin-notification
                    self._on_end()
                    raise

            # Create a fresh token and deadline for this hold
            token = object()  # unique object identity for this hold
            self._tokens[idx] = token
            self._deadlines[idx] = time.time() + max(0.0, float(duration))

            # Schedule a timer to finalize (turn OFF) after `duration` seconds
            t = threading.Timer(max(0.0, float(duration)), self._finalize, args=(idx, token, source))
            t.daemon = True
            self._timers[idx] = t
            t.start()

            return "started" if is_idle else "extended"

    def off(self, idx: int, *, source: str = "manual") -> bool:
        """
        Force pump `idx` OFF immediately, canceling any scheduled timer.

        Parameters
        ----------
        idx : int
            Pump index in the provided `pumps` list.
        source : str
            Optional tag for logging/diagnostics.

        Returns
        -------
        bool
            True if the pump was ON and is now turned OFF;
            False if the pump was already idle (no active hold).
        """
        with self._lock:
            # Cancel and clear the timer if present
            if self._timers[idx] is not None:
                try:
                    self._timers[idx].cancel()
                except Exception:
                    pass
            # If already idle, nothing to do
            if self._tokens[idx] is None:
                return False

            # Clear token/timer/deadline under the lock
            self._tokens[idx] = None
            self._timers[idx] = None
            self._deadlines[idx] = 0.0

        # Perform the OFF action outside the lock (avoid blocking critical section)
        try:
            self.pumps[idx].off()
            print(f"[{source}] OFF pump zone={idx+1}")
        finally:
            # Notify that a pump has ended
            self._on_end()
        return True

    def off_all(self, *, source: str = "manual") -> None:
        """
        Force all pumps OFF immediately, canceling any scheduled timers.
        Calls `off()` per pump and triggers the corresponding callbacks per pump.
        """
        for i in range(len(self.pumps)):
            self.off(i, source=source)

    def remaining(self, idx: int) -> float:
        """
        Return remaining ON-time for pump `idx` in seconds (>= 0.0).

        If the pump is idle or deadline is in the past, returns 0.0.
        """
        with self._lock:
            r = self._deadlines[idx] - time.time()
        return max(0.0, r)

    def is_on(self, idx: int) -> bool:
        """
        Return True if pump `idx` currently has an active hold (ON), else False.
        """
        with self._lock:
            return self._tokens[idx] is not None

    # ---- internal helpers ----------------------------------------------------

    def _finalize(self, idx: int, token: object, source: str) -> None:
        """
        Timer callback to turn a pump OFF when a hold expires.

        Token logic
        -----------
        Only the *current* token may finalize the pump. If this callback was scheduled
        by an older hold (a stale timer), it will find a different token in `_tokens[idx]`
        and **return without doing anything**.

        This guards against races where an "extend" created a new timer but the previous
        timer fires slightly later.
        """
        # Validate that this timer corresponds to the latest scheduled hold
        with self._lock:
            if self._tokens[idx] is not token:
                return  # stale timer; another hold superseded this one
            # Clear state for this pump
            self._tokens[idx] = None
            self._timers[idx] = None
            self._deadlines[idx] = 0.0

        # Turn OFF outside the lock and notify
        try:
            self.pumps[idx].off()
            print(f"[{source}] OFF pump zone={idx+1}")
        finally:
            self._on_end()


# ---- simple self-test / demonstration ---------------------------------------
if __name__ == "__main__":
    from pump import Pump

    # Example GPIO pins; adjust to your wiring
    p1 = Pump(channel=1, gpio_pin=12)
    p2 = Pump(channel=2, gpio_pin=16)
    p3 = Pump(channel=3, gpio_pin=20)
    p4 = Pump(channel=4, gpio_pin=21)

    pumps = [p1, p2, p3, p4]

    def clean():
        """Turn everything OFF and release GPIO on exit."""
        hold.off_all(source="cleanup")
        for p in pumps:
            try:
                p.destroy()
            except Exception as e:
                print(f"\n[cleanup] pump destroy err: {e}")
        print("\n[cleanup] GPIO released.")

    def on_begin():
        """Called when a pump transitions from idle to ON."""
        print("A pump has started.")

    def on_end():
        """Called when a pump transitions from ON to OFF."""
        print("A pump has ended.")

    try:
        hold = PumpHoldManager(pumps, on_begin=on_begin, on_end=on_end)
        # Staggered holds: each call schedules an OFF. Later ones can extend if repeated.
        hold.hold(0, 4, source="test")
        hold.hold(1, 3, source="test")
        hold.hold(2, 2, source="test")
        hold.hold(3, 1, source="test")
        time.sleep(5)  # wait long enough to observe timers expiring
    finally:
        clean()
