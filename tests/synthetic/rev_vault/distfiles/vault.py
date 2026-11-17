def check_pass(p):
    target = [102, 108, 97, 103, 123, 118, 97, 117, 108, 116, 95, 117, 110, 108, 111, 99, 107, 101, 100, 125]
    return [ord(c) for c in p] == target

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and check_pass(sys.argv[1]):
        print('Access Granted!')
    else:
        print('Denied')
