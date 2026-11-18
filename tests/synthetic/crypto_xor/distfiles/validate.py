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
        print("INVALID: Incorrect flag.")
        sys.exit(1)

if __name__ == "__main__":
    main()
