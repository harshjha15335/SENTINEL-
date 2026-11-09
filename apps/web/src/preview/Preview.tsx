import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@/features/experience/preview.css";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { ApiError } from "@/lib/api";
import { meKey } from "@/features/auth/session";
import {
  AuthorizedWorkspace,
  DemoDossier,
} from "@/features/experience/Dossier";
import { CommandCenter } from "./CommandCenter";
import { PreviewNavigation } from "./PreviewNavigation";
import { MoneyStory } from "@/features/experience/Story";

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
      <div className="v2-preview sentinel-experience">
        <PreviewNavigation />
        <Routes>
          <Route index element={<MoneyStory />} />
          <Route path="command-center" element={<CommandCenter />} />
          <Route path="dossier" element={<DemoDossier />} />
          <Route path="workspace" element={<AuthorizedWorkspace />} />
          <Route
            path="*"
            element={
              <main className="v2-state">
                <h1>Preview page not found.</h1>
                <a href="/__v2-preview">Follow the money</a>
              </main>
            }
          />
        </Routes>
      </div>
    </QueryClientProvider>
  );
}
