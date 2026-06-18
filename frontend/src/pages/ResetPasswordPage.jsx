import { useState } from "react";
import { Eye, EyeOff, KeyRound, LoaderCircle } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api("/api/v1/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password })
      });
      setMessage(result.message);
      setPassword("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto grid min-h-[72vh] max-w-xl place-items-center px-4 py-16">
      <div className="w-full border-y border-neutral-300 bg-white px-5 py-10 sm:px-8">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-green-50 text-green-700">
          <KeyRound size={24} />
        </span>
        <p className="mt-5 text-xs font-semibold uppercase text-green-700">Password reset</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ink">Choose a new password</h1>
        <p className="mt-3 leading-7 text-neutral-600">Use at least 8 characters.</p>

        {!token ? (
          <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            The password reset token is missing.
          </p>
        ) : (
          <form onSubmit={submit} className="mt-7 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-neutral-700">New password</span>
              <div className="relative">
                <input
                  required
                  minLength={8}
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                  className="h-11 w-full rounded-md border border-neutral-300 bg-white px-3 pr-11 text-sm outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-1 top-1 grid h-9 w-9 place-items-center text-neutral-500"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
            <button
              type="submit"
              disabled={busy}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
            >
              {busy && <LoaderCircle size={17} className="animate-spin" />}
              Reset password
            </button>
          </form>
        )}

        {message && (
          <p className="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
            {message}
          </p>
        )}
        <Link to="/" className="mt-6 inline-flex text-sm font-semibold text-neutral-500 hover:text-green-700">
          Return to library
        </Link>
      </div>
    </section>
  );
}
