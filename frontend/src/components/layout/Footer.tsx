// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 29th, 2026
// Description: React component for the footer of the Gmail Cleaner application.

export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white px-3 sm:px-6 py-4 sticky bottom-0 z-10 shadow-sm">
      <div className="flex flex-col md:flex-row justify-between items-center max-w-7xl mx-auto space-y-4 md:space-y-0">
        <div className="flex space-x-12">
          <p className="text-sm text-zinc-500">
            Copyright © 2026, Rye Stahle-Smith; All rights reserved.
          </p>
        </div>
        <div className="flex space-x-12">
          <a
            className="text-zinc-500 text-sm hover:text-gray-900 transition-colors"
            href={`${import.meta.env.VITE_SSE_BASE_URL}/docs`}
          >
            API Documentation
          </a>
          <a
            className="text-zinc-500 text-sm hover:text-gray-900 transition-colors"
            href="https://github.com/Bread2002/Gmail_Cleaner"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
