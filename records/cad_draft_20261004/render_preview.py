"""Diagnostic plot from actual saved BRep tessellation, not a fit certificate."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

root = Path(__file__).resolve().parent
data = json.loads((root / 'preview_geometry.json').read_text())
fig = plt.figure(figsize=(19, 7.5), facecolor='#fafbfc')
panels = [('compact', True, 'One connected printed core',
           'Measured BRep: 188 × 200 × 200 mm\nFour bays share this continuous support.'),
          ('compact', False, 'Compact hypothetical cards: bodies clear',
           'A–C upright; D rolled above on integral beams.\n199 × 116 × 40 mm fixtures; interfaces unmeasured.'),
          ('universal', False, 'Large envelope trial: REFUSED',
           '360 × 165 × 68 mm fixtures intersect posts.\nRed is actual intersection: 33,000 mm³ in A and C.')]
for index, (profile, core_only, title, caption) in enumerate(panels, 1):
    ax = fig.add_subplot(1, 3, index, projection='3d', computed_zorder=False)
    ax.set_facecolor('#fafbfc')
    all_points = []
    ordered = sorted(data[profile]['shapes'], key=lambda s: s['name'].startswith('COLLISION_'))
    for shape in ordered:
        name = shape['name']
        card = name.startswith('GPU_')
        collision = name.startswith('COLLISION_')
        if core_only and (card or collision or name.startswith('Metal')):
            continue
        points = shape['points']
        triangles = [[points[i] for i in face] for face in shape['faces']]
        all_points.extend(points)
        color = '#df3347' if collision else '#efaa35' if name.startswith('GPU_D') else '#4181c0' if card else '#6b7280' if name.startswith('Metal') else '#304355'
        alpha = 0.98 if collision or core_only else 0.22 if card else 0.88
        poly = Poly3DCollection(triangles, facecolor=color, alpha=alpha,
                               edgecolor='#172a3b', linewidth=0.25,
                               zorder=5 if collision else 3 if card else 2)
        ax.add_collection3d(poly)
        if card:
            origin = [min(p[j] for p in points) for j in range(3)]
            upper = [max(p[j] for p in points) for j in range(3)]
            ax.text((origin[0]+upper[0])/2, upper[1]/2, upper[2]+5,
                    name[4], color='#22384d', weight='bold', fontsize=12, zorder=10)
    bounds = [(min(p[j] for p in all_points), max(p[j] for p in all_points)) for j in range(3)]
    ax.set_xlim(bounds[0][0]-8, bounds[0][1]+8)
    ax.set_ylim(bounds[1][0]-8, bounds[1][1]+8)
    ax.set_zlim(0, bounds[2][1]+12)
    ax.set_box_aspect([b-a for a,b in bounds])
    ax.set_proj_type('ortho')
    ax.view_init(elev=22, azim=-57)
    ax.set_xlabel('width (mm)', labelpad=5, fontsize=9)
    ax.set_ylabel('card length (mm)', labelpad=5, fontsize=9)
    ax.set_zlabel('height (mm)', labelpad=3, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.set_title(title, fontsize=12, weight='bold', pad=15,
                 color='#bc2538' if profile == 'universal' else '#22384d')
    ax.text2D(0.5, -0.09, caption, transform=ax.transAxes, ha='center', va='top', fontsize=10)
fig.suptitle('THE HARNESS  ·  Integrated four-card Tetris draft', x=0.05, ha='left', fontsize=20, weight='bold', color='#22384d')
fig.text(0.05, 0.025, 'DRAFT ONLY  ·  GPU overhang allowed  ·  Contact patches, receiver mounts, PSU, cables, airflow and loads are not qualified  ·  No production STL', fontsize=11, color='#5b6370')
fig.subplots_adjust(left=0.025, right=0.975, top=0.84, bottom=0.17, wspace=0.07)
fig.savefig(root / 'integrated_tetris_actual_brep.png', dpi=150)
fig.savefig(root / 'integrated_tetris_actual_brep.svg')
print('ACTUAL_BREP_DIAGNOSTIC_RENDERED')
