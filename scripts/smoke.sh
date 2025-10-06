#!/bin/bash
# EstimAI End-to-End Smoke Test
# Tests: agent → review → commit → counts → export

set -e  # Exit on any error

# Configuration
BASE_URL="http://localhost:8000"
SESSION_ID="smoke_test_$(date +%s)"
SAMPLE_FILE="samples/280-utility-construction-plans.pdf"
TIMEOUT=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if backend is running
check_backend() {
    log_info "Checking if backend is running..."
    if curl -s "$BASE_URL/health" > /dev/null; then
        log_success "Backend is running"
    else
        log_error "Backend is not running. Please start it first."
        exit 1
    fi
}

# Check if sample file exists
check_sample_file() {
    log_info "Checking sample file..."
    if [ -f "$SAMPLE_FILE" ]; then
        log_success "Sample file found: $SAMPLE_FILE"
    else
        log_error "Sample file not found: $SAMPLE_FILE"
        exit 1
    fi
}

# Test 1: Agent Takeoff
test_agent_takeoff() {
    log_info "🧪 Test 1: Agent Takeoff"
    
    log_info "Uploading PDF and running agent takeoff..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/agent/takeoff" \
        -F "session_id=$SESSION_ID" \
        -F "upload_file=@$SAMPLE_FILE" \
        --max-time $TIMEOUT)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Agent takeoff completed"
        
        # Extract session_id from response
        EXTRACTED_SESSION=$(echo "$BODY" | jq -r '.session_id // empty')
        if [ -n "$EXTRACTED_SESSION" ]; then
            SESSION_ID="$EXTRACTED_SESSION"
            log_info "Using session ID: $SESSION_ID"
        fi
        
        # Check for warnings
        WARNINGS=$(echo "$BODY" | jq -r '.proposed_review.warnings[]? // empty')
        if [ -n "$WARNINGS" ]; then
            log_warning "Agent warnings: $WARNINGS"
        fi
        
        # Check processing time
        PROCESSING_TIME=$(echo "$BODY" | jq -r '.processing_time // empty')
        if [ -n "$PROCESSING_TIME" ]; then
            log_info "Processing time: ${PROCESSING_TIME}s"
        fi
        
    else
        log_error "Agent takeoff failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        exit 1
    fi
}

# Test 2: Review Status
test_review_status() {
    log_info "🧪 Test 2: Review Status"
    
    log_info "Checking review status..."
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/agent/takeoff/$SESSION_ID/status")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        STATUS=$(echo "$BODY" | jq -r '.status')
        log_success "Review status: $STATUS"
        
        if [ "$STATUS" = "completed" ]; then
            # Check summary
            STORM_PIPES=$(echo "$BODY" | jq -r '.summary.networks.storm.pipes // 0')
            SANITARY_PIPES=$(echo "$BODY" | jq -r '.summary.networks.sanitary.pipes // 0')
            WATER_PIPES=$(echo "$BODY" | jq -r '.summary.networks.water.pipes // 0')
            TOTAL_PIPES=$((STORM_PIPES + SANITARY_PIPES + WATER_PIPES))
            
            log_info "Pipe summary: $TOTAL_PIPES total ($STORM_PIPES storm, $SANITARY_PIPES sanitary, $WATER_PIPES water)"
            
            # Check QA flags
            QA_FLAGS=$(echo "$BODY" | jq -r '.summary.qa_flags // 0')
            log_info "QA flags: $QA_FLAGS"
            
        else
            log_warning "Review not completed, status: $STATUS"
        fi
        
    else
        log_error "Review status check failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        exit 1
    fi
}

# Test 3: Commit Review
test_commit_review() {
    log_info "🧪 Test 3: Commit Review"
    
    log_info "Committing review to database..."
    
    # Create commit payload
    COMMIT_PAYLOAD=$(cat <<EOF
{
    "session_id": "$SESSION_ID",
    "sheet_ref": "AUTO",
    "payload": {
        "sheet_units": "ft",
        "scale": "1\" = 50'",
        "networks": {
            "storm": {
                "pipes": [],
                "structures": []
            },
            "sanitary": {
                "pipes": [],
                "manholes": []
            },
            "water": {
                "pipes": [],
                "hydrants": [],
                "valves": []
            }
        },
        "roadway": {
            "curb_lf": 0,
            "sidewalk_sf": 0
        },
        "e_sc": {
            "silt_fence_lf": 0,
            "inlet_protection_ea": 0
        },
        "earthwork": {
            "cut_cy": null,
            "fill_cy": null,
            "source": "table"
        },
        "qa_flags": []
    }
}
EOF
)
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/takeoff/review" \
        -H "Content-Type: application/json" \
        -d "$COMMIT_PAYLOAD")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Review committed to database"
        
        # Check commit message
        MESSAGE=$(echo "$BODY" | jq -r '.message // empty')
        if [ -n "$MESSAGE" ]; then
            log_info "Commit message: $MESSAGE"
        fi
        
    else
        log_error "Review commit failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        exit 1
    fi
}

# Test 4: Counts Query
test_counts_query() {
    log_info "🧪 Test 4: Counts Query"
    
    log_info "Querying counts from database..."
    RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/counts")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Counts query successful"
        
        # Count items by category
        TOTAL_ITEMS=$(echo "$BODY" | jq 'length')
        log_info "Total count items: $TOTAL_ITEMS"
        
        # Count by category
        STORM_ITEMS=$(echo "$BODY" | jq '[.[] | select(.category | contains("storm"))] | length')
        SANITARY_ITEMS=$(echo "$BODY" | jq '[.[] | select(.category | contains("sanitary"))] | length')
        WATER_ITEMS=$(echo "$BODY" | jq '[.[] | select(.category | contains("water"))] | length')
        
        log_info "Items by category: $STORM_ITEMS storm, $SANITARY_ITEMS sanitary, $WATER_ITEMS water"
        
        # Check for depth buckets
        DEPTH_BUCKETS=$(echo "$BODY" | jq '[.[] | select(.category | contains("pipe") and contains("."))] | length')
        if [ "$DEPTH_BUCKETS" -gt 0 ]; then
            log_success "Depth bucket items found: $DEPTH_BUCKETS"
        fi
        
        # Check for pricing
        PRICED_ITEMS=$(echo "$BODY" | jq '[.[] | select(.attributes.unit_price != null)] | length')
        if [ "$PRICED_ITEMS" -gt 0 ]; then
            log_success "Priced items found: $PRICED_ITEMS"
        fi
        
    else
        log_error "Counts query failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        exit 1
    fi
}

# Test 5: PDF Export
test_pdf_export() {
    log_info "🧪 Test 5: PDF Export"
    
    log_info "Generating PDF summary..."
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/export/summary" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\"}" \
        --output "smoke_test_summary.pdf")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "PDF export completed"
        
        # Check file size
        if [ -f "smoke_test_summary.pdf" ]; then
            FILE_SIZE=$(stat -f%z "smoke_test_summary.pdf" 2>/dev/null || stat -c%s "smoke_test_summary.pdf" 2>/dev/null)
            FILE_SIZE_KB=$((FILE_SIZE / 1024))
            log_info "PDF file size: ${FILE_SIZE_KB}KB"
            
            if [ "$FILE_SIZE" -lt 1048576 ]; then  # 1MB
                log_success "PDF size under 1MB limit"
            else
                log_warning "PDF size exceeds 1MB limit"
            fi
            
            # Clean up
            rm -f "smoke_test_summary.pdf"
        fi
        
    else
        log_error "PDF export failed (HTTP $HTTP_CODE)"
        exit 1
    fi
}

# Test 6: Performance Metrics
test_performance() {
    log_info "🧪 Test 6: Performance Metrics"
    
    log_info "Running performance tests..."
    
    # Test response times
    START_TIME=$(date +%s.%N)
    curl -s "$BASE_URL/health" > /dev/null
    END_TIME=$(date +%s.%N)
    HEALTH_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    START_TIME=$(date +%s.%N)
    curl -s "$BASE_URL/api/v1/counts" > /dev/null
    END_TIME=$(date +%s.%N)
    COUNTS_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    log_info "Response times:"
    log_info "  Health check: ${HEALTH_TIME}s"
    log_info "  Counts query: ${COUNTS_TIME}s"
    
    # Check if times are reasonable
    if (( $(echo "$HEALTH_TIME < 1.0" | bc -l) )); then
        log_success "Health check response time acceptable"
    else
        log_warning "Health check response time slow: ${HEALTH_TIME}s"
    fi
    
    if (( $(echo "$COUNTS_TIME < 2.0" | bc -l) )); then
        log_success "Counts query response time acceptable"
    else
        log_warning "Counts query response time slow: ${COUNTS_TIME}s"
    fi
}

# Main execution
main() {
    echo "🚀 EstimAI End-to-End Smoke Test"
    echo "================================="
    echo "Session ID: $SESSION_ID"
    echo "Sample File: $SAMPLE_FILE"
    echo "Base URL: $BASE_URL"
    echo ""
    
    # Prerequisites
    check_backend
    check_sample_file
    
    # Run tests
    test_agent_takeoff
    test_review_status
    test_commit_review
    test_counts_query
    test_pdf_export
    test_performance
    
    echo ""
    log_success "🎉 All smoke tests passed!"
    log_info "Session ID: $SESSION_ID"
    log_info "You can view results at: $BASE_URL/api/v1/counts"
}

# Run main function
main "$@"
