"""Small, documented local adaptations; downloaded source ZIPs remain unchanged."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_forest():
    project = ROOT / 'projects/forest'
    (ROOT / 'verification/forest').mkdir(parents=True, exist_ok=True)
    path = project / 'Main.tscn'
    text = path.read_text(encoding='utf-8')
    nodes_before = text.count('[node ')
    instances_before = text.count('type="MultiMeshInstance3D"')
    # This editor-only scattering plugin was not included in the upstream ZIP.
    # Keep every pre-generated MultiMesh, mesh, transform, material and shader.
    if 'path="res://addons/groundcover/Groundcover.gd"' in text:
        text = re.sub(r'^\[ext_resource[^\n]*id="(?:34_a6vsm|6_lwrrj)"\]\n', '', text, flags=re.M)
        text = text.replace('script = ExtResource("34_a6vsm")\n', '')
        text = text.replace('groundcoverMeshes = [ExtResource("6_lwrrj")]\n', '')
        for line in ['groundcoverData = "res://Groundcover/Groundcover.txt"', 'updateCover = false', 'clear = false']:
            text = text.replace(line+'\n', '')
        text = text.replace('load_steps=3755', 'load_steps=3753', 1)
    if 'id="library_camera"' not in text:
        first_break = text.index('\n')
        text = text[:first_break+1] + '\n[ext_resource type="Script" path="res://library_camera.gd" id="library_camera"]\n' + text[first_break+1:]
        text = text.replace('load_steps=3753', 'load_steps=3754', 1)
        camera = '[node name="Camera3D" type="Camera3D" parent="."]\n'
        text = text.replace(camera, camera + 'script = ExtResource("library_camera")\n')
    assert nodes_before == text.count('[node ')
    assert instances_before == text.count('type="MultiMeshInstance3D"')
    path.write_text(text, encoding='utf-8')
    shutil.copyfile(ROOT / 'tools/forest_camera.gd', project / 'library_camera.gd')
    result = {'scene': 'forest', 'preserved_nodes': nodes_before, 'preserved_multimesh_nodes': instances_before,
              'changes': ['Detach missing groundcover editor generator; keep all baked vegetation.',
                          'Attach free-look controls to the original Camera3D.'],
              'limitation': 'Regenerating vegetation with the missing upstream groundcover plugin is unavailable.'}
    (ROOT / 'verification/forest/adaptation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


def prepare_tps():
    project = ROOT / 'projects/tps'
    (ROOT / 'verification/tps').mkdir(parents=True, exist_ok=True)
    menu = project / 'menu/menu.gd'
    text = menu.read_text(encoding='utf-8')
    if 'Viewport.SCALING_3D_MODE_NEAREST' in text:
        text = text.replace('\tif Settings.config_file.get_value("video", "scale_filter") == Viewport.SCALING_3D_MODE_NEAREST:\n\t\tscale_filter_nearest.button_pressed = true\n\telif Settings.config_file.get_value("video", "scale_filter") == Viewport.SCALING_3D_MODE_BILINEAR:',
                            '\tif Settings.config_file.get_value("video", "scale_filter") == Viewport.SCALING_3D_MODE_BILINEAR:')
        text = text.replace('\tif scale_filter_nearest.button_pressed:\n\t\tSettings.config_file.set_value("video", "scale_filter", Viewport.SCALING_3D_MODE_NEAREST)\n\telif scale_filter_bilinear.button_pressed:',
                            '\tif scale_filter_bilinear.button_pressed:')
        text = text.replace('func _ready() -> void:\n', 'func _ready() -> void:\n\t# Godot 4.6 has no nearest-neighbor 3D resolution scaling.\n\tscale_filter_nearest.hide()\n', 1)
        assert 'Viewport.SCALING_3D_MODE_NEAREST' not in text
        menu.write_text(text, encoding='utf-8')
    config = project / 'project.godot'
    text = config.read_text(encoding='utf-8')
    config.write_text(text.replace('config/features=PackedStringArray("4.7")', 'config/features=PackedStringArray("4.6")'), encoding='utf-8')
    result = {'scene': 'tps', 'changes': ['Hide the 4.7-only nearest-neighbor resolution option and remove its two enum references.',
              'Mark the locally adapted project as Godot 4.6; preserve all geometry, materials, lights and gameplay.']}
    (ROOT / 'verification/tps/adaptation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    prepare_forest()
    prepare_tps()
