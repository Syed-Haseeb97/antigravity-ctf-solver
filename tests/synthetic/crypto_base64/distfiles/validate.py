import sys
import hashlib

EXPECTED_HASH = "c13de28b64af2ef4004419909047748bfa9716c6ca37e79932dbc55e91cad1cf"

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
    main()
