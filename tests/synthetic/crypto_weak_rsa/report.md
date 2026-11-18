# Investigation Report: Mini RSA
- **Status**: `SOLVED`
- **Flag**: `flag{rsa_m42_factored}`
- **Category**: crypto
- **Turns**: 1
- **Time**: 79.40s
- **Tokens**: 22734

## Timeline of Turns
### Turn 1 (read_file)
- **Hypothesis**: Inspecting /challenge/distfiles/rsa.py will reveal the public key parameters (n, e) and the encrypted flag ciphertext c.
- **Thought**: We need to solve 'Mini RSA'. Tiny primes were used, so n can likely be factored very quickly or directly inspected. First, let's examine the distribution files in /challenge/distfiles/ to see the values of n, e, and ciphertext c, as well as the validation logic.
- **Command**: `/challenge/distfiles/rsa.py`
- **Exit Code**: 0
```
# RSA Parameters:
n = 3233
e = 17
c = 2557
# The flag is formatted as: flag{rsa_m42_factored}

```
