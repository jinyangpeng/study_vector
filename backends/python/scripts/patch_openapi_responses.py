"""一次性脚本：给所有业务端点补 400/404/422 响应。

原因：schemathesis 会随机生成 400（body 解析失败）、422（参数校验失败）、
404（资源不存在）的请求；OpenAPI spec 必须先文档化这些状态码，
否则测试报 "UndefinedStatusCode" 失败。
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_FILE = REPO_ROOT / "contracts" / "openapi.yaml"

# 不补 404/422 的端点（健康探针）
SKIP_PATHS = {"/api/v1/health", "/api/v1/health/ready"}


def main() -> None:
    with open(SPEC_FILE, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    # 补一个通用的 400 响应组件（用于 body 解析失败）
    spec.setdefault("components", {}).setdefault("responses", {})
    if "BadRequestBody" not in spec["components"]["responses"]:
        spec["components"]["responses"]["BadRequestBody"] = {
            "description": "请求体解析失败（JSON 格式错误等）",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ApiResponse"}
                }
            },
        }

    not_found_ref = {"$ref": "#/components/responses/NotFound"}
    bad_request_ref = {"$ref": "#/components/responses/BadRequest"}
    body_parse_ref = {"$ref": "#/components/responses/BadRequestBody"}

    for path, methods in spec["paths"].items():
        if path in SKIP_PATHS:
            continue
        for method, op in methods.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not isinstance(op, dict):
                continue
            op.setdefault("responses", {})

            # 有 path parameter 的端点：补 404
            has_path_param = "{" in path
            if has_path_param and "404" not in op["responses"]:
                op["responses"]["404"] = not_found_ref

            # 有 requestBody 或 POST/PUT/PATCH 端点：补 422（参数语义错误）
            if (
                "requestBody" in op or method in {"post", "put", "patch"}
            ) and "422" not in op["responses"]:
                op["responses"]["422"] = bad_request_ref

            # POST/PUT/PATCH 端点：补 400（body 解析失败）
            if method in {"post", "put", "patch"} and "400" not in op["responses"]:
                op["responses"]["400"] = body_parse_ref

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
