import { Footer } from "../components/layout/Footer";

export default function TermsOfServicePage() {
  return (
    <div className="flex flex-col min-h-screen bg-white text-zinc-200">
      <div className="flex-1 overflow-y-auto mx-auto max-w-3xl px-6 py-12">
        <a
          href="/"
          className="mb-8 inline-block text-sm text-blue-400 hover:text-blue-600"
        >
          ← Back
        </a>
        <h1 className="mb-2 text-3xl font-bold text-black">Terms of Service</h1>
        <p className="mb-10 text-sm text-zinc-500">
          <strong>Last Updated:</strong> June 4th, 2026
        </p>

        <div className="space-y-8 text-sm leading-relaxed">
          <section>
            <h2 className="mb-2 text-lg font-semibold text-black">Agreement</h2>
            <p className="text-black">
              By using Gmail Cleaner you agree to these terms. If you do not
              agree, do not use the application. These services are subject to
              change or be discontinued.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
