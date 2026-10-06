"""Read the actual saved FreeCAD shapes; generate diagnostic mesh data only."""
import json
from pathlib import Path
import FreeCAD as App

root = Path('E:/the_harness/records/cad_draft_20261004')
result = {}
for profile in ('compact', 'universal'):
    folder = root / (profile + '_revision2')
    doc = App.openDocument(str(folder / 'integrated_four_card_DRAFT.FCStd'))
    try:
        shapes = []
        core = doc.getObject('IntegratedPrintedCore_DRAFT').Shape
        for obj in doc.Objects:
            if not hasattr(obj, 'Shape'):
                continue
            points, faces = obj.Shape.tessellate(0.8)
            shapes.append({'name': obj.Name, 'label': obj.Label,
                           'points': [[p.x, p.y, p.z] for p in points],
                           'faces': [list(face) for face in faces]})
            if obj.Name.startswith('GPU_'):
                overlap = core.common(obj.Shape)
                if overlap.Volume > 1e-6:
                    points, faces = overlap.tessellate(0.8)
                    shapes.append({'name': 'COLLISION_' + obj.Name,
                                   'label': 'Actual positive-volume intersection',
                                   'points': [[p.x, p.y, p.z] for p in points],
                                   'faces': [list(face) for face in faces]})
        result[profile] = {'shapes': shapes,
                           'state': json.loads((folder / 'state.json').read_text())}
    finally:
        App.closeDocument(doc.Name)
(root / 'preview_geometry.json').write_text(json.dumps(result) + '\n', encoding='utf-8')
print('ACTUAL_SAVED_BREP_PREVIEW_GEOMETRY_EXPORTED', flush=True)
