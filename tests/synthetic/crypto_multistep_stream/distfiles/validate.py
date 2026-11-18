import sys
import hashlib

EXPECTED_HASH = "4cf4efdade08d161a01aea5ecdad0e61afd1f0e3146279a0abea67072e85e892"

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
