#!/bin/bash
###############################################################################
# Script: load-test.sh
# Description: Load testing script for Sentilyze API
# Usage: ./load-test.sh [endpoint] [options]
###############################################################################

set -uo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-dev}"
API_BASE_URL=""
DURATION=60
CONCURRENT_USERS=10
RAMP_UP=10
OUTPUT_FORMAT="console"  # console, json, html

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

###############################################################################
# Show Help
###############################################################################
show_help() {
    cat << EOF
Sentilyze Load Testing Tool

Usage: $0 [endpoint] [options]

Endpoints:
  analyze              POST /api/v1/analyze (sentiment analysis)
  batch                POST /api/v1/analyze/batch (batch analysis)
  health               GET /health (health check)
  all                  Run all tests sequentially

Options:
  --url, -u <url>             Base API URL (auto-detected if not provided)
  --duration, -d <seconds>    Test duration (default: 60)
  --users, -U <count>         Concurrent users (default: 10)
  --ramp-up, -r <seconds>     Ramp-up time (default: 10)
  --format, -f <format>       Output format: console, json, html (default: console)
  --auth-token, -t <token>    Authentication token
  --help, -h                  Show this help message

Examples:
  $0 health                    Test health endpoint
  $0 analyze --users 50        Test analyze with 50 concurrent users
  $0 all --duration 300        Run all tests for 5 minutes
  $0 analyze --format html     Generate HTML report

EOF
}

###############################################################################
# Detect API URL
###############################################################################
detect_api_url() {
    if [[ -n "$API_BASE_URL" ]]; then
        return
    fi
    
    if [[ "$ENVIRONMENT" == "local" ]]; then
        API_BASE_URL="http://localhost:8080"
    else
        # Try to get from Cloud Run
        local url
        url=$(gcloud run services describe "sentilyze-api-${ENVIRONMENT}" \
            --platform managed \
            --region us-central1 \
            --format='value(status.url)' 2>/dev/null)
        
        if [[ -n "$url" ]]; then
            API_BASE_URL="$url"
        else
            log_error "Could not auto-detect API URL. Please provide with --url"
            exit 1
        fi
    fi
}

###############################################################################
# Check Dependencies
###############################################################################
check_dependencies() {
    local has_curl=false
    local has_ab=false
    local has_wrk=false
    local has_k6=false
    
    command -v curl &> /dev/null && has_curl=true
    command -v ab &> /dev/null && has_ab=true
    command -v wrk &> /dev/null && has_wrk=true
    command -v k6 &> /dev/null && has_k6=true
    
    if [[ "$has_k6" == "true" ]]; then
        LOAD_TEST_TOOL="k6"
    elif [[ "$has_wrk" == "true" ]]; then
        LOAD_TEST_TOOL="wrk"
    elif [[ "$has_ab" == "true" ]]; then
        LOAD_TEST_TOOL="ab"
    elif [[ "$has_curl" == "true" ]]; then
        LOAD_TEST_TOOL="curl"
    else
        log_error "No load testing tool found. Install one of: k6, wrk, apache2-utils (ab), or curl"
        exit 1
    fi
    
    log_info "Using load testing tool: $LOAD_TEST_TOOL"
}

###############################################################################
# Test Health Endpoint
###############################################################################
test_health() {
    local endpoint="${API_BASE_URL}/health"
    
    log_info "Testing health endpoint: $endpoint"
    log_info "Duration: ${DURATION}s, Users: $CONCURRENT_USERS"
    
    case "$LOAD_TEST_TOOL" in
        k6)
            run_k6_test "$endpoint" "GET" ""
            ;;
        wrk)
            run_wrk_test "$endpoint"
            ;;
        ab)
            run_ab_test "$endpoint"
            ;;
        curl)
            run_curl_test "$endpoint"
            ;;
    esac
}

###############################################################################
# Test Analyze Endpoint
###############################################################################
test_analyze() {
    local endpoint="${API_BASE_URL}/api/v1/analyze"
    local payload='{"text": "This is a test sentiment analysis request for load testing purposes. The service should handle this efficiently.", "language": "en"}'
    
    log_info "Testing analyze endpoint: $endpoint"
    log_info "Duration: ${DURATION}s, Users: $CONCURRENT_USERS"
    
    case "$LOAD_TEST_TOOL" in
        k6)
            run_k6_test "$endpoint" "POST" "$payload"
            ;;
        wrk)
            log_warning "wrk doesn't support POST body easily, using curl instead"
            run_curl_test "$endpoint" "$payload"
            ;;
        ab)
            run_ab_post_test "$endpoint" "$payload"
            ;;
        curl)
            run_curl_test "$endpoint" "$payload"
            ;;
    esac
}

###############################################################################
# Test Batch Endpoint
###############################################################################
test_batch() {
    local endpoint="${API_BASE_URL}/api/v1/analyze/batch"
    local payload='{"texts": ["Test 1", "Test 2", "Test 3"], "language": "en"}'
    
    log_info "Testing batch endpoint: $endpoint"
    log_info "Duration: ${DURATION}s, Users: $CONCURRENT_USERS"
    
    # Batch tests are typically slower, reduce concurrent users
    local adjusted_users=$(( CONCURRENT_USERS / 2 ))
    if [[ $adjusted_users -lt 1 ]]; then
        adjusted_users=1
    fi
    
    case "$LOAD_TEST_TOOL" in
        k6)
            CONCURRENT_USERS=$adjusted_users run_k6_test "$endpoint" "POST" "$payload"
            ;;
        *)
            log_warning "Batch testing with $LOAD_TEST_TOOL may be limited"
            run_curl_test "$endpoint" "$payload"
            ;;
    esac
}

###############################################################################
# k6 Test Runner
###############################################################################
run_k6_test() {
    local url="$1"
    local method="$2"
    local payload="$3"
    local temp_script="/tmp/sentilyze-load-test-$(date +%s).js"
    
    # Create k6 script
    cat > "$temp_script" << EOF
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '${RAMP_UP}s', target: ${CONCURRENT_USERS} },
    { duration: '${DURATION}s', target: ${CONCURRENT_USERS} },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const url = '${url}';
  const headers = {
    'Content-Type': 'application/json',
  };
  
  let res;
  if ('${method}' === 'POST' && '${payload}' !== '') {
    res = http.post(url, '${payload}', { headers });
  } else {
    res = http.get(url);
  }
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
EOF
    
    k6 run "$temp_script" 2>&1 | tee "${PROJECT_ROOT}/logs/load-test-$(date +%Y%m%d-%H%M%S).log"
    
    rm -f "$temp_script"
}

###############################################################################
# wrk Test Runner
###############################################################################
run_wrk_test() {
    local url="$1"
    
    wrk -t$CONCURRENT_USERS -c$((CONCURRENT_USERS * 10)) -d${DURATION}s --latency "$url" 2>&1 | \
        tee "${PROJECT_ROOT}/logs/load-test-$(date +%Y%m%d-%H%M%S).log"
}

###############################################################################
# ab (Apache Bench) Test Runner
###############################################################################
run_ab_test() {
    local url="$1"
    
    ab -n $((CONCURRENT_USERS * DURATION)) -c $CONCURRENT_USERS -g "${PROJECT_ROOT}/logs/ab-data-$(date +%Y%m%d-%H%M%S).tsv" "$url" 2>&1 | \
        tee "${PROJECT_ROOT}/logs/load-test-$(date +%Y%m%d-%H%M%S).log"
}

run_ab_post_test() {
    local url="$1"
    local payload="$2"
    local temp_file="/tmp/sentilyze-payload-$(date +%s).json"
    
    echo "$payload" > "$temp_file"
    
    ab -n $((CONCURRENT_USERS * DURATION / 2)) -c $CONCURRENT_USERS \
        -T 'application/json' -p "$temp_file" "$url" 2>&1 | \
        tee "${PROJECT_ROOT}/logs/load-test-$(date +%Y%m%d-%H%M%S).log"
    
    rm -f "$temp_file"
}

###############################################################################
# Curl-based Test Runner (fallback)
###############################################################################
run_curl_test() {
    local url="$1"
    local payload="${2:-}"
    local total_requests=$((CONCURRENT_USERS * DURATION / 2))
    local success_count=0
    local fail_count=0
    local total_time=0
    local min_time=999999
    local max_time=0
    
    log_info "Running curl-based test (${total_requests} requests)..."
    
    mkdir -p "${PROJECT_ROOT}/logs"
    local log_file="${PROJECT_ROOT}/logs/load-test-$(date +%Y%m%d-%H%M%S).log"
    
    for ((i=1; i<=total_requests; i++)); do
        local start_time end_time duration
        start_time=$(date +%s%N)
        
        local curl_opts="-s -o /dev/null -w %{http_code},%{time_total}"
        local response
        
        if [[ -n "$payload" ]]; then
            response=$(curl $curl_opts -X POST -H "Content-Type: application/json" -d "$payload" "$url" 2>/dev/null)
        else
            response=$(curl $curl_opts "$url" 2>/dev/null)
        fi
        
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        
        local http_code
        http_code=$(echo "$response" | cut -d',' -f1)
        local curl_time
        curl_time=$(echo "$response" | cut -d',' -f2)
        
        if [[ "$http_code" == "200" ]]; then
            ((success_count++))
        else
            ((fail_count++))
        fi
        
        total_time=$((total_time + duration))
        
        if [[ $duration -lt $min_time ]]; then
            min_time=$duration
        fi
        
        if [[ $duration -gt $max_time ]]; then
            max_time=$duration
        fi
        
        # Progress indicator
        if [[ $((i % 10)) -eq 0 ]]; then
            echo -n "."
        fi
        
        # Small delay to not overwhelm
        sleep 0.1
    done
    
    echo ""
    
    # Calculate stats
    local avg_time=$((total_time / total_requests))
    local success_rate=$((success_count * 100 / total_requests))
    
    # Output results
    cat > "$log_file" << EOF
Load Test Results
=================
Endpoint: $url
Duration: ${DURATION}s
Concurrent Users: $CONCURRENT_USERS
Total Requests: $total_requests

Results:
  Success Rate: ${success_rate}%
  Success Count: $success_count
  Fail Count: $fail_count

Timing (ms):
  Min: $min_time
  Max: $max_time
  Avg: $avg_time
EOF
    
    log_success "Test complete! Results saved to: $log_file"
    
    # Display summary
    echo ""
    echo "========================================="
    echo "Load Test Summary"
    echo "========================================="
    echo "Success Rate: ${success_rate}%"
    echo "Avg Response Time: ${avg_time}ms"
    echo "Min/Max: ${min_time}ms / ${max_time}ms"
    echo "========================================="
}

###############################################################################
# Generate Report
###############################################################################
generate_report() {
    local report_file="${PROJECT_ROOT}/logs/load-test-report-$(date +%Y%m%d-%H%M%S).html"
    
    if [[ "$OUTPUT_FORMAT" == "html" ]]; then
        cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Sentilyze Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .metric { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Sentilyze Load Test Report</h1>
    <p>Generated: EOF
        echo "$(date)" >> "$report_file"
        cat >> "$report_file" << 'EOF'
</p>
    <div class="metric">
        <h2>Test Configuration</h2>
        <p>See log files for detailed results</p>
    </div>
</body>
</html>
EOF
        log_success "HTML report generated: $report_file"
    fi
}

###############################################################################
# Main Execution
###############################################################################
main() {
    local endpoint="${1:-health}"
    
    # Parse remaining arguments
    shift || true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url|-u)
                API_BASE_URL="$2"
                shift 2
                ;;
            --duration|-d)
                DURATION="$2"
                shift 2
                ;;
            --users|-U)
                CONCURRENT_USERS="$2"
                shift 2
                ;;
            --ramp-up|-r)
                RAMP_UP="$2"
                shift 2
                ;;
            --format|-f)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            --auth-token|-t)
                AUTH_TOKEN="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    if [[ "$endpoint" == "help" ]] || [[ -z "$endpoint" ]]; then
        show_help
        exit 0
    fi
    
    log_info "========================================="
    log_info "Sentilyze Load Testing Tool"
    log_info "Endpoint: $endpoint"
    log_info "Environment: $ENVIRONMENT"
    log_info "========================================="
    
    detect_api_url
    check_dependencies
    
    log_info "Target URL: $API_BASE_URL"
    
    # Create logs directory
    mkdir -p "${PROJECT_ROOT}/logs"
    
    case "$endpoint" in
        health)
            test_health
            ;;
        analyze)
            test_analyze
            ;;
        batch)
            test_batch
            ;;
        all)
            log_info "Running all tests..."
            test_health
            sleep 5
            test_analyze
            sleep 5
            test_batch
            ;;
        *)
            log_error "Unknown endpoint: $endpoint"
            show_help
            exit 1
            ;;
    esac
    
    generate_report
    
    log_success "========================================="
    log_success "Load testing complete!"
    log_success "========================================="
}

# Run main function
main "$@"
