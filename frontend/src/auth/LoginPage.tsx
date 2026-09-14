import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { ApiError } from "../api/client";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ログインに失敗しました");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>🌷 幼稚園さがし</h1>
        <p className="muted">ログインして、あなたにピッタリの幼稚園を探しましょう。</p>
        <form onSubmit={onSubmit}>
          <label>
            ユーザーID
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            パスワード
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {error && <div className="error-box">{error}</div>}
          <button type="submit" disabled={busy}>
            {busy ? "ログイン中…" : "ログイン"}
          </button>
        </form>
        <p className="muted small">
          デモアカウント: <code>demo / demo</code>, <code>taro / taro</code>
        </p>
      </div>
    </div>
  );
}
