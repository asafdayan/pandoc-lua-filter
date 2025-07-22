#!/usr/bin/env python3
import sys
import re
import os

def sanitize_markdown(input_text):
    lines = input_text.splitlines()
    output = []
    previous_blank = True

    i = 0
    while i < len(lines):
        line = lines[i]

        # Add blank lines around headings
        if re.match(r'^\s*#{1,6}\s+\S', line):
            if not previous_blank:
                output.append("")
            output.append(line)
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                output.append("")
            previous_blank = False
        else:
            output.append(line)
            previous_blank = (line.strip() == "")
        i += 1

    result = "\n".join(output)

    # Remove $$ around environments like align*, gather*, etc.
    result = re.sub(
        r'\$\$\s*\\begin\{(align\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}\s*\$\$',
        r'\\begin{\1}\2\\end{\1}',
        result,
        flags=re.DOTALL
    )

    return result

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: sanitize_markdown.py <input_file.md>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, encoding='utf-8') as f:
        input_text = f.read()

    sanitized = sanitize_markdown(input_text)

    # Overwrite the input file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(sanitized)

    print(f"{file_path} sanitized and saved.")