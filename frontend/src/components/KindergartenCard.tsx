import type { Kindergarten } from "../types";

interface Props {
  kg: Kindergarten;
  favorited: boolean;
  rank?: number;
  onToggleFavorite: (kg: Kindergarten) => void;
  onConsultVisit?: (kg: Kindergarten) => void;
  onOpenDetail?: (kg: Kindergarten) => void;
}

/** 検索結果の要約カード。詳細は onOpenDetail のモーダルで表示する。 */
export default function KindergartenCard({
  kg,
  favorited,
  rank,
  onToggleFavorite,
  onConsultVisit,
  onOpenDetail,
}: Props) {
  const clickable = !!onOpenDetail;
  const openDetail = () => onOpenDetail?.(kg);

  return (
    <div
      className={`kg-card ${clickable ? "clickable" : ""}`}
      onClick={clickable ? openDetail : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDetail();
              }
            }
          : undefined
      }
    >
      <div className="kg-card-head">
        <div>
          {rank != null && <span className="kg-rank">おすすめ #{rank}</span>}
          <h3>{kg.name}</h3>
          <div className="muted small">
            {kg.area}・{kg.nearest_station}
          </div>
        </div>
        <button
          className={`heart ${favorited ? "on" : ""}`}
          title={favorited ? "お気に入りから外す" : "お気に入りに登録"}
          onClick={(e) => {
            e.stopPropagation();
            onToggleFavorite(kg);
          }}
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

      {kg.match_reasons && kg.match_reasons.length > 0 && (
        <ul className="kg-reasons">
          {kg.match_reasons.slice(0, 3).map((r, i) => (
            <li key={i}>✓ {r}</li>
          ))}
        </ul>
      )}

      <div className="kg-actions">
        {onOpenDetail && (
          <button
            className="ghost"
            onClick={(e) => {
              e.stopPropagation();
              openDetail();
            }}
          >
            詳細を見る
          </button>
        )}
        {onConsultVisit && (
          <button
            className="secondary"
            onClick={(e) => {
              e.stopPropagation();
              onConsultVisit(kg);
            }}
          >
            この園の見学を相談する
          </button>
        )}
      </div>
    </div>
  );
}
