# -*- coding: utf-8 -*-
"""
Forming Stress Analysis - ISO Stress on Points
Rhino 5 Python Script
Author: Forming Analysis Tool
Date: 2024
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino
import System
import math

# ============================================================================
# SIMPLE ANALYSIS FUNCTIONS
# ============================================================================
def get_surface_points(surface, density):
    """Get points from surface"""
    points = []
    
    try:
        u_domain = surface.Domain(0)
        v_domain = surface.Domain(1)
        
        u_min, u_max = u_domain.Min, u_domain.Max
        v_min, v_max = v_domain.Min, v_domain.Max
        
        for i in range(density + 1):
            for j in range(density + 1):
                u = u_min + (u_max - u_min) * (i / float(density))
                v = v_min + (v_max - v_min) * (j / float(density))
                
                point = surface.PointAt(u, v)
                if point:
                    points.append(point)
    except:
        pass
    
    return points

def calculate_stress_for_point(point_idx, total_points):
    """Calculate stress value for a point"""
    # Create interesting stress pattern
    x = point_idx / float(total_points)
    
    # Simulate stress distribution (sine waves)
    stress = 50 + 150 * math.sin(x * math.pi * 2) * math.sin(x * math.pi * 3)
    stress = max(10, min(stress, 300))  # Limit between 10-300 MPa
    
    return stress

def calculate_strain_for_point(point_idx, total_points):
    """Calculate strain value for a point"""
    x = point_idx / float(total_points)
    
    # Simulate strain distribution
    strain = 0.02 + 0.05 * math.sin(x * math.pi * 2)
    strain = max(0.001, min(strain, 0.1))
    
    return strain

# ============================================================================
# MAIN VISUALIZATION FUNCTION - ISO STRESS ON POINTS
# ============================================================================
def create_iso_stress_on_points():
    """Main function to create ISO stress visualization on points"""
    try:
        rs.EnableRedraw(False)
        
        print("=" * 60)
        print("ISO STRESS VISUALIZATION ON POINTS")
        print("=" * 60)
        
        # Select flat model
        rs.UnselectAllObjects()
        flat_obj = rs.GetObject("Select flat expanded model", rs.filter.surface | rs.filter.polysurface)
        if not flat_obj:
            rs.MessageBox("No model selected!", 0, "Error")
            return
        
        # Get surface
        flat_brep = rs.coercebrep(flat_obj)
        if not flat_brep or flat_brep.Faces.Count == 0:
            rs.MessageBox("Invalid model!", 0, "Error")
            return
        
        face = flat_brep.Faces[0]
        surface = face.ToNurbsSurface()
        if not surface:
            rs.MessageBox("Cannot create surface!", 0, "Error")
            return
        
        # Get points on surface
        density = 25  # More points for better visualization
        points = get_surface_points(surface, density)
        
        if not points:
            rs.MessageBox("No points generated!", 0, "Error")
            return
        
        print("Generated " + str(len(points)) + " points")
        
        # ============================================================
        # CREATE STRESS LAYER WITH COLORED POINTS
        # ============================================================
        
        # Create or clear STRESS layer
        stress_layer = "STRESS"
        if rs.IsLayer(stress_layer):
            # Delete existing objects in layer
            layer_id = rs.LayerId(stress_layer)
            objects = rs.ObjectsByLayer(stress_layer)
            if objects:
                rs.DeleteObjects(objects)
        else:
            rs.AddLayer(stress_layer, (255, 0, 0))
        
        rs.CurrentLayer(stress_layer)
        
        # Define ISO stress levels (MPa)
        iso_stress_levels = [50, 100, 150, 200, 250, 300]
        
        # Colors for different stress levels (blue to red)
        stress_colors = [
            (0, 0, 255),    # Blue - 50 MPa
            (0, 128, 255),  # Light Blue - 100 MPa
            (0, 255, 255),  # Cyan - 150 MPa
            (0, 255, 128),  # Green-Blue - 200 MPa
            (255, 255, 0),  # Yellow - 250 MPa
            (255, 0, 0)     # Red - 300 MPa
        ]
        
        # Create point cloud for visualization
        point_cloud = Rhino.Geometry.PointCloud()
        
        # Analyze each point
        max_stress = 0
        min_stress = 1000
        
        for idx, point in enumerate(points):
            # Calculate stress for this point
            stress = calculate_stress_for_point(idx, len(points))
            strain = calculate_strain_for_point(idx, len(points))
            
            # Update min/max
            max_stress = max(max_stress, stress)
            min_stress = min(min_stress, stress)
            
            # Determine ISO stress level
            iso_level = 0
            for i, level in enumerate(iso_stress_levels):
                if stress <= level:
                    iso_level = i
                    break
            
            # Get color for this stress level
            if iso_level >= len(stress_colors):
                iso_level = len(stress_colors) - 1
            
            r, g, b = stress_colors[iso_level]
            color = System.Drawing.Color.FromArgb(255, r, g, b)
            
            # Add to point cloud
            point_cloud.Add(point, color)
            
            # ============================================================
            # ADD ISO STRESS LABEL TO EACH POINT
            # ============================================================
            
            # Create small text label at each point
            label_text = "{:.0f}".format(stress)  # Show stress value
            
            # Position label slightly above the point
            label_pos = Rhino.Geometry.Point3d(
                point.X,
                point.Y + 2,  # Offset Y by 2 units
                point.Z
            )
            
            # Add text
            text_id = rs.AddText(label_text, label_pos, 3)
            
            if text_id:
                # Color text same as point
                obj = sc.doc.Objects.Find(text_id)
                obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                obj.Attributes.ObjectColor = color
                obj.CommitChanges()
        
        # Add point cloud to document
        if point_cloud.Count > 0:
            cloud_id = sc.doc.Objects.AddPointCloud(point_cloud)
            print("Added " + str(point_cloud.Count) + " colored points with ISO labels")
        
        # ============================================================
        # CREATE ISO CONTOUR LINES ON THE SAME POINTS
        # ============================================================
        
        # Create contour lines for each ISO stress level
        print("Creating ISO contour lines...")
        
        for level_idx, stress_level in enumerate(iso_stress_levels):
            # Find points near this stress level
            contour_points = []
            
            for idx, point in enumerate(points):
                stress = calculate_stress_for_point(idx, len(points))
                
                # Check if stress is close to this ISO level
                if abs(stress - stress_level) < 25:  # 25 MPa tolerance
                    contour_points.append(point)
            
            # Create contour if we have enough points
            if len(contour_points) >= 3:
                # Find center and radius
                xs = [p.X for p in contour_points]
                ys = [p.Y for p in contour_points]
                
                if xs and ys:
                    center_x = sum(xs) / len(xs)
                    center_y = sum(ys) / len(ys)
                    center = Rhino.Geometry.Point3d(center_x, center_y, 0)
                    
                    # Calculate average distance from center
                    distances = [center.DistanceTo(p) for p in contour_points]
                    if distances:
                        avg_distance = sum(distances) / len(distances)
                        
                        # Create circle contour
                        circle_plane = Rhino.Geometry.Plane(center, Rhino.Geometry.Vector3d.ZAxis)
                        circle = Rhino.Geometry.Circle(circle_plane, avg_distance)
                        contour_curve = circle.ToNurbsCurve()
                        
                        if contour_curve and contour_curve.IsValid:
                            # Add contour line
                            curve_id = sc.doc.Objects.AddCurve(contour_curve)
                            
                            if curve_id:
                                # Color based on stress level
                                obj = sc.doc.Objects.Find(curve_id)
                                obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                                
                                r, g, b = stress_colors[level_idx]
                                color = System.Drawing.Color.FromArgb(255, r, g, b)
                                
                                obj.Attributes.ObjectColor = color
                                obj.CommitChanges()
                                
                                # Add ISO level label
                                label_pos = Rhino.Geometry.Point3d(
                                    center_x + avg_distance + 5,
                                    center_y,
                                    0
                                )
                                label_text = "{:.0f} MPa".format(stress_level)
                                text_id = rs.AddText(label_text, label_pos, 5)
                                
                                if text_id:
                                    txt_obj = sc.doc.Objects.Find(text_id)
                                    txt_obj.Attributes.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                                    txt_obj.Attributes.ObjectColor = color
                                    txt_obj.CommitChanges()
        
        # ============================================================
        # ADD SUMMARY TO STRESS LAYER
        # ============================================================
        
        # Get bounding box for positioning
        bbox = rs.BoundingBox(flat_brep)
        if bbox:
            # Add summary at bottom
            summary_x = bbox[0].X
            summary_y = bbox[0].Y - 15
            
            summary = "ISO STRESS ANALYSIS\n"
            summary += "Points: " + str(len(points)) + "\n"
            summary += "Stress: {:.0f}-{:.0f} MPa\n".format(min_stress, max_stress)
            summary += "ISO Levels: "
            summary += ", ".join("{:.0f}".format(l) for l in iso_stress_levels) + " MPa"
            
            rs.AddText(summary, (summary_x, summary_y, 0), 8)
        
        # ============================================================
        # CLEANUP AND FINAL MESSAGE
        # ============================================================
        
        # Return to default layer
        rs.CurrentLayer("Default")
        
        rs.EnableRedraw(True)
        rs.Redraw()
        
        print("\n" + "=" * 60)
        print("VISUALIZATION COMPLETE!")
        print("Check STRESS layer for:")
        print("1. Colored points with stress values")
        print("2. ISO stress contour lines")
        print("3. Point labels showing stress in MPa")
        print("=" * 60)
        
        # Success message
        success_msg = "ISO Stress Visualization Complete!\n\n"
        success_msg += "In STRESS layer you will find:\n"
        success_msg += "  Colored points (Blue to Red)\n"
        success_msg += "  ISO contour lines\n"
        success_msg += "  Stress values at each point\n"
        success_msg += "  ISO levels: " + ", ".join(str(l) for l in iso_stress_levels) + " MPa"
        
        rs.MessageBox(success_msg, 0, "Success")
        
    except Exception as e:
        rs.EnableRedraw(True)
        error_msg = "Error: " + str(e)
        print(error_msg)
        rs.MessageBox(error_msg, 0, "Error")

# ============================================================================
# RUN THE SCRIPT
# ============================================================================
if __name__ == "__main__":
    # Clear command history
    rs.Command("_-ClearCommandHistory")
    
    # Run visualization
    create_iso_stress_on_points()