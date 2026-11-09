import "@fontsource/space-grotesk/latin-400.css";
import "@fontsource/space-grotesk/latin-500.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/jetbrains-mono/latin-400.css";
import "./preview.css";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { ApiError } from "@/lib/api";
import { meKey } from "@/features/auth/session";
import { AuthorizedWorkspace, DemoDossier } from "./Dossier";
import { EvidenceStory } from "./Story";

/** Development only. Private data uses a separate cache and the unchanged API/session. */
export default function Preview() {
  const [client] = useState(() => {
    const cache = new QueryCache({
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) {
          instance.clear();
          instance.setQueryData(meKey, null);
        }
      },
    });
    const instance: QueryClient = new QueryClient({
      queryCache: cache,
      defaultOptions: {
        queries: {
          retry: false,
          refetchOnWindowFocus: false,
          gcTime: 0,
          staleTime: 0,
        },
      },
    });
    return instance;
  });
  return (
    <QueryClientProvider client={client}>
      <div className="v2-preview">
        <Routes>
          <Route index element={<EvidenceStory />} />
          <Route path="dossier" element={<DemoDossier />} />
          <Route path="workspace" element={<AuthorizedWorkspace />} />
          <Route
            path="*"
            element={
              <main className="v2-state">
                <h1>Preview page not found.</h1>
                <a href="/__v2-preview">Return to the reel</a>
              </main>
            }
          />
        </Routes>
      </div>
    </QueryClientProvider>
  );
}
