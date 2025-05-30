#!/bin/bash

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first."
    exit 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed. Please install curl first."
    exit 1
fi

# Function to display usage
usage() {
    echo "Usage: $0 -k <api_key> -d <days>"
    echo "Options:"
    echo "  -k    LaunchDarkly API key with reader access"
    echo "  -d    Number of days to check for inactivity"
    echo "Example: $0 -k api-123456 -d 30"
    exit 1
}

# Parse command line arguments
while getopts "k:d:" opt; do
    case $opt in
        k) API_KEY="$OPTARG";;
        d) DAYS="$OPTARG";;
        ?) usage;;
    esac
done

# Validate required parameters
if [ -z "$API_KEY" ] || [ -z "$DAYS" ]; then
    echo "Error: Both API key and days are required"
    usage
fi

# Validate days is a number
if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
    echo "Error: Days must be a positive integer"
    exit 1
fi

# API endpoint
API_URL="https://app.launchdarkly.com/api/v2/members"

# Calculate timestamp for X days ago in milliseconds
DAYS_AGO_MS=$(( $(date +%s) * 1000 - DAYS * 24 * 60 * 60 * 1000 ))

# Create output files with timestamp
OUTPUT_FILE="inactive_members_$(date +%Y%m%d_%H%M%S).txt"
DELETION_LOG="inactive_members_deletion_$(date +%Y%m%d_%H%M%S).json"

# Initialize variables
current_url="$API_URL"
page=1
nextPage=1
total_processed=0
inactive_count=0

echo "Checking for members who haven't logged in for $DAYS days or more..."
echo "----------------------------------------"

# Initialize deletion log file with array start
echo "[" > "$POTENTIAL_DELETION_LOG"

# Main pagination loop
while [ $nextPage -eq 1 ]; do
    echo "Processing page $page..." >&2
    
    # Get the page data
    response=$(curl -s -H "Authorization: $API_KEY" "$current_url")
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to fetch data from $current_url" >&2
        echo "Current URL: $current_url"
        echo "Response: "
        echo "$response"
        exit 1
    fi
    
    # Process the response to find inactive members
    echo "$response" | jq --arg days_ago "$DAYS_AGO_MS" '
    .items[] | 
    select(._lastSeen == null or ._lastSeen < ($days_ago | tonumber)) |
    select(.email != "demoengineering@launchdarkly.com") |
    {
        email: .email,
        lastSeen: (if ._lastSeen then (._lastSeen/1000 | strftime("%Y-%m-%d %H:%M:%S")) else "Never" end),
        daysInactive: (if ._lastSeen then (((now * 1000) - ._lastSeen)/86400000 | floor) else "N/A" end),
        role: .role,
        id: ._id
    } | 
    [.email, .lastSeen, .daysInactive, .role, .id] | 
    @tsv' -r | while IFS=$'\t' read -r email last_seen days_inactive role id; do
        printf "Email: %-40s Last Seen: %-20s Days Inactive: %-10s Role: %s\n" \
               "$email" "$last_seen" "$days_inactive" "$role" >> "$OUTPUT_FILE"
        
        # Add member to deletion log
        echo "{\"memberId\": \"$id\", \"email\": \"$email\", \"lastSeen\": \"$last_seen\", \"role\": \"$role\"}" >> "$DELETION_LOG"
        inactive_count=$((inactive_count + 1))
    done
    
    # Update total processed count
    page_members=$(echo "$response" | jq '.items | length')
    total_processed=$((total_processed + page_members))
    
    # Get the next URL from the response
    next_url=$(echo "$response" | jq -r '._links.next.href // empty')
    if [ -n "$next_url" ]; then
        current_url="https://app.launchdarkly.com$next_url"
    else
        nextPage=0
    fi
    
    page=$((page + 1))
done

# Close the JSON array in the deletion log
echo "]" >> "$DELETION_LOG"

echo "----------------------------------------"
echo "Search completed successfully"
echo "Total members processed: $total_processed"
echo "Total inactive members (excluding demo): $inactive_count"
echo "Results saved to: $OUTPUT_FILE"
echo "Deletion log created: $DELETION_LOG" 