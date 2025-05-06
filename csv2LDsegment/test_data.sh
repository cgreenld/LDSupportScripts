#!/bin/bash
# Description: Script to generate CSV with random 5-digit strings

# Exit on any error
set -e

# Set output file
OUTPUT_FILE="test_data.csv"

# Create/clear the output file
echo "id" > $OUTPUT_FILE

# Generate 200 random 5-digit numbers
echo "Generating 200 random 5-digit strings..."
for i in {1..200}
do
    # Generate random number between 10000 and 99999
    random_num=$(printf "%05d\n" $(( RANDOM % 90000 + 10000 )))
    echo "$random_num" >> $OUTPUT_FILE
done

echo "Generated $OUTPUT_FILE with 200 entries"
echo "Script completed successfully"