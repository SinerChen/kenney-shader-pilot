"""Build prompts from live workspace entries and public I/O types."""
import hashlib
import json
from pathlib import Path
from io_types import io_schema, schema_markdown
from workspace_layout import public_dir

ROOT = Path(__file__).resolve().parent


def install_types(project, task, write=None):
    project = Path(project).resolve()
    text = json.dumps(io_schema(task), ensure_ascii=False, indent=2) + "\n"
    write = write or (lambda path, content: path.write_bytes(content.encode("utf-8")))
    public = public_dir(project)
    public.mkdir(parents=True, exist_ok=True)
    paths = [public / "io_schema.json", *sorted((public / "sample_inputs").glob("*.json"))]
    for path in paths:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("kind") != "input_output_types":
                key = hashlib.sha256(str(project).encode("utf-8")).hexdigest()[:16]
                archive = ROOT / "author/archived_public_samples" / key / path.name
                archive.parent.mkdir(parents=True, exist_ok=True)
                if not archive.exists():
                    archive.write_bytes(path.read_bytes())
        write(path, text)
    return [path.name for path in paths]


def visible_files(project):
    project=Path(project)
    fixture_names={"adapter_base.gd","base_stage.tscn","bridge.gd","entry.tscn","entry.gd","scene_access.gd","background.gdshader"}
    source_file=public_dir(project) / 'scene_files.json'
    source_files=set(json.loads(source_file.read_text(encoding="utf-8"))["files"]) if source_file.exists() else set()
    source_roots={"Main.tscn","Materials","Meshes","Shaders","Scripts","Textures","Groundcover"}
    files=[]
    for p in project.rglob("*"):
        rel=p.relative_to(project)
        if not p.is_file() or p.is_symlink() or any(part.startswith(".") or part=="__pycache__" for part in rel.parts) or p.suffix==".uid":continue
        name=rel.as_posix();head=rel.parts[0]
        relevant=(name=="project.godot" or head in {"solution","scratch","assets"}
                  or (head=="fixture" and p.name in fixture_names)
                  or (head in source_roots and name in source_files))
        if relevant:files.append(name)
    return sorted(files)


def directory_table(project):
    project=Path(project)
    names={Path(name).parts[0] for name in visible_files(project)}
    names.update(name for name in ["solution","scratch"] if (project/name).is_dir())
    descriptions={
        "project.godot":"当前 Godot 工程配置",
        "Main.tscn":"完整森林场景",
        "fixture":"当前实验场景入口与固定宿主文件",
        "assets":"当前任务使用的纹理、采样数据与输入资源",
        "Materials":"原场景材质资源",
        "Meshes":"原场景模型与网格资源",
        "Shaders":"原场景着色器与相关资源",
        "Scripts":"原场景脚本",
        "Textures":"原场景纹理",
        "Groundcover":"原场景地表植被资源",
        "solution":"本次需要实现或修改的效果文件",
        "scratch":"临时脚本、调试材料与中间文件",
    }
    rows=["| 目录 / 文件 | 内容 |","|---|---|"]
    for name,description in descriptions.items():
        if name in names:
            label=name+("/" if (project/name).is_dir() else "")
            rows.append(f"| {label} | {description} |")
    return "\n".join(rows)


def render_prompt(task, spec, workspace=None):
    project = Path(workspace) if workspace is not None else ROOT / "starters" / task
    if not project.is_dir():
        project = ROOT / "tasks" / task
    effect, algorithm = spec
    return f"""## 1. 效果与算法

效果：{effect}

算法：{algorithm}

## 2. 输入输出类型

以下输入输出约定用于后续的算法函数测试。测试程序将按这些接口和类型传入数据、调用算法函数，并读取返回结果进行验证。

{schema_markdown(task)}

## 可观察和修改的目录

当前实验根目录：`{project.resolve().as_posix()}`。

所有路径相对于当前实验根目录。

{directory_table(project)}

## 工具

- `read(path, start_line=1, line_count=200)`：读取文本文件或列出目录。
- `write(path, content)`：在 solution/ 或 scratch/ 内创建或覆盖文件，content 为完整文本。
- `render(camera=..., frames=..., resolution=...)`：运行当前实现并获取渲染结果，可请求视频。

## 自主渲染观察

你可以自行选择观察位置、角度、距离、连续渲染帧数和图像分辨率。render 的相机参数仅用于本次观察，不改写场景相机或输入配置文件。

例如，从自选位置连续观察 120 帧：

```json
{{"camera":{{"position":[6,4,8],"look_at":[0,0,0]}},"frames":120,"resolution":[960,640]}}
```

camera.position 和 look_at 使用世界坐标，分别表示相机位置与观察目标。省略 camera 时使用场景相机。frames 为连续渲染帧数，使用 1–180 的整数；resolution 为 [宽,高]。

每次 render 从当前文件的新场景实例开始。可以从不同位置重复观察效果，结合渲染结果和日志定位编译或运行问题。

根据实现需要自行调用 read、write 和 render，调用顺序及是否渲染由你决定。完成后简要说明修改了哪些文件和实现了什么效果。
"""
