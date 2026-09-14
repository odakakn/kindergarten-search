import type { Kindergarten } from "../types";

interface Props {
  kg: Kindergarten;
  favorited: boolean;
  onToggleFavorite: (kg: Kindergarten) => void;
  onConsultVisit?: (kg: Kindergarten) => void;
}

export default function KindergartenCard({
  kg,
  favorited,
  onToggleFavorite,
  onConsultVisit,
}: Props) {
  return (
    <div className="kg-card">
      <div className="kg-card-head">
        <div>
          <h3>{kg.name}</h3>
          <div className="muted small">
            {kg.area}・{kg.nearest_station}
          </div>
        </div>
        <button
          className={`heart ${favorited ? "on" : ""}`}
          title={favorited ? "お気に入りから外す" : "お気に入りに登録"}
          onClick={() => onToggleFavorite(kg)}
        >
          {favorited ? "♥" : "♡"}
        </button>
      </div>

      <div className="kg-meta">
        <span className="pill">月額 {kg.monthly_fee.toLocaleString()}円</span>
        <span className="pill">
          {kg.min_age}〜{kg.max_age}歳
        </span>
        <span className="pill">{kg.education_style}</span>
        {kg.has_bus && <span className="pill">送迎バス</span>}
        {kg.extended_care && <span className="pill">預かり保育</span>}
      </div>

      <div className="kg-features">
        {kg.features
          .filter((f) => !["送迎バス", "預かり保育"].includes(f))
          .map((f) => (
            <span key={f} className="tag">
              {f}
            </span>
          ))}
      </div>

      <p className="kg-philo">{kg.philosophy}</p>

      {kg.match_reasons && kg.match_reasons.length > 0 && (
        <ul className="kg-reasons">
          {kg.match_reasons.map((r, i) => (
            <li key={i}>✓ {r}</li>
          ))}
        </ul>
      )}

      {onConsultVisit && (
        <div className="kg-actions">
          <button className="secondary" onClick={() => onConsultVisit(kg)}>
            この園の見学を相談する
          </button>
        </div>
      )}
    </div>
  );
}
