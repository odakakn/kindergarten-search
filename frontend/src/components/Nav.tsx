import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="nav">
      <div className="nav-brand">🌷 幼稚園さがし</div>
      <nav className="nav-links">
        <NavLink to="/" end>
          相談チャット
        </NavLink>
        <NavLink to="/favorites">お気に入り</NavLink>
        <NavLink to="/profile">プロフィール</NavLink>
      </nav>
      <div className="nav-user">
        <span className="muted small">{user?.display_name}</span>
        <button className="ghost" onClick={onLogout}>
          ログアウト
        </button>
      </div>
    </header>
  );
}
