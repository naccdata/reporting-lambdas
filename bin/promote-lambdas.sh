#!/bin/zsh

# NACC Identifiers Lambda Production Promotion Script
# Promotes Lambda functions to production by updating their production version aliases

# Removed set -e to avoid issues with read commands and loops

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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: ./bin/promote-lambdas.sh [OPTIONS]"
    echo ""
    echo "Promote Lambda functions to production by updating production version aliases"
    echo ""
    echo "Options:"
    echo "  --all              Promote all Lambda functions without prompting"
    echo "  --version VERSION  Promote all functions to specific version (requires --all)"
    echo "  --dry-run          Show what would be done without executing"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./bin/promote-lambdas.sh                           # Interactive mode - ask for each Lambda"
    echo "  ./bin/promote-lambdas.sh --all                     # Promote all to their latest versions"
    echo "  ./bin/promote-lambdas.sh --all --version 9         # Promote all to version 9"
    echo "  ./bin/promote-lambdas.sh --dry-run                 # Preview changes without applying"
}

# Parse command line arguments
PROMOTE_ALL=false
TARGET_VERSION=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            PROMOTE_ALL=true
            shift
            ;;
        --version)
            TARGET_VERSION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
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

# Validate arguments
if [[ -n "$TARGET_VERSION" && "$PROMOTE_ALL" != true ]]; then
    print_error "--version requires --all flag"
    exit 1
fi

# Function to get current production version for a lambda
get_current_prod_version() {
    local lambda_dir="$1"
    grep -A 3 'variable "prod_function_version"' "${lambda_dir}/variables.tf" | grep 'default' | grep -o '"[0-9]*"' | tr -d '"' || echo "unknown"
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

# Function to get latest AWS version for a lambda
get_latest_aws_version() {
    local function_name="$1"
    local latest_version
    
    # Get the latest version from AWS (highest version number)
    latest_version=$(exec_cmd aws lambda list-versions-by-function \
        --function-name "$function_name" \
        --query 'Versions[?Version!=`$LATEST`].Version' \
        --output text | tr '\t' '\n' | sort -n | tail -1 2>/dev/null || echo "")
    
    if [[ -z "$latest_version" ]]; then
        echo "unknown"
    else
        echo "$latest_version"
    fi
}

# Function to promote a single lambda
promote_lambda() {
    local lambda_name="$1"
    local target_version="$2"
    local lambda_dir="lambda/$lambda_name"
    
    if [[ ! -d "$lambda_dir" ]]; then
        print_error "Lambda directory not found: $lambda_dir"
        return 1
    fi
    
    local current_version
    current_version=$(get_current_prod_version "$lambda_dir")
    
    print_status "Promoting $lambda_name from version $current_version to $target_version"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "  [DRY RUN] Would run: cd $lambda_dir && terraform apply -var=\"prod_function_version=$target_version\" -auto-approve"
        return 0
    fi
    
    # Run terraform apply and capture output
    local terraform_output
    local terraform_exit_code
    terraform_output=$(exec_cmd bash -c "cd $lambda_dir && terraform apply -var=\"prod_function_version=$target_version\" -auto-approve" 2>&1)
    terraform_exit_code=$?
    
    # Show terraform output
    echo "$terraform_output"
    
    if [[ $terraform_exit_code -ne 0 ]]; then
        print_error "Failed to promote $lambda_name (terraform failed)"
        return 1
    fi
    
    # Check if terraform actually made changes
    if echo "$terraform_output" | grep -q "No changes. Your infrastructure matches the configuration."; then
        print_warning "$lambda_name was already at version $target_version (no changes made)"
        return 2  # Special return code for "no changes needed"
    elif echo "$terraform_output" | grep -q "Apply complete!"; then
        print_success "Successfully promoted $lambda_name to version $target_version"
        return 0
    else
        print_warning "$lambda_name promotion completed but status unclear"
        return 0
    fi
}

# Function to get lambda function name from variables.tf
get_lambda_function_name() {
    local lambda_dir="$1"
    # Look for lambda_function_name variable default value (may be several lines after variable declaration)
    grep -A 5 'variable "lambda_function_name"' "${lambda_dir}/variables.tf" | grep 'default' | grep -o '"[^"]*"' | tr -d '"' || echo ""
}

# Main execution
echo "NACC Identifiers Lambda Production Promotion"
echo "============================================"
echo

# Ensure devcontainer is ready (if running outside)
if ! is_in_devcontainer; then
    print_status "Ensuring devcontainer is ready..."
    ./bin/start-devcontainer.sh > /dev/null
else
    print_status "Running inside devcontainer"
fi

# Get list of all lambda directories
lambda_dirs=($(find lambda -maxdepth 1 -type d -name "*" | grep -v "^lambda$" | sort))

if [[ ${#lambda_dirs[@]} -eq 0 ]]; then
    print_error "No Lambda directories found"
    exit 1
fi

print_status "Found ${#lambda_dirs[@]} Lambda functions"

# Collect promotion targets using temporary files (more compatible than associative arrays)
promotion_file=$(mktemp)
promoted_count=0
skipped_count=0
failed_count=0
no_change_count=0

for lambda_dir in "${lambda_dirs[@]}"; do
    lambda_name=$(basename "$lambda_dir")
    current_version=$(get_current_prod_version "$lambda_dir")
    
    if [[ "$current_version" == "unknown" ]]; then
        print_warning "Skipping $lambda_name - cannot determine current version"
        ((skipped_count++))
        continue
    fi
    
    # Determine target version
    if [[ -n "$TARGET_VERSION" ]]; then
        target_version="$TARGET_VERSION"
    elif [[ "$PROMOTE_ALL" == true ]]; then
        # Get latest AWS version
        function_name=$(get_lambda_function_name "$lambda_dir")
        if [[ -n "$function_name" ]]; then
            target_version=$(get_latest_aws_version "$function_name")
            if [[ "$target_version" == "unknown" ]]; then
                print_warning "Skipping $lambda_name - cannot determine latest AWS version"
                ((skipped_count++))
                continue
            fi
        else
            print_warning "Skipping $lambda_name - cannot determine function name"
            ((skipped_count++))
            continue
        fi
    else
        # Interactive mode
        echo ""
        print_status "Lambda: $lambda_name (current production version: $current_version)"
        
        # Get latest AWS version for suggestion
        function_name=$(get_lambda_function_name "$lambda_dir")
        if [[ -n "$function_name" ]]; then
            latest_version=$(get_latest_aws_version "$function_name")
            if [[ "$latest_version" != "unknown" && "$latest_version" != "$current_version" ]]; then
                echo "  Latest AWS version: $latest_version"
            fi
        fi
        
        echo -n "  Promote to version (or 'skip'): "
        read -r user_input
        
        if [[ "$user_input" == "skip" || -z "$user_input" ]]; then
            print_status "Skipping $lambda_name"
            ((skipped_count++))
            continue
        fi
        
        if [[ ! "$user_input" =~ ^[0-9]+$ ]]; then
            print_warning "Invalid version '$user_input' for $lambda_name - skipping"
            ((skipped_count++))
            continue
        fi
        
        target_version="$user_input"
    fi
    
    # Check if version is different from current
    if [[ "$target_version" == "$current_version" ]]; then
        print_status "$lambda_name already at version $target_version - skipping"
        ((skipped_count++))
        continue
    fi
    
    # Store promotion target
    echo "$lambda_name:$target_version" >> "$promotion_file"
done

# Show summary of planned promotions
if [[ -s "$promotion_file" ]]; then
    echo ""
    print_status "Planned promotions:"
    while IFS=':' read -r lambda_name target_version; do
        current_version=$(get_current_prod_version "lambda/$lambda_name")
        echo "  $lambda_name: $current_version → $target_version"
    done < "$promotion_file"
    
    if [[ "$DRY_RUN" != true && "$PROMOTE_ALL" != true ]]; then
        echo ""
        echo -n "Proceed with promotions? (y/N): "
        read -r confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            print_status "Promotion cancelled"
            rm -f "$promotion_file"
            exit 0
        fi
    fi
    
    echo ""
    print_status "Starting promotions..."
    
    # Execute promotions
    while IFS=':' read -r lambda_name target_version; do
        promote_lambda "$lambda_name" "$target_version"
        promote_result=$?
        case $promote_result in
            0)
                ((promoted_count++))
                ;;
            2)
                ((no_change_count++))
                ;;
            *)
                ((failed_count++))
                ;;
        esac
    done < "$promotion_file"
else
    print_status "No promotions needed"
fi

# Clean up
rm -f "$promotion_file"

# Final summary
echo ""
print_status "Promotion Summary:"
echo "  Promoted: $promoted_count"
echo "  Already current: $no_change_count"
echo "  Skipped: $skipped_count"
echo "  Failed: $failed_count"

if [[ $failed_count -gt 0 ]]; then
    print_warning "Some promotions failed. Check the output above for details."
    exit 1
elif [[ $promoted_count -gt 0 ]]; then
    print_success "Promotions completed successfully!"
    
    if [[ $no_change_count -gt 0 ]]; then
        print_status "$no_change_count Lambda(s) were already at the target version"
    fi
    
    if [[ "$DRY_RUN" != true ]]; then
        echo ""
        print_status "Next steps:"
        echo "  1. Verify deployments: ./bin/version-check.sh"
        echo "  2. Test production endpoints"
        echo "  3. Update version mapping: ./bin/version-track.sh --version v1.2.0"
    fi
elif [[ $no_change_count -gt 0 ]]; then
    print_status "All Lambda functions were already at their target versions"
else
    print_status "No changes made"
fi