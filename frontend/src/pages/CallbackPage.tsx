import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuth } from '../hooks/useAuth';

export function CallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const called = useRef(false);  // prevent double-invoke in React StrictMode

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (error || !code || !state) {
      navigate('/login?error=auth_failed', { replace: true });
      return;
    }

    authApi
      .callback({ code, state })
      .then(({ session_token, user_email }) => {
        loginWithToken(session_token, user_email);
        navigate('/', { replace: true });
      })
      .catch(() => {
        navigate('/login?error=auth_failed', { replace: true });
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-600 font-medium">Signing you in…</p>
      </div>
    </div>
  );
}
