"""CSV export utilities."""
import csv
import io
from typing import List, Dict, Any
from datetime import datetime
from ..models import CountItem, ReviewSession

def export_count_items_to_csv(count_items: List[CountItem]) -> str:
    """Export count items to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "File", "Page", "Type", "Confidence", "X_PDF", "Y_PDF", 
        "Points_Per_Foot", "Status", "Reviewer_Note", "X_PDF_Edited", 
        "Y_PDF_Edited", "Type_Edited", "Created_At", "Updated_At"
    ])
    
    # Write data rows
    for item in count_items:
        writer.writerow([
            str(item.id),
            item.file,
            item.page,
            item.type,
            item.confidence,
            item.x_pdf,
            item.y_pdf,
            item.points_per_foot,
            item.status,
            item.reviewer_note or "",
            item.x_pdf_edited or "",
            item.y_pdf_edited or "",
            item.type_edited or "",
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else ""
        ])
    
    return output.getvalue()

def export_review_sessions_to_csv(sessions: List[ReviewSession]) -> str:
    """Export review sessions to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "File", "Pages", "Points_Per_Foot", "Metrics", 
        "Created_At", "Updated_At"
    ])
    
    # Write data rows
    for session in sessions:
        writer.writerow([
            str(session.id),
            session.file,
            ",".join(map(str, session.pages)),
            session.points_per_foot,
            str(session.metrics) if session.metrics else "",
            session.created_at.isoformat() if session.created_at else "",
            session.updated_at.isoformat() if session.updated_at else ""
        ])
    
    return output.getvalue()

def export_metrics_summary(metrics: Dict[str, Any]) -> str:
    """Export metrics summary to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Metric", "Value"])
    
    # Write metrics
    for category, values in metrics.items():
        if isinstance(values, dict):
            for key, value in values.items():
                writer.writerow([f"{category}_{key}", value])
        else:
            writer.writerow([category, values])
    
    return output.getvalue()
