import { useEffect, useState, type FormEvent } from "react";
import { apiGet, apiPut } from "../api/client";
import type { Profile } from "../types";

const PRIORITY_TAGS = [
  "英語教育",
  "預かり保育",
  "送迎バス",
  "給食あり",
  "のびのび保育",
  "お勉強系",
  "モンテッソーリ",
  "自然体験",
  "音楽教育",
  "体操教室",
  "少人数制",
  "小学校受験対応",
  "課外活動充実",
];

const EMPTY: Profile = { priorities: [] };

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<Profile>("/api/profile")
      .then((p) => setProfile({ ...p, priorities: p.priorities || [] }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const togglePriority = (tag: string) => {
    setProfile((prev) => {
      const has = prev.priorities.includes(tag);
      return {
        ...prev,
        priorities: has
          ? prev.priorities.filter((t) => t !== tag)
          : [...prev.priorities, tag],
      };
    });
    setSaved(false);
  };

  const numOrNull = (v: string): number | null => {
    if (v.trim() === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = await apiPut<Profile>("/api/profile", profile);
      setProfile({ ...updated, priorities: updated.priorities || [] });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="center-note">読み込み中…</div>;

  return (
    <div className="page">
      <h2>プロフィール</h2>
      <p className="muted">
        ここで登録した情報は、相談チャットのレコメンドに<strong>コンテキスト</strong>として使われます。
      </p>

      <form className="profile-form" onSubmit={onSubmit}>
        <div className="grid2">
          <label>
            お子さんのお名前
            <input
              value={profile.child_name ?? ""}
              onChange={(e) => set("child_name", e.target.value || null)}
            />
          </label>
          <label>
            お子さんの年齢（歳）
            <input
              type="number"
              min={0}
              max={6}
              value={profile.child_age ?? ""}
              onChange={(e) => set("child_age", numOrNull(e.target.value))}
            />
          </label>
          <label>
            居住エリア
            <input
              value={profile.home_area ?? ""}
              placeholder="例: 世田谷区"
              onChange={(e) => set("home_area", e.target.value || null)}
            />
          </label>
          <label>
            通園手段
            <input
              value={profile.commute_method ?? ""}
              placeholder="例: 自転車 / 徒歩 / バス"
              onChange={(e) => set("commute_method", e.target.value || null)}
            />
          </label>
          <label>
            予算上限（月額・円）
            <input
              type="number"
              min={0}
              step={1000}
              value={profile.budget_max ?? ""}
              onChange={(e) => set("budget_max", numOrNull(e.target.value))}
            />
          </label>
          <label>
            希望する保育時間帯
            <input
              value={profile.desired_hours ?? ""}
              placeholder="例: 8:00-18:00"
              onChange={(e) => set("desired_hours", e.target.value || null)}
            />
          </label>
        </div>

        <fieldset>
          <legend>重視したいこと</legend>
          <div className="tag-picker">
            {PRIORITY_TAGS.map((tag) => (
              <button
                type="button"
                key={tag}
                className={`tag-toggle ${profile.priorities.includes(tag) ? "on" : ""}`}
                onClick={() => togglePriority(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={profile.needs_bus ?? false}
            onChange={(e) => set("needs_bus", e.target.checked)}
          />
          送迎バスが必要
        </label>

        <div className="grid2">
          <label>
            きょうだい構成
            <input
              value={profile.siblings ?? ""}
              onChange={(e) => set("siblings", e.target.value || null)}
            />
          </label>
          <label>
            アレルギー・配慮事項
            <input
              value={profile.allergies ?? ""}
              onChange={(e) => set("allergies", e.target.value || null)}
            />
          </label>
        </div>

        <label>
          その他メモ
          <textarea
            rows={3}
            value={profile.notes ?? ""}
            onChange={(e) => set("notes", e.target.value || null)}
          />
        </label>

        <div className="form-actions">
          <button type="submit" disabled={busy}>
            {busy ? "保存中…" : "保存する"}
          </button>
          {saved && <span className="saved-note">✓ 保存しました</span>}
        </div>
      </form>
    </div>
  );
}
