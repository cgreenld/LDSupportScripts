#!/bin/bash
# Description: Script to update LaunchDarkly segment via API

# Exit on any error
set -e

# Default values
ACTION=""
environment="Production"
API_KEY=""
PROJECT_KEY=""
SEGMENT_KEY=""
FILE_NAME=""
PROD_MODE="n"

# Function to handle approval requests in production mode
approval_request() {
    local action=$1
    local count=$2
    local segment=$3
    
    if [ "${PROD_MODE}" = "y" ]; then
        echo "----------------------------------------"
        echo "Production Mode: Confirmation Required"
        echo "Action: $action"
        echo "Number of IDs: $count"
        echo "Segment: $segment"
        echo "----------------------------------------"
        read -p "Do you want to proceed with this change? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "Operation cancelled by user"
            exit 0
        fi
        echo "Approval granted, proceeding with operation..."
    fi
}

# Help function
print_usage() {
  echo "Usage: $0 [-a action] [-e environment] [-p project] [-s segment] [-k api_key] [-f filename] [-prod y/n] [-h]"
  echo "  -a : Action: 'add' or 'remove' (required)"
  echo "  -e : Environment (required)"
  echo "  -p : Project key (required)"
  echo "  -s : Segment key (required)"
  echo "  -k : API key (required)"
  echo "  -f : File Name (required)"
  echo "  -prod : Production mode (y/n) - if 'y', will require confirmation for each batch"
  echo "  -h : Display this help message"
}

# Parse command line arguments
while getopts "a:e:p:s:k:f:prod:h:" flag; do
  case "${flag}" in
    a) ACTION=${OPTARG};;
    e) environment=${OPTARG};;
    p) PROJECT_KEY=${OPTARG};;
    s) SEGMENT_KEY=${OPTARG};;
    k) API_KEY=${OPTARG};;
    f) FILE_NAME=${OPTARG};;
    prod) PROD_MODE=${OPTARG};;
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
echo "Production Mode: $PROD_MODE"

# Validate required arguments
if [ -z "${PROJECT_KEY}" ] || [ -z "${ACTION}" ] || [ -z "${SEGMENT_KEY}" ] || [ -z "${FILE_NAME}" ]; then
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

# Validate production mode
if [ "${PROD_MODE}" != "y" ] && [ "${PROD_MODE}" != "n" ]; then
  echo "Error: Production mode must be either 'y' or 'n'"
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


# Create JSON payload based on action
if [ "${ACTION}" == "add" ]; then
    echo "Adding IDs to segment rule clause..."
    # Create the JSON array from our IDs
    json_values="[$array_string]"
    PAYLOAD=$(cat <<EOF
{
    "comment": "Adding values to clause via script",
    "instructions": [
        {
            "kind": "addValuesToClause",
            "ruleId": "$RULE_ID",
            "clauseId": "$CLAUSE_ID",
            "values": [$array_string]
        }
    ]
}
EOF
)
else
    echo "Removing IDs from segment rule clause..."
    PAYLOAD=$(cat <<EOF
{
    "comment": "removing values to clause via script",
    "instructions": [
        {
            "kind": "removeValuesFromClause",
            "ruleId": "$RULE_ID",
            "clauseId": "$CLAUSE_ID",
            "values": [$array_string]
        }
    ]
}
EOF
)
fi

# Debug: Show the payload being sent
echo "Debug - Payload being sent:"
echo "$PAYLOAD" | jq '.'

# Make API call
echo "Making API call to update segment..."
response=$(curl -s -w "\n%{http_code}" -X PATCH \
  "https://app.launchdarkly.com/api/v2/segments/$PROJECT_KEY/$environment/$SEGMENT_KEY" \
  -H "Authorization: $API_KEY" \
  -H "Content-Type: application/json" \
  -H "Content-Type: application/json; domain-model=launchdarkly.semanticpatch" \
  -d "$PAYLOAD")
echo $response

# Get status code from response
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed \$d)

# Check response
if [ "$http_code" -eq 200 ]; then
  echo "Successfully updated segment"
  echo "Response: $body"
else
  echo "Error updating segment. Status code: $http_code"
  echo "Error response: $body"
  exit 1
fi

echo "Script completed successfully" 