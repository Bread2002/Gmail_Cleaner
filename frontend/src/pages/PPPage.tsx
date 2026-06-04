import { Footer } from "../components/layout/Footer";

export default function PrivacyPolicyPage() {
  return (
    <div className="flex flex-col min-h-screen bg-white text-zinc-200">
      <div className="flex-1 overflow-y-auto mx-auto max-w-3xl px-6 py-12">
        <a
          href="/"
          className="mb-8 inline-block text-sm text-blue-400 hover:text-blue-600"
        >
          ← Back
        </a>
        <h1 className="mb-2 text-3xl font-bold text-black">Privacy Policy</h1>
        <p className="mb-10 text-sm text-zinc-500">
          <strong>Last Updated:</strong> June 4th, 2026
        </p>

        <div className="space-y-8 text-sm leading-relaxed">
          <section>
            <h2 className="mb-2 text-lg font-semibold text-black">Overview</h2>
            <p className="text-black">
              Gmail Cleaner is a local-first, full-scale web application built
              with React TS + FastAPI. Includes inbox scanning, bulk message
              trashing/ sender blocking, and customizable user presets. This
              policy describes what information the app may collect and how it
              is used so you can make informed choices.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
