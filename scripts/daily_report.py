"""
Daily Report Script
Generate daily call summary.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.logging.log_store import CallLogStore
from datetime import date, timedelta
import argparse


def generate_daily_report(date_str: str = None):
    """Generate and print daily report."""
    if not date_str:
        date_str = date.today().isoformat()
    
    store = CallLogStore()
    stats = store.get_daily_stats(date_str)
    
    print("\n" + "="*60)
    print(f"  ZYLIN DAILY REPORT - {stats['date']}")
    print("="*60 + "\n")
    
    print(f"📞 Total Calls: {stats['total_calls']}")
    print(f"\n📊 By Intent:")
    print(f"   • FAQ: {stats['faq_count']}")
    print(f"   • Booking: {stats['booking_count']}")
    print(f"   • Urgent: {stats['urgent_count']}")
    
    print(f"\n📅 Bookings Created: {stats['bookings_created']}")
    print(f"🚨 Escalations: {stats['escalations']}")
    
    if stats['avg_duration_seconds'] > 0:
        minutes = stats['avg_duration_seconds'] // 60
        seconds = stats['avg_duration_seconds'] % 60
        print(f"⏱️  Average Call Duration: {int(minutes)}m {int(seconds)}s")
    
    # Get recent calls
    logs = store.list_logs(start_date=date_str, end_date=date_str, limit=10)
    
    if logs:
        print(f"\n📋 Recent Calls:")
        for log in logs[:5]:
            time = log.start_time.split("T")[1][:5] if "T" in log.start_time else "N/A"
            phone = log.caller_phone or "Unknown"
            intent = log.intent or "other"
            print(f"   • {time} | {phone} | {intent}")
    
    print("\n" + "="*60 + "\n")
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Zylin daily report")
    parser.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format (default: today)",
        default=None
    )
    parser.add_argument(
        "--yesterday",
        action="store_true",
        help="Generate report for yesterday"
    )
    
    args = parser.parse_args()
    
    report_date = args.date
    if args.yesterday:
        report_date = (date.today() - timedelta(days=1)).isoformat()
    
    generate_daily_report(report_date)
