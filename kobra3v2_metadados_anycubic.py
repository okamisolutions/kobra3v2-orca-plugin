# /// script
# requires-python = ">=3.10"
#
# [tool.orcaslicer.plugin]
# name = "Kobra 3 V2 Anycubic Metadata"
# description = "Adds the Anycubic metadata the Kobra 3 V2 touchscreen expects to OrcaSlicer G-code (export and network upload)."
# author = "Raul Ponce Quaresma"
# version = "0.4.0"
# ///

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Raul Ponce Quaresma. Desenvolvido com assistência de ferramentas de IA.

import json
import re
import orca


def _first_match(text, pattern, default=""):
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else default


def _split_values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip().strip('"') for x in value if str(x).strip()]
    s = str(value)
    return [x.strip().strip('"') for x in s.split(";") if x.strip()]


def _hex_to_rgb(value):
    value = (value or "").strip().strip('"').lstrip("#")
    if len(value) >= 6 and re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
        return [int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)]
    return [222, 67, 67]


def _extract_model_names(text):
    names = re.findall(r"^EXCLUDE_OBJECT_DEFINE\s+NAME=([^\s]+)", text, flags=re.MULTILINE)
    out, seen = [], set()
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out or ["model"]


def _extract_filaments(text, ctx):
    types = _split_values(ctx.config_value("filament_type"))
    colors = _split_values(ctx.config_value("filament_colour"))

    if not types:
        raw = _first_match(text, r"^;\s*filament_type\s*=\s*(.+)$", "PLA")
        types = [x.strip() for x in raw.split(";") if x.strip()] or ["PLA"]

    if not colors:
        raw = _first_match(text, r"^;\s*filament_colour\s*=\s*(.+)$", "#DE4343")
        colors = [x.strip() for x in raw.split(";") if x.strip()] or ["#DE4343"]

    count = max(len(types), len(colors), 1)
    types += [types[-1] if types else "PLA"] * (count - len(types))
    colors += [colors[-1] if colors else "#DE4343"] * (count - len(colors))
    return types[:count], colors[:count]


def _project_info(count, ctx):
    raw = ctx.config_value("flush_volumes_matrix")
    matrix = []

    if raw is not None:
        try:
            vals = str(raw).replace(";", ",").split(",")
            matrix = [float(x) for x in vals if x.strip()]
        except Exception:
            matrix = []

    expected = count * count
    if len(matrix) != expected:
        matrix = [0.0] if count == 1 else [140.0] * expected

    multipliers = [1.0] * max(count, 4 if count == 1 else count)

    if count == 1:
        vector = [140.0, 140.0]
    else:
        vector = [
            matrix[i * count + j]
            for i in range(count)
            for j in range(count)
            if i != j
        ] or [140.0, 140.0]

    return {
        "flush_multiplier": 1.0,
        "flush_volumes_chan_multipliers": multipliers,
        "flush_volumes_matrix": matrix,
        "flush_volumes_vector": vector,
    }


def _process(filename, ctx):
    with open(filename, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    owned_prefixes = (
        "; exclude_object:",
        "; model_instances:",
        "; source_info:",
        "; paint_info =",
        "; project_info =",
        "; flush_multiplier_calculate_by_acnext:",
        "; test_mode:",
        "; filament_colour_type",
    )

    cleaned_lines = [
        line for line in text.splitlines(keepends=True)
        if not line.lstrip().startswith(owned_prefixes)
    ]
    cleaned = "".join(cleaned_lines)

    model_names = _extract_model_names(cleaned)
    types, colors = _extract_filaments(cleaned, ctx)

    source_info = {
        "models": [
            {
                "file_source": 0,
                "mo_file_id": -1,
                "name": name,
                "referrer_source": -1,
            }
            for name in model_names
        ],
        "models_from": 0,
        "plate_index": 1,
        "slice_paras_process": 2,
        "software_version": f"OrcaSlicer {ctx.orca_version} Anycubic-compatible",
    }

    paint_info = [
        {
            "material_type": types[i],
            "paint_color": _hex_to_rgb(colors[i]),
            "paint_index": i,
        }
        for i in range(len(types))
    ]

    project_info = _project_info(len(types), ctx)

    source_json = json.dumps(source_info, separators=(",", ":"))
    paint_json = json.dumps(paint_info, separators=(",", ":"))
    project_json = json.dumps(project_info, separators=(",", ":"))

    out = []
    skip_thumb_padding = False
    added_exec_head = False
    added_m75 = False

    for line in cleaned.splitlines(keepends=True):
        if line.startswith("; THUMBNAIL_BLOCK_START"):
            out.append(line)
            skip_thumb_padding = True
            continue

        if skip_thumb_padding:
            if line.strip() in ("", ";"):
                continue
            skip_thumb_padding = False

        if line.startswith("; thumbnail begin") and "512x512" in line and " top" not in line:
            line = line.rstrip("\r\n") + " top\n"

        if line.startswith("; HEADER_BLOCK_END"):
            out.append("; exclude_object: 1\n")
            out.append(f"; model_instances: {len(model_names)}\n")
            out.append(f"; source_info: {source_json}\n")
            out.append(f"; paint_info = {paint_json}\n")
            out.append(f"; project_info = {project_json}\n")
            out.append("; flush_multiplier_calculate_by_acnext: 1\n")
            out.append("; test_mode: 0\n")

        if (not added_exec_head) and line.startswith("; filament start gcode"):
            out.append("; EXECUTABLE_BLOCK_HEAD\n")
            added_exec_head = True
            out.append(line)
            if not added_m75:
                out.append("M75 ; The first extruder is ready.\n")
                added_m75 = True
            continue

        out.append(line)

    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(out)


class Kobra3V2MetadataPipeline(orca.slicing.SlicingPipelineCapabilityBase):
    def get_name(self):
        return "Kobra 3 V2 Anycubic Metadata"

    def execute(self, ctx):
        if ctx.step != orca.slicing.Step.psGCodePostProcess:
            return orca.ExecutionResult.success()

        try:
            _process(ctx.gcode_path, ctx)
            return orca.ExecutionResult.success(
                f"Kobra 3 V2 metadata applied for {ctx.host or 'file export'}"
            )
        except Exception as exc:
            return orca.ExecutionResult.failure(
                orca.PluginResult.RecoverableError,
                f"Kobra 3 V2 metadata failed: {exc}",
            )


@orca.plugin
class Kobra3V2MetadataPlugin(orca.base):
    def register_capabilities(self):
        orca.register_capability(Kobra3V2MetadataPipeline)
