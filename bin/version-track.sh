#!/bin/zsh

# NACC Identifiers Lambda Version Mapping Script
# Simple script to track semantic version to AWS Lambda version mapping

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: ./bin/version-track.sh [OPTIONS]

Track semantic version to AWS Lambda version mapping

OPTIONS:
    -v, --version VERSION    Semantic version (e.g., v1.1.0)
    -h, --help              Show this help message

EXAMPLES:
    # Track version mapping after manual deployment
    ./bin/version-track.sh --version v1.1.0

MANUAL WORKFLOW:
    1. Make your changes: git commit -m "Your changes"
    2. Create git tag: git tag -a v1.1.0 -m "Release v1.1.0: Description"
    3. Build packages: cd lambda/search_naccid && pants package src/python::
    4. Deploy: terraform apply
    5. Track mapping: ./bin/version-track.sh --version v1.1.0
    6. Update CHANGELOG.md manually
    7. Commit docs: git add . && git commit -m "Update version mapping"

EOF
}

# Default values
SEMANTIC_VERSION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            SEMANTIC_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$SEMANTIC_VERSION" ]]; then
    print_error "Semantic version is required. Use -v or --version"
    show_usage
    exit 1
fi

# Validate semantic version format
if [[ ! "$SEMANTIC_VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid semantic version format. Use vX.Y.Z (e.g., v1.1.0)"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
    exit 1
fi

# Check if tag exists
if ! git tag -l | grep -q "^${SEMANTIC_VERSION}$"; then
    print_error "Git tag ${SEMANTIC_VERSION} does not exist"
    print_status "Create the tag first: git tag -a ${SEMANTIC_VERSION} -m 'Release ${SEMANTIC_VERSION}: Description'"
    exit 1
fi

# Get tag information
TAG_COMMIT=$(git rev-list -n 1 "$SEMANTIC_VERSION")
TAG_DATE=$(git log -1 --format="%ai" "$SEMANTIC_VERSION" | cut -d' ' -f1)
TAG_MESSAGE=$(git tag -l --format='%(contents:subject)' "$SEMANTIC_VERSION" 2>/dev/null || echo "No message")

print_status "Tracking version: $SEMANTIC_VERSION"
print_status "Git commit: ${TAG_COMMIT:0:7}"
print_status "Date: $TAG_DATE"

# Function to get lambda function name from variables.tf
get_lambda_function_name() {
    local lambda_dir="$1"
    grep -A 5 'variable "lambda_function_name"' "${lambda_dir}/variables.tf" | grep 'default' | grep -o '"[^"]*"' | tr -d '"' || echo ""
}

# Function to detect if running inside devcontainer
is_in_devcontainer() {
    [[ -n "${REMOTE_CONTAINERS:-}" ]] || [[ -n "${CODESPACES:-}" ]] || [[ -f "/.dockerenv" ]]
}

# Function to execute command (with or without devcontainer wrapper)
exec_cmd() {
    if is_in_devcontainer; then
        # Running inside devcontainer - execute directly
        "$@"
    else
        # Running outside devcontainer - use wrapper
        ./bin/exec-in-devcontainer.sh "$@"
    fi
}

# Function to get actual production version from AWS
get_aws_prod_version() {
    local function_name="$1"
    if [[ -z "$function_name" ]]; then
        echo "unknown"
        return
    fi
    
    # Get the version that the production alias points to
    local prod_version
    prod_version=$(exec_cmd aws lambda get-alias --function-name "$function_name" --name "prod" --query 'FunctionVersion' --output text 2>/dev/null || echo "unknown")
    echo "$prod_version"
}

# Function to get current AWS Lambda versions from AWS (actual production versions)
get_current_aws_versions() {
    local versions_map=""
    
    print_status "Querying AWS for actual production versions..."
    
    for lambda_dir in lambda/*/; do
        if [[ -f "${lambda_dir}variables.tf" ]]; then
            local lambda_name=$(basename "$lambda_dir")
            local function_name=$(get_lambda_function_name "$lambda_dir")
            local aws_version=$(get_aws_prod_version "$function_name")
            versions_map="${versions_map}| ${lambda_name} | AWS v${aws_version} |\n"
        fi
    done
    
    echo -e "$versions_map"
}

# Function to update VERSION_MAPPING.md
update_version_mapping() {
    print_status "Recording version mapping for ${SEMANTIC_VERSION}..."
    
    # Get current AWS Lambda versions from Terraform
    local current_versions=$(get_current_aws_versions)
    
    # Add new version entry to VERSION_MAPPING.md
    cat >> VERSION_MAPPING.md << EOF

## ${SEMANTIC_VERSION} - ${TAG_DATE}
- **Git Commit**: ${TAG_COMMIT:0:7}
- **Date**: $TAG_DATE
- **Tag Message**: $TAG_MESSAGE

### Lambda Versions at ${SEMANTIC_VERSION}
| Lambda Function | AWS Version |
|----------------|-------------|
EOF
    echo -e "$current_versions" >> VERSION_MAPPING.md
    
    print_success "Added ${SEMANTIC_VERSION} mapping to VERSION_MAPPING.md"
}

# Ensure devcontainer is ready (if running outside)
if ! is_in_devcontainer; then
    print_status "Ensuring devcontainer is ready..."
    ./bin/start-devcontainer.sh > /dev/null
else
    print_status "Running inside devcontainer"
fi

# Main execution
print_status "Tracking version mapping for: $SEMANTIC_VERSION"

# Update version mapping
update_version_mapping

print_success "Version mapping recorded!"
print_status "Manual next steps:"
echo "  1. Update CHANGELOG.md with release notes"
echo "  2. Commit the documentation: git add VERSION_MAPPING.md && git commit -m 'Add version mapping for ${SEMANTIC_VERSION}'"