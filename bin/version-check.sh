#!/bin/zsh

# NACC Identifiers Lambda Version Check Script
# Shows current version status and AWS Lambda version information

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

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get current git information
get_git_info() {
    echo "=== Git Information ==="
    echo "Current branch: $(git branch --show-current)"
    echo "Latest commit: $(git rev-parse --short HEAD) - $(git log -1 --pretty=format:'%s')"
    echo "Latest tag: $(git describe --tags --abbrev=0 2>/dev/null || echo 'No tags found')"
    echo
}

# Function to show Terraform version information
show_terraform_versions() {
    echo "=== Terraform Production Versions ==="
    echo "Lambda Function                | Production Version"
    echo "-------------------------------|-------------------"
    
    for lambda_dir in lambda/*/; do
        if [[ -f "${lambda_dir}variables.tf" ]]; then
            lambda_name=$(basename "$lambda_dir")
            # Extract default value from prod_function_version variable
            version=$(grep -A 3 'variable "prod_function_version"' "${lambda_dir}variables.tf" | grep 'default' | grep -o '"[0-9]*"' | tr -d '"' || echo "N/A")
            printf "%-30s | %s\n" "$lambda_name" "$version"
        fi
    done
    echo
}

# Function to show version distribution
show_version_distribution() {
    echo "=== Production Version Distribution ==="
    
    # Create temporary files to collect version data
    temp_versions=$(mktemp)
    temp_summary=$(mktemp)
    
    # Collect all versions and their lambdas
    for lambda_dir in lambda/*/; do
        if [[ -f "${lambda_dir}variables.tf" ]]; then
            lambda_name=$(basename "$lambda_dir")
            version=$(grep -A 3 'variable "prod_function_version"' "${lambda_dir}variables.tf" | grep 'default' | grep -o '"[0-9]*"' | tr -d '"' || echo "unknown")
            
            if [[ "$version" != "unknown" ]]; then
                echo "$version $lambda_name" >> "$temp_versions"
            fi
        fi
    done
    
    if [[ ! -s "$temp_versions" ]]; then
        print_warning "No production versions found"
        rm -f "$temp_versions" "$temp_summary"
        return
    fi
    
    # Sort and group by version
    sort -n "$temp_versions" | awk '{
        if ($1 != prev_version) {
            if (prev_version != "") {
                print "  Version " prev_version ": " count " Lambda(s) -" lambdas
            }
            prev_version = $1
            count = 1
            lambdas = " " $2
        } else {
            count++
            lambdas = lambdas " " $2
        }
    } END {
        if (prev_version != "") {
            print "  Version " prev_version ": " count " Lambda(s) -" lambdas
        }
    }' > "$temp_summary"
    
    echo "Version distribution (each Lambda can have independent production versions):"
    cat "$temp_summary"
    
    print_status "Note: Independent versioning allows selective rollbacks and staged deployments"
    
    # Clean up
    rm -f "$temp_versions" "$temp_summary"
    echo
}

# Function to show recent releases
show_recent_releases() {
    echo "=== Recent Releases ==="
    
    if git tag -l | grep -q "^v"; then
        echo "Recent semantic version tags:"
        git tag -l "v*" | sort -V | tail -5 | while read tag; do
            commit_date=$(git log -1 --format="%ai" "$tag" 2>/dev/null || echo "Unknown date")
            commit_msg=$(git tag -l --format='%(contents:subject)' "$tag" 2>/dev/null || echo "No message")
            echo "  $tag - $commit_date - $commit_msg"
        done
    else
        print_warning "No semantic version tags found"
        echo "  Use: git tag -a v1.0.0 -m 'Release v1.0.0: Initial release'"
    fi
    echo
}

# Function to suggest next version
suggest_next_version() {
    echo "=== Version Suggestions ==="
    
    # Get the latest semantic version tag
    latest_tag=$(git tag -l "v*" | sort -V | tail -1 2>/dev/null || echo "")
    
    if [[ -n "$latest_tag" ]]; then
        # Parse semantic version
        if [[ "$latest_tag" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
            major=$(echo "$latest_tag" | sed 's/v\([0-9]*\)\.\([0-9]*\)\.\([0-9]*\)/\1/')
            minor=$(echo "$latest_tag" | sed 's/v\([0-9]*\)\.\([0-9]*\)\.\([0-9]*\)/\2/')
            patch=$(echo "$latest_tag" | sed 's/v\([0-9]*\)\.\([0-9]*\)\.\([0-9]*\)/\3/')
            
            echo "Current version: $latest_tag"
            echo "Suggested next versions:"
            echo "  Patch (bug fixes): v${major}.${minor}.$((patch + 1))"
            echo "  Minor (new features): v${major}.$((minor + 1)).0"
            echo "  Major (breaking changes): v$((major + 1)).0.0"
        else
            print_warning "Latest tag '$latest_tag' doesn't follow semantic versioning"
            echo "Suggested next version: v1.0.0"
        fi
    else
        echo "No previous versions found"
        echo "Suggested initial version: v1.0.0"
    fi
    echo
}

# Function to check deployment readiness
check_deployment_readiness() {
    echo "=== Deployment Readiness ==="
    
    # Check for uncommitted changes
    if git diff-index --quiet HEAD --; then
        print_success "No uncommitted changes"
    else
        print_warning "You have uncommitted changes"
        echo "  Commit changes before creating a release"
    fi
    
    # Check if on main branch
    current_branch=$(git branch --show-current)
    if [[ "$current_branch" == "main" ]]; then
        print_success "On main branch"
    else
        print_warning "Not on main branch (currently on: $current_branch)"
        echo "  Consider switching to main for releases"
    fi
    
    # Check devcontainer status
    if ./bin/start-devcontainer.sh > /dev/null 2>&1; then
        print_success "Devcontainer is ready"
    else
        print_warning "Devcontainer may not be ready"
        echo "  Run: ./bin/start-devcontainer.sh"
    fi
    
    echo
}

# Main execution
echo "NACC Identifiers Lambda Version Status"
echo "======================================"
echo

get_git_info
show_terraform_versions
show_version_distribution
show_recent_releases
suggest_next_version
check_deployment_readiness

echo "=== Quick Commands ==="
echo "Track version mapping: ./bin/version-track.sh --version v1.1.0"
echo "Check specific lambda: cd lambda/search_naccid && terraform show"
echo "View all tags:         git tag -l"
echo "View changelog:        cat CHANGELOG.md"