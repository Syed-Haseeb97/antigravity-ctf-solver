import sys

TARGET = [58, 51, 57, 44, 33, 105, 25, 16, 14, 0, 10, 118, 97, 106, 94, 82, 81, 75, 81, 192, 187, 214, 223, 154, 155, 153, 130, 134, 248, 234, 229, 235, 220, 198, 168, 206, 182, 56, 76, 84, 35, 35, 7, 168, 179, 183, 197, 194, 19]

def vm_run(key: str) -> bool:
    if len(key) != 49:
        return False
    data = [ord(c) for c in key]
    res = []
    for i, b in enumerate(data):
        # Instruction stream:
        # OP 0x01: XOR_CONST 0x4B
        t = (b ^ 0x4B)
        # OP 0x02: ADD_CONST 13 (mod 256)
        t = (t + 13) % 256
        # OP 0x03: XOR_INDEX_MOD (i * 7)
        t = t ^ ((i * 7) % 256)
        res.append(t)
    return res == TARGET

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if vm_run(sys.argv[1]):
            print("ACCESS GRANTED")
            sys.exit(0)
    print("ACCESS DENIED")
    sys.exit(1)
