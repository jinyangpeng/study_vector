"""验证 contracts/openapi.yaml 是否符合 OpenAPI 3.1 规范。

使用 openapi-spec-validator（pure Python，无需 Node）。

用法：
    python -m scripts.validate_openapi
    # 或
    uv run python -m scripts.validate_openapi

退出码：0=通过；非 0=有错误。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 强制 stdout/stderr 用 UTF-8（Windows 默认 GBK 编码下 emoji 会炸）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_FILE = REPO_ROOT / "contracts" / "openapi.yaml"


def main() -> int:
    if not CONTRACTS_FILE.exists():
        print(f"❌ 找不到契约文件：{CONTRACTS_FILE}", file=sys.stderr)
        return 1

    print(f"▶ 校验 OpenAPI 契约：{CONTRACTS_FILE.relative_to(REPO_ROOT)}")

    try:
        spec_dict, base_uri = read_from_filename(str(CONTRACTS_FILE))
        validate(spec_dict)
    except Exception as e:  # noqa: BLE001
        print(f"❌ 契约校验失败：", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    # 统计信息
    paths = spec_dict.get("paths", {})
    schemas = spec_dict.get("components", {}).get("schemas", {})
    tags = spec_dict.get("tags", [])
    print("✅ 契约校验通过")
    print(f"   - OpenAPI 版本：{spec_dict.get('openapi')}")
    print(f"   - API 版本：    {spec_dict.get('info', {}).get('version')}")
    print(f"   - tags：        {len(tags)} 个")
    print(f"   - paths：       {len(paths)} 个端点")
    print(f"   - schemas：     {len(schemas)} 个")

    # 列出所有端点
    print("\n📋 端点清单：")
    for path, methods in sorted(paths.items()):
        for method, op in methods.items():
            if method.startswith("_") or method not in {
                "get", "post", "put", "delete", "patch"
            }:
                continue
            summary = op.get("summary", "(无)")
            op_id = op.get("operationId", "(无)")
            tags_list = op.get("tags", [])
            print(f"   {method.upper():6} {path:55} [{','.join(tags_list)}] {summary}  op={op_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
