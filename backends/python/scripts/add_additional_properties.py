"""一次性脚本：给所有 requestBody schema 加 additionalProperties: false。

原因：schemathesis 会随机生成额外属性，但 FastAPI 用了 extra="forbid"
会拒绝，导致 422。告诉 schemathesis 这些 schema 不允许额外属性，
它就会按规则生成合法数据。
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_FILE = REPO_ROOT / "contracts" / "openapi.yaml"


def main() -> None:
    with open(SPEC_FILE, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    # 遍历所有 requestBody schema，加 additionalProperties: false
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not isinstance(op, dict):
                continue
            if "requestBody" not in op:
                continue

            for content_type, content_obj in op["requestBody"].get(
                "content", {}
            ).items():
                if "schema" in content_obj:
                    schema = content_obj["schema"]
                    # 只给 object 类型加
                    if schema.get("type") == "object" or "$ref" in schema:
                        schema["additionalProperties"] = False

    # 也处理 components.schemas 里的 object
    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        if isinstance(schema, dict) and schema.get("type") == "object":
            schema["additionalProperties"] = False

    with open(SPEC_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            spec,
            f,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

    print(f"Updated {SPEC_FILE}")


if __name__ == "__main__":
    main()
