# Investigation Report: Single Byte XOR
- **Status**: `SOLVED`
- **Flag**: `flag{xor_single_byte_cracked}`
- **Category**: crypto
- **Turns**: 4
- **Time**: 121.44s
- **Tokens**: 93552

## Timeline of Turns
### Turn 1 (bash)
- **Hypothesis**: The distfiles contain the hex-encoded ciphertext and the validation script showing the exact encryption method and flag structure.
- **Thought**: This is Turn 1 of a Crypto challenge involving single-byte XOR. The challenge files are located in `/challenge/distfiles/cipher.hex` and `/challenge/distfiles/validate.py`. Inspecting the files will reveal the ciphertext format, key space, and flag format/validation rules.
- **Command**: `cat /challenge/distfiles/cipher.hex; echo ''; cat /challenge/distfiles/validate.py`
- **Exit Code**: 0
```
3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27
import sys
import hashlib

EXPECTED_HASH = "5536686278be374f2cbfe6ec04813c5310a95bcd7a7405808db389ab958b2eed"

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
        print("INVALID: Incorrect fla...
```

### Turn 2 (bash)
- **Hypothesis**: Run output as bash
- **Thought**: Direct text output parsed as bash fallback
- **Command**: `{`
- **Exit Code**: 2
```
STDERR:
bash: -c: line 2: syntax error: unexpected end of file
```

### Turn 3 (bash)
- **Hypothesis**: Brute-forcing all 256 single-byte XOR keys on the ciphertext hex string will yield the plaintext whose SHA-256 matches EXPECTED_HASH.
- **Thought**: The ciphertext hex is '3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27'. It was encrypted using single-byte XOR. We can easily test all 256 possible single-byte keys in Python, decode to ASCII/UTF-8, check if the output matches standard flag format or printable English/flag format, and verify its SHA256 against EXPECTED_HASH ('5536686278be374f2cbfe6ec04813c5310a95bcd7a7405808db389ab958b2eed'). Let's run a one-line Python script via bash to find the key and print the flag.
- **Command**: `python3 -c 'import hashlib, bytes; ct = bytes.fromhex("3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27"); target = "5536686278be374f2cbfe6ec04813c5310a95bcd7a7405808db389ab958b2eed"; [print(f"KEY: {k}, PLAINTEXT: {res.decode(errors="replace")}") for k in range(256) for res in [bytes([b ^ k for b in ct])] if hashlib.sha256(res).hexdigest() == target or b"flag" in res.lower()]'`
- **Exit Code**: 1
```
STDERR:
  File "<string>", line 1
    import hashlib, bytes; ct = bytes.fromhex("3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27"); target = "5536686278be374f2cbfe6ec04813c5310a95bcd7a7405808db389ab958b2eed"; [print(f"KEY: {k}, PLAINTEXT: {res.decode(errors="replace")}") for k in range(256) for res in [bytes([b ^ k for b in ct])] if hashlib.sha256(res).hexdigest() == target or b"flag" in res.lower()]
                                                                                     ...
```

### Turn 4 (bash)
- **Hypothesis**: The single-byte XOR key is 0x5a, which decrypts the ciphertext to the flag starting with 'flag{'.
- **Thought**: The ciphertext hex is '3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27'. Let's check: typically flags start with 'flag{' or similar, or plaintext words. Let's see: ct[0..3] = 3c 36 3b 3d. If plaintext starts with 'flag{': 'f'=0x66 -> 0x3c ^ 0x66 = 0x5a ('Z'). If k = 0x5a: 0x3c^0x5a = 'f' (0x66), 0x36^0x5a = 'l' (0x6c), 0x3b^0x5a = 'a' (0x61), 0x3d^0x5a = 'g' (0x67), 0x21^0x5a = '{' (0x7b). Indeed, key = 0x5a! Let's decode the entire string with 0x5a: bytes([b ^ 0x5a for b in bytes.fromhex('3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27')]). Let's write a python one-liner without quotation syntax errors or run it cleanly via python3.
- **Command**: `python3 -c 'ct=bytes.fromhex("3c363b3d21223528052933343d363f0538232e3f0539283b39313f3e27"); pt=bytes([b^0x5a for b in ct]); print(pt.decode())'`
- **Exit Code**: 0
```
flag{xor_single_byte_cracked}
```
