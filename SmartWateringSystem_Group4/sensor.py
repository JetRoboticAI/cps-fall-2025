"""
ADS1115-based capacitive soil moisture sensor helper.

Design goals
------------
- Provide a small, reusable wrapper around Adafruit's ADS1115 driver for reading
  soil moisture sensors (capacitive probes) connected single-ended to A0..A3.
- Share ONE I2C bus and ONE ADS1115 object across all Sensor instances in the
  same Python process. This prevents reinitializing hardware per instance.
- Support simple calibration with two voltage anchors:
    v_dry : voltage observed when soil is bone-dry  (higher voltage)
    v_wet : voltage observed when soil is saturated (lower voltage)
  Humidity (%) is mapped linearly from voltage using these anchors.
- Offer convenience methods:
    read_voltage(n)          -> averaged voltage (V)
    get_humidity(n, v)       -> percentage [0..100], from averaged voltage or a supplied voltage
    get_raw(n)               -> raw ADC value as returned by the library (driver scale)
    get_dry(n, v)            -> dryness (%) = 100 - humidity
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Mode
from adafruit_ads1x15.analog_in import AnalogIn


class Sensor:
    """
    Represents one soil moisture input connected to a single-ended ADS1115 channel.

    This class uses process-wide, shared hardware handles:
      - Sensor._i2c : the shared busio.I2C object
      - Sensor._ads : the shared ADS.ADS1115 object
      - Sensor._ads_addr : the I2C address that _ads was created with
    The first Sensor created will initialize the hardware. Subsequent Sensors
    reuse the same ADS/I2C objects (address must match) and may update gain and data_rate.
    """

    # Shared I2C/ADS device within the current Python process
    _i2c = None          # type: busio.I2C | None
    _ads = None          # type: ADS.ADS1115 | None
    _ads_addr = None     # type: int | None

    # Map logical 0..3 channels to Adafruit constants
    _CHAN_MAP = {
        0: ADS.P0,
        1: ADS.P1,
        2: ADS.P2,
        3: ADS.P3,
    }

    def __init__(
        self,
        channel: int,
        adc_addr: int = 0x48,
        v_dry: float = 2.2,
        v_wet: float = 0.9,
        gain: int = 1,
        data_rate: int = 128
    ):
        """
        Create a Sensor bound to a single ADS1115 channel.

        Parameters
        ----------
        channel : int
            ADS1115 single-ended channel index (0..3).
        adc_addr : int
            I2C address of the ADS1115 (default 0x48).
        v_dry : float
            Calibration anchor (volts) measured when soil is completely dry.
            Typically higher than v_wet for capacitive probes.
        v_wet : float
            Calibration anchor (volts) measured when soil is fully wet.
        gain : int
            ADS1115 gain setting (maps to input range; see Adafruit docs).
        data_rate : int
            ADS1115 data rate in SPS (samples per second).

        Notes
        -----
        - If this is the first Sensor instance, the I2C bus and ADS1115 are created here.
        - If an ADS1115 already exists, 'adc_addr' must match the existing address.
          The shared ADS object's gain and data_rate are updated to the values passed here.
        """
        if channel not in self._CHAN_MAP:
            raise ValueError("channel 0 - 3 only")

        # Initialize or reuse the shared ADS1115
        if Sensor._ads is None:
            # First Sensor in the process: set up the I2C bus and ADS1115 device
            Sensor._i2c = busio.I2C(board.SCL, board.SDA)
            Sensor._ads = ADS.ADS1115(Sensor._i2c, address=adc_addr)
            Sensor._ads.gain = gain
            Sensor._ads.data_rate = data_rate
            Sensor._ads_addr = adc_addr
            # Optional: switch to single-shot mode if desired (continuous is default)
            # Sensor._ads.mode = Mode.SINGLE
        else:
            # Reuse existing ADS, but ensure the address matches
            if Sensor._ads_addr != adc_addr:
                raise ValueError(
                    f"ADS1115 address mismatch: previously initialized with 0x{Sensor._ads_addr:02X}"
                )
            # Update shared gain/data_rate to the most recently requested values
            Sensor._ads.gain = gain
            Sensor._ads.data_rate = data_rate

        # Store per-instance calibration and channel metadata
        self.channel = channel
        self.adc_addr = adc_addr
        self.v_dry = float(v_dry)
        self.v_wet = float(v_wet)

        # Create a channel view object for reads on this specific input
        self._chan = AnalogIn(Sensor._ads, self._CHAN_MAP[channel])

    # ==== voltage reading =====================================================

    def read_voltage(self, n: int = 1) -> float:
        """
        Read the channel voltage in volts. If n>1, return the arithmetic mean of n samples.

        Parameters
        ----------
        n : int
            Number of samples to average (default 1). A small average helps reduce noise.

        Returns
        -------
        float
            Voltage in volts.

        Implementation details
        ----------------------
        - The first read is intentionally discarded to mitigate a potential stale/settling read
          immediately after channel access (empirical practice).
        - A short sleep (~2 ms) between samples helps stabilize readings at higher data rates.
        """
        _ = self._chan.voltage  # discard the first reading
        if n <= 1:
            return float(self._chan.voltage)

        total = 0.0
        for _ in range(n):
            total += float(self._chan.voltage)
            time.sleep(0.002)
        return total / n

    # ==== humidity calculation ===============================================

    def get_humidity(self, n: int = 1, v: float | None = None) -> float:
        """
        Compute humidity (%) from either a supplied voltage or an averaged read.

        Parameters
        ----------
        n : int
            Number of samples to average if 'v' is None.
        v : float | None
            If provided, use this voltage (volts) instead of reading from hardware.

        Returns
        -------
        float
            Humidity percentage in the range [0..100], clamped.

        Notes
        -----
        - Uses a linear map between the calibration anchors (v_dry -> 0%, v_wet -> 100%).
        - For capacitive probes, typical behavior is voltage decreases as moisture increases.
        """
        if v is None:
            v = self.read_voltage(n)
        return self._map_to_percent(v, self.v_dry, self.v_wet)

    def get_raw(self, n: int = 1) -> int:
        """
        Return the raw ADC reading as reported by Adafruit's driver.

        Parameters
        ----------
        n : int
            Number of samples to average (integer average). Default 1.

        Returns
        -------
        int
            Raw ADC value on the driver's native scale (see Adafruit docs).

        Implementation details
        ----------------------
        - Like read_voltage(), the first read is discarded.
        - The result is an integer mean when n>1 (floor division).
        """
        _ = self._chan.value  # discard first reading
        if n <= 1:
            return int(self._chan.value)

        total = 0
        for _ in range(n):
            total += int(self._chan.value)
            time.sleep(0.002)
        return total // n

    def get_dry(self, n: int = 1, v: float | None = None) -> float:
        """
        Convenience: return dryness (%) = 100 - humidity.

        Parameters
        ----------
        n : int
            Number of samples to average if 'v' is None.
        v : float | None
            Optional pre-read voltage to reuse.

        Returns
        -------
        float
            Dryness percentage in the range [0..100].
        """
        return 100.0 - self.get_humidity(n, v)

    # ==== mapping utility =====================================================

    @staticmethod
    def _map_to_percent(num: float, hi: float, lo: float) -> float:
        """
        Map 'num' in the interval [lo, hi] to a percentage [0..100], clamped.

        Parameters
        ----------
        num : float
            Measured voltage to map.
        hi : float
            Voltage corresponding to 0% humidity (dry anchor).
        lo : float
            Voltage corresponding to 100% humidity (wet anchor).

        Returns
        -------
        float
            Percentage in [0..100].

        Explanation
        -----------
        For capacitive sensors: higher voltage -> drier soil.
        We therefore compute:
            pct = (hi - num) / (hi - lo) * 100
        and clamp to [0, 100]. A tiny minimum span prevents division by zero.
        """
        span = max(1e-9, hi - lo)
        pct = (hi - num) / span * 100.0
        return max(0.0, min(100.0, pct))

    # ==== representation ======================================================

    def __repr__(self):
        """
        Human-friendly status string including calibration and a live sample.
        Note: this performs a read to include current voltage and computed humidity.
        """
        v = self.read_voltage()
        h = self.get_humidity(v=v)
        d = 100.0 - h
        return (
            f"Sensor(channel={self.channel}, addr=0x{self.adc_addr:02X}, gain={Sensor._ads.gain}, "
            f"v_dry={self.v_dry}V, v_wet={self.v_wet}V)\n"
            f"    voltage={v:.3f}V, humidity={h:.1f}%, dry={d:.1f}%"
        )


if __name__ == '__main__':
    # Example: create four sensors on the same ADS1115 (0x48), one per channel,
    # with identical calibration anchors. Adjust v_dry/v_wet to your probes.
    s1 = Sensor(channel=0, adc_addr=0x48, v_dry=2.2, v_wet=0.9)
    s2 = Sensor(channel=1, adc_addr=0x48, v_dry=2.2, v_wet=0.9)
    s3 = Sensor(channel=2, adc_addr=0.48, v_dry=2.2, v_wet=0.9)  # <-- NOTE: typo? 0.48 probably meant 0x48
    s4 = Sensor(channel=3, adc_addr=0x48, v_dry=2.2, v_wet=0.9)
    sensors = [s1, s2, s3, s4]

    try:
        # Simple continuous printout every 3 seconds. Press Ctrl+C to exit.
        while True:
            for i, s in enumerate(sensors):
                print(f"Sensor {i + 1}: {s}")
            print()
            time.sleep(3)
    except KeyboardInterrupt:
        print("Exit")
