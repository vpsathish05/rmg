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
    <div className="min-h-screen w-full flex items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <div className="flex items-center justify-center gap-2 mb-1">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center font-black text-xs text-white"
              style={{ background: "#19105B" }}
            >
              J
            </div>
            <span className="font-bold text-xl" style={{ color: "#19105B" }}>RMG Engine</span>
          </div>
          <p className="text-[10px] font-medium tracking-widest uppercase" style={{ color: "#94A3B8" }}>JMan Group</p>
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

          <Button
            type="submit"
            className="w-full h-10 mt-1 text-white font-semibold"
            style={{ background: "#3411A3" }}
            disabled={pending}
          >
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
  );
}
