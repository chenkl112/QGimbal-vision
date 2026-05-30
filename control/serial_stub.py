from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Optional


CMD_NOP = 0x00
CMD_ENABLE = 0x01
CMD_DISABLE = 0x02
CMD_CURRENT_CTRL = 0x03
CMD_SPEED_CTRL = 0x04
CMD_ANGLE_CTRL = 0x05
CMD_LOW_SPEED_CTRL = 0x06
CMD_STEP_ANGLE_CTRL = 0x07
CMD_ENABLE_STABILITY = 0xFF
CMD_DISABLE_STABILITY = 0xFE
CMD_ENABLE_LASER = 0xFD
CMD_DISABLE_LASER = 0xFC
CMD_RESET_IMU = 0xFB


def _crc8(
    data: bytes,
    polynomial: int = 0x07,
    init: int = 0x00,
    xor_out: int = 0x00,
) -> int:
    """CRC8 matching the STM32 firmware implementation."""
    crc = init & 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polynomial) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return (crc ^ xor_out) & 0xFF


@dataclass(slots=True)
class GimbalSerialStub:
    """Serial sender for STM32 QGimbal firmware.

    Firmware RX packet format (little-endian, packed):
        uint8  cmd
        float  yaw
        float  pitch
        uint8  crc8   (CRC8 over previous 9 bytes)

    Command values mirror QGimbal/Applications/Src/TransmitTask.cpp.
    """

    port: Optional[str] = "/dev/ttyS1"
    baudrate: int = 115200

    # Compatibility with the previous API:
    # 0 disable, 1 enable, any other value leaves the state unchanged.
    laser_enabled: int = 2
    enabled: int = 1
    stability_enabled: int = 2

    _ser: object | None = field(default=None, init=False, repr=False)

    def open(self) -> None:
        """Open serial port and apply requested startup states."""
        if self.port is None:
            self._ser = None
            return

        import serial  # type: ignore

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0,
            write_timeout=0,
        )

        self._apply_startup_states()

    def close(self) -> None:
        ser = self._ser
        self._ser = None
        if ser is None:
            return

        if self.enabled == 1:
            try:
                ser.write(self.build_packet(CMD_DISABLE, 0.0, 0.0))
            except Exception:
                pass

        close = getattr(ser, "close", None)
        if callable(close):
            close()

    def build_packet(self, cmd: int, yaw: float = 0.0, pitch: float = 0.0) -> bytes:
        payload = struct.pack("<Bff", int(cmd) & 0xFF, float(yaw), float(pitch))
        return payload + struct.pack("<B", _crc8(payload))

    def send_command(self, cmd: int, yaw: float = 0.0, pitch: float = 0.0) -> None:
        ser = self._ser
        if ser is None:
            return

        write = getattr(ser, "write", None)
        if callable(write):
            write(self.build_packet(cmd, yaw, pitch))

    def send_rpm(self, yaw_rpm: float, pitch_rpm: float) -> None:
        """Send yaw/pitch speed command in RPM."""
        self.send_command(CMD_SPEED_CTRL, yaw_rpm, pitch_rpm)

    def start(self) -> None:
        self.send_command(CMD_ENABLE)

    def stop(self) -> None:
        self.send_command(CMD_DISABLE)

    def enable_stability(self) -> None:
        self.send_command(CMD_ENABLE_STABILITY)

    def disable_stability(self) -> None:
        self.send_command(CMD_DISABLE_STABILITY)

    def enable_laser(self) -> None:
        self.send_command(CMD_ENABLE_LASER)

    def disable_laser(self) -> None:
        self.send_command(CMD_DISABLE_LASER)

    def reset_imu(self) -> None:
        self.send_command(CMD_RESET_IMU)

    def _apply_startup_states(self) -> None:
        if self.enabled == 1:
            self.start()
        elif self.enabled == 0:
            self.stop()

        if self.stability_enabled == 1:
            self.enable_stability()
        elif self.stability_enabled == 0:
            self.disable_stability()

        if self.laser_enabled == 1:
            self.enable_laser()
        elif self.laser_enabled == 0:
            self.disable_laser()
