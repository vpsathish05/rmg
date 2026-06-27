"use client";
import { useActionState } from "react";
import { login, type LoginState } from "@/lib/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [state, action, pending] = useActionState<LoginState, FormData>(
    login,
    undefined
  );

  return (
    <div className="min-h-screen flex">
      {/* Left panel — JMan brand */}
      <div
        className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12"
        style={{ background: "#0A1628" }}
      >
        <div>
          <div className="flex items-baseline gap-2 mb-12">
            <span className="text-white font-bold text-xl tracking-tight">RMG</span>
            <span className="text-xs font-medium tracking-widest uppercase" style={{ color: "#0AB5A6" }}>
              JMan Group
            </span>
          </div>
          <h1 className="text-3xl font-semibold text-white leading-snug text-balance mb-4">
            Resource Management<br />for the JMan Group
          </h1>
          <p className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.50)" }}>
            AI-powered resourcing — match the right consultant to the right engagement, faster.
          </p>
        </div>

        {/* Feature list */}
        <div className="space-y-4">
          {[
            { label: "Smart Recommendations", detail: "Scored by skill, competency, availability & productivity" },
            { label: "Live Availability",      detail: "Real-time allocation view across all 1,000+ consultants" },
            { label: "Pipeline Forecasting",   detail: "Demand signals from deal pipeline before SOW is signed" },
          ].map(({ label, detail }) => (
            <div key={label} className="flex gap-3">
              <span
                className="mt-1 w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: "#0AB5A6" }}
              />
              <div>
                <p className="text-sm font-medium text-white">{label}</p>
                <p className="text-xs mt-0.5" style={{ color: "rgba(255,255,255,0.40)" }}>{detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex items-center justify-center bg-background px-6">
        <div className="w-full max-w-sm">
          {/* Mobile brand (hidden on desktop) */}
          <div className="lg:hidden mb-8 text-center">
            <span className="font-bold text-xl text-foreground">RMG</span>
            <span className="ml-2 text-xs font-medium tracking-widest uppercase text-primary">JMan Group</span>
          </div>

          <h2 className="text-xl font-semibold text-foreground mb-1">Sign in</h2>
          <p className="text-sm text-muted-foreground mb-7">Enter your RMG credentials to continue.</p>

          <form action={action} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-foreground mb-1.5">
                Username
              </label>
              <Input
                id="username"
                name="username"
                autoComplete="username"
                autoFocus
                required
                disabled={pending}
                placeholder="rmg"
                className="h-10"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-foreground mb-1.5">
                Password
              </label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                disabled={pending}
                className="h-10"
              />
            </div>

            {state?.error && (
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/8 border border-destructive/20 rounded-md px-3 py-2.5">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {state.error}
              </div>
            )}

            <Button type="submit" className="w-full h-10 mt-1" disabled={pending}>
              {pending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Signing in…</>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <p className="text-xs text-muted-foreground text-center mt-8">
            JMan Group · Resource Management Group
          </p>
        </div>
      </div>
    </div>
  );
}
