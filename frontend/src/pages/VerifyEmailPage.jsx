import { useEffect, useState } from "react";
import { CheckCircle2, LoaderCircle, XCircle } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: "loading", message: "Checking your verification link..." });
  const { refreshUser } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setState({ status: "error", message: "The verification token is missing." });
      return;
    }
    api(`/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(async (result) => {
        await refreshUser();
        setState({ status: "success", message: result.message });
      })
      .catch((error) => setState({ status: "error", message: error.message }));
  }, []);

  const Icon = state.status === "loading" ? LoaderCircle : state.status === "success" ? CheckCircle2 : XCircle;

  return (
    <section className="mx-auto grid min-h-[72vh] max-w-2xl place-items-center px-4 py-16 text-center">
      <div className="w-full border-y border-neutral-300 bg-white px-6 py-12">
        <Icon
          size={48}
          className={`mx-auto ${state.status === "loading" ? "animate-spin text-green-600" : state.status === "success" ? "text-green-600" : "text-red-500"}`}
        />
        <h1 className="mt-5 font-display text-4xl font-semibold text-ink">
          {state.status === "loading" ? "Verifying your email" : state.status === "success" ? "Email verified" : "Link unavailable"}
        </h1>
        <p className="mt-3 text-neutral-600">{state.message}</p>
        {state.status !== "loading" && (
          <Link to="/account" className="mt-7 inline-flex h-11 items-center rounded-md bg-ink px-5 text-sm font-semibold text-white">
            Go to account
          </Link>
        )}
      </div>
    </section>
  );
}
