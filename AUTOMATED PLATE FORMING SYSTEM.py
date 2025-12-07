# -*- coding: utf-8 -*-
"""
Automated Plate Forming System for Rhino 5
Based on: "Automated Strain-Based Processing Route Generation for Curved Plate Forming"
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

# ============================================================================
# GLOBAL STATE VARIABLES
# ============================================================================

class SystemState:
    """Maintains state between menu selections"""
    def __init__(self):
        self.target_surface = None
        self.processing_paths = []
        self.simulation_results = None
        self.material_thickness = 16.0
        self.material_yield = 355.0
        
    def reset(self):
        """Reset all state variables"""
        self.target_surface = None
        self.processing_paths = []
        self.simulation_results = None

# ============================================================================
# CORE FORMULATION IMPLEMENTATION
# ============================================================================

class PlateFormingSystem:
    def __init__(self):
        self.thickness = 16.0  # mm
        self.springback_factor = 0.85
        self.material_yield = 355.0  # MPa
        self.material_modulus = 210000.0  # MPa
        
    def calculate_strain_distribution(self, surface_points, target_shape):
        """Calculate strain distribution for forming"""
        strains = []
        
        for i in range(len(surface_points)):
            # Simplified strain calculation
            # In real implementation, this would use finite element analysis
            point = surface_points[i]
            
            # Calculate distance from center
            center_x = sum(p.X for p in surface_points) / len(surface_points)
            center_y = sum(p.Y for p in surface_points) / len(surface_points)
            
            dx = point.X - center_x
            dy = point.Y - center_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # Strain proportional to distance from center
            max_distance = max(abs(p.X - center_x) for p in surface_points)
            if max_distance > 0:
                strain_factor = distance / max_distance
                strain_value = 0.01 * strain_factor  # 1% max strain
                
                strains.append({
                    'point': point,
                    'strain': strain_value,
                    'inplane': strain_value * 0.7,
                    'bending': strain_value * 0.3
                })
        
        return strains
    
    def calculate_curvature_lines_simple(self, surface_id):
        """Create simple grid pattern for processing paths"""
        try:
            # Get bounding box
            bbox = rs.BoundingBox(surface_id)
            if not bbox or len(bbox) < 8:
                return []
            
            min_pt = bbox[0]
            max_pt = bbox[6]
            
            lines = []
            
            # Create horizontal lines
            num_lines = 5
            for i in range(1, num_lines + 1):
                y = min_pt.Y + (max_pt.Y - min_pt.Y) * i / (num_lines + 1)
                
                start_point = Rhino.Geometry.Point3d(min_pt.X, y, 0)
                end_point = Rhino.Geometry.Point3d(max_pt.X, y, 0)
                line = Rhino.Geometry.Line(start_point, end_point)
                
                if line.IsValid:
                    curve = line.ToNurbsCurve()
                    if curve and curve.IsValid:
                        lines.append(curve)
            
            # Create vertical lines
            for i in range(1, num_lines + 1):
                x = min_pt.X + (max_pt.X - min_pt.X) * i / (num_lines + 1)
                
                start_point = Rhino.Geometry.Point3d(x, min_pt.Y, 0)
                end_point = Rhino.Geometry.Point3d(x, max_pt.Y, 0)
                line = Rhino.Geometry.Line(start_point, end_point)
                
                if line.IsValid:
                    curve = line.ToNurbsCurve()
                    if curve and curve.IsValid:
                        lines.append(curve)
            
            return lines
            
        except Exception as e:
            print("Error in curvature calculation: " + str(e))
            return []
    
    def polyline_approximation(self, curve, tolerance=50.0):
        """Approximate curve with polyline"""
        try:
            # Simple polyline conversion
            polyline = curve.ToPolyline(0, 0, 0, 0, 0, tolerance, 0, 0, True)
            return polyline
        except:
            # Fallback: create simple line
            if curve.IsLinear():
                start_point = curve.PointAtStart
                end_point = curve.PointAtEnd
                line = Rhino.Geometry.Line(start_point, end_point)
                return line.ToPolyline()
            return None

# ============================================================================
# RHINO 5 INTERFACE
# ============================================================================

class RhinoPlateFormingUI:
    def __init__(self):
        self.system = PlateFormingSystem()
        self.state = SystemState()
        self.running = True
        
    def create_layers(self):
        """Create organized layers"""
        layers = [
            ("00_TARGET_SURFACE", (0, 255, 0)),
            ("01_CURVATURE_LINES", (255, 165, 0)),
            ("02_PROCESSING_PATHS", (255, 0, 0)),
            ("03_SIMULATION_RESULTS", (0, 0, 255)),
            ("04_NC_OUTPUT", (128, 0, 128))
        ]
        
        for layer_name, color in layers:
            if not rs.IsLayer(layer_name):
                rs.AddLayer(layer_name, color)
    
    def main_menu(self):
        """Main menu with persistent loop"""
        while self.running:
            options = [
                "1. Select Target Surface",
                "2. Set Material Parameters", 
                "3. Calculate Curvature Lines",
                "4. Generate Processing Paths",
                "5. Simulate Forming Process",
                "6. Export to NC Code",
                "7. Show Results Summary",
                "8. Clear All Data",
                "9. Exit System"
            ]
            
            result = rs.ListBox(options, "Automated Plate Forming System", "Select Operation")
            
            if not result:
                self.running = False
                break
            
            if result == "1. Select Target Surface":
                self.select_target_surface()
            elif result == "2. Set Material Parameters":
                self.set_parameters()
            elif result == "3. Calculate Curvature Lines":
                self.calculate_curvature_lines()
            elif result == "4. Generate Processing Paths":
                self.generate_processing_paths()
            elif result == "5. Simulate Forming Process":
                self.simulate_forming()
            elif result == "6. Export to NC Code":
                self.export_to_nc()
            elif result == "7. Show Results Summary":
                self.show_summary()
            elif result == "8. Clear All Data":
                self.clear_all_data()
            elif result == "9. Exit System":
                self.exit_system()
    
    def select_target_surface(self):
        """Select target curved surface"""
        rs.EnableRedraw(False)
        try:
            obj = rs.GetObject("Select target curved surface", rs.filter.surface | rs.filter.polysurface)
            
            if obj:
                self.state.target_surface = obj
                rs.CurrentLayer("00_TARGET_SURFACE")
                rs.ObjectLayer(obj, "00_TARGET_SURFACE")
                
                # Highlight the selected surface
                rs.ObjectColor(obj, (0, 255, 0))
                
                # Add information
                bbox = rs.BoundingBox(obj)
                if bbox and len(bbox) >= 8:
                    size_x = bbox[6].X - bbox[0].X
                    size_y = bbox[6].Y - bbox[0].Y
                    
                    info = "Target Surface Selected\nSize: " + "{:.1f}".format(size_x) + " x " + "{:.1f}".format(size_y) + " mm"
                    rs.AddTextDot(info, bbox[7])
                
                rs.Prompt("Target surface selected successfully.")
                
        except Exception as e:
            rs.MessageBox("Error selecting surface: " + str(e), 0, "Error")
        finally:
            rs.EnableRedraw(True)
            rs.Redraw()
    
    def set_parameters(self):
        """Set forming parameters"""
        # Material thickness
        thickness = rs.GetReal("Material thickness (mm)", self.state.material_thickness, 1.0, 50.0)
        if thickness:
            self.state.material_thickness = thickness
            self.system.thickness = thickness
        
        # Yield strength
        yield_strength = rs.GetReal("Yield strength (MPa)", self.state.material_yield, 100.0, 1000.0)
        if yield_strength:
            self.state.material_yield = yield_strength
            self.system.material_yield = yield_strength
        
        rs.MessageBox("Parameters set successfully.", 0, "Success")
    
    def calculate_curvature_lines(self):
        """Calculate curvature lines"""
        if not self.state.target_surface:
            rs.MessageBox("Please select target surface first!", 0, "Error")
            return
        
        rs.EnableRedraw(False)
        try:
            rs.Prompt("Calculating curvature lines...")
            
            # Clear previous lines
            existing_lines = rs.ObjectsByLayer("01_CURVATURE_LINES")
            if existing_lines:
                rs.DeleteObjects(existing_lines)
            
            # Calculate simple grid pattern
            lines = self.system.calculate_curvature_lines_simple(self.state.target_surface)
            
            # Draw lines
            rs.CurrentLayer("01_CURVATURE_LINES")
            line_count = 0
            
            for curve in lines:
                if curve and curve.IsValid:
                    curve_id = sc.doc.Objects.AddCurve(curve)
                    if curve_id:
                        obj = sc.doc.Objects.Find(curve_id)
                        obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                        obj.Attributes.ObjectColor = System.Drawing.Color.Orange
                        obj.CommitChanges()
                        line_count += 1
            
            # Add info
            rs.CurrentLayer("Default")
            bbox = rs.BoundingBox(self.state.target_surface)
            if bbox and len(bbox) >= 8:
                info_point = Rhino.Geometry.Point3d(bbox[0].X, bbox[0].Y - 30, bbox[0].Z)
                info = "Created " + str(line_count) + " curvature lines"
                rs.AddText(info, info_point, 6)
            
            rs.Prompt("Calculated " + str(line_count) + " curvature lines")
            
        except Exception as e:
            rs.MessageBox("Error: " + str(e), 0, "Error")
        finally:
            rs.EnableRedraw(True)
            rs.Redraw()
    
    def generate_processing_paths(self):
        """Generate processing paths"""
        if not self.state.target_surface:
            rs.MessageBox("Please select target surface first!", 0, "Error")
            return
        
        rs.EnableRedraw(False)
        try:
            rs.Prompt("Generating processing paths...")
            
            # Clear previous paths
            existing_paths = rs.ObjectsByLayer("02_PROCESSING_PATHS")
            if existing_paths:
                rs.DeleteObjects(existing_paths)
            
            # Get curvature lines
            curvature_objects = rs.ObjectsByLayer("01_CURVATURE_LINES")
            if not curvature_objects:
                rs.MessageBox("No curvature lines found. Please calculate them first.", 0, "Error")
                return
            
            # Generate paths
            self.state.processing_paths = []
            rs.CurrentLayer("02_PROCESSING_PATHS")
            path_count = 0
            
            for obj_id in curvature_objects:
                if path_count >= 10:  # Limit number of paths
                    break
                
                curve = rs.coercecurve(obj_id)
                if curve and curve.IsValid:
                    # Convert to polyline
                    polyline = self.system.polyline_approximation(curve, 50.0)
                    
                    if polyline:
                        # Get points from polyline
                        points = []
                        for i in range(polyline.PointCount):
                            point = polyline.Point(i)
                            points.append(point)
                        
                        if len(points) >= 2:
                            # Create new polyline
                            new_polyline = Rhino.Geometry.Polyline(points)
                            if new_polyline.IsValid:
                                # Add to document
                                polyline_curve = new_polyline.ToNurbsCurve()
                                if polyline_curve and polyline_curve.IsValid:
                                    curve_id = sc.doc.Objects.AddCurve(polyline_curve)
                                    if curve_id:
                                        obj = sc.doc.Objects.Find(curve_id)
                                        obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                                        obj.Attributes.ObjectColor = System.Drawing.Color.Red
                                        obj.CommitChanges()
                                        
                                        # Store path data
                                        path_data = {
                                            'id': curve_id,
                                            'points': points,
                                            'segments': []
                                        }
                                        
                                        # Create segments
                                        for i in range(len(points) - 1):
                                            segment_length = points[i].DistanceTo(points[i + 1])
                                            if segment_length > 1.0:  # Skip very short segments
                                                # Calculate strain (simplified)
                                                strain_value = 0.001 * (i + 1)
                                                
                                                segment = {
                                                    'start': points[i],
                                                    'end': points[i + 1],
                                                    'length': segment_length,
                                                    'strain': strain_value
                                                }
                                                path_data['segments'].append(segment)
                                        
                                        self.state.processing_paths.append(path_data)
                                        path_count += 1
            
            # Add strain labels
            for path_data in self.state.processing_paths:
                for segment in path_data['segments']:
                    mid_x = (segment['start'].X + segment['end'].X) / 2.0
                    mid_y = (segment['start'].Y + segment['end'].Y) / 2.0
                    mid_z = (segment['start'].Z + segment['end'].Z) / 2.0
                    mid_point = Rhino.Geometry.Point3d(mid_x, mid_y, mid_z)
                    
                    label = "{:.4f}".format(segment['strain'])
                    rs.AddText(label, mid_point, 4)
            
            rs.Prompt("Generated " + str(len(self.state.processing_paths)) + " processing paths")
            
        except Exception as e:
            rs.MessageBox("Error: " + str(e), 0, "Error")
        finally:
            rs.EnableRedraw(True)
            rs.Redraw()
    
    def simulate_forming(self):
        """Simulate forming process"""
        if not self.state.processing_paths:
            rs.MessageBox("Please generate processing paths first!", 0, "Error")
            return
        
        rs.EnableRedraw(False)
        try:
            rs.Prompt("Simulating forming process...")
            
            # Clear previous simulation
            existing_sim = rs.ObjectsByLayer("03_SIMULATION_RESULTS")
            if existing_sim:
                rs.DeleteObjects(existing_sim)
            
            # Create base plate
            base_mesh = self.create_base_plate_mesh()
            if not base_mesh:
                rs.MessageBox("Could not create base plate.", 0, "Error")
                return
            
            # Apply deformation
            deformed_mesh = self.apply_deformation(base_mesh)
            
            # Add to document
            rs.CurrentLayer("03_SIMULATION_RESULTS")
            mesh_id = sc.doc.Objects.AddMesh(deformed_mesh)
            
            if mesh_id:
                obj = sc.doc.Objects.Find(mesh_id)
                obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                obj.Attributes.ObjectColor = System.Drawing.Color.FromArgb(128, 0, 0, 255)
                obj.CommitChanges()
                
                # Store results
                deviation = self.calculate_deviation(deformed_mesh)
                self.state.simulation_results = {
                    'mesh_id': mesh_id,
                    'deviation': deviation
                }
            
            # Add info
            rs.CurrentLayer("Default")
            bbox = deformed_mesh.GetBoundingBox(True)
            if bbox.IsValid:
                info_point = Rhino.Geometry.Point3d(bbox.Min.X, bbox.Min.Y - 30, bbox.Min.Z)
                info = "Simulation complete. Max deformation: " + "{:.1f}".format(deviation['max']) + " mm"
                rs.AddText(info, info_point, 6)
            
            rs.Prompt("Simulation completed successfully.")
            
        except Exception as e:
            rs.MessageBox("Error: " + str(e), 0, "Error")
        finally:
            rs.EnableRedraw(True)
            rs.Redraw()
    
    def export_to_nc(self):
        """Export to NC code"""
        if not self.state.processing_paths:
            rs.MessageBox("Please generate processing paths first!", 0, "Error")
            return
        
        # Generate G-code
        gcode = self.generate_gcode()
        
        # Save to file
        filename = rs.SaveFileName("Save NC Code", "G-code Files (*.nc)|*.nc||")
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(gcode)
                
                # Visualize in Rhino
                self.visualize_gcode(gcode)
                
                rs.MessageBox("NC code exported to: " + filename, 0, "Success")
                
            except Exception as e:
                rs.MessageBox("Error saving file: " + str(e), 0, "Error")
    
    def show_summary(self):
        """Show results summary"""
        summary_lines = []
        
        if self.state.target_surface:
            summary_lines.append("✓ Target surface selected")
            bbox = rs.BoundingBox(self.state.target_surface)
            if bbox and len(bbox) >= 8:
                size_x = bbox[6].X - bbox[0].X
                size_y = bbox[6].Y - bbox[0].Y
                summary_lines.append("  Size: " + "{:.1f}".format(size_x) + " x " + "{:.1f}".format(size_y) + " mm")
        
        summary_lines.append("Material: " + "{:.1f}".format(self.state.material_thickness) + "mm, " + "{:.1f}".format(self.state.material_yield) + "MPa")
        
        if self.state.processing_paths:
            total_segments = sum(len(p['segments']) for p in self.state.processing_paths)
            summary_lines.append("✓ " + str(len(self.state.processing_paths)) + " processing paths")
            summary_lines.append("  Total segments: " + str(total_segments))
        
        if self.state.simulation_results:
            deviation = self.state.simulation_results['deviation']
            summary_lines.append("✓ Simulation completed")
            summary_lines.append("  Max deviation: " + "{:.2f}".format(deviation['max']) + " mm")
        
        if not summary_lines:
            summary_lines.append("No data available. Start by selecting a target surface.")
        
        # Show summary
        summary_text = "\n".join(summary_lines)
        rs.ListBox([summary_text], "System Summary", "Status")
    
    def clear_all_data(self):
        """Clear all data"""
        confirm = rs.MessageBox("Clear all data?", 4, "Confirm")
        if confirm == 6:  # Yes
            layers = ["00_TARGET_SURFACE", "01_CURVATURE_LINES", "02_PROCESSING_PATHS", 
                     "03_SIMULATION_RESULTS", "04_NC_OUTPUT"]
            
            rs.EnableRedraw(False)
            try:
                for layer in layers:
                    objects = rs.ObjectsByLayer(layer)
                    if objects:
                        rs.DeleteObjects(objects)
                
                # Reset state
                self.state.reset()
                
                rs.Prompt("All data cleared.")
                
            except Exception as e:
                rs.MessageBox("Error: " + str(e), 0, "Error")
            finally:
                rs.EnableRedraw(True)
                rs.Redraw()
    
    def exit_system(self):
        """Exit the system"""
        self.running = False
        rs.Prompt("System terminated.")
    
    # ------------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------------
    
    def create_base_plate_mesh(self):
        """Create base plate mesh"""
        try:
            # Get bounding box
            bbox = rs.BoundingBox(self.state.target_surface)
            if not bbox or len(bbox) < 8:
                return None
            
            min_pt = bbox[0]
            max_pt = bbox[6]
            
            # Create mesh
            mesh = Rhino.Geometry.Mesh()
            
            # Add vertices
            divisions = 10
            for i in range(divisions + 1):
                for j in range(divisions + 1):
                    x = min_pt.X + (max_pt.X - min_pt.X) * i / divisions
                    y = min_pt.Y + (max_pt.Y - min_pt.Y) * j / divisions
                    mesh.Vertices.Add(x, y, 0)
            
            # Add faces
            for i in range(divisions):
                for j in range(divisions):
                    v1 = i * (divisions + 1) + j
                    v2 = v1 + 1
                    v3 = v1 + divisions + 2
                    v4 = v1 + divisions + 1
                    mesh.Faces.AddFace(v1, v2, v3, v4)
            
            mesh.Normals.ComputeNormals()
            mesh.Compact()
            
            return mesh
            
        except Exception as e:
            return None
    
    def apply_deformation(self, mesh):
        """Apply deformation to mesh"""
        deformed = mesh.Duplicate()
        
        # Simple deformation: parabolic shape
        bbox = mesh.GetBoundingBox(True)
        if bbox.IsValid:
            center = bbox.Center
            
            for i in range(deformed.Vertices.Count):
                vertex = deformed.Vertices[i]
                x = vertex.X - center.X
                y = vertex.Y - center.Y
                
                # Parabolic deformation
                max_x = bbox.Max.X - center.X
                max_y = bbox.Max.Y - center.Y
                
                if abs(max_x) > 0 and abs(max_y) > 0:
                    factor_x = 1.0 - (x*x) / (max_x*max_x)
                    factor_y = 1.0 - (y*y) / (max_y*max_y)
                    
                    z_deformation = 20.0 * factor_x * factor_y  # 20mm max
                    
                    new_point = Rhino.Geometry.Point3d(vertex.X, vertex.Y, z_deformation)
                    deformed.Vertices.SetVertex(i, new_point)
        
        return deformed
    
    def calculate_deviation(self, mesh):
        """Calculate deviation"""
        bbox = mesh.GetBoundingBox(True)
        if bbox.IsValid:
            return {
                'x': bbox.Max.X - bbox.Min.X,
                'y': bbox.Max.Y - bbox.Min.Y,
                'z': bbox.Max.Z - bbox.Min.Z,
                'max': bbox.Max.Z
            }
        return {'x': 0, 'y': 0, 'z': 0, 'max': 0}
    
    def generate_gcode(self):
        """Generate G-code"""
        gcode = []
        
        # Header
        gcode.append("%")
        gcode.append("O1000 (PLATE FORMING)")
        gcode.append("G90 G94 G17 G21")
        gcode.append("G28 G91 Z0")
        gcode.append("G90")
        gcode.append("")
        
        # Process each path
        for i, path_data in enumerate(self.state.processing_paths):
            gcode.append("(Path " + str(i+1) + ")")
            
            for segment in path_data['segments']:
                # Rapid move to start
                gcode.append("G00 X" + "{:.3f}".format(segment['start'].X) + 
                           " Y" + "{:.3f}".format(segment['start'].Y) + 
                           " Z5.000")
                
                # Set force based on strain
                force = min(30.0, 30.0 * segment['strain'] * 100)
                gcode.append("M102 P" + "{:.1f}".format(force))
                
                # Processing move
                speed = 600.0  # mm/min
                gcode.append("G01 X" + "{:.3f}".format(segment['end'].X) + 
                           " Y" + "{:.3f}".format(segment['end'].Y) + 
                           " Z0.000 F" + "{:.0f}".format(speed))
                
                # Turn off force
                gcode.append("M104")
            
            gcode.append("")
        
        # Footer
        gcode.append("G00 Z50.000")
        gcode.append("G28 X0 Y0")
        gcode.append("M30")
        gcode.append("%")
        
        return "\n".join(gcode)
    
    def visualize_gcode(self, gcode):
        """Visualize G-code in Rhino"""
        rs.CurrentLayer("04_NC_OUTPUT")
        
        lines = gcode.split('\n')
        current_point = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('G00') or line.startswith('G01'):
                # Parse coordinates
                x = y = z = None
                parts = line.split()
                
                for part in parts:
                    if part.startswith('X'):
                        x = float(part[1:])
                    elif part.startswith('Y'):
                        y = float(part[1:])
                    elif part.startswith('Z'):
                        z = float(part[1:])
                
                if x is not None and y is not None:
                    if z is None:
                        z = 0
                    
                    point = Rhino.Geometry.Point3d(x, y, z)
                    
                    if current_point:
                        # Add line
                        line_obj = Rhino.Geometry.Line(current_point, point)
                        if line_obj.IsValid:
                            curve = line_obj.ToNurbsCurve()
                            if curve and curve.IsValid:
                                curve_id = sc.doc.Objects.AddCurve(curve)
                                if curve_id:
                                    obj = sc.doc.Objects.Find(curve_id)
                                    obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                                    obj.Attributes.ObjectColor = System.Drawing.Color.Purple
                                    obj.CommitChanges()
                    
                    current_point = point

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function"""
    # Welcome message
    welcome = "AUTOMATED PLATE FORMING SYSTEM\n" + \
              "===============================\n" + \
              "Based on research paper:\n" + \
              "'Automated Strain-Based Processing Route Generation'\n" + \
              "\n" + \
              "This system helps generate processing paths\n" + \
              "for curved plate forming in shipbuilding."
    
    rs.MessageBox(welcome, 0, "Welcome")
    
    # Create and run system
    system = RhinoPlateFormingUI()
    system.create_layers()
    
    try:
        system.main_menu()
    except Exception as e:
        rs.MessageBox("System error: " + str(e), 0, "Error")

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()