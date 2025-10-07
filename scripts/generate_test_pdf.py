#!/usr/bin/env python3
"""
Generate a realistic test PDF with vector geometry and invert elevations.

This PDF includes:
- Vector polylines (storm, sanitary, water pipes)
- Scale bar (1" = 20')
- Invert elevation labels (IE=XX.X at endpoints)
- Layer names
- Legend
- Proper coordinate system
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import math

# Page setup
PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)  # 11" x 8.5"
MARGIN = 0.5 * inch

# Scale: 1" = 20' (drawing scale)
SCALE_TEXT = '1" = 20\''
FEET_PER_INCH = 20.0
POINTS_PER_INCH = 72.0
POINTS_PER_FOOT = POINTS_PER_INCH / FEET_PER_INCH  # 3.6 points/foot

# Drawing area (in PDF points)
DRAWING_LEFT = MARGIN
DRAWING_BOTTOM = MARGIN
DRAWING_WIDTH = PAGE_WIDTH - (2 * MARGIN)
DRAWING_HEIGHT = PAGE_HEIGHT - (2 * MARGIN) - (1 * inch)  # Leave space for title/scale

# Origin of coordinate system (bottom-left of drawing area)
ORIGIN_X = DRAWING_LEFT
ORIGIN_Y = DRAWING_BOTTOM


def ft_to_points(feet):
    """Convert feet to PDF points using scale."""
    return feet * POINTS_PER_FOOT


def draw_scale_bar(c, x, y):
    """Draw scale bar and label."""
    # Scale bar: 1 inch long
    c.setStrokeColor(HexColor('#000000'))
    c.setLineWidth(2)
    c.line(x, y, x + inch, y)
    
    # Tick marks
    c.line(x, y - 5, x, y + 5)
    c.line(x + inch, y - 5, x + inch, y + 5)
    
    # Label
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + (inch / 2), y - 20, "SCALE: 1\" = 20'")


def draw_pipe(c, x1_ft, y1_ft, x2_ft, y2_ft, color, width=2, layer_name=""):
    """
    Draw a pipe as a polyline.
    
    Args:
        c: Canvas
        x1_ft, y1_ft: Start point in feet (drawing coordinates)
        x2_ft, y2_ft: End point in feet (drawing coordinates)
        color: Hex color string
        width: Line width in points
        layer_name: Layer name (for metadata)
    """
    # Convert feet to PDF points
    x1 = ORIGIN_X + ft_to_points(x1_ft)
    y1 = ORIGIN_Y + ft_to_points(y1_ft)
    x2 = ORIGIN_X + ft_to_points(x2_ft)
    y2 = ORIGIN_Y + ft_to_points(y2_ft)
    
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)


def draw_label(c, x_ft, y_ft, text, size=8):
    """Draw text label at coordinates (in feet)."""
    x = ORIGIN_X + ft_to_points(x_ft)
    y = ORIGIN_Y + ft_to_points(y_ft)
    
    c.setFillColor(HexColor('#000000'))
    c.setFont("Helvetica", size)
    c.drawString(x, y, text)


def draw_invert_label(c, x_ft, y_ft, ie_value, label_type="IE"):
    """Draw invert elevation label."""
    text = f"{label_type}={ie_value:.1f}"
    draw_label(c, x_ft, y_ft, text, size=7)


def draw_pipe_with_labels(c, x1_ft, y1_ft, x2_ft, y2_ft, ie_in, ie_out, dia_in, material, color, discipline):
    """Draw a complete pipe with elevations and material label."""
    # Draw pipe line
    draw_pipe(c, x1_ft, y1_ft, x2_ft, y2_ft, color, width=2)
    
    # Draw invert elevations at endpoints
    draw_invert_label(c, x1_ft - 5, y1_ft + 3, ie_in, "IE")
    draw_invert_label(c, x2_ft + 2, y2_ft + 3, ie_out, "IE")
    
    # Draw material/diameter label at midpoint
    mid_x = (x1_ft + x2_ft) / 2
    mid_y = (y1_ft + y2_ft) / 2
    material_text = f'{dia_in}" {material.upper()}'
    draw_label(c, mid_x, mid_y + 5, material_text, size=8)


def generate_test_pdf(output_path="samples/test_vector_with_elevations.pdf"):
    """Generate realistic test PDF."""
    c = canvas.Canvas(output_path, pagesize=landscape(letter))
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 30, "UTILITY PLAN - TEST SITE")
    
    # Scale bar
    draw_scale_bar(c, PAGE_WIDTH - MARGIN - (2 * inch), PAGE_HEIGHT - 50)
    
    # Legend
    legend_x = MARGIN
    legend_y = PAGE_HEIGHT - 80
    c.setFont("Helvetica-Bold", 10)
    c.drawString(legend_x, legend_y, "LEGEND:")
    c.setFont("Helvetica", 9)
    
    # Storm
    c.setStrokeColor(HexColor('#0066CC'))
    c.setLineWidth(3)
    c.line(legend_x, legend_y - 20, legend_x + 30, legend_y - 20)
    c.setFillColor(HexColor('#000000'))
    c.drawString(legend_x + 35, legend_y - 23, "SD = Storm Drain")
    
    # Sanitary
    c.setStrokeColor(HexColor('#CC0000'))
    c.setLineWidth(3)
    c.line(legend_x, legend_y - 40, legend_x + 30, legend_y - 40)
    c.setFillColor(HexColor('#000000'))
    c.drawString(legend_x + 35, legend_y - 43, "SS = Sanitary Sewer")
    
    # Water
    c.setStrokeColor(HexColor('#00AA00'))
    c.setLineWidth(3)
    c.line(legend_x, legend_y - 60, legend_x + 30, legend_y - 60)
    c.setFillColor(HexColor('#000000'))
    c.drawString(legend_x + 35, legend_y - 63, "WM = Water Main")
    
    # --- STORM PIPES (Blue) ---
    # Pipe 1: Horizontal run
    draw_pipe_with_labels(c, 50, 100, 200, 100, ie_in=95.5, ie_out=94.8, dia_in=12, material="PVC", color='#0066CC', discipline="storm")
    
    # Pipe 2: Diagonal run
    draw_pipe_with_labels(c, 200, 100, 280, 150, ie_in=94.8, ie_out=93.5, dia_in=12, material="PVC", color='#0066CC', discipline="storm")
    
    # Pipe 3: Vertical-ish run
    draw_pipe_with_labels(c, 100, 50, 100, 130, ie_in=96.2, ie_out=95.0, dia_in=15, material="CONCRETE", color='#0066CC', discipline="storm")
    
    # Pipe 4: Another horizontal
    draw_pipe_with_labels(c, 300, 80, 450, 80, ie_in=93.0, ie_out=91.5, dia_in=18, material="HDPE", color='#0066CC', discipline="storm")
    
    # --- SANITARY PIPES (Red) ---
    # Pipe 5: Parallel to storm
    draw_pipe_with_labels(c, 50, 80, 200, 80, ie_in=92.5, ie_out=91.2, dia_in=8, material="PVC", color='#CC0000', discipline="sanitary")
    
    # Pipe 6: Connecting run
    draw_pipe_with_labels(c, 200, 80, 280, 60, ie_in=91.2, ie_out=89.8, dia_in=8, material="PVC", color='#CC0000', discipline="sanitary")
    
    # Pipe 7: Branch
    draw_pipe_with_labels(c, 150, 80, 150, 50, ie_in=91.8, ie_out=91.0, dia_in=6, material="PVC", color='#CC0000', discipline="sanitary")
    
    # --- WATER PIPES (Green) ---
    # Pipe 8: Main line
    draw_pipe_with_labels(c, 50, 120, 250, 120, ie_in=88.5, ie_out=88.0, dia_in=6, material="DI", color='#00AA00', discipline="water")
    
    # Pipe 9: Service lateral
    draw_pipe_with_labels(c, 150, 120, 150, 140, ie_in=88.3, ie_out=88.1, dia_in=4, material="COPPER", color='#00AA00', discipline="water")
    
    # Pipe 10: Another main segment
    draw_pipe_with_labels(c, 250, 120, 380, 115, ie_in=88.0, ie_out=87.2, dia_in=8, material="DI", color='#00AA00', discipline="water")
    
    # --- PIPE WITHOUT ELEVATIONS (for testing DEPTH_UNAVAILABLE) ---
    # Pipe 11: No IE labels
    draw_pipe(c, 400, 50, 500, 70, '#0066CC', width=2)
    draw_label(c, 450, 65, '12" PVC', size=8)
    draw_label(c, 480, 55, '(NO IE LABELS)', size=6)
    
    # Add layer labels
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor('#666666'))
    c.drawString(legend_x + 300, legend_y - 20, "Layer: STORM SEWER")
    c.drawString(legend_x + 300, legend_y - 40, "Layer: SANITARY SEWER")
    c.drawString(legend_x + 300, legend_y - 60, "Layer: WATER MAIN")
    
    # Border
    c.setStrokeColor(HexColor('#000000'))
    c.setLineWidth(1)
    c.rect(DRAWING_LEFT, DRAWING_BOTTOM, DRAWING_WIDTH, DRAWING_HEIGHT)
    
    # Notes
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#666666'))
    notes_x = MARGIN
    notes_y = MARGIN - 15
    c.drawString(notes_x, notes_y, "NOTE: This is a test PDF with vector geometry, invert elevations (IE), and proper scale.")
    c.drawString(notes_x, notes_y - 12, "      Designed to test EstimAI elevation extraction and depth calculation.")
    
    c.save()
    print(f"✅ Generated test PDF: {output_path}")
    print(f"   Page size: {PAGE_WIDTH/inch:.1f}\" x {PAGE_HEIGHT/inch:.1f}\"")
    print(f"   Scale: {SCALE_TEXT} ({FEET_PER_INCH} ft/in)")
    print(f"   Pipes: 11 total (4 storm, 3 sanitary, 3 water, 1 without elevations)")
    print(f"   Features: Vector geometry, IE labels, layer names, legend, scale bar")


if __name__ == "__main__":
    generate_test_pdf()

