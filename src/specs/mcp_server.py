"""
MCP server that exposes the specs RAG as tools (prototype, stdio transport).

Run from src/:  SPECS_MCP_USER_ID=<id> python -m specs.mcp_server

The user is fixed per server process by SPECS_MCP_USER_ID and is never a tool argument,
so the model can only search that user's own documents.
Anything printed to stdout would corrupt the MCP stream; log to stderr only.
"""
import json
import os
import sys

if os.path.isdir("/tmp/mcp_lib"):  # temporary: remove once mcp is installed in the image
    sys.path.append("/tmp/mcp_lib")

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mechanics.settings")
django.setup()

from mcp.server.mcpserver import MCPServer  # noqa: E402

from specs.rag_engine import DOC_KEY, get_rag_engine  # noqa: E402
from specs.versions import TRANSLATION_ONLY, library_state  # noqa: E402
from springcalc import CompressionSpring, Material, get_available_materials  # noqa: E402

USER_ID = int(os.environ["SPECS_MCP_USER_ID"])

TRANSLATION_WARNING = (
    "TRANSLATION ONLY, the original may prevail / SOLO TRADUCCIÓN, puede prevalecer el original"
)
NO_RESULTS = (
    "No relevant fragments were found in the user's documents. "
    "/ No se encontraron fragmentos relevantes en los documentos del usuario."
)
CALCULATION_ERROR = "Calculation error / Error de cálculo"


def _magnitude(quantity):
    """Plain float from a pint quantity (or a number)."""
    return float(quantity.magnitude) if hasattr(quantity, "magnitude") else float(quantity)

server = MCPServer(
    "specs",
    instructions="Search the user's engineering specifications (OEM standards) and cite the source document.",
)


@server.tool()
def search_specifications(query: str, max_results: int = 5) -> str:
    """Search the user's engineering specifications (OEM standards) and return the most
    relevant fragments with their source document and OEM. Use it for any requirement,
    limit value or test condition of a standard; never invent values."""
    retriever = get_rag_engine(USER_ID).retriever
    nodes = retriever.retrieve(query)[:max(1, min(max_results, 10))]
    if not nodes:
        return NO_RESULTS
    states = library_state(USER_ID)
    parts = []
    for i, n in enumerate(nodes, 1):
        md = n.node.metadata
        state = states.get(md.get(DOC_KEY))
        warning = f" | {TRANSLATION_WARNING}" if state and state.state == TRANSLATION_ONLY else ""
        parts.append(
            f"[{i}] Document: {md.get('filename', '?')} | OEM: {md.get('company') or '?'} "
            f"| similarity {float(n.score or 0):.2f}{warning}\n{n.node.get_content()[:1500]}"
        )
    return "\n\n".join(parts)


@server.tool()
def list_spring_materials() -> str:
    """List the spring wire material codes accepted by calculate_compression_spring."""
    return ", ".join(str(name) for name in get_available_materials())


@server.tool()
def calculate_compression_spring(
    wire_diameter_mm: float,
    mean_diameter_mm: float,
    total_coils: float,
    free_length_mm: float,
    working_length_mm: float,
    material: str = "SL",
) -> str:
    """Calculate a helical compression spring (closed and ground ends) with the springcalc
    library. Returns the spring rate, solid length, the load and shear stress at the working
    length, and the tensile strength range of the wire. All lengths and diameters are in mm.
    It reports facts only and does NOT judge whether the design is acceptable: compare the
    results with a limit found in a standard (search_specifications) and, if no limit is
    found, say so. Call list_spring_materials first if unsure about the material code."""
    try:
        spring = CompressionSpring(material=Material(material_name=material), wire_diameter=wire_diameter_mm)
        spring.set_diameter(mean_diameter=mean_diameter_mm)
        spring.calculate_spring_properties(nr_coils=total_coils, pitch=None, free_length=free_length_mm)
        spring.empty_tables()
        spring.add_load_position(free_length_mm)
        spring.add_load_position(working_length_mm)
        working = spring.get_data_positions()[-1]
        return json.dumps({
            "material": material,
            "spring_rate_N_per_mm": round(_magnitude(spring.spring_constant), 3),
            "solid_length_mm": round(_magnitude(spring.solid_length), 2),
            "spring_index": round(_magnitude(spring.spring_index), 2),
            "wahl_factor": round(_magnitude(spring.wahl_factor), 3),
            "active_coils": _magnitude(spring.nr_active_coils),
            "wire_length_mm": round(_magnitude(spring.wire_length), 1),
            "working_length_mm": _magnitude(working.position),
            "load_at_working_length_N": round(_magnitude(working.load), 2),
            "shear_stress_at_working_length_MPa": round(_magnitude(working.stress), 1),
            "wire_tensile_strength_min_MPa": _magnitude(spring.RMa_min),
            "wire_tensile_strength_max_MPa": _magnitude(spring.RMa_max),
            "stress_to_min_tensile_strength_ratio": round(
                _magnitude(working.stress) / _magnitude(spring.RMa_min), 3),
            "material_elastic_limit_factor": _magnitude(spring.material.elastic_limit_factor),
        }, indent=2)
    except Exception as exc:  # the library raises ValueError for invalid geometry
        return f"{CALCULATION_ERROR}: {exc}"


if __name__ == "__main__":
    server.run("stdio")
