import { createHandler } from "./receiver.ts";

Deno.serve(createHandler({ env: (name) => Deno.env.get(name), fetch }));
