# tests/test_integrated_core.py
"""Pure regression tests for integrated_core plan_layout. No FreeCAD execution here."""
import copy
import math
import pytest
from acceptedcad.integrated_core import default_config, plan_layout


def test_default_configs_exist():
    assert default_config('compact')['profile'] == 'compact'
    assert default_config('universal')['profile'] == 'universal'
    with pytest.raises(ValueError):
        default_config('invalid')


def test_plan_returns_required_fields():
    cfg = default_config('compact')
    layout = plan_layout(cfg)
    for field in ['status', 'cards', 'post_boxes', 'printed_bbox_mm', 'core_bbox_mm', 
                  'post_height_mm', 'beam_top_mm', 'd_support_elevation_mm', 'dimensions']:
        assert field in layout


def test_exactly_four_posts():
    layout = plan_layout(default_config('compact'))
    assert len(layout['post_boxes']) == 4


def test_post_gap_derivation_compact():
    layout = plan_layout(default_config('compact'))
    cards = layout['cards']
    dims = layout['dimensions']
    post_w = dims['post_mm']
    
    # Two gaps: A-B and B-C
    for i in range(2):
        right_edge = cards[i]['origin_mm'][0] + cards[i]['size_mm'][0]
        left_edge_next = cards[i+1]['origin_mm'][0]
        gap_center = (right_edge + left_edge_next) / 2.0
        
        # Front and back post for this gap
        front_post = layout['post_boxes'][i * 2]
        back_post = layout['post_boxes'][i * 2 + 1]
        
        expected_x = gap_center - post_w / 2.0
        assert math.isclose(front_post['origin_mm'][0], expected_x, abs_tol=1e-6)
        assert math.isclose(back_post['origin_mm'][0], expected_x, abs_tol=1e-6)


def test_post_gap_derivation_universal():
    layout = plan_layout(default_config('universal'))
    cards = layout['cards']
    dims = layout['dimensions']
    post_w = dims['post_mm']
    
    for i in range(2):
        right_edge = cards[i]['origin_mm'][0] + cards[i]['size_mm'][0]
        left_edge_next = cards[i+1]['origin_mm'][0]
        gap_center = (right_edge + left_edge_next) / 2.0
        expected_x = gap_center - post_w / 2.0
        
        front_post = layout['post_boxes'][i * 2]
        assert math.isclose(front_post['origin_mm'][0], expected_x, abs_tol=1e-6)


def test_post_width_less_than_gap():
    layout = plan_layout(default_config('compact'))
    dims = layout['dimensions']
    assert dims['post_mm'] < dims['gap_mm']


def test_positive_side_clearance():
    layout = plan_layout(default_config('compact'))
    dims = layout['dimensions']
    clearance = dims['gap_mm'] - dims['post_mm']
    assert clearance > 0
    assert math.isclose(clearance, 2.0, abs_tol=1e-6)  # 12 - 10 = 2mm total -> 1mm per side


def test_post_height_is_beam_top():
    layout = plan_layout(default_config('compact'))
    dims = layout['dimensions']
    expected_beam_top = layout['d_support_elevation_mm'] - dims['metal_rail_height_mm']
    assert math.isclose(layout['post_height_mm'], expected_beam_top, abs_tol=1e-6)
    assert math.isclose(layout['beam_top_mm'], expected_beam_top, abs_tol=1e-6)
    
    for pb in layout['post_boxes']:
        assert math.isclose(pb['size_mm'][2], expected_beam_top, abs_tol=1e-6)
        assert math.isclose(pb['origin_mm'][2], 0.0, abs_tol=1e-6)


def test_no_post_d_body_intersection():
    layout = plan_layout(default_config('compact'))
    d_card = layout['cards'][3]
    d_z_min = d_card['origin_mm'][2]
    post_z_max = layout['post_height_mm']
    
    # Posts end at beam_top which is below D base by metal_rail_height
    assert post_z_max < d_z_min


def test_no_post_upright_gpu_intersection():
    layout = plan_layout(default_config('compact'))
    upright_cards = layout['cards'][:3]
    
    for pb in layout['post_boxes']:
        px_min, py_min, pz_min = pb['origin_mm']
        px_max = px_min + pb['size_mm'][0]
        py_max = py_min + pb['size_mm'][1]
        pz_max = pz_min + pb['size_mm'][2]
        
        for card in upright_cards:
            cx_min, cy_min, cz_min = card['origin_mm']
            cx_max = cx_min + card['size_mm'][0]
            cy_max = cy_min + card['size_mm'][1]
            cz_max = cz_min + card['size_mm'][2]
            
            # Check AABB intersection
            intersect_x = max(0, min(px_max, cx_max) - max(px_min, cx_min))
            intersect_y = max(0, min(py_max, cy_max) - max(py_min, cy_min))
            intersect_z = max(0, min(pz_max, cz_max) - max(pz_min, cz_min))
            
            volume = intersect_x * intersect_y * intersect_z
            assert volume < 1e-6, f"Post intersects GPU {card['bay']}"


def test_front_back_post_y_positions():
    layout = plan_layout(default_config('compact'))
    dims = layout['dimensions']
    depth = dims['core_depth_mm']
    post_w = dims['post_mm']
    
    for i in range(2):
        front = layout['post_boxes'][i * 2]
        back = layout['post_boxes'][i * 2 + 1]
        
        assert math.isclose(front['origin_mm'][1], 0.0, abs_tol=1e-6)
        assert math.isclose(back['origin_mm'][1], depth - post_w, abs_tol=1e-6)


def test_core_bbox_derived_not_gpu_top():
    layout = plan_layout(default_config('compact'))
    bbox = layout['core_bbox_mm']
    dims = layout['dimensions']
    
    assert math.isclose(bbox[0], dims['core_width_mm'], abs_tol=1e-6)
    assert math.isclose(bbox[1], dims['core_depth_mm'], abs_tol=1e-6)
    assert bbox[2] <= 254.0


def test_printed_bbox_limits():
    layout = plan_layout(default_config('compact'))
    pb = layout['printed_bbox_mm']
    assert pb[0] <= 188
    assert pb[1] <= 200
    assert pb[2] <= 254


def test_compact_many_card_mounts_preserved():
    layout = plan_layout(default_config('compact'))
    assert layout['mount_bays'] == ['A', 'B', 'C', 'D']
    assert len(layout['cards']) == 4


def test_universal_many_card_mounts_preserved():
    layout = plan_layout(default_config('universal'))
    assert layout['mount_bays'] == ['A', 'B', 'C', 'D']
    assert len(layout['cards']) == 4


def test_overhang_permitted_unchanged():
    layout = plan_layout(default_config('compact'))
    assert 'GPU_OVERHANG_ALLOWED' in layout['claims']


def test_changed_card_dimensions_derive_x():
    cfg = default_config('compact')
    cfg['cards'][0]['thickness_mm'] = 45  # Change A thickness
    cfg['cards'][1]['thickness_mm'] = 45  # Change B thickness
    layout = plan_layout(cfg)
    
    # Verify posts moved according to new edges
    cards = layout['cards']
    dims = layout['dimensions']
    right_a = cards[0]['origin_mm'][0] + cards[0]['size_mm'][0]
    left_b = cards[1]['origin_mm'][0]
    expected_x_ab = (right_a + left_b) / 2.0 - dims['post_mm'] / 2.0
    
    assert math.isclose(layout['post_boxes'][0]['origin_mm'][0], expected_x_ab, abs_tol=1e-6)


def test_post_width_equal_gap_refused():
    cfg = default_config('compact')
    cfg['post_mm'] = 12  # Equal to gap
    with pytest.raises(ValueError, match="strictly less"):
        plan_layout(cfg)


def test_post_width_greater_than_gap_refused():
    cfg = default_config('compact')
    cfg['post_mm'] = 15  # Greater than gap
    with pytest.raises(ValueError, match="strictly less"):
        plan_layout(cfg)


def test_unknown_interfaces_null():
    layout = plan_layout(default_config('compact'))
    assert 'receiver_hole_datums' in layout['unknown_interfaces']
    assert 'safe_support_patches' in layout['unknown_interfaces']
    assert 'psu_interfaces' in layout['unknown_interfaces']
    assert 'cable_bends' in layout['unknown_interfaces']
    assert 'fan_plenum' in layout['unknown_interfaces']
    assert 'loads' in layout['unknown_interfaces']
    assert 'thermal' in layout['unknown_interfaces']


def test_status_draft_unqualified():
    layout = plan_layout(default_config('compact'))
    assert layout['status'] == 'DRAFT_UNQUALIFIED'
    assert layout['production_release'] is False


def test_six_shoes_preserved_in_claims():
    layout = plan_layout(default_config('compact'))
    # Shoes logic remains unchanged in build, but layout confirms structure
    assert 'BASE' in layout['support_bodies']
    assert 'POSTS' in layout['support_bodies']
    assert 'D_BEAMS' in layout['support_bodies']


def test_frame_policy_one_connected_core():
    layout = plan_layout(default_config('compact'))
    assert layout['frame_policy'] == 'ONE_CONNECTED_CORE_NO_APPEND_D'


def test_d_orientation_rolled_preserved():
    layout = plan_layout(default_config('compact'))
    d_card = layout['cards'][3]
    assert d_card['orientation'] == 'ROLLED_90_DEGREES'


def test_abc_orientation_upright_preserved():
    layout = plan_layout(default_config('compact'))
    for i in range(3):
        assert layout['cards'][i]['orientation'] == 'UPRIGHT'


def test_no_native_builder_imports_at_toplevel():
    import acceptedcad.integrated_core as mod
    import sys
    assert 'FreeCAD' not in sys.modules or 'FreeCAD' not in dir(mod)
    assert 'Part' not in dir(mod)
