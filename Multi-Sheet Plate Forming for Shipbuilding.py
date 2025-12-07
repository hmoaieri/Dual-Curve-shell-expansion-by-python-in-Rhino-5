# -*- coding: utf-8 -*-
"""
SURFACE DEVELOPMENT AND SHEET DIVISION
Develops (squishes) target surface, divides into 6x2m sheets, maps back
Author: Your Name
Date: 2024
"""

import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import System
import math
import clr
clr.AddReference('RhinoCommon')
clr.AddReference('System.Drawing')

# ============================================================================
# SURFACE DEVELOPMENT AND DIVISION
# ============================================================================

class SurfaceDeveloper:
    """Develop surface by squishing and divide into 6x2m sheets"""
    
    def __init__(self):
        self.sheet_width = 6.0  # meters
        self.sheet_height = 2.0  # meters
        self.weld_allowance = 0.01  # 10mm
        self.param_mapping = None
        self.development_lines = []
        
    def develop_surface(self, surface_obj):
        """Main function: Develop surface by squishing"""
        try:
            print("\n" + "="*60)
            print("SURFACE DEVELOPMENT PROCESS")
            print("="*60)
            
            if not surface_obj:
                print("ERROR: No surface object")
                return None
            
            # Step 1: Get surface properties
            surface_info = self.get_surface_info(surface_obj)
            if not surface_info:
                return None
            
            print("Surface analysis:")
            print("  Area: {self.format_number(surface_info['area'], 1)} m²")
            print("  Bounds: {self.format_number(surface_info['width'], 1)} x {self.format_number(surface_info['height'], 1)} m")
            print("  Developable: {surface_info['is_developable']}")
            
            # Step 2: Develop surface using UV parameterization
            print("\nDeveloping surface (squishing 3D → 2D)...")
            developed_surface = self.develop_by_uv_parameterization(surface_obj)
            
            if not developed_surface:
                print("ERROR: Could not develop surface")
                return None
            
            # Step 3: Divide developed surface into 6x2m sheets
            print("\nDividing developed surface into sheets...")
            division_result = self.divide_developed_surface(developed_surface)
            if not division_result:
                return None
            
            # Step 4: Map division lines back to original surface
            print("\nMapping division lines to target surface...")
            mapping_result = self.map_divisions_to_target(
                surface_obj, 
                developed_surface, 
                division_result
            )
            
            if not mapping_result:
                print("ERROR: Could not map divisions")
                return None
            
            # Step 5: Create final result
            result = {
                'original_surface': surface_obj,
                'developed_surface': developed_surface,
                'division_data': division_result,
                'mapped_divisions': mapping_result,
                'surface_info': surface_info,
                'sheets_required': division_result['sheets_required']
            }
            
            print("\n" + "="*60)
            print("DEVELOPMENT COMPLETE!")
            print("Sheets required: {division_result['sheets_required']}")
            print("Division lines created on target surface.")
            print("="*60)
            
            return result
            
        except Exception as e:
            print("ERROR in development process: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_surface_info(self, surface_obj):
        """Get information about the surface"""
        try:
            # Get surface geometry
            brep = rs.coercebrep(surface_obj)
            if not brep or brep.Faces.Count == 0:
                return None
            
            face = brep.Faces[0]
            
            # Check if surface is developable
            is_developable = False
            try:
                is_developable = face.IsDevelopable
            except:
                pass
            
            # Get area
            area = 0
            area_result = brep.GetArea()
            if area_result:
                if isinstance(area_result, tuple) and len(area_result) > 1:
                    if area_result[0]:
                        area = area_result[1]
                elif isinstance(area_result, (int, float)):
                    area = area_result
            
            # Get bounding box
            bbox = brep.GetBoundingBox(True)
            width = bbox.Max.X - bbox.Min.X
            height = bbox.Max.Y - bbox.Min.Y
            length = bbox.Max.Z - bbox.Min.Z
            
            return {
                'type': "Brep Face",
                'is_developable': is_developable,
                'area': area,
                'width': width,
                'height': height,
                'length': length,
                'bounding_box': bbox
            }
            
        except Exception as e:
            print("ERROR getting surface info: {e}")
            return None
    
    def develop_by_uv_parameterization(self, surface_obj):
        """Develop surface using UV parameterization to 2D plane"""
        try:
            print("  Using UV parameterization to develop surface...")
            
            # Get surface ID
            surface_id = surface_obj
            
            # If it's a polysurface, explode and use first face
            if rs.IsPolysurface(surface_id):
                surfaces = rs.ExplodePolysurfaces(surface_id)
                if surfaces:
                    surface_id = surfaces[0]
                    for s in surfaces[1:]:
                        rs.DeleteObject(s)
            
            # Get surface domains
            domain_u = rs.SurfaceDomain(surface_id, 0)
            domain_v = rs.SurfaceDomain(surface_id, 1)
            
            if not domain_u or not domain_v:
                print("  ERROR: Could not get surface domains")
                return self.create_bounding_box_development(surface_obj)
            
            u_min, u_max = domain_u
            v_min, v_max = domain_v
            
            # Create grid of UV points
            u_steps = 20
            v_steps = 20
            
            points_3d = []
            points_2d = []
            uv_pairs = []
            
            # Sample points from surface
            for i in range(u_steps):
                u = u_min + (u_max - u_min) * i / (u_steps - 1)
                for j in range(v_steps):
                    v = v_min + (v_max - v_min) * j / (v_steps - 1)
                    
                    # Get 3D point on original surface
                    point_3d = rs.EvaluateSurface(surface_id, u, v)
                    if point_3d:
                        points_3d.append(point_3d)
                        
                        # Map UV to 2D coordinates
                        # Scale to approximate real-world dimensions
                        scale_factor = 10.0  # Adjust based on surface size
                        x = (u - u_min) / (u_max - u_min) * scale_factor
                        y = (v - v_min) / (v_max - v_min) * scale_factor
                        
                        point_2d = (x, y, 0)
                        points_2d.append(point_2d)
                        uv_pairs.append((u, v, point_3d, point_2d))
            
            # Create mesh from 2D points
            mesh_faces = []
            for i in range(u_steps - 1):
                for j in range(v_steps - 1):
                    idx1 = i * v_steps + j
                    idx2 = i * v_steps + (j + 1)
                    idx3 = (i + 1) * v_steps + (j + 1)
                    idx4 = (i + 1) * v_steps + j
                    mesh_faces.append((idx1, idx2, idx3, idx4))
            
            developed_mesh = rs.AddMesh(points_2d, mesh_faces)
            
            if developed_mesh:
                # Store mapping for later use
                self.param_mapping = {
                    'surface_id': surface_id,
                    'points_3d': points_3d,
                    'points_2d': points_2d,
                    'uv_pairs': uv_pairs,
                    'domain_u': (u_min, u_max),
                    'domain_v': (v_min, v_max),
                    'u_steps': u_steps,
                    'v_steps': v_steps
                }
                
                # Create development lines (optional visualization)
                self.create_development_lines(points_3d, points_2d)
                
                print("  Developed surface with {len(points_3d)} sample points")
                return developed_mesh
            
            return self.create_bounding_box_development(surface_obj)
            
        except Exception as e:
            print("  ERROR in UV development: {e}")
            return self.create_bounding_box_development(surface_obj)
    
    def create_bounding_box_development(self, surface_obj):
        """Create development based on bounding box"""
        try:
            print("  Creating bounding box development...")
            
            bbox = rs.BoundingBox(surface_obj)
            if not bbox or len(bbox) < 8:
                return None
            
            min_pt = bbox[0]
            max_pt = bbox[6]
            
            # Use XY dimensions
            width = max_pt.X - min_pt.X
            height = max_pt.Y - min_pt.Y
            
            # Create flat rectangle
            points = [
                (min_pt.X, min_pt.Y, 0),
                (min_pt.X + width, min_pt.Y, 0),
                (min_pt.X + width, min_pt.Y + height, 0),
                (min_pt.X, min_pt.Y + height, 0)
            ]
            
            flat_surface = rs.AddSrfPt(points)
            if flat_surface:
                print("  Created bounding box development")
                return flat_surface
            
            return None
            
        except Exception as e:
            print("  ERROR in bounding box development: {e}")
            return None
    
    def create_development_lines(self, points_3d, points_2d):
        """Create lines showing development mapping"""
        try:
            # Offset 2D points for visibility
            offset_y = -8
            points_2d_offset = [(p[0], p[1] + offset_y, p[2]) for p in points_2d]
            
            # Create connection lines
            for i in range(0, len(points_3d), 5):  # Sample every 5th point
                if i < len(points_2d_offset):
                    line = rs.AddLine(points_3d[i], points_2d_offset[i])
                    if line:
                        self.development_lines.append(line)
            
            # Add development plane
            if points_2d_offset:
                # Create a plane at average height
                avg_z = sum(p[2] for p in points_2d_offset) / len(points_2d_offset)
                plane_pts = [
                    (-5, offset_y - 5, avg_z),
                    (15, offset_y - 5, avg_z),
                    (15, offset_y + 5, avg_z),
                    (-5, offset_y + 5, avg_z)
                ]
                dev_plane = rs.AddSrfPt(plane_pts)
                if dev_plane:
                    rs.ObjectColor(dev_plane, (150, 150, 200))
                    rs.ObjectLayer(dev_plane, "DEV_DEVELOPMENT_PLANE")
            
            return True
            
        except Exception as e:
            print("  ERROR creating development lines: {e}")
            return False
    
    def divide_developed_surface(self, developed_surface):
        """Divide developed surface into 6x2m sheets"""
        try:
            # Get bounding box of developed surface
            bbox = rs.BoundingBox(developed_surface)
            if not bbox or len(bbox) < 8:
                return None
            
            min_x = bbox[0].X
            min_y = bbox[0].Y
            max_x = bbox[6].X
            max_y = bbox[6].Y
            
            width = max_x - min_x
            height = max_y - min_y
            
            print("  Developed surface: {self.format_number(width, 1)} x {self.format_number(height, 1)} m")
            
            # Calculate sheet layout with weld allowance
            usable_w = self.sheet_width - self.weld_allowance
            usable_h = self.sheet_height - self.weld_allowance
            
            sheets_x = int(math.ceil(width / usable_w))
            sheets_y = int(math.ceil(height / usable_h))
            total_sheets = sheets_x * sheets_y
            
            print("  Sheet layout: {sheets_x} x {sheets_y}")
            print("  Total sheets: {total_sheets}")
            
            # Create division lines
            division_lines = []
            sheet_rectangles = []
            
            # Vertical division lines
            for i in range(1, sheets_x):
                x = min_x + i * usable_w
                line_start = (x, min_y, 0)
                line_end = (x, max_y, 0)
                line = rs.AddLine(line_start, line_end)
                if line:
                    division_lines.append({
                        'type': 'vertical',
                        'index': i,
                        'line_id': line,
                        'flat_coords': (line_start, line_end)
                    })
            
            # Horizontal division lines
            for j in range(1, sheets_y):
                y = min_y + j * usable_h
                line_start = (min_x, y, 0)
                line_end = (max_x, y, 0)
                line = rs.AddLine(line_start, line_end)
                if line:
                    division_lines.append({
                        'type': 'horizontal',
                        'index': j,
                        'line_id': line,
                        'flat_coords': (line_start, line_end)
                    })
            
            # Create sheet rectangles
            sheet_count = 0
            for i in range(sheets_x):
                for j in range(sheets_y):
                    sheet_count += 1
                    
                    x1 = min_x + i * usable_w
                    x2 = min(x1 + self.sheet_width, max_x)
                    y1 = min_y + j * usable_h
                    y2 = min(y1 + self.sheet_height, max_y)
                    
                    # Create rectangle
                    points = [
                        (x1, y1, 0),
                        (x2, y1, 0),
                        (x2, y2, 0),
                        (x1, y2, 0),
                        (x1, y1, 0)
                    ]
                    
                    rectangle = rs.AddPolyline(points)
                    if rectangle:
                        sheet_rectangles.append({
                            'sheet_number': sheet_count,
                            'grid_position': (i, j),
                            'rectangle_id': rectangle,
                            'bounds': (x1, y1, x2, y2),
                            'width': x2 - x1,
                            'height': y2 - y1,
                            'area': (x2 - x1) * (y2 - y1)
                        })
            
            return {
                'developed_surface': developed_surface,
                'division_lines': division_lines,
                'sheet_rectangles': sheet_rectangles,
                'sheets_required': total_sheets,
                'layout': (sheets_x, sheets_y),
                'bounds': (min_x, min_y, max_x, max_y)
            }
            
        except Exception as e:
            print("ERROR dividing developed surface: {e}")
            return None
    
    def map_divisions_to_target(self, target_surface, developed_surface, division_data):
        """Map division lines from developed surface to target surface"""
        try:
            print("  Mapping division lines to target...")
            
            mapped_lines = []
            mapped_sheets = []
            
            # Map division lines
            for division in division_data['division_lines']:
                flat_coords = division['flat_coords']
                
                # Map start and end points
                start_mapped = self.map_flat_to_target(flat_coords[0], target_surface)
                end_mapped = self.map_flat_to_target(flat_coords[1], target_surface)
                
                if start_mapped and end_mapped:
                    # Create curve on target surface
                    target_line = rs.AddLine(start_mapped, end_mapped)
                    if target_line:
                        mapped_lines.append({
                            'type': division['type'],
                            'index': division['index'],
                            'target_line_id': target_line,
                            'start_point': start_mapped,
                            'end_point': end_mapped
                        })
            
            # Map sheet boundaries
            for sheet in division_data['sheet_rectangles']:
                bounds = sheet['bounds']
                corners = [
                    (bounds[0], bounds[1], 0),  # Bottom-left
                    (bounds[2], bounds[1], 0),  # Bottom-right
                    (bounds[2], bounds[3], 0),  # Top-right
                    (bounds[0], bounds[3], 0)   # Top-left
                ]
                
                # Map all corners
                mapped_corners = []
                all_mapped = True
                
                for corner in corners:
                    mapped_point = self.map_flat_to_target(corner, target_surface)
                    if mapped_point:
                        mapped_corners.append(mapped_point)
                    else:
                        all_mapped = False
                        break
                
                if all_mapped and len(mapped_corners) == 4:
                    # Close the loop
                    mapped_corners.append(mapped_corners[0])
                    
                    # Create boundary curve on target
                    boundary = rs.AddPolyline(mapped_corners)
                    if boundary:
                        mapped_sheets.append({
                            'sheet_number': sheet['sheet_number'],
                            'boundary_id': boundary,
                            'corners': mapped_corners[:-1]
                        })
            
            print("  Mapped {len(mapped_lines)} division lines and {len(mapped_sheets)} sheet boundaries")
            
            return {
                'mapped_lines': mapped_lines,
                'mapped_sheets': mapped_sheets,
                'total_mapped': len(mapped_lines)
            }
            
        except Exception as e:
            print("ERROR mapping divisions: {e}")
            return None
    
    def map_flat_to_target(self, flat_point, target_surface):
        """Map point from flat development to target surface"""
        try:
            # If we have UV mapping, use it
            if self.param_mapping and 'uv_pairs' in self.param_mapping:
                # Find closest point in our 2D grid
                min_dist = float('inf')
                closest_uv = None
                
                for u, v, point_3d, point_2d in self.param_mapping['uv_pairs']:
                    dist = math.sqrt(
                        (point_2d[0] - flat_point[0])**2 +
                        (point_2d[1] - flat_point[1])**2
                    )
                    
                    if dist < min_dist:
                        min_dist = dist
                        closest_uv = (u, v)
                
                if closest_uv:
                    # Evaluate at the UV coordinates
                    target_point = rs.EvaluateSurface(target_surface, closest_uv[0], closest_uv[1])
                    return target_point
            
            # Fallback: Use closest point projection
            success, uv = rs.SurfaceClosestPoint(target_surface, flat_point)
            if success:
                return rs.EvaluateSurface(target_surface, uv[0], uv[1])
            
            return None
            
        except Exception as e:
            print("  WARNING in point mapping: {e}")
            return None
    
    def format_number(self, value, decimals=2):
        """Format number for display"""
        try:
            if value is None:
                return "0"
            if isinstance(value, int):
                return str(value)
            elif isinstance(value, float):
                return "{value:.{decimals}f}"
            else:
                return str(value)
        except:
            return str(value)

# ============================================================================
# VISUALIZATION AND DISPLAY
# ============================================================================

class DivisionVisualizer:
    """Visualize development and division results"""
    
    def __init__(self):
        self.layer_colors = {
            "01_ORIGINAL_SURFACE": (0, 200, 0),      # Green
            "02_DEVELOPED_SURFACE": (200, 200, 100), # Yellow
            "03_DEV_LINES": (200, 150, 100),        # Orange
            "04_DIVISION_LINES": (255, 100, 0),     # Bright orange
            "05_SHEET_BOUNDARIES": (0, 255, 0),     # Green
            "06_INFO": (200, 200, 200),             # Gray
            "07_DEVELOPMENT_PLANE": (150, 150, 200) # Light blue
        }
    
    def visualize_development(self, result):
        """Create comprehensive visualization"""
        try:
            if not result:
                return False
            
            # Setup layers
            self.setup_layers()
            
            # Original surface
            rs.CurrentLayer("01_ORIGINAL_SURFACE")
            original = result['original_surface']
            rs.ObjectLayer(original, "01_ORIGINAL_SURFACE")
            rs.ObjectColor(original, self.layer_colors["01_ORIGINAL_SURFACE"])
            
            # Developed surface (offset for clarity)
            rs.CurrentLayer("02_DEVELOPED_SURFACE")
            developed = result['developed_surface']
            rs.MoveObject(developed, (0, -10, 0))  # Offset downward
            rs.ObjectLayer(developed, "02_DEVELOPED_SURFACE")
            rs.ObjectColor(developed, self.layer_colors["02_DEVELOPED_SURFACE"])
            
            # Development lines (if any)
            rs.CurrentLayer("03_DEV_LINES")
            
            # Division lines on developed surface
            rs.CurrentLayer("04_DIVISION_LINES")
            division_data = result['division_data']
            
            for division in division_data['division_lines']:
                line_id = division['line_id']
                rs.ObjectLayer(line_id, "04_DIVISION_LINES")
                rs.ObjectColor(line_id, self.layer_colors["04_DIVISION_LINES"])
                rs.ObjectName(line_id, "{division['type']}_line_{division['index']}")
            
            # Sheet rectangles on developed surface
            for sheet in division_data['sheet_rectangles']:
                rect_id = sheet['rectangle_id']
                rs.ObjectLayer(rect_id, "04_DIVISION_LINES")
                rs.ObjectColor(rect_id, (100, 200, 255, 100))  # Semi-transparent blue
            
            # Mapped sheet boundaries on target surface
            rs.CurrentLayer("05_SHEET_BOUNDARIES")
            mapped_data = result['mapped_divisions']
            
            for sheet in mapped_data['mapped_sheets']:
                boundary_id = sheet['boundary_id']
                rs.ObjectLayer(boundary_id, "05_SHEET_BOUNDARIES")
                rs.ObjectColor(boundary_id, self.layer_colors["05_SHEET_BOUNDARIES"])
                
                # Make boundaries thicker
                obj = sc.doc.Objects.Find(boundary_id)
                if obj:
                    obj.Attributes.PlotWeight = 2.0
                    obj.CommitChanges()
                
                # Add sheet number
                corners = sheet['corners']
                if corners and len(corners) >= 4:
                    center = self.calculate_center(corners)
                    text = str(sheet['sheet_number'])
                    text_id = rs.AddText(text, center, 0.8)
                    if text_id:
                        rs.ObjectLayer(text_id, "05_SHEET_BOUNDARIES")
                        rs.ObjectColor(text_id, (255, 255, 0))  # Yellow
            
            # Mapped division lines on target surface
            for line in mapped_data['mapped_lines']:
                line_id = line['target_line_id']
                rs.ObjectLayer(line_id, "05_SHEET_BOUNDARIES")
                
                # Color by type
                if line['type'] == 'vertical':
                    rs.ObjectColor(line_id, (255, 0, 0))  # Red
                else:
                    rs.ObjectColor(line_id, (0, 0, 255))  # Blue
                
                # Make lines thick
                obj = sc.doc.Objects.Find(line_id)
                if obj:
                    obj.Attributes.PlotWeight = 1.5
                    obj.CommitChanges()
            
            # Add information
            self.add_information(result)
            
            # Zoom to extent
            rs.ZoomExtents()
            
            return True
            
        except Exception as e:
            print("ERROR in visualization: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def setup_layers(self):
        """Create and setup visualization layers"""
        for layer_name, color in self.layer_colors.items():
            if not rs.IsLayer(layer_name):
                rs.AddLayer(layer_name, color)
    
    def calculate_center(self, points):
        """Calculate center point of polygon"""
        if not points:
            return (0, 0, 0)
        
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_z = sum(p[2] for p in points)
        
        count = len(points)
        return (sum_x/count, sum_y/count, sum_z/count)
    
    def add_information(self, result):
        """Add information text to scene"""
        try:
            rs.CurrentLayer("06_INFO")
            
            # Get surface info
            surface_info = result['surface_info']
            division_data = result['division_data']
            mapped_data = result['mapped_divisions']
            
            # Create text block
            text_lines = []
            text_lines.append("="*40)
            text_lines.append("SURFACE DEVELOPMENT & DIVISION")
            text_lines.append("="*40)
            text_lines.append("")
            text_lines.append("ORIGINAL SURFACE:")
            text_lines.append("  Area: {surface_info['area']:.1f} m²")
            text_lines.append("  Size: {surface_info['width']:.1f} x {surface_info['height']:.1f} m")
            text_lines.append("")
            text_lines.append("SHEET DIVISION (6x2m):")
            text_lines.append("  Sheets: {division_data['sheets_required']}")
            text_lines.append("  Layout: {division_data['layout'][0]} x {division_data['layout'][1]}")
            text_lines.append("")
            text_lines.append("DEVELOPMENT PROCESS:")
            text_lines.append("  Method: UV Parameterization")
            text_lines.append("  Points sampled: 20x20 grid")
            text_lines.append("")
            text_lines.append("VISUALIZATION:")
            text_lines.append("  Green: Original surface")
            text_lines.append("  Yellow: Developed (squished) surface")
            text_lines.append("  Orange: Division lines (developed)")
            text_lines.append("  Bright Green: Sheet boundaries (target)")
            text_lines.append("  Red/Blue: Division lines (target)")
            
            # Position text
            bbox = rs.BoundingBox(result['original_surface'])
            if bbox and len(bbox) >= 8:
                text_point = (bbox[0].X, bbox[0].Y - 5, bbox[0].Z)
                
                for i, line in enumerate(text_lines):
                    line_point = (
                        text_point[0],
                        text_point[1] - (i * 1.2),
                        text_point[2]
                    )
                    rs.AddText(line, line_point, 0.6)
            
        except Exception as e:
            print("ERROR adding information: {e}")
    
    def clear_visualization(self):
        """Clear all visualization objects"""
        try:
            for layer_name in self.layer_colors.keys():
                if rs.IsLayer(layer_name):
                    objects = rs.ObjectsByLayer(layer_name)
                    if objects:
                        rs.DeleteObjects(objects)
            
            # Also clear any objects in default layer
            default_objects = rs.ObjectsByLayer("Default")
            if default_objects:
                for obj in default_objects:
                    if rs.ObjectName(obj) and "division" in rs.ObjectName(obj).lower():
                        rs.DeleteObject(obj)
            
            return True
            
        except Exception as e:
            print("ERROR clearing visualization: {e}")
            return False

# ============================================================================
# MAIN INTERFACE
# ============================================================================

def main():
    """Main interface for surface development and division"""
    
    developer = SurfaceDeveloper()
    visualizer = DivisionVisualizer()
    current_result = None
    
    while True:
        options = [
            "1. SELECT Surface",
            "2. DEVELOP & DIVIDE", 
            "3. VISUALIZE Results",
            "4. CREATE Example",
            "5. SHOW Report",
            "6. CLEAR All",
            "7. EXIT"
        ]
        
        choice = rs.ListBox(options, "SURFACE DEVELOPMENT SYSTEM", "Select Operation:")
        
        if not choice or choice == "7. EXIT":
            break
        
        # Option 1: Select surface
        elif choice == "1. SELECT Surface":
            try:
                obj = rs.GetObject("Select surface to develop and divide", 
                                 rs.filter.surface | rs.filter.polysurface)
                if obj:
                    info = developer.get_surface_info(obj)
                    if info:
                        msg = "SURFACE SELECTED\n\n"
                        msg += "Area: {info['area']:.1f} m²\n"
                        msg += "Size: {info['width']:.1f} x {info['height']:.1f} m\n\n"
                        
                        if info['is_developable']:
                            msg += "✓ Surface is developable\n"
                            msg += "  (Can be accurately developed)"
                        else:
                            msg += "⚠ Surface is not developable\n"
                            msg += "  (Using approximation development)"
                        
                        rs.MessageBox(msg, 0, "Ready for Development")
                        
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
        
        # Option 2: Develop and divide
        elif choice == "2. DEVELOP & DIVIDE":
            try:
                obj = rs.GetObject("Select surface", 
                                 rs.filter.surface | rs.filter.polysurface,
                                 preselect=True)
                if not obj:
                    rs.MessageBox("Please select a surface first!", 0, "Error")
                    continue
                
                rs.EnableRedraw(False)
                rs.Prompt("Developing surface and dividing into 6x2m sheets...")
                
                current_result = developer.develop_surface(obj)
                
                if current_result:
                    sheets = current_result['sheets_required']
                    msg = "DEVELOPMENT COMPLETE!\n\n"
                    msg += "Sheets required: {sheets} (6x2m)\n"
                    msg += "Division boundaries created on target surface.\n\n"
                    msg += "Click 'VISUALIZE Results' to see the development."
                    
                    rs.MessageBox(msg, 0, "Success")
                else:
                    rs.MessageBox("Development failed.", 0, "Error")
                    
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        # Option 3: Visualize
        elif choice == "3. VISUALIZE Results":
            if not current_result:
                rs.MessageBox("Please develop a surface first!", 0, "Error")
                continue
            
            try:
                rs.EnableRedraw(False)
                success = visualizer.visualize_development(current_result)
                
                if success:
                    msg = "VISUALIZATION READY\n\n"
                    msg += "Check the layers:\n"
                    msg += "• Green: Original surface\n"
                    msg += "• Yellow: Developed surface (below)\n"
                    msg += "• Bright Green: Sheet boundaries\n"
                    msg += "• Red/Blue: Division lines\n\n"
                    msg += "Sheet numbers show individual 6x2m panels."
                    
                    rs.MessageBox(msg, 0, "Visualization Complete")
                else:
                    rs.MessageBox("Visualization failed.", 0, "Error")
                    
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        # Option 4: Create example
        elif choice == "4. CREATE Example":
            try:
                # Create a cylindrical surface
                radius = 3.0
                height = 8.0
                
                # Create cylinder base
                base_circle = rs.AddCircle((0, 0, 0), radius)
                top_circle = rs.AddCircle((0, 0, height), radius)
                
                # Create cylindrical surface
                cylinder = rs.AddLoftSrf([base_circle, top_circle])
                
                if cylinder:
                    rs.DeleteObject(base_circle)
                    rs.DeleteObject(top_circle)
                    
                    msg = "EXAMPLE SURFACE CREATED\n\n"
                    msg += "Type: Cylindrical surface\n"
                    msg += "Size: ~6m diameter x 8m height\n"
                    msg += "Perfect for development test.\n\n"
                    msg += "Now click 'DEVELOP & DIVIDE'"
                    
                    rs.MessageBox(msg, 0, "Example Ready")
                    
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
        
        # Option 5: Show report
        elif choice == "5. SHOW Report":
            if not current_result:
                rs.MessageBox("No results to report!", 0, "Error")
                continue
            
            try:
                surface_info = current_result['surface_info']
                division_data = current_result['division_data']
                mapped_data = current_result['mapped_divisions']
                
                report = "DEVELOPMENT REPORT\n"
                report += "="*40 + "\n\n"
                
                report += "SURFACE ANALYSIS:\n"
                report += "  Area: {surface_info['area']:.1f} m²\n"
                report += "  Dimensions: {surface_info['width']:.1f} x {surface_info['height']:.1f} m\n"
                report += "  Developable: {surface_info['is_developable']}\n\n"
                
                report += "SHEET DIVISION:\n"
                report += "  Sheet size: 6.0 x 2.0 m\n"
                report += "  Sheets required: {division_data['sheets_required']}\n"
                report += "  Layout: {division_data['layout'][0]} columns x {division_data['layout'][1]} rows\n"
                report += "  Weld allowance: {developer.weld_allowance*1000:.0f} mm\n\n"
                
                report += "DEVELOPMENT RESULTS:\n"
                report += "  Division lines created: {mapped_data['total_mapped']}\n"
                report += "  Sheet boundaries created: {len(mapped_data.get('mapped_sheets', []))}\n\n"
                
                report += "INSTRUCTIONS:\n"
                report += "1. Follow green boundaries on target surface\n"
                report += "2. Cut 6x2m sheets along division lines\n"
                report += "3. Form sheets to match surface curvature"
                
                rs.MessageBox(report, 0, "Development Report")
                
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
        
        # Option 6: Clear all
        elif choice == "6. CLEAR All":
            try:
                visualizer.clear_visualization()
                current_result = None
                rs.MessageBox("All visualization cleared.", 0, "Done")
                
            except Exception as e:
                rs.MessageBox("Error: {e}", 0, "Error")
    
    rs.MessageBox("Surface Development System completed.", 0, "Goodbye")

# ============================================================================
# START PROGRAM
# ============================================================================

if __name__ == "__main__":
    welcome = "SURFACE DEVELOPMENT SYSTEM\n"
    welcome += "="*40 + "\n\n"
    welcome += "Develops curved surfaces by 'squishing' them to 2D,\n"
    welcome += "then divides into 6x2m sheets for manufacturing.\n\n"
    welcome += "PROCESS:\n"
    welcome += "1. Samples surface with UV grid\n"
    welcome += "2. Maps 3D points to 2D plane (squish)\n"
    welcome += "3. Divides 2D plane into 6x2m grids\n"
    welcome += "4. Maps divisions back to 3D surface\n\n"
    welcome += "Green boundaries show where to cut sheets."
    
    rs.MessageBox(welcome, 0, "Welcome to Surface Development")
    
    main()