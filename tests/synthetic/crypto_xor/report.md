# Investigation Report: Single Byte XOR
- **Status**: `SOLVED`
- **Flag**: `flag{xor_single_byte_cipher_cracked}`
- **Category**: crypto
- **Turns**: 1
- **Time**: 5.28s
- **Tokens**: 199

## Timeline of Turns
### Turn 1 (bash)
- **Hypothesis**: Single byte XOR key
- **Thought**: Brute force single-byte XOR key
- **Command**: `python3 -c "data = bytes.fromhex(open('distfiles/cipher.hex').read().strip()); print([bytes([b ^ k for b in data]) for k in range(256) if b'flag{' in bytes([b ^ k for b in data])][0].decode())"`
- **Exit Code**: 0
```
flag{xor_single_byte_cipher_cracked}
```
