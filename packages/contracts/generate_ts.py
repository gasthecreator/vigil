#!/usr/bin/env python3
"""Generate TypeScript types and client from docs/api/openapi.json.

Adheres to MASTER_PLAN.md §9.2, WP5.5, and Phase 5 deliverables.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "docs" / "api" / "openapi.json"
OUT_DIR = ROOT / "packages" / "contracts" / "ts"


def map_schema_type_to_ts(prop: dict) -> str:
    """Map OpenAPI property schema to TypeScript type string."""
    if "$ref" in prop:
        return prop["$ref"].split("/")[-1]

    any_of = prop.get("anyOf")
    if any_of:
        types = [map_schema_type_to_ts(t) for t in any_of]
        return " | ".join(types)

    prop_type = prop.get("type")
    if prop_type == "string":
        if prop.get("format") == "date-time":
            return "string /* ISO 8601 */"
        return "string"
    elif prop_type in ("integer", "number"):
        return "number"
    elif prop_type == "boolean":
        return "boolean"
    elif prop_type == "array":
        items = prop.get("items", {})
        item_ts = map_schema_type_to_ts(items)
        return f"{item_ts}[]"
    elif prop_type == "object":
        add_props = prop.get("additionalProperties")
        if add_props and isinstance(add_props, dict):
            val_ts = map_schema_type_to_ts(add_props)
            return f"Record<string, {val_ts}>"
        return "Record<string, unknown>"
    elif prop_type == "null":
        return "null"
    return "unknown"


def generate_ts():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    schemas = spec.get("components", {}).get("schemas", {})

    types_lines = [
        "/**",
        " * Auto-generated TypeScript types for Vigil Precision Oncology Platform API.",
        " * Generated from docs/api/openapi.json. DO NOT EDIT DIRECTLY.",
        " */",
        "",
    ]

    for name, schema in sorted(schemas.items()):
        description = schema.get("description", "")
        if description:
            types_lines.append(f"/** {description} */")

        schema_type = schema.get("type")
        enum_vals = schema.get("enum")
        if enum_vals:
            enum_ts = " | ".join([json.dumps(v) for v in enum_vals])
            types_lines.append(f"export type {name} = {enum_ts};\n")
            continue

        if schema_type == "object" or "properties" in schema:
            types_lines.append(f"export interface {name} {{")
            required = set(schema.get("required", []))
            for prop_name, prop_def in sorted(schema.get("properties", {}).items()):
                prop_desc = prop_def.get("description", "")
                if prop_desc:
                    types_lines.append(f"  /** {prop_desc} */")
                opt = "" if prop_name in required else "?"
                ts_type = map_schema_type_to_ts(prop_def)
                types_lines.append(f"  {prop_name}{opt}: {ts_type};")
            types_lines.append("}\n")
        else:
            types_lines.append(f"export type {name} = {map_schema_type_to_ts(schema)};\n")

    types_file = OUT_DIR / "types.ts"
    with open(types_file, "w", encoding="utf-8") as f:
        f.write("\n".join(types_lines))

    # Generate typed client wrapper
    client_lines = [
        "/**",
        " * Auto-generated API client for Vigil Precision Oncology Platform.",
        " * Generated from docs/api/openapi.json.",
        " */",
        "",
        'import type * as Types from "./types";',
        "",
        "export interface ClientConfig {",
        "  baseUrl: string;",
        "  authToken?: string;",
        "  role?: string;",
        "  userId?: string;",
        "}",
        "",
        "export class VigilApiClient {",
        "  constructor(private config: ClientConfig) {}",
        "",
        "  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {",
        "    const headers = new Headers(options.headers || {});",
        '    if (this.config.authToken) headers.set("Authorization", `Bearer ${this.config.authToken}`);',
        '    if (this.config.role) headers.set("X-Vigil-Role", this.config.role);',
        '    if (this.config.userId) headers.set("X-Vigil-User-Id", this.config.userId);',
        '    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {',
        '      headers.set("Content-Type", "application/json");',
        "    }",
        "",
        "    const resp = await fetch(`${this.config.baseUrl}${path}`, { ...options, headers });",
        "    if (!resp.ok) {",
        "      const errorBody = await resp.text();",
        "      throw new Error(`HTTP ${resp.status}: ${errorBody}`);",
        "    }",
        "    return resp.json() as Promise<T>;",
        "  }",
        "",
        "  // Health & Root",
        "  async getRoot(): Promise<Record<string, unknown>> {",
        '    return this.request("/");',
        "  }",
        "",
        "  // Patients & Surveillance",
        "  async createPatient(patient: Types.PatientCreate): Promise<Types.PatientSummary> {",
        '    return this.request("/api/v1/patients/", { method: "POST", body: JSON.stringify(patient) });',
        "  }",
        "",
        "  async ingestObservation(patientId: string, obs: Types.ObservationCreateRequest): Promise<Types.ObservationCreateResponse> {",
        '    return this.request(`/api/v1/patients/${patientId}/observations`, { method: "POST", body: JSON.stringify(obs) });',
        "  }",
        "",
        "  // Alerts",
        "  async listAlerts(statusFilter = 'open'): Promise<Types.AlertSummary[]> {",
        '    return this.request(`/api/v1/alerts/?status_filter=${statusFilter}`);',
        "  }",
        "",
        "  async acknowledgeAlert(alertId: string, ack: Types.AlertAcknowledgeRequest): Promise<Types.AlertAcknowledgeResponse> {",
        '    return this.request(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST", body: JSON.stringify(ack) });',
        "  }",
        "",
        "  // Offline Sync Replay",
        "  async processSyncBatch(batch: Types.SyncBatchRequest): Promise<Types.SyncBatchResponse> {",
        '    return this.request("/api/v1/sync/batch", { method: "POST", body: JSON.stringify(batch) });',
        "  }",
        "",
        "  // Audit Verification",
        "  async verifyAuditChain(): Promise<{ valid: boolean; total_events: number; head_hash: string }> {",
        '    return this.request("/api/v1/audit/verify");',
        "  }",
        "}",
        "",
    ]

    client_file = OUT_DIR / "client.ts"
    with open(client_file, "w", encoding="utf-8") as f:
        f.write("\n".join(client_lines))

    index_file = OUT_DIR / "index.ts"
    with open(index_file, "w", encoding="utf-8") as f:
        f.write('export * from "./types";\nexport * from "./client";\n')

    print(f"Generated TypeScript types & client in {OUT_DIR}")


if __name__ == "__main__":
    generate_ts()
