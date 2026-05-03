"""
Report Generation Module
Generates comprehensive proctoring reports in PDF and JSON formats
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import os

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates comprehensive proctoring reports"""
    
    def __init__(self, reports_dir: str):
        """
        Initialize report generator
        
        Args:
            reports_dir: Directory to store reports
        """
        self.reports_dir = reports_dir
        Path(reports_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, session_data: Dict, filename: Optional[str] = None) -> str:
        """
        Generate JSON format report
        
        Args:
            session_data: Session data dictionary
            filename: Optional custom filename
            
        Returns:
            Path to generated report
        """
        try:
            if filename is None:
                session_id = session_data.get("session_info", {}).get("session_id", "unknown")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{session_id}_{timestamp}.json"
            
            report_path = os.path.join(self.reports_dir, filename)
            
            # Add generation timestamp
            session_data["report_generated_at"] = datetime.now().isoformat()
            session_data["report_version"] = "1.0"
            
            with open(report_path, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            logger.info(f"JSON report generated: {report_path}")
            return report_path
        
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            raise
    
    def generate_text_report(self, session_data: Dict, filename: Optional[str] = None) -> str:
        """
        Generate text format report
        
        Args:
            session_data: Session data dictionary
            filename: Optional custom filename
            
        Returns:
            Path to generated report
        """
        try:
            if filename is None:
                session_id = session_data.get("session_info", {}).get("session_id", "unknown")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{session_id}_{timestamp}.txt"
            
            report_path = os.path.join(self.reports_dir, filename)
            
            with open(report_path, 'w') as f:
                self._write_text_report(f, session_data)
            
            logger.info(f"Text report generated: {report_path}")
            return report_path
        
        except Exception as e:
            logger.error(f"Error generating text report: {e}")
            raise
    
    def _write_text_report(self, file_handle, session_data: Dict):
        """Write text format report to file"""
        
        # Header
        file_handle.write("=" * 80 + "\n")
        file_handle.write("PROCTORING SESSION REPORT\n")
        file_handle.write("=" * 80 + "\n\n")
        
        # Session Information
        session_info = session_data.get("session_info", {})
        file_handle.write("SESSION INFORMATION\n")
        file_handle.write("-" * 80 + "\n")
        file_handle.write(f"Session ID: {session_info.get('session_id', 'N/A')}\n")
        file_handle.write(f"User ID: {session_info.get('user_id', 'N/A')}\n")
        
        start_time = session_info.get('start_time')
        if start_time:
            start_dt = datetime.fromtimestamp(start_time)
            file_handle.write(f"Start Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        end_time = session_info.get('end_time')
        if end_time:
            end_dt = datetime.fromtimestamp(end_time)
            file_handle.write(f"End Time: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        duration = session_info.get('duration_seconds', 0)
        duration_min = int(duration / 60)
        duration_sec = int(duration % 60)
        file_handle.write(f"Duration: {duration_min}m {duration_sec}s\n")
        file_handle.write(f"Status: {session_info.get('status', 'N/A')}\n")
        file_handle.write(f"Initial Verification: {'PASSED' if session_info.get('initial_verified') else 'FAILED'}\n\n")
        
        # Statistics
        stats = session_data.get("statistics", {})
        file_handle.write("STATISTICS\n")
        file_handle.write("-" * 80 + "\n")
        file_handle.write(f"Total Events: {stats.get('total_events', 0)}\n")
        file_handle.write(f"Total Warnings: {stats.get('total_warnings', 0)}\n")
        file_handle.write(f"  - Critical: {stats.get('critical_warnings', 0)}\n")
        file_handle.write(f"  - Alerts: {stats.get('alert_warnings', 0)}\n")
        file_handle.write(f"  - Warnings: {stats.get('warning_warnings', 0)}\n")
        file_handle.write(f"\nFace Detection Records: {stats.get('total_face_detections', 0)}\n")
        file_handle.write(f"  - Valid Detections: {stats.get('valid_face_detections', 0)}\n")
        file_handle.write(f"  - Invalid Detections: {stats.get('invalid_face_detections', 0)}\n")
        
        if stats.get('total_face_detections', 0) > 0:
            valid_pct = (stats.get('valid_face_detections', 0) / stats.get('total_face_detections', 1)) * 100
            file_handle.write(f"  - Detection Rate: {valid_pct:.1f}%\n")
        
        file_handle.write(f"\nEye Tracking Records: {stats.get('total_eye_tracking_records', 0)}\n")
        file_handle.write(f"\nVerification Records: {stats.get('total_verifications', 0)}\n")
        file_handle.write(f"  - Successful: {stats.get('successful_verifications', 0)}\n")
        file_handle.write(f"  - Failed: {stats.get('failed_verifications', 0)}\n\n")
        
        # Warnings Summary
        warnings = session_data.get("warnings", [])
        if warnings:
            file_handle.write("WARNINGS SUMMARY\n")
            file_handle.write("-" * 80 + "\n")
            
            for i, warning in enumerate(warnings[-20:], 1):  # Last 20 warnings
                timestamp = warning.get('timestamp')
                if timestamp:
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                else:
                    time_str = "N/A"
                
                level = warning.get('level', 'unknown').upper()
                title = warning.get('title', 'Unknown')
                description = warning.get('description', 'No description')
                
                file_handle.write(f"\n{i}. [{time_str}] [{level}] {title}\n")
                file_handle.write(f"   {description}\n")
        
        file_handle.write("\n" + "=" * 80 + "\n")
        file_handle.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_handle.write("=" * 80 + "\n")
    
    def generate_pdf_report(self, session_data: Dict, filename: Optional[str] = None) -> str:
        """
        Generate PDF format report
        
        Args:
            session_data: Session data dictionary
            filename: Optional custom filename
            
        Returns:
            Path to generated report
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib import colors
            
            if filename is None:
                session_id = session_data.get("session_info", {}).get("session_id", "unknown")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{session_id}_{timestamp}.pdf"
            
            report_path = os.path.join(self.reports_dir, filename)
            
            doc = SimpleDocTemplate(report_path, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f4788'),
                spaceAfter=30,
                alignment=1  # Center
            )
            story.append(Paragraph("Proctoring Session Report", title_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Session Information Table
            session_info = session_data.get("session_info", {})
            session_table_data = [
                ["Session ID", session_info.get('session_id', 'N/A')],
                ["User ID", session_info.get('user_id', 'N/A')],
                ["Status", session_info.get('status', 'N/A')],
                ["Initial Verification", "PASSED" if session_info.get('initial_verified') else "FAILED"],
            ]
            
            start_time = session_info.get('start_time')
            if start_time:
                start_dt = datetime.fromtimestamp(start_time)
                session_table_data.append(["Start Time", start_dt.strftime('%Y-%m-%d %H:%M:%S')])
            
            end_time = session_info.get('end_time')
            if end_time:
                end_dt = datetime.fromtimestamp(end_time)
                session_table_data.append(["End Time", end_dt.strftime('%Y-%m-%d %H:%M:%S')])
            
            duration = session_info.get('duration_seconds', 0)
            session_table_data.append(["Duration", f"{int(duration//60)}m {int(duration%60)}s"])
            
            session_table = Table(session_table_data, colWidths=[2*inch, 4*inch])
            session_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6f0ff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(session_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Statistics
            story.append(Paragraph("Statistics", styles['Heading2']))
            stats = session_data.get("statistics", {})
            
            stats_table_data = [
                ["Metric", "Count", "Percentage"],
                ["Total Events", str(stats.get('total_events', 0)), "100%"],
                ["Total Warnings", str(stats.get('total_warnings', 0)), "-"],
                ["  - Critical", str(stats.get('critical_warnings', 0)), "-"],
                ["  - Alerts", str(stats.get('alert_warnings', 0)), "-"],
                ["Face Detections", str(stats.get('total_face_detections', 0)), "100%"],
                ["  - Valid", str(stats.get('valid_face_detections', 0)), 
                 f"{(stats.get('valid_face_detections', 0)/max(stats.get('total_face_detections', 1), 1)*100):.1f}%"],
                ["  - Invalid", str(stats.get('invalid_face_detections', 0)), 
                 f"{(stats.get('invalid_face_detections', 0)/max(stats.get('total_face_detections', 1), 1)*100):.1f}%"],
                ["Eye Tracking Records", str(stats.get('total_eye_tracking_records', 0)), "-"],
                ["Verifications", str(stats.get('total_verifications', 0)), "100%"],
                ["  - Successful", str(stats.get('successful_verifications', 0)), 
                 f"{(stats.get('successful_verifications', 0)/max(stats.get('total_verifications', 1), 1)*100):.1f}%"],
                ["  - Failed", str(stats.get('failed_verifications', 0)), 
                 f"{(stats.get('failed_verifications', 0)/max(stats.get('total_verifications', 1), 1)*100):.1f}%"],
            ]
            
            stats_table = Table(stats_table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Build PDF
            doc.build(story)
            logger.info(f"PDF report generated: {report_path}")
            return report_path
        
        except ImportError:
            logger.warning("reportlab not available, generating text report instead")
            return self.generate_text_report(session_data, filename.replace('.pdf', '.txt'))
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            raise
    
    def generate_all_reports(self, session_data: Dict) -> Dict[str, str]:
        """
        Generate all report formats
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Dictionary with paths to generated reports
        """
        reports = {}
        
        try:
            reports['json'] = self.generate_json_report(session_data)
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
        
        try:
            reports['text'] = self.generate_text_report(session_data)
        except Exception as e:
            logger.error(f"Failed to generate text report: {e}")
        
        try:
            reports['pdf'] = self.generate_pdf_report(session_data)
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
        
        logger.info(f"All available reports generated: {list(reports.keys())}")
        return reports
