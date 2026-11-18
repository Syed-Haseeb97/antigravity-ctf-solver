# Linear Congruential Keystream Generator
A = 1664525
C = 1013904223
M = 2**32

class StreamCipher:
    def __init__(self, seed: int):
        self.state = seed

    def next_byte(self) -> int:
        self.state = (A * self.state + C) % M
        return (self.state >> 16) & 0xFF

def encrypt(data: bytes, seed: int) -> bytes:
    cipher = StreamCipher(seed)
    pad = (4 - (len(data) % 4)) % 4
    data += b"\x00" * pad
    chunked = bytearray()
    for i in range(0, len(data), 4):
        chunked.extend(data[i:i+4][::-1])
    ks = bytes([cipher.next_byte() for _ in range(len(chunked))])
    return bytes([c ^ k for c, k in zip(chunked, ks)])

# The target seed was generated as a 16-bit offset in range [0x8000, 0x9000]
# Known plaintext prefix: "flag{"
