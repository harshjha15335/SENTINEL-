import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useLogout, useMe, meKey } from "./session";
import { ME } from "@/test/utils";
function SessionProbe() {
  const me = useMe();
  const logout = useLogout();
  return (
    <>
      <p>{me.data?.email ?? "Signed out"}</p>
      <button onClick={() => logout.mutate()}>Leave workspace</button>
    </>
  );
}
it("sign-out updates an active session observer and removes cached private records", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(null, { status: 204 })),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  client.setQueryData(meKey, ME);
  client.setQueryData(["transactions"], [{ id: "private-record" }]);
  render(
    <QueryClientProvider client={client}>
      <SessionProbe />
    </QueryClientProvider>,
  );
  expect(screen.getByText(ME.email)).toBeInTheDocument();
  fireEvent.click(screen.getByText("Leave workspace"));
  await waitFor(() =>
    expect(screen.getByText("Signed out")).toBeInTheDocument(),
  );
  expect(client.getQueryData(["transactions"])).toBeUndefined();
  expect(client.getQueryData(meKey)).toBeNull();
  vi.unstubAllGlobals();
});
