import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../api/client";
import KindergartenCard from "../components/KindergartenCard";
import type { Kindergarten, VisitRequest } from "../types";

const statusLabel = (s: string) =>
  s === "received" ? "受付済み" : s === "cancelled" ? "取消済み" : s;

export default function FavoritesPage() {
  const [favorites, setFavorites] = useState<Kindergarten[]>([]);
  const [visits, setVisits] = useState<VisitRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      apiGet<Kindergarten[]>("/api/favorites"),
      apiGet<VisitRequest[]>("/api/visit-requests"),
    ])
      .then(([favs, vr]) => {
        setFavorites(favs);
        setVisits(vr);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const remove = async (kg: Kindergarten) => {
    setFavorites((prev) => prev.filter((f) => f.id !== kg.id));
    try {
      await apiDelete(`/api/favorites/${kg.id}`);
    } catch {
      load();
    }
  };

  const cancelVisit = async (v: VisitRequest) => {
    if (
      !window.confirm(
        `「${v.kindergarten_name}」の見学申込（${v.confirmation_id}）を取り消しますか？`,
      )
    )
      return;
    try {
      await apiPost(`/api/visit-requests/${v.confirmation_id}/cancel`);
    } finally {
      load();
    }
  };

  if (loading) return <div className="center-note">読み込み中…</div>;

  return (
    <div className="page">
      <h2>お気に入りの幼稚園</h2>
      {favorites.length === 0 ? (
        <p className="muted">
          まだお気に入りはありません。相談チャットで気になる園を見つけて ♡ で登録しましょう。
        </p>
      ) : (
        <div className="cards-grid">
          {favorites.map((kg) => (
            <KindergartenCard
              key={kg.id}
              kg={kg}
              favorited={true}
              onToggleFavorite={remove}
            />
          ))}
        </div>
      )}

      <h2 style={{ marginTop: "2rem" }}>見学申込の履歴</h2>
      {visits.length === 0 ? (
        <p className="muted">見学申込はまだありません。</p>
      ) : (
        <table className="visit-table">
          <thead>
            <tr>
              <th>確認番号</th>
              <th>幼稚園</th>
              <th>希望日</th>
              <th>状態</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {visits.map((v) => (
              <tr key={v.confirmation_id} className={v.status === "cancelled" ? "row-cancelled" : ""}>
                <td>
                  <code>{v.confirmation_id}</code>
                </td>
                <td>{v.kindergarten_name}</td>
                <td>{v.preferred_dates.join(", ") || "—"}</td>
                <td>{statusLabel(v.status)}</td>
                <td>
                  {v.status === "received" ? (
                    <button className="ghost danger" onClick={() => void cancelVisit(v)}>
                      キャンセル
                    </button>
                  ) : (
                    <span className="muted small">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
