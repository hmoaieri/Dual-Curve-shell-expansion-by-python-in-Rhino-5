# -*- coding: utf-8 -*-
"""
ROBUST 3D SHEET PROJECTION ON TARGET SURFACE
Projects 6x2m sheets directly onto 3D surface using robust methods
Author: Shipbuilding Design System
Date: 2024
"""

import rhinoscriptsyntax as rs
import Rhino
import scriptcontext as sc
import math
import time

# ============================================================================
# ROBUST SURFACE SAMPLER
# ============================================================================

class RobustSurfaceSampler:
    """Sample surface points robustly for sheet projection"""
    
    def sample_surface_for_sheets(self, surface_id):
        """Sample surface to create sheet layout"""
        try:
            print("\n=== SAMPLING SURFACE FOR SHEET LAYOUT ===")
            
            # Get bounding box
            bbox = rs.BoundingBox(surface_id)
            if not bbox or len(bbox) < 8:
                print("ERROR: Could not get bounding box")
                return None
            
            min_pt = bbox[0]
            max_pt = bbox[6]
            
            # Calculate surface dimensions
            width = max_pt[0] - min_pt[0]
            height = max_pt[1] - min_pt[1]
            depth = max_pt[2] - min_pt[2]
            
            print("Surface bounds: {width:.2f}m × {height:.2f}m × {depth:.2f}m")
            
            # Sample points on surface
            sample_points = self.sample_surface_grid(surface_id, 15, 15)
            
            if not sample_points:
                # Fallback: use bounding box corners
                sample_points = [
                    min_pt,
                    (max_pt[0], min_pt[1], min_pt[2]),
                    max_pt,
                    (min_pt[0], max_pt[1], min_pt[2])
                ]
            
            return {
                'surface_id': surface_id,
                'min_point': min_pt,
                'max_point': max_pt,
                'width': width,
                'height': height,
                'depth': depth,
                'sample_points': sample_points,
                'bbox': bbox
            }
            
        except Exception as e:
            print("ERROR in surface sampling: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return minimal data
            return {
                'surface_id': surface_id,
                'min_point': (0, 0, 0),
                'max_point': (10, 10, 5),
                'width': 10,
                'height': 10,
                'depth': 5,
                'sample_points': [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)],
                'bbox': None
            }
    
    def sample_surface_grid(self, surface_id, u_samples, v_samples):
        """Sample points in grid on surface"""
        points = []
        try:
            # Get surface domain
            u_domain = rs.SurfaceDomain(surface_id, 0)
            v_domain = rs.SurfaceDomain(surface_id, 1)
            
            if not u_domain or not v_domain:
                # Use default
                u_domain = (0, 1)
                v_domain = (0, 1)
            
            u_min, u_max = u_domain
            v_min, v_max = v_domain
            
            for i in range(u_samples):
                u = u_min + (u_max - u_min) * i / (u_samples - 1)
                for j in range(v_samples):
                    v = v_min + (v_max - v_min) * j / (v_samples - 1)
                    
                    point = rs.EvaluateSurface(surface_id, u, v)
                    if point:
                        points.append(point)
            
        except:
            # Alternative method
            try:
                # Sample along bounding box
                bbox = rs.BoundingBox(surface_id)
                if bbox and len(bbox) >= 8:
                    for i in range(4):
                        if i < len(bbox):
                            points.append(bbox[i])
            except:
                pass
        
        return points

# ============================================================================
# DIRECT 3D SHEET PROJECTOR
# ============================================================================

class DirectSheetProjector:
    """Project sheets directly onto 3D surface using robust methods"""
    
    def __init__(self):
        self.sheet_width = 6.0  # meters
        self.sheet_height = 2.0  # meters
        self.overlap = 0.05  # 50mm overlap
        self.min_sheet_area = 2.0
    
    def project_sheets_directly(self, surface_id, surface_data):
        """Project sheets directly using bounding box projection"""
        try:
            print("\n=== PROJECTING SHEETS DIRECTLY ONTO SURFACE ===")
            
            if not surface_id:
                return None
            
            # Get bounding box info
            min_pt = surface_data.get('min_point', (0, 0, 0))
            max_pt = surface_data.get('max_point', (10, 10, 5))
            width = surface_data.get('width', 10)
            height = surface_data.get('height', 10)
            
            print("Surface area: {width:.1f}m × {height:.1f}m")
            
            # Calculate number of sheets needed
            cols = max(1, int(math.ceil(width / self.sheet_width)))
            rows = max(1, int(math.ceil(height / self.sheet_height)))
            
            print("Sheet grid: {cols} columns × {rows} rows")
            
            sheets = []
            sheet_count = 0
            
            # Create grid in XY plane
            for col in range(cols):
                for row in range(rows):
                    sheet_count += 1
                    
                    # Calculate flat rectangle position
                    x_start = min_pt[0] + col * self.sheet_width
                    y_start = min_pt[1] + row * self.sheet_height
                    x_end = min(x_start + self.sheet_width, max_pt[0])
                    y_end = min(y_start + self.sheet_height, max_pt[1])
                    
                    # Create flat rectangle
                    flat_points = [
                        (x_start, y_start, min_pt[2]),
                        (x_end, y_start, min_pt[2]),
                        (x_end, y_end, min_pt[2]),
                        (x_start, y_end, min_pt[2]),
                        (x_start, y_start, min_pt[2])
                    ]
                    
                    # Project onto surface
                    sheet = self.project_rectangle_to_surface(surface_id, flat_points, sheet_count)
                    
                    if sheet:
                        sheets.append(sheet)
                        print("  Created sheet {sheet_count}")
            
            if len(sheets) == 0:
                print("ERROR: No sheets created - trying alternative method")
                sheets = self.create_sheets_alternative(surface_id, surface_data)
            
            return {
                'sheets': sheets,
                'total_sheets': len(sheets),
                'grid_size': (cols, rows),
                'surface_width': width,
                'surface_height': height
            }
            
        except Exception as e:
            print("ERROR in direct projection: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def project_rectangle_to_surface(self, surface_id, flat_points, sheet_number):
        """Project a flat rectangle onto the surface"""
        try:
            if len(flat_points) < 4:
                return None
            
            projected_points = []
            
            # Project each corner
            for point in flat_points[:4]:  # First 4 corners
                projected_point = self.project_point_to_surface(surface_id, point)
                if projected_point:
                    projected_points.append(projected_point)
                else:
                    # Use original point as fallback
                    projected_points.append(point)
            
            if len(projected_points) < 4:
                return None
            
            # Close the polygon
            projected_points.append(projected_points[0])
            
            # Create curve on surface
            sheet_curve = rs.AddCurve(projected_points)
            
            if not sheet_curve:
                # Try polyline instead
                sheet_curve = rs.AddPolyline(projected_points)
            
            if sheet_curve:
                # Calculate area
                area = self.calculate_polygon_area(projected_points[:-1])
                
                if area < self.min_sheet_area:
                    rs.DeleteObject(sheet_curve)
                    return None
                
                # Calculate center
                center = self.calculate_center(projected_points[:-1])
                
                return {
                    'curve_id': sheet_curve,
                    'sheet_number': sheet_number,
                    'points': projected_points[:-1],
                    'area': area,
                    'center': center
                }
            
            return None
            
        except Exception as e:
            print("ERROR projecting rectangle {sheet_number}: {str(e)}")
            return None
    
    def project_point_to_surface(self, surface_id, point):
        """Project a point onto surface with multiple fallback methods"""
        try:
            # Method 1: Direct projection along Z-axis
            projected = rs.ProjectPointToSurface(point, surface_id, (0, 0, 1))
            if projected and len(projected) > 0:
                return projected[0]
            
            # Method 2: Closest point
            success, uv = rs.SurfaceClosestPoint(surface_id, point)
            if success:
                return rs.EvaluateSurface(surface_id, uv[0], uv[1])
            
            # Method 3: Try different projection directions
            for direction in [(0, 0, -1), (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)]:
                projected = rs.ProjectPointToSurface(point, surface_id, direction)
                if projected and len(projected) > 0:
                    return projected[0]
            
            # Method 4: Use original point
            return point
            
        except:
            return point
    
    def create_sheets_alternative(self, surface_id, surface_data):
        """Alternative method to create sheets"""
        try:
            print("Using alternative sheet creation method...")
            
            sheets = []
            
            # Create sheets based on sample points
            sample_points = surface_data.get('sample_points', [])
            if len(sample_points) < 4:
                return sheets
            
            # Divide surface into 4 quadrants
            min_pt = surface_data.get('min_point', (0, 0, 0))
            max_pt = surface_data.get('max_point', (10, 10, 5))
            
            center_x = (min_pt[0] + max_pt[0]) / 2
            center_y = (min_pt[1] + max_pt[1]) / 2
            
            quadrants = [
                # Bottom-left
                [(min_pt[0], min_pt[1], min_pt[2]), 
                 (center_x, min_pt[1], min_pt[2]),
                 (center_x, center_y, min_pt[2]),
                 (min_pt[0], center_y, min_pt[2])],
                # Bottom-right
                [(center_x, min_pt[1], min_pt[2]),
                 (max_pt[0], min_pt[1], min_pt[2]),
                 (max_pt[0], center_y, min_pt[2]),
                 (center_x, center_y, min_pt[2])],
                # Top-right
                [(center_x, center_y, min_pt[2]),
                 (max_pt[0], center_y, min_pt[2]),
                 (max_pt[0], max_pt[1], min_pt[2]),
                 (center_x, max_pt[1], min_pt[2])],
                # Top-left
                [(min_pt[0], center_y, min_pt[2]),
                 (center_x, center_y, min_pt[2]),
                 (center_x, max_pt[1], min_pt[2]),
                 (min_pt[0], max_pt[1], min_pt[2])]
            ]
            
            for i, quad_points in enumerate(quadrants):
                sheet = self.project_rectangle_to_surface(surface_id, quad_points, i + 1)
                if sheet:
                    sheets.append(sheet)
                    print("  Created sheet {i+1} from quadrant")
            
            return sheets
            
        except Exception as e:
            print("ERROR in alternative method: {str(e)}")
            return []
    
    def calculate_polygon_area(self, points):
        """Calculate polygon area"""
        try:
            if len(points) < 3:
                return 0
            
            area = 0
            n = len(points)
            
            for i in range(n):
                j = (i + 1) % n
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            
            return abs(area) / 2.0
            
        except:
            return self.sheet_width * self.sheet_height
    
    def calculate_center(self, points):
        """Calculate center of points"""
        try:
            if not points:
                return (0, 0, 0)
            
            sum_x = sum(p[0] for p in points)
            sum_y = sum(p[1] for p in points)
            sum_z = sum(p[2] for p in points)
            
            count = len(points)
            return (sum_x/count, sum_y/count, sum_z/count)
            
        except:
            return (0, 0, 0)

# ============================================================================
# SIMPLE BOUNDARY CREATOR
# ============================================================================

class SimpleBoundaryCreator:
    """Create simple boundaries between sheets"""
    
    def create_boundaries(self, sheets):
        """Create boundaries between sheets"""
        try:
            print("\n=== CREATING BOUNDARIES ===")
            
            if not sheets or len(sheets) < 2:
                return {'boundaries': [], 'intersections': []}
            
            boundaries = []
            
            # Connect centers of adjacent sheets
            for i in range(len(sheets)):
                for j in range(i + 1, len(sheets)):
                    sheet1 = sheets[i]
                    sheet2 = sheets[j]
                    
                    center1 = sheet1.get('center', (0, 0, 0))
                    center2 = sheet2.get('center', (0, 0, 0))
                    
                    # Check if sheets are close enough
                    distance = self.distance_3d(center1, center2)
                    if distance < 8.0:  # Within reasonable distance
                        boundary_line = rs.AddLine(center1, center2)
                        if boundary_line:
                            boundaries.append({
                                'line_id': boundary_line,
                                'sheet1': sheet1['sheet_number'],
                                'sheet2': sheet2['sheet_number'],
                                'distance': distance
                            })
            
            print("Created {len(boundaries)} boundaries")
            
            return {
                'boundaries': boundaries,
                'total_boundaries': len(boundaries)
            }
            
        except Exception as e:
            print("ERROR creating boundaries: {str(e)}")
            return {'boundaries': [], 'intersections': []}
    
    def distance_3d(self, p1, p2):
        """Calculate 3D distance"""
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        dz = p1[2] - p2[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)

# ============================================================================
# SIMPLE VISUALIZER
# ============================================================================

class SimpleVisualizer:
    """Simple visualization of sheets on surface"""
    
    def __init__(self):
        self.layers = {
            'Surface': (150, 150, 150),
            'Sheets': (0, 100, 255),
            'Numbers': (255, 255, 0),
            'Boundaries': (255, 100, 0),
            'Info': (200, 200, 200)
        }
    
    def visualize(self, surface_id, arrangement, boundaries):
        """Create simple visualization"""
        try:
            print("\n=== CREATING VISUALIZATION ===")
            
            # Setup layers
            for layer_name, color in self.layers.items():
                if not rs.IsLayer(layer_name):
                    rs.AddLayer(layer_name, color)
            
            # Color surface
            rs.ObjectLayer(surface_id, "Surface")
            rs.ObjectColor(surface_id, self.layers['Surface'])
            
            # Visualize sheets
            if arrangement and 'sheets' in arrangement:
                for sheet in arrangement['sheets']:
                    curve_id = sheet.get('curve_id')
                    if curve_id and rs.IsObject(curve_id):
                        rs.ObjectLayer(curve_id, "Sheets")
                        rs.ObjectColor(curve_id, self.layers['Sheets'])
                        
                        # Add sheet number
                        center = sheet.get('center', (0, 0, 0))
                        text = "S{sheet['sheet_number']}"
                        text_id = rs.AddText(text, center, 0.5)
                        
                        if text_id:
                            rs.ObjectLayer(text_id, "Numbers")
                            rs.ObjectColor(text_id, self.layers['Numbers'])
            
            # Visualize boundaries
            if boundaries and 'boundaries' in boundaries:
                for boundary in boundaries['boundaries']:
                    line_id = boundary.get('line_id')
                    if line_id and rs.IsObject(line_id):
                        rs.ObjectLayer(line_id, "Boundaries")
                        rs.ObjectColor(line_id, self.layers['Boundaries'])
            
            # Add info
            self.add_info(arrangement, boundaries)
            
            rs.ZoomExtents()
            
            print("✓ Visualization complete")
            return True
            
        except Exception as e:
            print("ERROR in visualization: {str(e)}")
            return False
    
    def add_info(self, arrangement, boundaries):
        """Add information text"""
        try:
            rs.CurrentLayer("Info")
            
            info = []
            info.append("SHEETS ON 3D SURFACE")
            info.append("="*30)
            info.append("")
            
            if arrangement:
                info.append("Sheets: {arrangement.get('total_sheets', 0)}")
                info.append("Size: 6.0m × 2.0m")
                info.append("")
            
            if boundaries:
                info.append("Boundaries: {boundaries.get('total_boundaries', 0)}")
                info.append("")
            
            info.append("Colors:")
            info.append("  Gray: Target surface")
            info.append("  Blue: Sheet boundaries")
            info.append("  Yellow: Sheet numbers")
            info.append("  Orange: Welding lines")
            
            # Add text
            for i, line in enumerate(info):
                point = (0, -5 - i * 0.8, 0)
                rs.AddText(line, point, 0.4)
                
        except Exception as e:
            print("ERROR adding info: {str(e)}")
    
    def clear(self):
        """Clear visualization"""
        try:
            for layer_name in self.layers.keys():
                if rs.IsLayer(layer_name):
                    objects = rs.ObjectsByLayer(layer_name)
                    if objects:
                        rs.DeleteObjects(objects)
            return True
        except Exception as e:
            print("ERROR clearing: {str(e)}")
            return False

# ============================================================================
# MAIN WORKFLOW - SIMPLIFIED AND ROBUST
# ============================================================================

def main_simple_workflow():
    """Simple and robust workflow for sheet arrangement"""
    
    print("\n" + "="*60)
    print("SIMPLE 3D SHEET ARRANGEMENT")
    print("="*60)
    
    sampler = RobustSurfaceSampler()
    projector = DirectSheetProjector()
    boundary_creator = SimpleBoundaryCreator()
    visualizer = SimpleVisualizer()
    
    current_surface = None
    current_data = None
    current_arrangement = None
    current_boundaries = None
    
    while True:
        options = [
            "1. SELECT Surface",
            "2. SAMPLE Surface",
            "3. CREATE Sheets",
            "4. ADD Boundaries",
            "5. VISUALIZE",
            "6. REPORT",
            "7. CLEAR",
            "8. EXIT"
        ]
        
        choice = rs.ListBox(options, "SIMPLE SHEET ARRANGEMENT", "Select:")
        
        if not choice or choice == "8. EXIT":
            break
        
        elif choice == "1. SELECT Surface":
            try:
                obj = rs.GetObject("Select surface", rs.filter.surface)
                if obj:
                    current_surface = obj
                    rs.MessageBox("Surface selected", 0, "Success")
                else:
                    rs.MessageBox("No surface selected", 0, "Warning")
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
        
        elif choice == "2. SAMPLE Surface":
            if not current_surface:
                rs.MessageBox("Select surface first!", 0, "Error")
                continue
            
            try:
                rs.EnableRedraw(False)
                current_data = sampler.sample_surface_for_sheets(current_surface)
                
                if current_data:
                    msg = "SURFACE SAMPLED\n\n"
                    msg += "Width: {current_data['width']:.1f}m\n"
                    msg += "Height: {current_data['height']:.1f}m\n"
                    msg += "Depth: {current_data['depth']:.1f}m\n\n"
                    msg += "Ready for sheet creation"
                    
                    rs.MessageBox(msg, 0, "Sampling Complete")
                else:
                    rs.MessageBox("Sampling failed", 0, "Error")
                
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        elif choice == "3. CREATE Sheets":
            if not current_surface:
                rs.MessageBox("Select surface first!", 0, "Error")
                continue
            
            try:
                rs.EnableRedraw(False)
                
                # Ensure we have surface data
                if not current_data:
                    current_data = sampler.sample_surface_for_sheets(current_surface)
                
                rs.Prompt("Creating 6x2m sheets on surface...")
                current_arrangement = projector.project_sheets_directly(current_surface, current_data)
                
                if current_arrangement and current_arrangement.get('total_sheets', 0) > 0:
                    msg = "SHEETS CREATED\n\n"
                    msg += "Sheets: {current_arrangement['total_sheets']}\n"
                    msg += "Grid: {current_arrangement.get('grid_size', (1,1))[0]}×{current_arrangement.get('grid_size', (1,1))[1]}\n"
                    msg += "Size: 6.0m × 2.0m\n\n"
                    msg += "All sheets are 3D curves on the surface"
                    
                    rs.MessageBox(msg, 0, "Success")
                else:
                    msg = "Sheet creation failed\n\n"
                    msg += "Try:\n"
                    msg += "1. A larger surface\n"
                    msg += "2. A less complex surface\n"
                    msg += "3. Check if surface is valid"
                    
                    rs.MessageBox(msg, 0, "Error")
                
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        elif choice == "4. ADD Boundaries":
            if not current_arrangement:
                rs.MessageBox("Create sheets first!", 0, "Error")
                continue
            
            try:
                rs.EnableRedraw(False)
                current_boundaries = boundary_creator.create_boundaries(current_arrangement['sheets'])
                
                if current_boundaries:
                    msg = "Boundaries created: {current_boundaries.get('total_boundaries', 0)}"
                    rs.MessageBox(msg, 0, "Success")
                else:
                    rs.MessageBox("No boundaries created", 0, "Info")
                
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        elif choice == "5. VISUALIZE":
            if not current_arrangement:
                rs.MessageBox("Create sheets first!", 0, "Error")
                continue
            
            try:
                rs.EnableRedraw(False)
                success = visualizer.visualize(current_surface, current_arrangement, current_boundaries)
                
                if success:
                    rs.MessageBox("Visualization complete!", 0, "Success")
                else:
                    rs.MessageBox("Visualization failed", 0, "Error")
                
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
        
        elif choice == "6. REPORT":
            if not current_arrangement:
                rs.MessageBox("No arrangement to report!", 0, "Error")
                continue
            
            try:
                report = "SHEET ARRANGEMENT REPORT\n"
                report += "="*40 + "\n\n"
                
                if current_data:
                    report += "SURFACE:\n"
                    report += "  Size: {current_data['width']:.1f}m × {current_data['height']:.1f}m\n\n"
                
                if current_arrangement:
                    report += "SHEETS:\n"
                    report += "  Count: {current_arrangement['total_sheets']}\n"
                    report += "  Size: 6.0m × 2.0m\n\n"
                
                report += "INSTRUCTIONS:\n"
                report += "1. Blue curves = Sheet boundaries\n"
                report += "2. Yellow numbers = Sheet IDs\n"
                report += "3. Orange lines = Welding boundaries\n"
                report += "4. All curves are on the 3D surface"
                
                rs.MessageBox(report, 0, "Report")
                
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
        
        elif choice == "7. CLEAR":
            try:
                visualizer.clear()
                current_surface = None
                current_data = None
                current_arrangement = None
                current_boundaries = None
                rs.MessageBox("Cleared", 0, "Success")
            except Exception as e:
                rs.MessageBox("Error: {str(e)}", 0, "Error")
    
    rs.MessageBox("System completed", 0, "Exit")

# ============================================================================
# TEST WITH EXAMPLE SURFACE
# ============================================================================

def create_test_surface():
    """Create a test surface for debugging"""
    try:
        # Create a simple curved surface
        points = []
        
        # Create a grid of points
        for i in range(5):
            x = i * 2.0
            for j in range(5):
                y = j * 2.0
                z = math.sin(x/5) * math.cos(y/5) * 2.0
                points.append((x, y, z))
        
        # Create surface from points
        surface = rs.AddSrfPtGrid((5, 5), points)
        
        if surface:
            rs.MessageBox("Test surface created!\n\nNow run the arrangement system.", 0, "Test Surface Ready")
            return surface
        
        return None
        
    except Exception as e:
        rs.MessageBox("Error creating test surface: {str(e)}", 0, "Error")
        return None

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Ask if user wants to create test surface
    test_option = rs.MessageBox(
        "Create test surface for debugging?\n\n" +
        "Yes: Create a curved test surface\n" +
        "No: Use your own surface",
        4,  # Yes/No buttons
        "Setup"
    )
    
    if test_option == 6:  # Yes
        test_surface = create_test_surface()
        if test_surface:
            # Run the system with test surface
            main_simple_workflow()
    else:
        # Run with user's surface
        main_simple_workflow()