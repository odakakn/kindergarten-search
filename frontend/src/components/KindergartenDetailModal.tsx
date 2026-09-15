import { useEffect } from "react";
import type { Kindergarten } from "../types";

interface Props {
  kg: Kindergarten;
  rank?: number;
  favorited: boolean;
  onToggleFavorite: (kg: Kindergarten) => void;
  onConsultVisit?: (kg: Kindergarten) => void;
  onClose: () => void;
}

/** 幼稚園の全項目を表示する詳細モーダル（カードのタップで開く）。 */
export default function KindergartenDetailModal({
  kg,
  rank,
  favorited,
  onToggleFavorite,
  onConsultVisit,
  onClose,
}: Props) {
  // Esc で閉じる
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const specs: [string, string][] = [
    ["エリア", `${kg.area}・${kg.address_rough}`],
    ["最寄り", kg.nearest_station],
    ["対象年齢", `${kg.min_age}〜${kg.max_age}歳`],
    ["月額", `${kg.monthly_fee.toLocaleString()}円`],
    ["保育時間", kg.standard_hours],
    ["預かり保育", kg.extended_care ? kg.extended_hours || "あり" : "なし"],
    ["送迎バス", kg.has_bus ? "あり" : "なし"],
    ["給食", kg.lunch_type],
    ["教育方針", kg.education_style],
    ["定員", `${kg.capacity}名`],
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${kg.name} の詳細`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div>
            {rank != null && <span className="kg-rank">おすすめ #{rank}</span>}
            <h3>{kg.name}</h3>
            <div className="muted small">
              {kg.area}・{kg.nearest_station}
            </div>
          </div>
          <button className="ghost modal-close" aria-label="閉じる" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <dl className="kg-specs">
            {specs.map(([k, v]) => (
              <div key={k} className="kg-spec-row">
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>

          {kg.features.length > 0 && (
            <div className="kg-features">
              {kg.features.map((f) => (
                <span key={f} className="tag">
                  {f}
                </span>
              ))}
            </div>
          )}

          <p className="kg-philo">{kg.philosophy}</p>

          {kg.match_reasons && kg.match_reasons.length > 0 && (
            <ul className="kg-reasons">
              {kg.match_reasons.map((r, i) => (
                <li key={i}>✓ {r}</li>
              ))}
            </ul>
          )}

          {kg.url && (
            <div className="small">
              <a href={kg.url} target="_blank" rel="noreferrer">
                公式サイトを見る
              </a>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button
            className={`heart ${favorited ? "on" : ""}`}
            title={favorited ? "お気に入りから外す" : "お気に入りに登録"}
            onClick={() => onToggleFavorite(kg)}
          >
            {favorited ? "♥" : "♡"}
          </button>
          {onConsultVisit && (
            <button className="secondary" onClick={() => onConsultVisit(kg)}>
              この園の見学を相談する
            </button>
          )}
          <button className="ghost" onClick={onClose}>
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}
