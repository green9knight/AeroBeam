#!/usr/bin/env python
"""Debug script to test loading and running the .aerobeam configuration."""

import json
import traceback
from wing_stress_analyzer import WingStressAnalyzer

def load_and_analyze(filepath):
    """Load config and attempt analysis."""
    print("=" * 70)
    print(f"Testing configuration: {filepath}")
    print("=" * 70)
    
    # Load the config
    print("\n1. Loading configuration file...")
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
        print(f"   [OK] Loaded {len(config)} parameters")
    except Exception as e:
        print(f"   [FAIL] Could not load file: {e}")
        return False
    
    # Validate key parameters
    print("\n2. Validating key parameters...")
    required = ['b', 'root_chord', 'front_spar_type', 'rear_spar_type', 
                'wing_structure_type', 'Weight', 'n']
    missing = [k for k in required if k not in config]
    if missing:
        print(f"   [FAIL] Missing required parameters: {missing}")
        return False
    print(f"   [OK] All required parameters present")
    
    # Check for problematic values
    print("\n3. Checking for problematic values...")
    issues = []
    
    # Check spar types
    if config.get('front_spar_type') == 'C-Channel':
        if 'front_spar_width' not in config or 'front_spar_height' not in config:
            issues.append("C-Channel requires front_spar_width and front_spar_height")
    
    if config.get('rear_spar_type') == 'C-Channel':
        if 'rear_spar_width' not in config or 'rear_spar_height' not in config:
            issues.append("C-Channel requires rear_spar_width and rear_spar_height")
    
    # Check numeric values
    try:
        b = float(config.get('b', 0))
        if b <= 0:
            issues.append(f"Invalid span b={b}")
    except:
        issues.append(f"Cannot parse span: {config.get('b')}")
    
    if issues:
        print("   [WARN] Potential issues found:")
        for issue in issues:
            print(f"      - {issue}")
    else:
        print("   [OK] No obvious issues detected")
    
    # Attempt to create analyzer
    print("\n4. Creating WingStressAnalyzer...")
    try:
        analyzer = WingStressAnalyzer(config)
        print("   [OK] Analyzer created successfully")
    except Exception as e:
        print(f"   [FAIL] Could not create analyzer:")
        print(f"      {type(e).__name__}: {e}")
        traceback.print_exc()
        return False
    
    # Attempt analysis
    print("\n5. Running analysis...")
    try:
        analyzer.analyze()  # analyze() doesn't return anything, sets instance vars
        print("   [OK] Analysis completed successfully")
        
        # Show key results from instance variables
        print("\n6. Key Results:")
        print(f"   Max Front Spar Stress: {analyzer.sigma_max_front:.1f} psi at x={analyzer.x_sigma_max_front:.1f} in")
        print(f"   Max Rear Spar Stress: {analyzer.sigma_max_rear:.1f} psi at x={analyzer.x_sigma_max_rear:.1f} in")
        print(f"   Front Spar MS: {analyzer.ms_front}")
        print(f"   Rear Spar MS: {analyzer.ms_rear}")
        print(f"   Root Shear: {analyzer.V_root:.1f} lb")
        print(f"   Root Moment: {analyzer.M_root:.1f} lb-in")
        print(f"   Max Deflection: {analyzer.z_max:.3f} in")
        
        # Check for failures (ms_front and ms_rear are dicts)
        ms_f = analyzer.ms_front.get('MS', 0) if isinstance(analyzer.ms_front, dict) else analyzer.ms_front
        ms_r = analyzer.ms_rear.get('MS', 0) if isinstance(analyzer.ms_rear, dict) else analyzer.ms_rear
        
        if ms_f < 0 or ms_r < 0:
            print("\n   [WARN] Negative margin of safety detected!")
            if ms_f < 0:
                print(f"      Front spar MS = {ms_f:.3f}")
            if ms_r < 0:
                print(f"      Rear spar MS = {ms_r:.3f}")
        
        return True
        
    except Exception as e:
        print(f"   [FAIL] Analysis failed:")
        print(f"      {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = load_and_analyze("test_config.aerobeam")
    
    print("\n" + "=" * 70)
    if success:
        print("SUCCESS: Configuration is valid and analysis completed")
    else:
        print("FAILURE: Configuration has issues that prevent analysis")
    print("=" * 70)

# Made with Bob
