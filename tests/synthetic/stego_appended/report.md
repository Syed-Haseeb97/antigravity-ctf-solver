# Investigation Report: Appended PNG
- **Status**: `SOLVED`
- **Flag**: `flag{appended_bytes_stego_found}`
- **Category**: stego
- **Turns**: 1
- **Time**: 37.52s
- **Tokens**: 22850

## Timeline of Turns
### Turn 1 (bash)
- **Hypothesis**: The flag or a clue is appended directly after the PNG IEND chunk or validate.py contains the flag format/logic.
- **Thought**: The challenge title is 'Appended PNG' and the description says 'Check what lies past the image trailer.' The distfiles are /challenge/distfiles/hidden.png and /challenge/distfiles/validate.py. In PNG format, the image ends with an IEND chunk (`49 45 4E 44 AE 42 60 82`). Any data appended after the IEND chunk can be extracted directly, or we can inspect trailing bytes or strings. First, let's examine /challenge/distfiles/validate.py and inspect trailing bytes of /challenge/distfiles/hidden.png using a bash command or reading validate.py.
- **Command**: `python3 -c "with open('/challenge/distfiles/hidden.png', 'rb') as f: data = f.read(); idx = data.find(b'IEND'); print('After IEND:', data[idx+8:])" && cat /challenge/distfiles/validate.py`
- **Exit Code**: 0
```
After IEND: b'\nSECRET_FLAG=flag{appended_bytes_stego_found}\n'
import sys
import hashlib

EXPECTED_HASH = "8c95f122088c4f6c937383ff5dc13923b0633ac01f8a5184b89639ba1870b487"

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
        print("INVALID: Incorrec...
```
