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
      {logout.isError && <p role="alert">Sign out failed. Please retry.</p>}
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

it.each([503, 403, "network"])(
  "retains a valid session after logout failure %s and supports retry",
  async (failure) => {
    let attempts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).endsWith("/me"))
          return new Response(JSON.stringify(ME));
        attempts += 1;
        if (attempts === 1) {
          if (failure === "network") throw new TypeError("Network interrupted");
          return new Response(
            JSON.stringify({ error: { message: "Logout rejected" } }),
            { status: failure as number },
          );
        }
        return new Response(null, { status: 204 });
      }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    client.setQueryData(meKey, ME);
    const view = render(
      <QueryClientProvider client={client}>
        <SessionProbe />
      </QueryClientProvider>,
    );
    fireEvent.click(screen.getByText("Leave workspace"));
    await screen.findByRole("alert");
    expect(screen.getByText(ME.email)).toBeInTheDocument();
    expect(client.getQueryData(meKey)).toEqual(ME);
    // A fresh observer (analogous to remount) must not see a fabricated signed-out state.
    view.unmount();
    render(
      <QueryClientProvider client={client}>
        <SessionProbe />
      </QueryClientProvider>,
    );
    expect(screen.getByText(ME.email)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Leave workspace"));
    await waitFor(() => expect(client.getQueryData(meKey)).toBeNull());
    vi.unstubAllGlobals();
  },
);

it("handles session expiry while logout is pending without restoring private data", async () => {
  let finish: ((value: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          finish = resolve;
        }),
    ),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  client.setQueryData(meKey, ME);
  client.setQueryData(["transactions"], ["private"]);
  render(
    <QueryClientProvider client={client}>
      <SessionProbe />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByText("Leave workspace"));
  await waitFor(() => expect(finish).toBeDefined());
  finish?.(
    new Response(JSON.stringify({ error: { message: "Session expired" } }), {
      status: 401,
    }),
  );
  await waitFor(() => expect(client.getQueryData(meKey)).toBeNull());
  expect(client.getQueryData(["transactions"])).toBeUndefined();
  vi.unstubAllGlobals();
});
