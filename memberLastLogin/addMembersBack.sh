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
    echo "Usage: $0 -k <api_key> -f <deletion_log_file> -prod <y/n>"
    echo "Options:"
    echo "  -k    LaunchDarkly API key with admin access"
    echo "  -f    Path to the deletion log JSON file"
    echo "  -prod Production mode (y/n) - if 'y', will require confirmation for each member"
    echo "Example: $0 -k api-123456 -f inactive_members_deletion_20240315_123456.json -prod n"
    exit 1
}

# Parse command line arguments
while getopts "k:f:prod:" opt; do
    case $opt in
        k) API_KEY="$OPTARG";;
        f) DELETION_LOG="$OPTARG";;
        prod) PROD_MODE="$OPTARG";;
        ?) usage;;
    esac
done

# Validate required parameters
if [ -z "$API_KEY" ] || [ -z "$DELETION_LOG" ] || [ -z "$PROD_MODE" ]; then
    echo "Error: API key, deletion log file, and production mode are required"
    usage
fi

# Validate production mode
if [ "$PROD_MODE" != "y" ] && [ "$PROD_MODE" != "n" ]; then
    echo "Error: Production mode must be either 'y' or 'n'"
    usage
fi

# Check if deletion log file exists
if [ ! -f "$DELETION_LOG" ]; then
    echo "Error: Deletion log file '$DELETION_LOG' not found"
    exit 1
fi

# API endpoint
API_URL="https://app.launchdarkly.com/api/v2/members"

# Create a log file for the add-back operation
ADD_BACK_LOG="add_back_results_$(date +%Y%m%d_%H%M%S).txt"
echo "Add Back Operation Log - $(date)" > "$ADD_BACK_LOG"
echo "Production Mode: $PROD_MODE" >> "$ADD_BACK_LOG"
echo "----------------------------------------" >> "$ADD_BACK_LOG"

# Initialize counters
total_members=0
successful_adds=0
failed_adds=0
skipped_members=0

# Process each member in the deletion log
jq -c '.[]' "$DELETION_LOG" | while read -r member; do
    email=$(echo "$member" | jq -r '.email')
    role=$(echo "$member" | jq -r '.role')
    
    echo "Processing member: $email (Role: $role)" >> "$ADD_BACK_LOG"
    
    # If in production mode, ask for confirmation
    if [ "$PROD_MODE" = "y" ]; then
        read -p "Add member $email with role $role? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "Skipping member $email" >> "$ADD_BACK_LOG"
            skipped_members=$((skipped_members + 1))
            continue
        fi
    fi
    
    # Prepare the JSON payload for the API request
    payload=$(jq -n \
        --arg email "$email" \
        --arg role "$role" \
        '{
            "email": $email,
            "role": $role
        }')
    
    # Make the API request to add the member
    response=$(curl -s -X POST \
        -H "Authorization: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_URL")
    
    # Check if the request was successful
    if echo "$response" | jq -e '.error' > /dev/null; then
        error_message=$(echo "$response" | jq -r '.error')
        echo "Failed to add $email: $error_message" >> "$ADD_BACK_LOG"
        failed_adds=$((failed_adds + 1))
    else
        echo "Successfully added $email with role $role" >> "$ADD_BACK_LOG"
        successful_adds=$((successful_adds + 1))
    fi
    
    total_members=$((total_members + 1))
    
    # Add a small delay to avoid rate limiting
    sleep 1
done

# Print summary
echo "----------------------------------------" >> "$ADD_BACK_LOG"
echo "Add Back Operation Summary" >> "$ADD_BACK_LOG"
echo "Total members processed: $total_members" >> "$ADD_BACK_LOG"
echo "Successfully added: $successful_adds" >> "$ADD_BACK_LOG"
echo "Failed to add: $failed_adds" >> "$ADD_BACK_LOG"
echo "Skipped members: $skipped_members" >> "$ADD_BACK_LOG"

# Display the results
echo "Add back operation completed. See $ADD_BACK_LOG for details."
echo "Summary:"
echo "Total members processed: $total_members"
echo "Successfully added: $successful_adds"
echo "Failed to add: $failed_adds"
echo "Skipped members: $skipped_members" 