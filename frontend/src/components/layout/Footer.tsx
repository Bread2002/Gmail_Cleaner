// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 29th, 2026
// Description: React component for the footer of the Gmail Cleaner application.

export function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white px-3 sm:px-6 py-3 sticky z-10 shadow-sm">
      <div className="flex justify-between max-w-8xl">
        <div className="flex">
          <p className="text-sm text-black sm:hidden">
            © 2026, Rye Stahle-Smith.
          </p>
          <p className="text-sm text-black hidden sm:inline">
            Copyright © 2026, Rye Stahle-Smith; All rights reserved.
          </p>
        </div>
        <div className="flex space-x-2">
          <a
            className="text-black text-sm hover:text-gray-600 transition-colors"
            href={`${import.meta.env.VITE_SSE_BASE_URL}/docs`}
          >
            API Documentation
          </a>
          <a className="text-black text-sm">|</a>
          <a
            className="text-black text-sm hover:text-gray-600 transition-colors"
            href="https://github.com/Bread2002/Gmail_Cleaner"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
