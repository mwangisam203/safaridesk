import { useEffect, useRef, useState } from "react";
import { Check, LoaderCircle, Phone, ShieldCheck, Smartphone } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { TierBadge } from "../components/TierBadge";

const benefits = {
  basic: [
    "Unlimited BASIC article access",
    "Practical API, database, and DevOps guides",
    "Renewal reminders by email and SMS"
  ],
  pro: [
    "Everything in BASIC",
    "Advanced fintech and production systems",
    "Full PRO library access"
  ]
};

export function PlansPage() {
  const { user, refreshUser } = useAuth();
  const [plans, setPlans] = useState([]);
  const [selected, setSelected] = useState(null);
  const [phone, setPhone] = useState(user?.phone_number || "");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    api("/api/v1/payments/plans").then((data) => setPlans(data.plans));
  }, []);

  useEffect(() => {
    if (user?.phone_number) setPhone(user.phone_number);
  }, [user]);

  useEffect(() => () => {
    if (pollingRef.current) window.clearInterval(pollingRef.current);
  }, []);

  async function pay(plan) {
    setNotice(null);
    setPaymentStatus(null);
    if (!user) {
      setNotice({ type: "error", text: "Sign in or create an account before subscribing." });
      return;
    }
    if (!user.is_verified) {
      setNotice({ type: "error", text: "Verify your email before starting an M-Pesa payment." });
      return;
    }
    setSelected(plan.tier);
    setBusy(true);
    try {
      const result = await api("/api/v1/payments/stk-push", {
        method: "POST",
        body: JSON.stringify({ tier: plan.tier, phone_number: phone || null })
      });
      setPaymentStatus({
        checkout_request_id: result.checkout_request_id,
        status: "pending",
        message: result.message
      });
      pollPaymentStatus(result.checkout_request_id);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  function pollPaymentStatus(checkoutRequestId) {
    if (pollingRef.current) window.clearInterval(pollingRef.current);
    let attempts = 0;
    const maxAttempts = 24;

    pollingRef.current = window.setInterval(async () => {
      attempts += 1;
      try {
        const status = await api(`/api/v1/payments/status/${checkoutRequestId}`);
        setPaymentStatus(status);

        if (status.status === "completed") {
          window.clearInterval(pollingRef.current);
          pollingRef.current = null;
          setNotice({ type: "success", text: status.message });
          await refreshUser();
        }

        if (status.status === "failed" || status.status === "cancelled") {
          window.clearInterval(pollingRef.current);
          pollingRef.current = null;
          setNotice({ type: "error", text: status.message });
        }
      } catch (error) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
        setNotice({ type: "error", text: error.message });
      }

      if (attempts >= maxAttempts) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
        setPaymentStatus((current) => current && {
          ...current,
          message: "Still waiting for confirmation. You can check your account in a moment."
        });
      }
    }, 5000);
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8 lg:py-16">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase text-green-700">Simple 30-day access</p>
        <h1 className="mt-2 font-display text-5xl font-semibold leading-tight text-ink">
          Choose the depth you need.
        </h1>
        <p className="mt-4 text-lg leading-8 text-neutral-600">
          Pay directly with M-Pesa. Renewals extend your remaining time, and you receive reminders before access expires.
        </p>
      </div>

      <div className="mt-10 grid gap-5 lg:grid-cols-2">
        {plans.map((plan) => (
          <article
            key={plan.tier}
            className={`relative overflow-hidden rounded-lg border bg-white p-6 shadow-soft sm:p-8 ${
              plan.tier === "pro" ? "border-sun" : "border-neutral-200"
            }`}
          >
            {plan.tier === "pro" && (
              <span className="absolute right-0 top-0 bg-sun px-4 py-2 text-xs font-bold uppercase text-ink">
                Full library
              </span>
            )}
            <TierBadge tier={plan.tier} />
            <div className="mt-6 flex items-end gap-2">
              <span className="font-display text-5xl font-semibold text-ink">KES {plan.amount}</span>
              <span className="pb-1 text-sm text-neutral-500">/ {plan.duration_days} days</span>
            </div>
            {plan.billing_mode === "upgrade" && plan.credit_applied > 0 && (
              <p className="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
                Includes KES {Number(plan.credit_applied).toFixed(2)} credit from your current plan.
              </p>
            )}
            {plan.billing_mode === "renew" && (
              <p className="mt-3 text-sm text-neutral-500">
                Renews from your current expiry date.
              </p>
            )}
            {plan.billing_mode === "upgrade" && (
              <p className="mt-3 text-sm text-neutral-500">
                Upgrade starts a fresh {plan.tier.toUpperCase()} term today.
              </p>
            )}
            <ul className="mt-7 space-y-3">
              {benefits[plan.tier].map((benefit) => (
                <li key={benefit} className="flex items-start gap-3 text-sm leading-6 text-neutral-700">
                  <Check size={18} className="mt-0.5 shrink-0 text-green-600" />
                  {benefit}
                </li>
              ))}
            </ul>
            <div className="mt-8 border-t border-neutral-200 pt-6">
              <label className="block text-sm font-semibold text-neutral-700">
                M-Pesa phone number
                <div className="relative mt-2">
                  <Phone size={17} className="absolute left-3 top-3 text-neutral-400" />
                  <input
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="0712 345 678"
                    className="h-11 w-full rounded-md border border-neutral-300 pl-10 pr-3 outline-none focus:border-green-500"
                  />
                </div>
              </label>
              <button
                type="button"
                onClick={() => pay(plan)}
                disabled={busy}
                className={`mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-md text-sm font-semibold ${
                  plan.tier === "pro" ? "bg-ink text-white hover:bg-green-700" : "bg-green-600 text-white hover:bg-green-700"
                } disabled:opacity-60`}
              >
                {busy && selected === plan.tier ? <LoaderCircle size={17} className="animate-spin" /> : <Smartphone size={17} />}
                Pay with M-Pesa
              </button>
            </div>
          </article>
        ))}
      </div>

      {notice && (
        <div className={`mt-6 rounded-md border px-4 py-3 text-sm ${
          notice.type === "success" ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"
        }`}>
          {notice.text}
        </div>
      )}

      {paymentStatus && paymentStatus.status === "pending" && (
        <div className="mt-6 flex items-start gap-3 rounded-md border border-yellow-200 bg-yellow-50 px-4 py-4 text-yellow-900">
          <LoaderCircle className="mt-0.5 shrink-0 animate-spin" size={18} />
          <div>
            <p className="font-semibold">Waiting for payment confirmation</p>
            <p className="mt-1 text-sm">{paymentStatus.message}</p>
            <p className="mt-1 text-xs text-yellow-700">
              Keep this page open after entering your M-Pesa PIN.
            </p>
          </div>
        </div>
      )}

      <div className="mt-10 grid gap-5 border-y border-neutral-200 py-7 sm:grid-cols-3">
        <TrustItem icon={Smartphone} title="M-Pesa native" text="Pay from the phone number you already use." />
        <TrustItem icon={ShieldCheck} title="Confirmed access" text="Your tier activates only after payment confirmation." />
        <TrustItem icon={Check} title="Grace built in" text="A 3-day grace window protects your reading access." />
      </div>
    </section>
  );
}

function TrustItem({ icon: Icon, title, text }) {
  return (
    <div className="flex gap-3">
      <Icon size={21} className="mt-0.5 shrink-0 text-green-600" />
      <div>
        <p className="font-semibold text-ink">{title}</p>
        <p className="mt-1 text-sm leading-6 text-neutral-500">{text}</p>
      </div>
    </div>
  );
}
