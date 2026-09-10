"""Imports the heaviest dependencies and every wheel we built, and reports versions.

Deleted in Task 11. Until then this is the only proof that the wheels in android/wheels
load on a real device, which no build log can give.
"""

import json


def report() -> str:
    out: dict[str, str] = {}
    import lxml
    import numpy
    import orjson
    import ormsgpack
    import pandas
    import pydantic
    import pydantic_core
    import uuid_utils
    import xxhash
    import yaml

    out["numpy"] = numpy.__version__
    out["pandas"] = pandas.__version__
    out["lxml"] = lxml.__version__
    out["pyyaml"] = yaml.__version__
    out["pydantic"] = pydantic.__version__
    out["pydantic_core"] = pydantic_core.__version__
    out["orjson"] = orjson.__version__
    out["ormsgpack"] = ormsgpack.__version__
    out["uuid_utils"] = uuid_utils.__version__
    out["uuid7_works"] = str(len(str(uuid_utils.uuid7())) == 36)
    out["xxhash"] = xxhash.VERSION

    # Prove the native code runs, not just that it imports.
    from pydantic import BaseModel

    class Probe(BaseModel):
        x: int

    out["pydantic_core_validates"] = str(Probe(x="3").x == 3)
    out["orjson_roundtrip"] = str(orjson.loads(orjson.dumps({"a": [1, 2]})) == {"a": [1, 2]})
    out["ormsgpack_roundtrip"] = str(ormsgpack.unpackb(ormsgpack.packb({"b": 2})) == {"b": 2})
    out["xxhash_digest"] = xxhash.xxh3_128_hexdigest(b"wha")[:8]

    import langgraph
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(dict)
    graph.add_node("step", lambda state: {"n": state.get("n", 0) + 1})
    graph.add_edge(START, "step")
    graph.add_edge("step", END)
    out["langgraph"] = getattr(langgraph, "__version__", "imported")
    out["langgraph_runs"] = str(graph.compile().invoke({"n": 0})["n"] == 1)
    return json.dumps(out, indent=1)
