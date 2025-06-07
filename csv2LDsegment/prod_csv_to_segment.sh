#!/bin/bash
# Description: Script to create approval requests for LaunchDarkly segment updates in production

# Exit on any error
set -e

# Default values
ACTION=""
environment="production"
API_KEY=""
PROJECT_KEY=""
SEGMENT_KEY=""
FILE_NAME=""
MEMBER_ID=""

# Help function
print_usage() {
  echo "Usage: $0 [-a action] [-e environment] [-p project] [-s segment] [-k api_key] [-f filename] [-m member_id] [-h]"
  echo "  -a : Action: 'add' or 'remove' (required)"
  echo "  -e : Environment (required)"
  echo "  -p : Project key (required)"
  echo "  -s : Segment key (required)"
  echo "  -k : API key (required)"
  echo "  -f : File Name (required)"
  echo "  -m : Member ID to notify (required)"
  echo "  -h : Display this help message"
}

# Parse command line arguments
while getopts "a:e:p:s:k:f:m:h:" flag; do
  case "${flag}" in
    a) ACTION=${OPTARG};;
    e) environment=${OPTARG};;
    p) PROJECT_KEY=${OPTARG};;
    s) SEGMENT_KEY=${OPTARG};;
    k) API_KEY=${OPTARG};;
    f) FILE_NAME=${OPTARG};;
    m) MEMBER_ID=${OPTARG};;
    h) print_usage
       exit 0;;
    *) print_usage
       exit 1;;
  esac
done

# Add debug output to check variables
echo "Debug - Script parameters:"
echo "Action: $ACTION"
echo "Environment: $environment"
echo "Project Key: $PROJECT_KEY"
echo "Segment Key: $SEGMENT_KEY"
echo "API Key: $API_KEY"
echo "File Name: $FILE_NAME"
echo "Member ID: $MEMBER_ID"

# Validate required arguments
if [ -z "${PROJECT_KEY}" ] || [ -z "${ACTION}" ] || [ -z "${SEGMENT_KEY}" ] || [ -z "${FILE_NAME}" ] || [ -z "${MEMBER_ID}" ]; then
  echo "Error: missing value is are required"
  print_usage
  exit 1
fi

# Validate action
if [ "${ACTION}" != "add" ] && [ "${ACTION}" != "remove" ]; then
  echo "Error: Action must be either 'add' or 'remove'"
  print_usage
  exit 1
fi

echo "Fetching segment information..."
segment_info=$(curl -s -X GET \
    "https://app.launchdarkly.com/api/v2/segments/$PROJECT_KEY/$environment/$SEGMENT_KEY" \
    -H "Authorization: $API_KEY" \
    -H "Content-Type: application/json")

# Check for authorization errors
if echo "$segment_info" | jq -e '.code == "unauthorized"' > /dev/null; then
    echo "Error: Authorization failed. Please check your API key."
    echo "API Response: $(echo "$segment_info" | jq -r '.message')"
    exit 1
fi

# Check if the curl command was successful
if [ $? -ne 0 ] || [ -z "$segment_info" ]; then
    echo "Error: Failed to fetch segment information"
    exit 1
fi

# Print rule and clause information
echo "Available Rules and Clauses:"
echo "$segment_info" | jq -r '.rules[] | "Rule ID: \(._id)\nRule Description: \(.description)\nClauses:" + (.clauses[] | "\n  Clause ID: \(._id)\n  Attribute: \(.attribute)\n  Operator: \(.op)\n  Values: \(.values | join(", "))\n")'

# Extract rule and clause IDs
RULE_ID=$(echo "$segment_info" | jq -r '.rules[0]._id')
CLAUSE_ID=$(echo "$segment_info" | jq -r '.rules[0].clauses[0]._id')

echo "Found Rule ID: $RULE_ID"
echo "Found Clause ID: $CLAUSE_ID"

# Initialize empty array
IDS=()

# Read IDs from the CSV file (skipping header)
echo "Reading IDs from $FILE_NAME..."
IDS=($(tail -n +2 "$FILE_NAME"))

# Debug: Show what we read
echo "Read ${#IDS[@]} IDs from CSV:"

# now we need to read it into an array
array_string=""
first=true

# Loop through each ID and build the JSON array
for id in "${IDS[@]}"; do
    if [ "$first" = true ]; then
        array_string="\"$id\""
        first=false
    else
        array_string="$array_string,\"$id\""
    fi
done

# Create the resource ID for the segment
resource_id="proj/${PROJECT_KEY}:env/${environment}:segment/${SEGMENT_KEY}"

# Create the approval request payload
approval_payload=$(cat <<EOF
{
    "resourceId": "$resource_id",
    "description": "Requesting to ${ACTION} ${#IDS[@]} IDs to segment ${SEGMENT_KEY} in ${environment} environment",
    "instructions": [
        {
            "kind": "${ACTION}ValuesToClause",
            "ruleId": "$RULE_ID",
            "clauseId": "$CLAUSE_ID",
            "values": [$array_string]
        }
    ],
    "notifyMemberIds": ["$MEMBER_ID"]
}
EOF
)

# Debug: Show the payload being sent
echo "Debug - Approval Request Payload:"
echo "$approval_payload" | jq '.'

# Make the approval request API call
echo "Creating approval request..."
approval_response=$(curl -s -X POST \
    "https://app.launchdarkly.com/api/v2/approval-requests" \
    -H "Authorization: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$approval_payload")

# Check if the approval request was successful
if echo "$approval_response" | jq -e '.error' > /dev/null; then
    error_message=$(echo "$approval_response" | jq -r '.error')
    echo "Error creating approval request: $error_message"
    exit 1
fi

echo approval_response
echo "$approval_response"

# Extract and display the approval request ID
approval_id=$(echo "$approval_response" | jq -r '._id')
echo "----------------------------------------"
echo "Approval Request ID: $approval_id"
echo "Please wait for approval in the LaunchDarkly UI before proceeding with the segment update."
echo "----------------------------------------" 