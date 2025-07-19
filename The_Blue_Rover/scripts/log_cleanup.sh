#!/bin/bash
"""
Log Cleanup and Rotation Script for Blue Rover

Manages log file rotation, cleanup, and maintenance tasks.
Can be run manually or scheduled via cron.
"""

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
DAYS_TO_KEEP=7
MAX_LOG_SIZE="10M"
MAX_TELEMETRY_SIZE="50M"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if log directory exists
check_log_directory() {
    if [ ! -d "$LOG_DIR" ]; then
        log_warn "Log directory $LOG_DIR does not exist, creating it..."
        mkdir -p "$LOG_DIR"
    fi
}

# Function to rotate large log files
rotate_large_logs() {
    log_info "Checking for large log files to rotate..."
    
    find "$LOG_DIR" -name "*.log" -size +$MAX_LOG_SIZE -print0 | while IFS= read -r -d '' file; do
        log_info "Rotating large log file: $(basename "$file")"
        
        # Create rotated filename with timestamp
        timestamp=$(date +"%Y%m%d_%H%M%S")
        rotated_file="${file}.${timestamp}"
        
        # Move current log to rotated name
        mv "$file" "$rotated_file"
        
        # Compress the rotated file
        gzip "$rotated_file"
        
        log_info "Rotated and compressed: $(basename "$rotated_file").gz"
    done
}

# Function to rotate large telemetry files
rotate_large_telemetry() {
    log_info "Checking for large telemetry files to rotate..."
    
    find "$LOG_DIR" -name "*_telemetry.jsonl" -size +$MAX_TELEMETRY_SIZE -print0 | while IFS= read -r -d '' file; do
        log_info "Rotating large telemetry file: $(basename "$file")"
        
        # Create rotated filename with timestamp
        timestamp=$(date +"%Y%m%d_%H%M%S")
        rotated_file="${file}.${timestamp}"
        
        # Move current telemetry to rotated name
        mv "$file" "$rotated_file"
        
        # Compress the rotated file
        gzip "$rotated_file"
        
        log_info "Rotated and compressed: $(basename "$rotated_file").gz"
    done
}

# Function to clean up old log files
cleanup_old_logs() {
    log_info "Cleaning up log files older than $DAYS_TO_KEEP days..."
    
    # Count files before cleanup
    old_count=$(find "$LOG_DIR" -name "*.log*" -mtime +$DAYS_TO_KEEP | wc -l)
    
    if [ "$old_count" -gt 0 ]; then
        log_info "Found $old_count old log files to remove"
        
        # Remove old log files
        find "$LOG_DIR" -name "*.log*" -mtime +$DAYS_TO_KEEP -delete
        
        log_info "Removed $old_count old log files"
    else
        log_info "No old log files found"
    fi
}

# Function to clean up old telemetry files
cleanup_old_telemetry() {
    log_info "Cleaning up telemetry files older than $DAYS_TO_KEEP days..."
    
    # Count files before cleanup
    old_count=$(find "$LOG_DIR" -name "*_telemetry.jsonl*" -mtime +$DAYS_TO_KEEP | wc -l)
    
    if [ "$old_count" -gt 0 ]; then
        log_info "Found $old_count old telemetry files to remove"
        
        # Remove old telemetry files
        find "$LOG_DIR" -name "*_telemetry.jsonl*" -mtime +$DAYS_TO_KEEP -delete
        
        log_info "Removed $old_count old telemetry files"
    else
        log_info "No old telemetry files found"
    fi
}

# Function to clean up empty directories
cleanup_empty_dirs() {
    log_info "Cleaning up empty directories..."
    
    find "$LOG_DIR" -type d -empty -delete 2>/dev/null || true
}

# Function to show disk usage
show_disk_usage() {
    log_info "Current log directory disk usage:"
    du -sh "$LOG_DIR" 2>/dev/null || log_warn "Could not calculate disk usage"
    
    log_info "Log file breakdown:"
    find "$LOG_DIR" -name "*.log*" -exec du -sh {} \; 2>/dev/null | sort -hr | head -10 || true
}

# Function to compress old uncompressed files
compress_old_files() {
    log_info "Compressing old uncompressed log files..."
    
    # Compress log files older than 1 day that aren't already compressed
    find "$LOG_DIR" -name "*.log.*" -not -name "*.gz" -mtime +1 -print0 | while IFS= read -r -d '' file; do
        log_info "Compressing: $(basename "$file")"
        gzip "$file"
    done
    
    # Compress telemetry files older than 1 day that aren't already compressed
    find "$LOG_DIR" -name "*_telemetry.jsonl.*" -not -name "*.gz" -mtime +1 -print0 | while IFS= read -r -d '' file; do
        log_info "Compressing: $(basename "$file")"
        gzip "$file"
    done
}

# Function to validate log files
validate_log_files() {
    log_info "Validating log file integrity..."
    
    error_count=0
    
    # Check for corrupted gzip files
    find "$LOG_DIR" -name "*.gz" -print0 | while IFS= read -r -d '' file; do
        if ! gzip -t "$file" 2>/dev/null; then
            log_error "Corrupted gzip file: $(basename "$file")"
            error_count=$((error_count + 1))
        fi
    done
    
    # Check for valid JSON in telemetry files
    find "$LOG_DIR" -name "*_telemetry.jsonl" -print0 | while IFS= read -r -d '' file; do
        if [ -s "$file" ]; then
            # Check last few lines for valid JSON
            tail -n 5 "$file" | while IFS= read -r line; do
                if [ -n "$line" ] && ! echo "$line" | python3 -m json.tool >/dev/null 2>&1; then
                    log_warn "Invalid JSON line in: $(basename "$file")"
                    break
                fi
            done
        fi
    done
    
    if [ "$error_count" -eq 0 ]; then
        log_info "All log files validated successfully"
    else
        log_warn "Found $error_count corrupted files"
    fi
}

# Function to create log summary report
create_summary_report() {
    log_info "Creating log summary report..."
    
    report_file="$LOG_DIR/cleanup_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Blue Rover Log Cleanup Report"
        echo "Generated: $(date)"
        echo "================================"
        echo
        echo "Log Directory: $LOG_DIR"
        echo "Days to Keep: $DAYS_TO_KEEP"
        echo "Max Log Size: $MAX_LOG_SIZE"
        echo "Max Telemetry Size: $MAX_TELEMETRY_SIZE"
        echo
        echo "Current Files:"
        find "$LOG_DIR" -type f | wc -l | xargs echo "Total files:"
        find "$LOG_DIR" -name "*.log*" | wc -l | xargs echo "Log files:"
        find "$LOG_DIR" -name "*_telemetry.jsonl*" | wc -l | xargs echo "Telemetry files:"
        find "$LOG_DIR" -name "*.gz" | wc -l | xargs echo "Compressed files:"
        echo
        echo "Disk Usage:"
        du -sh "$LOG_DIR" 2>/dev/null || echo "Could not calculate"
        echo
        echo "Largest Files:"
        find "$LOG_DIR" -type f -exec du -h {} \; 2>/dev/null | sort -hr | head -5 || echo "None found"
    } > "$report_file"
    
    log_info "Summary report created: $(basename "$report_file")"
}

# Main execution
main() {
    log_info "Starting Blue Rover log cleanup and maintenance..."
    log_info "Log directory: $LOG_DIR"
    log_info "Days to keep: $DAYS_TO_KEEP"
    
    # Check if log directory exists
    check_log_directory
    
    # Show current disk usage
    show_disk_usage
    
    # Perform maintenance tasks
    rotate_large_logs
    rotate_large_telemetry
    compress_old_files
    cleanup_old_logs
    cleanup_old_telemetry
    cleanup_empty_dirs
    
    # Validate files
    validate_log_files
    
    # Create summary report
    create_summary_report
    
    # Show final disk usage
    echo
    show_disk_usage
    
    log_info "Log cleanup and maintenance completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Blue Rover Log Cleanup Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --days DAYS         Number of days to keep logs (default: $DAYS_TO_KEEP)"
        echo "  --max-size SIZE     Maximum log file size before rotation (default: $MAX_LOG_SIZE)"
        echo "  --dry-run           Show what would be done without making changes"
        echo "  --report-only       Only generate summary report"
        echo
        echo "Examples:"
        echo "  $0                  Run with default settings"
        echo "  $0 --days 14        Keep logs for 14 days"
        echo "  $0 --dry-run        Preview actions without executing"
        exit 0
        ;;
    --days)
        DAYS_TO_KEEP="$2"
        shift 2
        ;;
    --max-size)
        MAX_LOG_SIZE="$2"
        shift 2
        ;;
    --dry-run)
        log_info "DRY RUN MODE - No changes will be made"
        # Override functions to just echo what they would do
        mv() { echo "Would move: $1 -> $2"; }
        rm() { echo "Would remove: $*"; }
        gzip() { echo "Would compress: $*"; }
        export -f mv rm gzip
        ;;
    --report-only)
        check_log_directory
        show_disk_usage
        create_summary_report
        exit 0
        ;;
esac

# Run main function
main "$@"