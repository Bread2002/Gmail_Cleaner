// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for the main application shell in the Gmail Cleaner application.

// Import necessary modules and components
import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Footer } from "./Footer";
import { SettingsPage } from "../../pages/SettingsPage";

// Define the AppShell component that serves as the main layout for the application, including the header and outlet for nested routes
export function AppShell() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (!settingsOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSettingsOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [settingsOpen]);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header onSettingsOpen={() => setSettingsOpen(true)} />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        <Outlet />
      </main>
      <Footer />

      {settingsOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-20"
            onClick={() => setSettingsOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white z-30 shadow-2xl overflow-y-auto">
            <div className="px-6 py-6">
              <SettingsPage onClose={() => setSettingsOpen(false)} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
