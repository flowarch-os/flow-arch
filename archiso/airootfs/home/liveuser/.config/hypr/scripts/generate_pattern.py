"""
generates svg patterns for wallpapers.
available patterns: hex, circles, triangles, waves, lines, grid, cross, dots, diamond.
"""

import sys
import random
import math

def create_hex_grid(width, height, bg_color, fg_color):
    """generates a honeycomb/hexagonal grid pattern."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    hex_radius = 40
    dx = hex_radius * 3/2
    dy = hex_radius * math.sqrt(3)
    
    cols = int(width / dx) + 2
    rows = int(height / dy) + 2
    
    for row in range(rows):
        for col in range(cols):
            x = col * dx
            y = row * dy
            if col % 2 == 1:
                y += dy / 2
                
            opacity = random.uniform(0.1, 0.4)
            points = []
            for i in range(6):
                angle_deg = 60 * i
                angle_rad = math.pi / 180 * angle_deg
                px = x + hex_radius * math.cos(angle_rad)
                py = y + hex_radius * math.sin(angle_rad)
                points.append(f"{px},{py}")
            
            svg += f'<polygon points="{" ".join(points)}" fill="none" stroke="{fg_color}" stroke-width="2" stroke-opacity="{opacity}"/>'
            
    svg += '</svg>'
    return svg

def create_circles(width, height, bg_color, fg_color):
    """generates random overlapping circles."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    for _ in range(50):
        cx = random.randint(0, width)
        cy = random.randint(0, height)
        r = random.randint(20, 200)
        opacity = random.uniform(0.05, 0.2)
        stroke_w = random.randint(1, 5)
        
        svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{fg_color}" stroke-width="{stroke_w}" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_triangles(width, height, bg_color, fg_color):
    """generates a grid of random triangles."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    cell_size = 80
    cols = int(width / cell_size) + 2
    rows = int(height / cell_size) + 2

    for r in range(rows):
        for c in range(cols):
            x = c * cell_size
            y = r * cell_size
            
            opacity1 = random.uniform(0.1, 0.3)
            opacity2 = random.uniform(0.1, 0.3)
            
            if random.choice([True, False]):
                svg += f'<polygon points="{x},{y+cell_size} {x+cell_size},{y} {x},{y}" fill="{fg_color}" fill-opacity="{opacity1}"/>'
                svg += f'<polygon points="{x},{y+cell_size} {x+cell_size},{y} {x+cell_size},{y+cell_size}" fill="{fg_color}" fill-opacity="{opacity2}"/>'
            else:
                svg += f'<polygon points="{x},{y} {x+cell_size},{y} {x+cell_size},{y+cell_size}" fill="{fg_color}" fill-opacity="{opacity1}"/>'
                svg += f'<polygon points="{x},{y} {x},{y+cell_size} {x+cell_size},{y+cell_size}" fill="{fg_color}" fill-opacity="{opacity2}"/>'

    svg += '</svg>'
    return svg

def create_waves(width, height, bg_color, fg_color):
    """generates flowing sine-like waves."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    num_lines = 20
    step_y = height / num_lines
    
    for i in range(num_lines + 5):
        y_base = i * step_y
        path_d = f"M 0 {y_base}"
        
        for x in range(0, width + 100, 100):
            y_offset = random.randint(-40, 40)
            path_d += f" Q {x+50} {y_base + y_offset} {x+100} {y_base}"
            
        opacity = random.uniform(0.1, 0.4)
        svg += f'<path d="{path_d}" fill="none" stroke="{fg_color}" stroke-width="3" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_lines(width, height, bg_color, fg_color):
    """generates diagonal lines."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    step = 40
    # draw more lines to cover rotation
    for i in range(-height, width + height, step):
        opacity = random.uniform(0.1, 0.3)
        svg += f'<line x1="{i}" y1="0" x2="{i+height}" y2="{height}" stroke="{fg_color}" stroke-width="2" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_grid(width, height, bg_color, fg_color):
    """generates a standard square grid."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    step = 50
    for x in range(0, width + step, step):
        opacity = random.uniform(0.05, 0.2)
        svg += f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{fg_color}" stroke-width="1" stroke-opacity="{opacity}"/>'
        
    for y in range(0, height + step, step):
        opacity = random.uniform(0.05, 0.2)
        svg += f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{fg_color}" stroke-width="1" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_cross(width, height, bg_color, fg_color):
    """generates a pattern of plus signs."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    step = 60
    size = 10
    for y in range(0, height, step):
        for x in range(0, width, step):
            opacity = random.uniform(0.1, 0.4)
            # horizontal part
            svg += f'<line x1="{x-size}" y1="{y}" x2="{x+size}" y2="{y}" stroke="{fg_color}" stroke-width="3" stroke-opacity="{opacity}"/>'
            # vertical part
            svg += f'<line x1="{x}" y1="{y-size}" x2="{x}" y2="{y+size}" stroke="{fg_color}" stroke-width="3" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_dots(width, height, bg_color, fg_color):
    """generates a simple grid of dots."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    step = 40
    for y in range(0, height, step):
        for x in range(0, width, step):
            r = random.randint(2, 6)
            opacity = random.uniform(0.2, 0.6)
            svg += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fg_color}" fill-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

def create_diamond(width, height, bg_color, fg_color):
    """generates a diamond grid pattern."""
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="100%" height="100%" fill="{bg_color}"/>'
    
    w = 60
    h = 100
    cols = int(width / w) + 2
    rows = int(height / h) + 2
    
    for r in range(rows):
        for c in range(cols):
            cx = c * w
            cy = r * h
            if r % 2 == 1:
                cx += w / 2
            
            opacity = random.uniform(0.1, 0.3)
            # diamond shape using polygon
            pts = f"{cx},{cy-h/2} {cx+w/2},{cy} {cx},{cy+h/2} {cx-w/2},{cy}"
            svg += f'<polygon points="{pts}" fill="none" stroke="{fg_color}" stroke-width="2" stroke-opacity="{opacity}"/>'

    svg += '</svg>'
    return svg

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python3 generate_pattern.py <pattern> <bg_hex> <fg_hex> <output_file>")
        print("patterns: hex, circles, triangles, waves, lines, grid, cross, dots, diamond")
        sys.exit(1)

    pattern = sys.argv[1]
    bg_color = sys.argv[2]
    fg_color = sys.argv[3]
    output_file = sys.argv[4]
    
    width = 1920
    height = 1080

    if not bg_color.startswith('#'): bg_color = '#' + bg_color
    if not fg_color.startswith('#'): fg_color = '#' + fg_color

    content = ""
    if pattern == "hex":
        content = create_hex_grid(width, height, bg_color, fg_color)
    elif pattern == "circles":
        content = create_circles(width, height, bg_color, fg_color)
    elif pattern == "triangles":
        content = create_triangles(width, height, bg_color, fg_color)
    elif pattern == "waves":
        content = create_waves(width, height, bg_color, fg_color)
    elif pattern == "lines":
        content = create_lines(width, height, bg_color, fg_color)
    elif pattern == "grid":
        content = create_grid(width, height, bg_color, fg_color)
    elif pattern == "cross":
        content = create_cross(width, height, bg_color, fg_color)
    elif pattern == "dots":
        content = create_dots(width, height, bg_color, fg_color)
    elif pattern == "diamond":
        content = create_diamond(width, height, bg_color, fg_color)
    else:
        print(f"error: unknown pattern '{pattern}'")
        sys.exit(1)

    with open(output_file, "w") as f:
        f.write(content)
