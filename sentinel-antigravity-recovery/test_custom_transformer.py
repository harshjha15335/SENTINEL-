import json
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from app.services.investigation.schemas import InvestigationFindings
from pydantic import TypeAdapter

class SentinelGoogleJsonSchemaTransformer(GoogleJsonSchemaTransformer):
    def __init__(self, schema, *, strict=None, **kwargs):
        super().__init__(
            schema,
            strict=strict,
            prefer_inlined_defs=True,
            simplify_nullable_unions=True,
        )

schema = TypeAdapter(InvestigationFindings).json_schema()
transformed = SentinelGoogleJsonSchemaTransformer(schema).walk()

print("Has $defs:", "$defs" in transformed)
print("Has $ref:", "$ref" in str(transformed))
print("Has anyOf null:", "{'type': 'null'}" in str(transformed))
print("Sample of transformed:")
print(json.dumps(transformed, indent=2)[:500])

