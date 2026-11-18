# Investigation Report: EXIF Hunter
- **Status**: `SOLVED`
- **Flag**: `flag{exif_metadata_extracted_properly}`
- **Category**: forensics
- **Turns**: 2
- **Time**: 70.87s
- **Tokens**: 45970

## Timeline of Turns
### Turn 1 (bash)
- **Hypothesis**: The flag or verification logic is contained in or verified by /challenge/distfiles/validate.py, and evidence.jpg contains the comment metadata holding the flag.
- **Thought**: The challenge 'EXIF Hunter' explicitly directs us to look at the JPEG file's metadata and comment ('Metadata holds secrets. Inspect the file comment.'). We also have /challenge/distfiles/validate.py which likely contains the verification logic or flag format. First, inspecting validate.py and the distfiles directory will provide ground truth on what flag format is expected and what files exist.
- **Command**: `cat /challenge/distfiles/validate.py 2>/dev/null || cat validate.py 2>/dev/null || ls -la /challenge/distfiles`
- **Exit Code**: 0
```
import sys
import hashlib

EXPECTED_HASH = "6aab80793162fd854718985981050a29b1216d464e36abf679d1766ba3f1dac6"

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

### Turn 2 (bash)
- **Hypothesis**: The flag is stored in the JPEG comment or EXIF metadata of /challenge/distfiles/evidence.jpg.
- **Thought**: The validate.py script verifies the flag by checking if SHA256 matches EXPECTED_HASH ('6aab80793162fd854718985981050a29b1216d464e36abf679d1766ba3f1dac6'). The challenge description explicitly hints: 'Metadata holds secrets. Inspect the file comment.' The evidence image is located at /challenge/distfiles/evidence.jpg. We can use exiftool, strings, or python to inspect JPEG COM (Comment) markers / EXIF tags directly.
- **Command**: `exiftool /challenge/distfiles/evidence.jpg 2>/dev/null || python3 -c "from PIL import Image; img=Image.open('/challenge/distfiles/evidence.jpg'); print(img.app.get('COM') or img.info)" 2>/dev/null || strings /challenge/distfiles/evidence.jpg | grep -iE 'flag\{|ctf\{'`
- **Exit Code**: 0
```
ExifTool Version Number         : 12.40
File Name                       : evidence.jpg
Directory                       : /challenge/distfiles
File Size                       : 46 bytes
File Modification Date/Time     : 2026:11:18 02:47:52+00:00
File Access Date/Time           : 2026:11:18 02:47:52+00:00
File Inode Change Date/Time     : 2026:11:18 02:47:52+00:00
File Permissions                : -rwxrwxrwx
File Type                       : JPEG
File Type Extension             : jpg
MIME Type    ...
```
