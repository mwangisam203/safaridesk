import { useState } from "react";
import { KeyRound, LoaderCircle, MailCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api("/api/v1/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email })
      });
      setMessage(result.message);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecoveryShell
      icon={KeyRound}
      eyebrow="Account recovery"
      title="Reset your password"
      message="Enter your account email and we will send a password reset link if the account exists."
    >
      <form onSubmit={submit} className="mt-7 space-y-4">
        <EmailField value={email} onChange={setEmail} />
        <SubmitButton busy={busy}>Send reset link</SubmitButton>
      </form>
      {message && <ResultMessage>{message}</ResultMessage>}
    </RecoveryShell>
  );
}

export function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await api("/api/v1/auth/resend-verification-email", {
        method: "POST",
        body: JSON.stringify({ email })
      });
      setMessage(result.message);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecoveryShell
      icon={MailCheck}
      eyebrow="Email verification"
      title="Send a fresh verification link"
      message="Use this if your first verification email expired or never arrived."
    >
      <form onSubmit={submit} className="mt-7 space-y-4">
        <EmailField value={email} onChange={setEmail} />
        <SubmitButton busy={busy}>Send verification email</SubmitButton>
      </form>
      {message && <ResultMessage>{message}</ResultMessage>}
    </RecoveryShell>
  );
}

function RecoveryShell({ icon: Icon, eyebrow, title, message, children }) {
  return (
    <section className="mx-auto grid min-h-[72vh] max-w-xl place-items-center px-4 py-16">
      <div className="w-full border-y border-neutral-300 bg-white px-5 py-10 sm:px-8">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-green-50 text-green-700">
          <Icon size={24} />
        </span>
        <p className="mt-5 text-xs font-semibold uppercase text-green-700">{eyebrow}</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ink">{title}</h1>
        <p className="mt-3 leading-7 text-neutral-600">{message}</p>
        {children}
        <Link to="/" className="mt-6 inline-flex text-sm font-semibold text-neutral-500 hover:text-green-700">
          Return to library
        </Link>
      </div>
    </section>
  );
}

function EmailField({ value, onChange }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-neutral-700">Email address</span>
      <input
        required
        type="email"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="email"
        className="h-11 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100"
      />
    </label>
  );
}

function SubmitButton({ busy, children }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
    >
      {busy && <LoaderCircle size={17} className="animate-spin" />}
      {children}
    </button>
  );
}

function ResultMessage({ children }) {
  return (
    <p className="mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
      {children}
    </p>
  );
}
