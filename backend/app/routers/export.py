"""
Export API

Handles data export in CSV and PDF formats.
"""

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date, timedelta
from enum import Enum
import io

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user
from app.services.export_service import ExportService, ExportConfig

router = APIRouter()


class DataType(str, Enum):
    """Data types available for export"""
    sleep = "sleep"
    nutrition = "nutrition"
    exercise = "exercise"
    vitals = "vitals"
    body = "body"
    chronic = "chronic"
    anomalies = "anomalies"
    all = "all"


@router.get("/csv")
async def export_csv(
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    data_types: List[DataType] = Query([DataType.all], description="Data types to export"),
    combined: bool = Query(False, description="Combine all data into single file"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export health data as CSV.
    
    Returns CSV files for selected data types.
    If combined=True, returns a single CSV with all data.
    """
    # Default dates
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    
    # Determine what to include
    include_all = DataType.all in data_types
    
    config = ExportConfig(
        start_date=start,
        end_date=end,
        include_sleep=include_all or DataType.sleep in data_types,
        include_nutrition=include_all or DataType.nutrition in data_types,
        include_exercise=include_all or DataType.exercise in data_types,
        include_vitals=include_all or DataType.vitals in data_types,
        include_body=include_all or DataType.body in data_types,
        include_chronic=include_all or DataType.chronic in data_types,
        include_anomalies=include_all or DataType.anomalies in data_types,
    )
    
    service = ExportService(db, current_user.id)
    exports = await service.export_csv(config, combined=combined)
    
    if combined:
        # Return single combined CSV
        csv_content = exports.get("combined", "")
        filename = f"vitaliq_export_{start.isoformat()}_to_{end.isoformat()}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    else:
        # Return JSON with multiple CSV strings
        return {
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat()
            },
            "exports": {
                data_type: {
                    "filename": f"vitaliq_{data_type}_{start.isoformat()}_to_{end.isoformat()}.csv",
                    "content": csv_content,
                    "rows": csv_content.count('\n') - 1 if csv_content else 0
                }
                for data_type, csv_content in exports.items()
                if csv_content.strip()
            }
        }


@router.get("/csv/{data_type}")
async def export_single_csv(
    data_type: DataType,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export a single data type as CSV file download"""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    
    config = ExportConfig(
        start_date=start,
        end_date=end,
        include_sleep=data_type == DataType.sleep,
        include_nutrition=data_type == DataType.nutrition,
        include_exercise=data_type == DataType.exercise,
        include_vitals=data_type == DataType.vitals,
        include_body=data_type == DataType.body,
        include_chronic=data_type == DataType.chronic,
        include_anomalies=data_type == DataType.anomalies,
    )
    
    service = ExportService(db, current_user.id)
    exports = await service.export_csv(config)
    
    csv_content = exports.get(data_type.value, "")
    filename = f"vitaliq_{data_type.value}_{start.isoformat()}_to_{end.isoformat()}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/pdf")
async def export_pdf(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export health report as PDF.
    
    Note: PDF generation requires reportlab library.
    This endpoint returns the data that would be in the PDF.
    """
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    
    config = ExportConfig(
        start_date=start,
        end_date=end,
        include_sleep=True,
        include_nutrition=True,
        include_exercise=True,
        include_vitals=True,
        include_body=True,
        include_chronic=True,
        include_anomalies=True,
    )
    
    service = ExportService(db, current_user.id)
    
    # Generate summary data for report
    summary = await service.generate_summary_data(config)
    
    # Try to generate PDF if reportlab is available
    try:
        pdf_bytes = await _generate_pdf_report(summary, current_user)
        
        filename = f"vitaliq_report_{start.isoformat()}_to_{end.isoformat()}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except ImportError:
        # reportlab not installed, return JSON summary instead
        return {
            "message": "PDF generation requires reportlab library. Returning JSON summary instead.",
            "install_hint": "pip install reportlab",
            "summary": summary
        }


async def _generate_pdf_report(summary: dict, user) -> bytes:
    """Generate PDF report using reportlab"""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=10,
        spaceBefore=15
    )
    
    story = []
    
    # Title
    story.append(Paragraph("VitalIQ Health Report", title_style))
    story.append(Paragraph(f"Period: {summary['period']['start']} to {summary['period']['end']}", styles['Normal']))
    story.append(Paragraph(f"Generated for: {user.email}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Sleep Section
    if "sleep" in summary.get("sections", {}):
        sleep = summary["sections"]["sleep"]
        story.append(Paragraph("Sleep Summary", heading_style))
        
        sleep_data = [
            ["Metric", "Value"],
            ["Total Nights Tracked", str(sleep.get("total_nights", 0))],
            ["Average Duration", f"{sleep.get('avg_duration', 0)} hours"],
            ["Average Quality", f"{sleep.get('avg_quality', 0)}/100"],
            ["Best Night", f"{sleep.get('best_night', 0)}/100"],
            ["Worst Night", f"{sleep.get('worst_night', 0)}/100"],
        ]
        
        t = Table(sleep_data, colWidths=[2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
    
    # Exercise Section
    if "exercise" in summary.get("sections", {}):
        exercise = summary["sections"]["exercise"]
        story.append(Paragraph("Exercise Summary", heading_style))
        
        exercise_data = [
            ["Metric", "Value"],
            ["Total Workouts", str(exercise.get("total_workouts", 0))],
            ["Active Days", str(exercise.get("active_days", 0))],
            ["Total Minutes", str(exercise.get("total_minutes", 0))],
            ["Total Calories Burned", str(exercise.get("total_calories", 0))],
            ["Avg Workout Duration", f"{exercise.get('avg_workout_duration', 0)} min"],
        ]
        
        t = Table(exercise_data, colWidths=[2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
    
    # Nutrition Section
    if "nutrition" in summary.get("sections", {}):
        nutrition = summary["sections"]["nutrition"]
        story.append(Paragraph("Nutrition Summary", heading_style))
        
        nutrition_data = [
            ["Metric", "Value"],
            ["Total Meals Logged", str(nutrition.get("total_meals", 0))],
            ["Avg Daily Calories", str(int(nutrition.get("avg_daily_calories", 0)))],
            ["Avg Daily Protein", f"{nutrition.get('avg_daily_protein', 0)}g"],
        ]
        
        t = Table(nutrition_data, colWidths=[2.5*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 15))
    
    # Anomalies Section
    if "anomalies" in summary.get("sections", {}):
        anomalies = summary["sections"]["anomalies"]
        story.append(Paragraph("Anomaly Summary", heading_style))
        
        story.append(Paragraph(f"Total Anomalies Detected: {anomalies.get('total', 0)}", styles['Normal']))
        
        if anomalies.get("by_severity"):
            severity_text = ", ".join([f"{k}: {v}" for k, v in anomalies["by_severity"].items()])
            story.append(Paragraph(f"By Severity: {severity_text}", styles['Normal']))
        
        if anomalies.get("most_common_metric"):
            story.append(Paragraph(f"Most Common: {anomalies['most_common_metric']}", styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("Generated by VitalIQ - Personal Health & Wellness Aggregator", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)))
    
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


@router.get("/summary")
async def get_export_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a summary of available data for export"""
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=30))
    
    config = ExportConfig(
        start_date=start,
        end_date=end
    )
    
    service = ExportService(db, current_user.id)
    summary = await service.generate_summary_data(config)
    
    return summary
