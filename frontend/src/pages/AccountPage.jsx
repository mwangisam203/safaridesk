import { useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  LoaderCircle,
  MailCheck,
  Shield,
  UserRound
} from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { TierBadge } from "../components/TierBadge";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { formatDate } from "../lib/content";

export function AccountPage() {
  const { user, subscription, loading } = useAuth();
  const [verificationMessage, setVerificationMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (loading) return <div className="grid min-h-[70vh] place-items-center"><LoaderCircle className="animate-spin text-green-600" /></div>;
  if (!user) return <Navigate to="/" replace />;

  async function resendVerification() {
    setBusy(true);
    try {
      const result = await api("/api/v1/auth/resend-verification", { method: "POST" });
      setVerificationMessage(result.message);
    } catch (error) {
      setVerificationMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  const statusTone = subscription?.status === "grace_period"
    ? "border-yellow-300 bg-yellow-50 text-yellow-900"
    : subscription?.is_active
      ? "border-green-200 bg-green-50 text-green-800"
      : "border-neutral-300 bg-white text-neutral-700";

  return (
    <section className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="flex flex-col gap-5 border-b border-neutral-200 pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-green-700">Reader account</p>
          <h1 className="mt-2 font-display text-4xl font-semibold text-ink">Good to see you, {user.full_name.split(" ")[0]}.</h1>
          <p className="mt-2 text-neutral-500">{user.email}</p>
        </div>
        <TierBadge tier={user.subscription_tier} />
      </div>

      {!user.is_verified && (
        <div className="mt-6 flex flex-col gap-4 rounded-md border border-yellow-300 bg-yellow-50 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-yellow-700" />
            <div>
              <p className="font-semibold text-yellow-900">Verify your email to enable payments</p>
              <p className="mt-1 text-sm text-yellow-800">Your reading account works, but subscriptions and admin actions stay locked.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={resendVerification}
            disabled={busy}
            className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-semibold text-white"
          >
            {busy ? <LoaderCircle size={16} className="animate-spin" /> : <MailCheck size={16} />}
            Resend email
          </button>
          {verificationMessage && <span className="text-sm text-yellow-900">{verificationMessage}</span>}
        </div>
      )}

      <div className="mt-7 grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <article className="rounded-lg border border-neutral-200 bg-white p-6 shadow-soft sm:p-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase text-neutral-500">Subscription</p>
              <h2 className="mt-2 font-display text-3xl font-semibold text-ink">
                {subscription?.tier?.toUpperCase() || "FREE"} access
              </h2>
            </div>
            {subscription?.is_active ? <CheckCircle2 className="text-green-600" /> : <Shield className="text-neutral-400" />}
          </div>
          <div className={`mt-6 rounded-md border p-4 ${statusTone}`}>
            <p className="font-semibold">{subscription?.message || "You are on the FREE tier."}</p>
          </div>
          <dl className="mt-6 grid gap-5 sm:grid-cols-3">
            <Metric label="Status" value={subscription?.status || "free"} />
            <Metric label="Days remaining" value={subscription?.days_remaining ?? "—"} />
            <Metric label="Expires" value={subscription?.expires_at ? formatDate(subscription.expires_at) : "—"} />
          </dl>
          <Link to="/plans" className="mt-7 inline-flex h-11 items-center rounded-md bg-ink px-5 text-sm font-semibold text-white hover:bg-green-700">
            {subscription?.is_active ? "Renew or change plan" : "Choose a plan"}
          </Link>
        </article>

        <article className="rounded-lg border border-neutral-200 bg-white p-6 sm:p-7">
          <p className="text-xs font-semibold uppercase text-neutral-500">Profile details</p>
          <div className="mt-5 space-y-5">
            <ProfileRow icon={UserRound} label="Full name" value={user.full_name} />
            <ProfileRow icon={CalendarDays} label="Member since" value={formatDate(user.created_at)} />
            <ProfileRow icon={MailCheck} label="Email status" value={user.is_verified ? "Verified" : "Not verified"} />
            <ProfileRow icon={Shield} label="Account status" value={user.is_active ? "Active" : "Inactive"} />
          </div>
        </article>
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-neutral-400">{label}</dt>
      <dd className="mt-1 capitalize text-neutral-800">{String(value).replace("_", " ")}</dd>
    </div>
  );
}

function ProfileRow({ icon: Icon, label, value }) {
  return (
    <div className="flex gap-3 border-b border-neutral-100 pb-4 last:border-0">
      <Icon size={19} className="mt-0.5 text-green-600" />
      <div>
        <p className="text-xs font-semibold uppercase text-neutral-400">{label}</p>
        <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
      </div>
    </div>
  );
}
