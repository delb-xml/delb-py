import ast
import asyncio
from io import StringIO
from pathlib import Path
from typing import Final

FIRST_LINE_COMMENT: Final = "# DO NOT EDIT! this files is generated.\n"


async def generate_reexports(exports: ast.Assign, target_file: Path) -> None:
    b = StringIO()

    b.write(FIRST_LINE_COMMENT)
    b.write("# flake8: noqa\n")
    b.write(f"from _delb.{target_file.stem} import (\n")

    assert isinstance(exports.value, ast.Tuple)
    for node in exports.value.elts:
        match node:
            case ast.Attribute():
                assert isinstance(node.value, ast.Name)
                b.write(f"{node.value.id},\n")
            case ast.Constant():
                assert isinstance(node.value, str)
                b.write(f"{node.value},\n")
            case _:
                raise RuntimeError(f"Unhandled node type: {node.__class__.__name__}")

    b.write(")\n")
    b.write(ast.unparse(exports))

    target_file.write_text(b.getvalue())


def get_exports(module_node: ast.Module) -> ast.Assign:
    for node in reversed(module_node.body):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        assert isinstance(target, ast.Name)
        if target.id != "__all__":
            continue
        assert isinstance(target.ctx, ast.Store)
        assert isinstance(node.value, ast.Tuple)
        return node
    raise RuntimeError("No exports found.")


def parse_file(module_file: Path) -> ast.Module:
    return ast.parse(module_file.read_text(), filename=module_file.name)


async def process_module(source_file: Path, target_file: Path) -> None:
    source_exports = get_exports(parse_file(source_file))
    target_exports = get_exports(parse_file(target_file))

    if ast.compare(source_exports, target_exports):
        print(f"Skipping {source_file.name} (unchanged)")
        return

    await generate_reexports(source_exports, target_file)


async def main() -> None:
    root_folder = Path(__file__).parent.resolve()
    source_folder = root_folder / "_delb"
    target_folder = root_folder / "delb"

    async with asyncio.TaskGroup() as task_group:
        for module_file in target_folder.glob("*.py"):
            with module_file.open("rt") as f:
                if f.readline() != FIRST_LINE_COMMENT:
                    print(f"Skipping {module_file.name} (no valid target)")
                    continue
            task_group.create_task(
                process_module(source_folder / module_file.name, module_file)
            )


if __name__ == "__main__":
    asyncio.run(main())
