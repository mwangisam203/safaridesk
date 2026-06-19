import { Link } from "react-router-dom";
import { Mail, ShieldCheck, FileText, MessageSquare } from "lucide-react";

const updatedAt = "June 19, 2026";

export function TermsPage() {
  return (
    <LegalLayout
      eyebrow="Terms"
      title="Terms of service"
      intro="These terms explain the basic rules for using SafariDesk, including accounts, subscriptions, and paid technical content."
      icon={FileText}
    >
      <LegalSection title="Using SafariDesk">
        SafariDesk provides technical articles, guides, and subscription-based access for learning backend systems, payments, databases, and production practices. You are responsible for keeping your account details accurate and your login credentials private.
      </LegalSection>

      <LegalSection title="Accounts and access">
        Some features require an active account and verified email address. We may restrict access for inactive, abusive, fraudulent, or policy-violating accounts. Admin features are limited to authorized administrators.
      </LegalSection>

      <LegalSection title="Subscriptions and payments">
        Paid access is activated only after payment confirmation. Renewals, upgrades, downgrades, grace periods, and subscription expiry follow the rules shown in the app at the time of purchase. Failed, cancelled, or unconfirmed payment attempts do not activate access.
      </LegalSection>

      <LegalSection title="Content use">
        SafariDesk content is for personal learning and internal reference. Do not copy, resell, scrape, republish, or redistribute paid content without permission.
      </LegalSection>

      <LegalSection title="Availability">
        We work to keep the service reliable, but access may be interrupted by maintenance, provider outages, payment network issues, hosting incidents, or other operational events.
      </LegalSection>

      <LegalSection title="Contact">
        Questions about these terms can be sent through the <Link className="font-semibold text-green-700" to="/contact">contact page</Link>.
      </LegalSection>
    </LegalLayout>
  );
}

export function PrivacyPage() {
  return (
    <LegalLayout
      eyebrow="Privacy"
      title="Privacy policy"
      intro="This policy summarizes what SafariDesk collects, why it is used, and how account and payment-related information is handled."
      icon={ShieldCheck}
    >
      <LegalSection title="Information we collect">
        We collect account information such as name, email address, phone number, verification status, subscription tier, and activity needed to provide the service. For payments, we store transaction references, statuses, amounts, phone numbers, and provider receipts.
      </LegalSection>

      <LegalSection title="How we use information">
        We use this information to authenticate users, verify accounts, provide paid access, process subscriptions, send important account messages, prevent abuse, support admins, and troubleshoot service issues.
      </LegalSection>

      <LegalSection title="Payments and providers">
        SafariDesk integrates with payment, email, SMS, hosting, database, and storage providers. These services process only the data needed for their role, such as sending verification email, confirming M-Pesa payments, or serving article images.
      </LegalSection>

      <LegalSection title="Security">
        Passwords are stored as hashes. Secrets and provider credentials should be kept outside source code. Access to admin and paid content is controlled by account status, verification, and subscription rules.
      </LegalSection>

      <LegalSection title="Retention">
        We keep account, subscription, transaction, and audit records while needed to operate the service, support users, comply with business records, and investigate abuse or payment issues.
      </LegalSection>

      <LegalSection title="Your choices">
        You can contact SafariDesk to ask about your account information, correction requests, or account access questions through the <Link className="font-semibold text-green-700" to="/contact">contact page</Link>.
      </LegalSection>
    </LegalLayout>
  );
}

export function ContactPage() {
  return (
    <LegalLayout
      eyebrow="Contact"
      title="Contact SafariDesk"
      intro="Reach out for account, payment, subscription, or content questions."
      icon={MessageSquare}
    >
      <div className="rounded-lg border border-neutral-200 bg-white p-6 shadow-soft">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-green-50 text-green-700">
            <Mail size={20} />
          </span>
          <div>
            <h2 className="font-display text-2xl font-semibold text-ink">Support email</h2>
            <p className="mt-2 text-neutral-600">
              For now, contact SafariDesk support by email. Include your account email and a short description of the issue.
            </p>
            <a
              className="mt-4 inline-flex h-11 items-center rounded-md bg-ink px-5 text-sm font-semibold text-white hover:bg-green-700"
              href="mailto:support@safaridesk.com"
            >
              support@safaridesk.com
            </a>
          </div>
        </div>
      </div>

      <LegalSection title="What to include">
        For account or subscription issues, include the email used on SafariDesk, your phone number if the issue is payment-related, and any M-Pesa receipt or checkout reference shown by the app.
      </LegalSection>

      <LegalSection title="Security note">
        Do not send passwords, access tokens, API keys, or full payment credentials. SafariDesk support should never ask for your password.
      </LegalSection>
    </LegalLayout>
  );
}

function LegalLayout({ eyebrow, title, intro, icon: Icon, children }) {
  return (
    <section className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14">
      <div className="border-b border-neutral-200 pb-7">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-green-50 text-green-700">
          <Icon size={21} />
        </span>
        <p className="mt-5 text-xs font-semibold uppercase text-green-700">{eyebrow}</p>
        <h1 className="mt-2 font-display text-4xl font-semibold text-ink">{title}</h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-neutral-600">{intro}</p>
        <p className="mt-3 text-sm text-neutral-500">Last updated: {updatedAt}</p>
      </div>
      <div className="mt-8 space-y-7">{children}</div>
    </section>
  );
}

function LegalSection({ title, children }) {
  return (
    <section>
      <h2 className="font-display text-2xl font-semibold text-ink">{title}</h2>
      <p className="mt-3 leading-7 text-neutral-600">{children}</p>
    </section>
  );
}
