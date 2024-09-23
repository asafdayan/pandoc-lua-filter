#!/bin/bash

# Usage function to display help
usage() {
  echo "Usage: $0 -v <file_path>"
  exit 1
}

# Parse the -v flag for the file path
while getopts ":v:" opt; do
  case $opt in
    v)
      file_path=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      usage
      ;;
  esac
done

# Check if the file path is provided
if [ -z "$file_path" ]; then
  usage
fi

# Extract the file name from the file path without the extension
file_name=$(basename "$file_path" .md)

# Run the pandoc command
pandoc "$file_path" --lua-filter=final_filter.lua --from=markdown+lists_without_preceding_blankline \
  --metadata=lang:he --metadata=dir:rtl -o "${file_name}.tex"

echo "Conversion complete: ${file_name}.tex created"
