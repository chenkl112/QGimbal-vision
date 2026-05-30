import struct

from control.serial_stub import CMD_ENABLE, CMD_SPEED_CTRL, GimbalSerialStub, _crc8


def test_build_packet_layout_and_crc8() -> None:
    stub = GimbalSerialStub(port=None)

    packet = stub.build_packet(CMD_SPEED_CTRL, 12.5, -7.25)

    assert len(packet) == 10
    assert packet[0] == CMD_SPEED_CTRL
    assert struct.unpack("<ff", packet[1:9]) == (12.5, -7.25)
    assert packet[-1] == _crc8(packet[:-1])


def test_send_rpm_writes_speed_ctrl_packet() -> None:
    class FakeSerial:
        def __init__(self) -> None:
            self.writes: list[bytes] = []

        def write(self, data: bytes) -> None:
            self.writes.append(bytes(data))

    stub = GimbalSerialStub(port=None)
    fake_serial = FakeSerial()
    stub._ser = fake_serial

    stub.send_rpm(1.5, 2.5)

    assert fake_serial.writes == [stub.build_packet(CMD_SPEED_CTRL, 1.5, 2.5)]


def test_start_writes_enable_command() -> None:
    class FakeSerial:
        def __init__(self) -> None:
            self.writes: list[bytes] = []

        def write(self, data: bytes) -> None:
            self.writes.append(bytes(data))

    stub = GimbalSerialStub(port=None)
    fake_serial = FakeSerial()
    stub._ser = fake_serial

    stub.start()

    assert fake_serial.writes == [stub.build_packet(CMD_ENABLE, 0.0, 0.0)]
