from dataclasses import replace
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from google.genai.types import FunctionCallingConfigMode

class SentinelGoogleJsonSchemaTransformer(GoogleJsonSchemaTransformer):
    def __init__(self, schema, *, strict=None, **kwargs):
        super().__init__(
            schema,
            strict=strict,
            prefer_inlined_defs=True,
            simplify_nullable_unions=True,
        )

    def transform(self, schema):
        schema = super().transform(schema)
        # Strip keywords that Gemini's OpenAPI 3.0 subset parser rejects
        schema.pop("minItems", None)
        schema.pop("maxItems", None)
        return schema

class SentinelGoogleModel(GoogleModel):
    def prepare_request(self, model_settings, model_request_parameters):
        model_settings, model_request_parameters = super().prepare_request(model_settings, model_request_parameters)
        
        def clean_tool(tool_def):
            transformer = SentinelGoogleJsonSchemaTransformer(tool_def.parameters_json_schema, strict=tool_def.strict)
            clean_schema = transformer.walk()
            return replace(tool_def, parameters_json_schema=clean_schema)

        model_request_parameters = replace(
            model_request_parameters,
            function_tools=[clean_tool(t) for t in model_request_parameters.function_tools],
            output_tools=[clean_tool(t) for t in model_request_parameters.output_tools],
        )
        return model_settings, model_request_parameters

    async def _build_content_and_config(self, messages, model_settings, model_request_parameters):
        contents, config = await super()._build_content_and_config(
            messages, model_settings, model_request_parameters
        )
        # Fix Bug 1: Pydantic-AI 2.55.0 bug where response_modalities is sent as ['TEXT']
        # even when tool-use is forced or tools are present.
        if config.get("tools"):
            config["response_modalities"] = None

        # Fix Bug 2: Upgrade mode: ANY to VALIDATED (or AUTO)
        tool_config = config.get("tool_config")
        if tool_config and "function_calling_config" in tool_config:
            fcc = tool_config["function_calling_config"]
            if fcc.get("mode") == FunctionCallingConfigMode.ANY:
                if self.profile.get("google_supports_strict_tool_definition", False):
                    fcc["mode"] = FunctionCallingConfigMode.VALIDATED
                else:
                    fcc["mode"] = FunctionCallingConfigMode.AUTO

        return contents, config

