// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 28th, 2026
// Description: React component for the main application shell in the Gmail Cleaner application.

// Import necessary modules and components
import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Footer } from "./Footer";

// Define the AppShell component that serves as the main layout for the application, including the header and outlet for nested routes
export function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
