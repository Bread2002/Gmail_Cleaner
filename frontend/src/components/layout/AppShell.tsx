import { Outlet } from "react-router-dom";
import { Header } from "./Header";

export function AppShell() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
