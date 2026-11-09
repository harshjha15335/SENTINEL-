from app.services.investigation.schemas import InvestigationFindings
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from pydantic import TypeAdapter

schema = TypeAdapter(InvestigationFindings).json_schema()
has_defs_orig = "$defs" in schema
print("Original schema has $defs:", has_defs_orig)

t1 = GoogleJsonSchemaTransformer(schema, prefer_inlined_defs=True, simplify_nullable_unions=True)
transformed = t1.walk()
has_defs_trans = "$defs" in transformed
has_ref_trans = "$ref" in str(transformed)
print("Transformed schema has $defs:", has_defs_trans)
print("Transformed schema has $ref:", has_ref_trans)

