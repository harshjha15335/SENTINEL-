import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { CursorSmudge } from "@/components/ui/CursorSmudge";
import { WalletOrbit } from "./WalletOrbit";
import { introWasCompleted, resetIntro } from "@/features/experience/introSession";
import { ErrorState } from "@/components/ui/States";

import { useLogin, useMe } from "./session";

// Keep validation compatible with the existing CSP without probing dynamic code generation.
z.config({ jitless: true });

const schema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const me = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/app";
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (me.data) {
    const finishedIntro = introWasCompleted();
    return <Navigate to={finishedIntro ? from : "/intro"} replace state={finishedIntro ? undefined : { from }} />;
  }

  const onSubmit = handleSubmit((values) =>
    login.mutate(values, {
      onSuccess: () => {
        resetIntro();
        navigate("/intro", { replace: true, state: { from } });
      },
    }),
  );

  return (
    <main className="workspace-auth">
      <CursorSmudge />
      <section className="workspace-auth-story">
        <Link to="/" className="workspace-brand">
          <span>S</span>SENTINEL
        </Link>
        <div className="workspace-auth-story-copy">
          <p className="workspace-kicker">FOLLOW THE MONEY</p>
          <h2>
            Investigate payments.
            <br />Decide with evidence.
          </h2>
          <p>
            Review unusual payment patterns, trace risk signals, and document
            human decisions in one workspace.
          </p>
        </div>
        <WalletOrbit />
        <p className="workspace-auth-provenance">Sandbox workspace · illustrative payment data.</p>
      </section>
      <section className="workspace-auth-form">
        <div>
          <div className="auth-brand mb-8 flex items-center gap-2.5">
            <ShieldCheck aria-hidden className="size-6 text-accent" />
            <div>
              <p className="text-base font-semibold tracking-[0.14em]">
                SENTINEL
              </p>
              <p className="text-xs text-fg-subtle">
                Payment trust &amp; recovery · sandbox
              </p>
            </div>
          </div>
          <h1 className="text-xl font-semibold">Sign in to your workspace</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Merchant operators only. Sessions expire after 8 hours.
          </p>
          <form
            onSubmit={onSubmit}
            noValidate
            className="mt-6 flex flex-col gap-4"
          >
            <Field label="Work email" error={errors.email?.message} id="email">
              <input
                id="email"
                type="email"
                autoComplete="username"
                {...register("email")}
                className={inputClass}
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? "email-error" : undefined}
              />
            </Field>
            <Field
              label="Password"
              error={errors.password?.message}
              id="password"
            >
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
                className={inputClass}
                aria-invalid={!!errors.password}
                aria-describedby={
                  errors.password ? "password-error" : undefined
                }
              />
            </Field>
            {login.error && <ErrorState error={login.error} />}
            <Button type="submit" busy={login.isPending} className="mt-2 h-10">
              Sign in
            </Button>
          </form>
        </div>
      </section>
    </main>
  );
}

const inputClass =
  "h-10 w-full rounded-md border border-line-strong bg-sunken px-3 text-sm text-fg placeholder:text-fg-subtle focus:border-accent focus:outline-none aria-[invalid=true]:border-critical";

function Field({
  label,
  id,
  error,
  children,
}: {
  label: string;
  id: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-fg-muted">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="text-xs text-critical">
          {error}
        </p>
      )}
    </div>
  );
}
