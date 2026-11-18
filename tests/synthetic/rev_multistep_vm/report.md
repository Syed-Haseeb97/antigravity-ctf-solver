# Investigation Report: Bytecode Enigma
- **Status**: `SOLVED`
- **Flag**: `flag{vm_bytecode_disassembled_and_reversed_31415}`
- **Category**: rev
- **Turns**: 7
- **Time**: 262.49s
- **Tokens**: 166158

## Timeline of Turns
### Turn 1 (bash)
- **Hypothesis**: Inspect challenge files
- **Thought**: Text response parsed with safe fallback command
- **Command**: `ls -la /challenge/distfiles`
- **Exit Code**: 0
```
total 8
drwxrwxrwx 1 root root 4096 Nov 18 02:47 .
drwxr-xr-x 1 root root 4096 Nov 18 03:17 ..
-rwxrwxrwx 1 root root  510 Nov 18 02:47 validate.py
-rwxrwxrwx 1 root root  888 Nov 18 02:47 vm_checker.py
```

### Turn 2 (read_file)
- **Hypothesis**: Inspecting validate.py will reveal the challenge entry point, bytecode payload, or verification logic.
- **Thought**: The directory contains two Python files: validate.py and vm_checker.py. The first step in analyzing this reverse engineering challenge is to read the source code of both files to understand the VM structure, the bytecode instructions, and how the input flag is validated.
- **Command**: `/challenge/distfiles/validate.py`
- **Exit Code**: 0
```
import sys
import hashlib

EXPECTED_HASH = "2bf66b9cc09fcfd7ba6c81507c87441c783e249c5cd53cf5bc049a3eb03d0dad"

def main():
    if len(sys.argv) < 2:
        cand = sys.stdin.read().strip()
    else:
        cand = sys.argv[1].strip()

    h = hashlib.sha256(cand.encode("utf-8")).hexdigest()
    if h == EXPECTED_HASH:
        print("VALID: Flag accepted!")
        sys.exit(0)
    else:
        print("INVALID: Incorrect flag.")
        sys.exit(1)

if __name__ == "__main__":
  ...
```

### Turn 3 (read_file)
- **Hypothesis**: Inspecting vm_checker.py will reveal the custom virtual machine architecture, the instruction decoder, and the bytecode payload required to reverse the flag.
- **Thought**: In Turn 2, validate.py was read and appears to verify candidate input against a SHA-256 hash. The challenge description states that a custom virtual machine evaluates input keys with transformations such as XOR, ADD, and ROL. The file vm_checker.py likely contains the VM implementation, bytecode, and validation logic.
- **Command**: `/challenge/distfiles/vm_checker.py`
- **Exit Code**: 0
```
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
    ...
```

### Turn 4 (bash)
- **Hypothesis**: Inspect challenge files
- **Thought**: Text response parsed with safe fallback command
- **Command**: `ls -la /challenge/distfiles`
- **Exit Code**: 0
```
total 8
drwxrwxrwx 1 root root 4096 Nov 18 02:47 .
drwxr-xr-x 1 root root 4096 Nov 18 03:17 ..
-rwxrwxrwx 1 root root  510 Nov 18 02:47 validate.py
-rwxrwxrwx 1 root root  888 Nov 18 02:47 vm_checker.py
```

### Turn 5 (bash)
- **Hypothesis**: Displaying the complete contents of vm_checker.py will reveal the full transformation logic and operations applied to the input bytes.
- **Thought**: In Turn 3, reading `/challenge/distfiles/vm_checker.py` was truncated right at the transformation loop inside `vm_run`. I need the full contents of `vm_checker.py` to see the complete VM logic and transformation pipeline so that we can write a solver script or invert the operations.
- **Command**: `cat /challenge/distfiles/vm_checker.py`
- **Exit Code**: 0
```
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
    ...
```

### Turn 6 (bash)
- **Hypothesis**: Viewing lines 10 to 40 of vm_checker.py will reveal the complete byte transformation algorithm applied inside vm_run.
- **Thought**: In Turn 5, the output of `cat /challenge/distfiles/vm_checker.py` was truncated before showing the loop body of `vm_run`. We need to see the full transformation operations (e.g., XOR, addition, bit rotations, or index-based operations) applied to `data` to invert them against `TARGET`.
- **Command**: `tail -n +10 /challenge/distfiles/vm_checker.py`
- **Exit Code**: 0
```
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
    s...
```

### Turn 7 (bash)
- **Hypothesis**: Inverting the mathematical transformation pipeline on the TARGET array will reconstruct the full 49-character flag.
- **Thought**: The byte transformation pipeline inside vm_run applies three sequential invertible operations to each input character byte: XOR with 0x4B, modular addition of 13, and XOR with ((i * 7) % 256). Since all operations are fully reversible, we can invert them in reverse order: b = (((TARGET[i] ^ ((i * 7) % 256)) - 13) % 256) ^ 0x4B.
- **Command**: `python3 -c "TARGET = [58, 51, 57, 44, 33, 105, 25, 16, 14, 0, 10, 118, 97, 106, 94, 82, 81, 75, 81, 192, 187, 214, 223, 154, 155, 153, 130, 134, 248, 234, 229, 235, 220, 198, 168, 206, 182, 56, 76, 84, 35, 35, 7, 168, 179, 183, 197, 194, 19]; print(''.join(chr((((t ^ ((i * 7) % 256)) - 13) % 256) ^ 0x4B) for i, t in enumerate(TARGET)))"`
- **Exit Code**: 0
```
flag{vm_bytecode_disassembled_and_reversed_31415}
```
