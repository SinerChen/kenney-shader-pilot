"""Extract only Forest grass cards and their texture. No network or model calls."""
import json
import shutil
import struct
import certifi
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'realistic/projects/forest'
ASSETS = ROOT / 'project/assets'

def accessor(document, blob, index):
    item = document['accessors'][index]
    view = document['bufferViews'][item['bufferView']]
    size = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
    kind = {5126: 'f', 5121: 'B', 5123: 'H', 5125: 'I'}[item['componentType']]
    stride = view.get('byteStride', size * struct.calcsize(kind))
    offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    return [list(struct.unpack_from('<' + kind*size, blob, offset+i*stride)) for i in range(item['count'])]

def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(certifi.where(), ASSETS/'cacert.pem')
    archive = ROOT / 'source_archive/source'
    archive.mkdir(parents=True, exist_ok=True)
    cards = []
    for name in ('Grass1.glb','Grass2.glb','Grass3.glb','Grass4.glb'):
        source = SOURCE / 'Meshes/Plants' / name
        shutil.copyfile(source, archive / name)
        content = source.read_bytes()
        json_size = struct.unpack_from('<I', content, 12)[0]
        document = json.loads(content[20:20+json_size])
        blob = content[28+json_size:]
        primitive = document['meshes'][0]['primitives'][0]
        positions = accessor(document,blob,primitive['attributes']['POSITION'])
        uvs = accessor(document,blob,primitive['attributes']['TEXCOORD_0'])
        assert len(positions) == 4 and len(uvs) == 4
        # Verified against Godot's imported mesh arrays: preserve glTF UV Y.
        cards.append({'source':name,'positions':positions,'uv':uvs})
    (ASSETS/'grass_cards.json').write_text(json.dumps(cards,indent=2)+'\n',encoding='utf-8')
    for name in ('Grass_BaseColor.png','Grass_ORM.png'):
        shutil.copyfile(SOURCE/'Textures/Plants'/name, ASSETS/name)
    for source_name,target_name in [('LICENSE','LICENSE-Forest.txt'),('Asset Credits.txt','UPSTREAM-ASSET-CREDITS.txt')]:
        shutil.copyfile(SOURCE/source_name,ASSETS/target_name)
    record = {'source_project':'Rytelier/Godot-4-forest-benchmark',
              'source_local':str(SOURCE),'original_asset':'https://polyhaven.com/a/grass_medium_01',
              'cards':4,'original_vertices_per_card':4,'height_segments':18,'width_segments':4,
              'preparation':'Use original card UVs and texture; flatten each bottom edge to ground, scale 4x, subdivide by bilinear interpolation; UV2.y stores normalized root-to-tip position.',
              'retained_originals':'source_archive/source/*.glb (outside runtime project)','model_api_calls':0}
    (ASSETS/'source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Prepared four Forest grass cards and two required textures.')

if __name__ == '__main__':
    main()
