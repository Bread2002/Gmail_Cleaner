import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export function Header() {
  const { userEmail, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="border-b border-gray-200 bg-white px-6 py-2 flex items-center justify-between sticky top-0 z-10 shadow-sm">
      <Link to="/" className="flex items-center gap-2.5 no-underline">
        <img
          src="/logo.png"
          alt="Gmail Cleaner"
          className="h-9 w-9 rounded-lg object-contain"
        />
        <span className="font-semibold text-gray-900 text-lg">
          Gmail Cleaner
        </span>
      </Link>

      <div className="flex items-center gap-4">
        {/* <Link
          to="/settings"
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors no-underline"
        >
          ⚙️ Settings
        </Link> */}
        {userEmail && (
          <span className="text-sm text-gray-500 hidden sm:block truncate max-w-[200px]">
            {userEmail}
          </span>
        )}
        <button
          onClick={() => navigate("/settings")}
          className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-md transition-colors"
        >
          ⚙️ Settings
        </button>
        <button
          onClick={handleLogout}
          className="text-sm bg-red-700 hover:bg-red-800 text-white px-3 py-1.5 rounded-md transition-colors"
        >
          <strong>Sign Out</strong>
        </button>
      </div>
    </header>
  );
}
