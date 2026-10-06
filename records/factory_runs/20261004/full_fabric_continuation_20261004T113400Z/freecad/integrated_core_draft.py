import os, json, math

def build(config, output_dir):
    import FreeCAD
    import Part
    if not isinstance(config, dict):
        raise ValueError('config must be dict')
    schema = config.get('schema', {})
    for k in ('compact_L','compact_H','compact_T','gap','margin','universal_L','universal_H','universal_T','base_wall','rail_w','foot_h'):
        v = schema.get(k)
        if v is None or not isinstance(v, (int,float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f'invalid schema param: {k}')
    cL,cH,cT,gap,mg = schema['compact_L'],schema['compact_H'],schema['compact_T'],schema['gap'],schema['margin']
    uL,uH,uT = schema['universal_L'],schema['universal_H'],schema['universal_T']
    bw,rw,fh = schema['base_wall'],schema['rail_w'],schema['foot_h']
    rot = config.get('selected_print_rotation_quarterturn', 0)
    if rot not in (0,1,2,3):
        raise ValueError('rotation must be 0-3 quarter turns')
    core_W = 3*cT + 2*gap + 2*mg
    core_D = cL
    core_H = cH + gap + uT + 2*bw + fh
    limits = [(200,188,254),(188,254,200),(254,200,188),(200,254,188)]
    lW,lD,lH = limits[rot]
    if core_W > lW or core_D > lD or core_H > lH:
        raise ValueError(f'core bbox {core_W}x{core_D}x{core_H} exceeds print limit {lW}x{lD}x{lH} at rot={rot}')
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(output_dir):
        raise FileExistsError(f'refuse existing artifact: {f}')
    doc = FreeCAD.newDocument('DraftCore')
    try:
        shapes = []
        shapes.append(Part.makeBox(core_W, core_D, bw))
        shapes.append(Part.makeBox(core_W, core_D, bw, FreeCAD.Vector(0,0,core_H-bw)))
        for i in range(4):
            x = mg + i*(cT+gap)
            shapes.append(Part.makeBox(rw, core_D, core_H, FreeCAD.Vector(x-rw/2,0,0)))
            shapes.append(Part.makeBox(rw, core_D, core_H, FreeCAD.Vector(x+cT+rw/2,0,0)))
        shapes.append(Part.makeBox(core_W, rw, core_H, FreeCAD.Vector(0,0,0)))
        shapes.append(Part.makeBox(core_W, rw, core_H, FreeCAD.Vector(0,core_D-rw,0)))
        shapes.append(Part.makeBox(core_W, core_D, fh, FreeCAD.Vector(0,0,-fh)))
        rib = Part.makeBox(bw, core_D, core_H/2, FreeCAD.Vector(core_W/2-bw/2,0,bw))
        shapes.append(rib)
        fused = shapes[0]
        for s in shapes[1:]:
            fused = fused.fuse(s)
            fused = fused.removeSplitter()
            if not fused.isValid() or len(fused.Solids) != 1:
                raise RuntimeError('disconnected or invalid shape after fuse')
        gpu_boxes = []
        for i in range(3):
            x = mg + i*(cT+gap)
            b = Part.makeBox(cT, cL, cH, FreeCAD.Vector(x, 0, bw))
            b.Label = f'GPU_Box_{chr(65+i)}_Concept'
            gpu_boxes.append(b)
        dx = mg + gap
        d_box = Part.makeBox(uT, uL, uH, FreeCAD.Vector(dx, 0, bw+cH+gap))
        d_box.Label = 'GPU_Box_D_Concept_Rolled'
        gpu_boxes.append(d_box)
        obj = doc.addObject('Part::Feature', 'Printed_Core_DRAFT')
        obj.Shape = fused
        for gb in gpu_boxes:
            o = doc.addObject('Part::Feature', gb.Label)
            o.Shape = gb
        fcstd_path = os.path.join(output_dir, 'draft_core_4bay.FCStd')
        step_path = os.path.join(output_dir, 'draft_core_4bay.step')
        doc.saveAs(fcstd_path)
        fused.exportStep(step_path)
        state = {'measured': False, 'qualified': False, 'status': 'DRAFT_UNQUALIFIED',
                 'core_bbox_mm': {'W': core_W, 'D': core_D, 'H': core_H},
                 'solid_count': len(fused.Solids), 'print_rotation_quarterturn': rot,
                 'known_assumptions': ['compact_fixture_explicitly_unmeasured','gpu_overhang_allowed','no_48mm_cap','no_appendD','no_restD_on_shroud',
                                       'metal_rails_not_fused','d_support_contact_placeholder_unknown','no_fake_qualified_support_patch',
                                       'receiver_holes_null','psu_bend_fan_plenum_null','lower_card_removal_blocked_by_rolled_top_NOT_CHECKED',
                                       'actual_removal_sweep_unknown','analytical_collision_CONCEPT_ONLY'],
                 'missing_interfaces': ['receiver_pcb_mounts','safe_support_patches','psu_envelope','fan_plenum','cable_bends','fastener_holes_production'],
                 'gates': {'removal_sweep': 'NOT_CHECKED', 'collision': 'CONCEPT_COLLISION', 'fit': 'NO_FITS_PASS'}}
        with open(os.path.join(output_dir, 'state.json'), 'w') as f:
            json.dump(state, f, indent=2)
        return state
    finally:
        FreeCAD.closeDocument(doc.Name)

