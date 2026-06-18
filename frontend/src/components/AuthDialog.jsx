import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, LoaderCircle, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const initialLogin = { email: "", password: "" };
const initialRegister = {
  full_name: "",
  email: "",
  phone_number: "",
  password: ""
};

export function AuthDialog({ open, mode: initialMode = "login", onClose }) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState(initialLogin);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setMode(initialMode);
      setForm(initialMode === "login" ? initialLogin : initialRegister);
      setError("");
    }
  }, [open, initialMode]);

  if (!open) return null;

  function switchMode(next) {
    setMode(next);
    setError("");
    setForm(next === "login" ? initialLogin : initialRegister);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(form);
      else await register(form);
      onClose();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-ink/45 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md overflow-hidden rounded-lg border border-white/40 bg-white shadow-soft">
        <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase text-green-600">SafariDesk account</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink">
              {mode === "login" ? "Welcome back" : "Create your reader profile"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="grid h-9 w-9 place-items-center rounded-md text-neutral-500 hover:bg-neutral-100"
            aria-label="Close"
          >
            <X size={19} />
          </button>
        </div>

        <div className="grid grid-cols-2 border-b border-neutral-200 bg-neutral-50 p-1">
          {["login", "register"].map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => switchMode(item)}
              className={`h-10 rounded-md text-sm font-semibold capitalize ${
                mode === item ? "bg-white text-ink shadow-sm" : "text-neutral-500"
              }`}
            >
              {item}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-4 p-6">
          {mode === "register" && (
            <>
              <Field
                label="Full name"
                value={form.full_name}
                onChange={(value) => setForm({ ...form, full_name: value })}
                autoComplete="name"
              />
              <Field
                label="Phone number"
                value={form.phone_number}
                onChange={(value) => setForm({ ...form, phone_number: value })}
                placeholder="0712 345 678"
                autoComplete="tel"
              />
            </>
          )}
          <Field
            label="Email address"
            type="email"
            value={form.email}
            onChange={(value) => setForm({ ...form, email: value })}
            autoComplete="email"
          />
          <label className="block">
            <span className="mb-1.5 block text-sm font-semibold text-neutral-700">Password</span>
            <div className="relative">
              <input
                required
                minLength={mode === "register" ? 8 : undefined}
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
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

          {error && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-60"
          >
            {busy && <LoaderCircle size={17} className="animate-spin" />}
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
          {mode === "login" && (
            <div className="flex items-center justify-between gap-3 text-sm">
              <Link
                to="/forgot-password"
                onClick={onClose}
                className="font-semibold text-green-700 hover:text-ink"
              >
                Forgot password?
              </Link>
              <Link
                to="/resend-verification"
                onClick={onClose}
                className="font-semibold text-neutral-500 hover:text-ink"
              >
                Resend verification
              </Link>
            </div>
          )}
          {mode === "register" && (
            <p className="text-center text-xs leading-5 text-neutral-500">
              We will email you a verification link before payments are enabled.
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", ...props }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-semibold text-neutral-700">{label}</span>
      <input
        required
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100"
        {...props}
      />
    </label>
  );
}
