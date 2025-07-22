#!/usr/bin/env python3
import sys
import re
import os

def restore_math_blocks(input_text):
    # Wrap align-like environments in $$ again
    def replacer(match):
        env = match.group(1)
        body = match.group(2)
        return f"$$\n\\begin{{{env}}}{body}\\end{{{env}}}\n$$"

    result = re.sub(
        r'\\begin\{(align\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}',
        replacer,
        input_text,
        flags=re.DOTALL
    )
    return result

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: restore_math_blocks.py <input_file.md>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    restored = restore_math_blocks(content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(restored)

    print(f"{file_path} math blocks restored with $$")