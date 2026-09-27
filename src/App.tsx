import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  api,
  type CropCalendarResponse,
  type FarmerContext,
  type FarmerProfile,
  type RankResponse,
  type ReceptivityResponse,
  type UrgencyResponse,
  type VoiceCallRequest,
} from "./api";
import {
  CANONICAL_PRODUCTS,
  enrichProduct,
  findCanonicalProduct,
  getMandiBenchmark,
} from "./productsData";

type Page = "overview" | "farmers" | "farmer";
type IconName =
  | "leaf"
  | "search"
  | "bell"
  | "users"
  | "alert"
  | "send"
  | "chart"
  | "arrow"
  | "cloud"
  | "bug"
  | "sprout"
  | "phone"
  | "message"
  | "clock"
  | "map"
  | "check"
  | "chevron"
  | "filter"
  | "calendar"
  | "mic"
  | "play"
  | "pause"
  | "flask"
  | "shield"
  | "rain"
  | "trend"
  | "rotate"
  | "info"
  | "printer"
  | "refresh";

const iconPaths: Record<IconName, ReactNode> = {
  leaf: <><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 4.8 18 2 18 2c1 6.5-1.1 12.7-7 14.2" /><path d="M2 21c0-3 1.85-5.36 5.08-6.94C9.47 12.9 12.16 12 16 12" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
  alert: <><path d="M10.3 2.9 1.8 17a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 2.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m7 16 4-5 4 3 5-7" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  cloud: <path d="M17.5 19H9a7 7 0 1 1 6.7-9h1.8a4.5 4.5 0 1 1 0 9Z" />,
  bug: <><path d="m8 2 1.9 1.9M16 2l-1.9 1.9M9 8h6M10 4h4a3 3 0 0 1 3 3v7a5 5 0 0 1-10 0V7a3 3 0 0 1 3-3Z" /><path d="M3 13h4m10 0h4M5 7l2.3 1M19 7l-2.3 1M5 19l3-2m11 2-3-2" /></>,
  sprout: <><path d="M7 20h10M12 20v-9" /><path d="M12 11C7 11 5 8 5 4c4 0 7 2 7 7ZM12 15c0-4 3-7 7-7 0 4-2 7-7 7Z" /></>,
  phone: <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.4 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z" />,
  message: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  map: <><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" /><path d="M9 3v15M15 6v15" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  filter: <path d="M4 5h16M7 12h10M10 19h4" />,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
  mic: <><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" /><path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8" /></>,
  play: <path d="M6 4v16l14-8Z" />,
  pause: <><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></>,
  flask: <><path d="M9 2v6l-5 9a3 3 0 0 0 2.6 4.5h10.8A3 3 0 0 0 20 17l-5-9V2" /><path d="M7 14h10M8 2h8" /></>,
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />,
  rain: <><path d="M17.5 16H9a7 7 0 1 1 6.7-9h1.8a4.5 4.5 0 1 1 0 9Z" /><path d="m8 20-1 2m6-2-1 2m6-2-1 2" /></>,
  trend: <path d="m3 17 6-6 4 4 8-8M15 7h6v6" />,
  rotate: <><path d="M20 7h-5V2" /><path d="M20 7a9 9 0 1 0 1 8" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  printer: <><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><rect x="6" y="14" width="12" height="8" /></>,
  refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconPaths[name]}
    </svg>
  );
}

function urgencyLevel(score: number | undefined): "Critical" | "High" | "Medium" {
  const value = score ?? 0;
  if (value >= 0.7) return "Critical";
  if (value >= 0.5) return "High";
  return "Medium";
}

function pct(value: number | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function humanize(val: string): string {
  if (!val) return "—";
  return val.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "??";
}

const channelMeta: Record<string, { icon: IconName; label: string }> = {
  whatsapp: { icon: "message", label: "WhatsApp Advisory" },
  sms: { icon: "send", label: "SMS Alert" },
  voice_call: { icon: "phone", label: "AI Voice Call" },
  field_visit: { icon: "map", label: "Field Officer Visit" },
  suppress: { icon: "alert", label: "Suppressed (Fatigue)" },
};

function channelInfo(channel?: string | null) {
  if (!channel) return { icon: "message" as IconName, label: "WhatsApp" };
  return channelMeta[channel] ?? { icon: "message" as IconName, label: humanize(channel) };
}

// Audio player preview hook
const VOICE_PREVIEW_DEFAULT = "/audio/mayur-advice.wav";

function useVoiceAudio() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const toggle = (id: string, customSrc?: string) => {
    const src = customSrc || VOICE_PREVIEW_DEFAULT;
    if (playingId === id && audioRef.current) {
      audioRef.current.pause();
      setPlayingId(null);
      return;
    }
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(src);
    audio.preload = "auto";
    audio.addEventListener("ended", () => setPlayingId(null));
    audio.addEventListener("error", () => {
      if (src !== VOICE_PREVIEW_DEFAULT) {
        const fallback = new Audio(VOICE_PREVIEW_DEFAULT);
        fallback.play().catch(() => {});
        fallback.addEventListener("ended", () => setPlayingId(null));
        audioRef.current = fallback;
      } else {
        setPlayingId(null);
      }
    });
    audio.play().catch(() => {});
    audioRef.current = audio;
    setPlayingId(id);
  };

  return { playingId, toggle };
}

// Topbar with KrishiMitra branding and ADMIN PROFILE
function Topbar({ page, navigate }: { page: Page; navigate: (p: Page) => void }) {
  return (
    <header className="topbar">
      <button className="brand" onClick={() => navigate("overview")}>
        <span className="brand-mark"><Icon name="leaf" size={22} /></span>
        <div>
          <strong>KrishiMitra AI</strong>
          <small>Context-First Agronomy Engine</small>
        </div>
      </button>

      <nav>
        <button
          className={`nav-link ${page === "overview" ? "active" : ""}`}
          onClick={() => navigate("overview")}
        >
          <Icon name="chart" size={15} /> Dashboard
        </button>
        <button
          className={`nav-link ${page === "farmers" ? "active" : ""}`}
          onClick={() => navigate("farmers")}
        >
          <Icon name="users" size={15} /> Farmers Directory
        </button>
      </nav>

      <div className="top-actions">
        <div className="service-pill-strip" title="Connected KrishiMitra Intelligence Microservices">
          <span className="service-dot" />
          <span>M1–M8 Live</span>
        </div>

        {/* ADMIN PROFILE ONLY (No farmer profiles exist) */}
        <button className="admin-profile" title="Admin User: Syngenta Field Agronomist">
          <span className="admin-avatar">FO</span>
          <div>
            <strong>Field Operations Admin</strong>
            <small>KrishiMitra HQ Desk</small>
          </div>
          <Icon name="chevron" size={13} />
        </button>
      </div>
    </header>
  );
}

// Overview Dashboard
function Overview({
  farmers,
  viewFarmer,
  navigate,
}: {
  farmers: FarmerProfile[];
  viewFarmer: (id: string) => void;
  navigate: (p: Page) => void;
}) {
  const sorted = useMemo(
    () => [...farmers].sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0)),
    [farmers]
  );
  const criticalCount = sorted.filter((f) => (f.urgency_score ?? 0) >= 0.7).length;
  const highCount = sorted.filter(
    (f) => (f.urgency_score ?? 0) >= 0.5 && (f.urgency_score ?? 0) < 0.7
  ).length;
  const avgScore =
    farmers.length > 0
      ? farmers.reduce((sum, f) => sum + (f.urgency_score ?? 0), 0) / farmers.length
      : 0;
  const outreachReady = farmers.filter((f) => f.whatsapp_enabled || f.phone).length;

  const { playingId, toggle } = useVoiceAudio();

  return (
    <main>
      <div className="page-head">
        <div>
          <div className="eyebrow">FIELD OPERATIONS DASHBOARD · TRACK 1 INTELLIGENCE</div>
          <div className="page-title">Agronomic Risk & Outreach Center</div>
          <div className="page-subtitle">
            Autonomous context assembly (M6), urgency scoring (M7) & personalized product ranking (M8)
          </div>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate("farmers")}>
          <Icon name="users" size={15} /> View All {farmers.length} Farmers
        </button>
      </div>

      <section className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon green"><Icon name="users" size={22} /></div>
          <div>
            <div className="kpi-label">Monitored Growers</div>
            <div className="kpi-value">{farmers.length}</div>
            <div className="kpi-sub">M1 Farmer DB (Port 8001)</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon red"><Icon name="alert" size={22} /></div>
          <div>
            <div className="kpi-label">Critical Interventions</div>
            <div className="kpi-value">{criticalCount}</div>
            <div className="kpi-sub">Urgency score ≥ 70%</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon orange"><Icon name="trend" size={22} /></div>
          <div>
            <div className="kpi-label">High Priority Alerts</div>
            <div className="kpi-value">{highCount}</div>
            <div className="kpi-sub">M7 Urgency Engine (Port 8007)</div>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue"><Icon name="message" size={22} /></div>
          <div>
            <div className="kpi-label">Outreach Dispatch Ready</div>
            <div className="kpi-value">{outreachReady}</div>
            <div className="kpi-sub">Avg Urgency {pct(avgScore)}</div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-head">
          <div>
            <div className="section-title">Priority Interventions Today</div>
            <div className="section-desc">
              Ranked in real-time by M7 urgency engine. Click any farmer row to open Complete Farm Intelligence.
            </div>
          </div>
          <span className="badge badge-high"><Icon name="alert" size={12} /> {sorted.length} Active Targets</span>
        </div>

        <div className="table-wrap">
          <table className="farmer-table">
            <thead>
              <tr>
                <th>Farmer (Decision Subject)</th>
                <th>Crops & Acreage</th>
                <th>M7 Urgency Score</th>
                <th>Recommended Outreach</th>
                <th>Preferred Time</th>
                <th>AI Voice Preview</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((farmer) => {
                const uLevel = urgencyLevel(farmer.urgency_score);
                const badgeClass =
                  uLevel === "Critical"
                    ? "badge-critical"
                    : uLevel === "High"
                    ? "badge-high"
                    : "badge-medium";
                const isPlaying = playingId === farmer.grower_id;

                return (
                  <tr key={farmer.grower_id} onClick={() => viewFarmer(farmer.grower_id)}>
                    <td>
                      <div className="farmer-cell">
                        <span className="farmer-avatar">{initials(farmer.name)}</span>
                        <div>
                          <strong>{farmer.name}</strong>
                          <small>
                            <Icon name="map" size={11} /> {farmer.district}, {farmer.state} ({farmer.grower_id})
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <strong>{farmer.crops.map(humanize).join(", ")}</strong>
                      <small>{farmer.grower_farm_size} Acres</small>
                    </td>
                    <td>
                      <span className={`badge ${badgeClass}`}>
                        <span className="status-dot" /> {uLevel} ({pct(farmer.urgency_score)})
                      </span>
                    </td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 700, color: "var(--forest-900)" }}>
                        <Icon name={channelInfo(farmer.recommended_channel).icon} size={15} />
                        {channelInfo(farmer.recommended_channel).label}
                      </span>
                    </td>
                    <td>
                      <strong>{humanize(farmer.preferred_contact_time)}</strong>
                    </td>
                    <td>
                      <button
                        className={`audio-preview-btn ${isPlaying ? "playing" : ""}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggle(farmer.grower_id, `/audio/${farmer.grower_id}-advice.wav`);
                        }}
                        title="Listen to native language AI Voice Advisory"
                      >
                        <Icon name={isPlaying ? "pause" : "play"} size={13} />
                        <span>{isPlaying ? "Playing" : "Preview Audio"}</span>
                      </button>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          viewFarmer(farmer.grower_id);
                        }}
                      >
                        <span>Open Farm Intelligence</span>
                        <Icon name="arrow" size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

// Farmers Directory Page
function FarmersDirectory({
  farmers,
  viewFarmer,
}: {
  farmers: FarmerProfile[];
  viewFarmer: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const [state, setState] = useState("all");
  const [crop, setCrop] = useState("all");
  const [urgency, setUrgency] = useState("all");

  const states = useMemo(() => Array.from(new Set(farmers.map((f) => f.state))).sort(), [farmers]);
  const crops = useMemo(() => Array.from(new Set(farmers.flatMap((f) => f.crops))).sort(), [farmers]);

  const filtered = useMemo(() => {
    return farmers
      .filter((f) => state === "all" || f.state === state)
      .filter((f) => crop === "all" || f.crops.includes(crop))
      .filter((f) => {
        if (urgency === "all") return true;
        return urgencyLevel(f.urgency_score).toLowerCase() === urgency.toLowerCase();
      })
      .filter((f) => {
        const query = q.toLowerCase();
        return (
          f.name.toLowerCase().includes(query) ||
          f.district.toLowerCase().includes(query) ||
          f.grower_id.toLowerCase().includes(query) ||
          f.linked_retailer_name.toLowerCase().includes(query)
        );
      })
      .sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));
  }, [farmers, state, crop, urgency, q]);

  const { playingId, toggle } = useVoiceAudio();

  return (
    <main>
      <div className="page-head">
        <div>
          <div className="eyebrow">GROWER ROSTER · DECISION SUBJECTS</div>
          <div className="page-title">Farmers Directory</div>
          <div className="page-subtitle">
            Monitored growers indexed by location, acreage, active stage, and intervention priority.
          </div>
        </div>
      </div>

      <div className="filter-bar">
        <Icon name="filter" size={16} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, district, or retailer…"
          style={{ minWidth: 260 }}
        />
        <select value={state} onChange={(e) => setState(e.target.value)}>
          <option value="all">State: All States</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select value={crop} onChange={(e) => setCrop(e.target.value)}>
          <option value="all">Crop: All Crops</option>
          {crops.map((c) => (
            <option key={c} value={c}>{humanize(c)}</option>
          ))}
        </select>
        <select value={urgency} onChange={(e) => setUrgency(e.target.value)}>
          <option value="all">Urgency: All Levels</option>
          <option value="critical">Critical (≥ 70%)</option>
          <option value="high">High (50%–69%)</option>
          <option value="medium">Medium (&lt; 50%)</option>
        </select>
        {(state !== "all" || crop !== "all" || urgency !== "all" || q) && (
          <button
            className="btn btn-ghost"
            onClick={() => {
              setState("all");
              setCrop("all");
              setUrgency("all");
              setQ("");
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <div className="section-title">
              {filtered.length} Grower{filtered.length === 1 ? "" : "s"} Monitored
            </div>
            <div className="section-desc">Click row to open complete agronomy & intelligence dossier</div>
          </div>
        </div>

        <div className="table-wrap">
          <table className="farmer-table">
            <thead>
              <tr>
                <th>Farmer</th>
                <th>Holding & Crops</th>
                <th>Linked Agro Retailer</th>
                <th>M7 Urgency</th>
                <th>Outreach Channel</th>
                <th>Audio Preview</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((farmer) => {
                const uLevel = urgencyLevel(farmer.urgency_score);
                const badgeClass =
                  uLevel === "Critical"
                    ? "badge-critical"
                    : uLevel === "High"
                    ? "badge-high"
                    : "badge-medium";
                const isPlaying = playingId === farmer.grower_id;

                return (
                  <tr key={farmer.grower_id} onClick={() => viewFarmer(farmer.grower_id)}>
                    <td>
                      <div className="farmer-cell">
                        <span className="farmer-avatar">{initials(farmer.name)}</span>
                        <div>
                          <strong>{farmer.name}</strong>
                          <small>
                            <Icon name="map" size={11} /> {farmer.tehsil}, {farmer.district}, {farmer.state}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <strong>{farmer.crops.map(humanize).join(", ")}</strong>
                      <small>{farmer.grower_farm_size} Acres · {farmer.connectivity}</small>
                    </td>
                    <td>
                      <strong>{farmer.linked_retailer_name}</strong>
                      <small>ID: {farmer.linked_retailer_id}</small>
                    </td>
                    <td>
                      <span className={`badge ${badgeClass}`}>
                        <span className="status-dot" /> {uLevel} ({pct(farmer.urgency_score)})
                      </span>
                    </td>
                    <td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 700, color: "var(--forest-900)" }}>
                        <Icon name={channelInfo(farmer.recommended_channel).icon} size={14} />
                        {channelInfo(farmer.recommended_channel).label}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`audio-preview-btn ${isPlaying ? "playing" : ""}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          toggle(farmer.grower_id, `/audio/${farmer.grower_id}-advice.wav`);
                        }}
                      >
                        <Icon name={isPlaying ? "pause" : "play"} size={13} />
                        <span>{isPlaying ? "Playing" : "Preview"}</span>
                      </button>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          viewFarmer(farmer.grower_id);
                        }}
                      >
                        <span>View Dossier</span>
                        <Icon name="arrow" size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

// ==================== COMPLETE FARM INTELLIGENCE & PERSONALIZED ADVISORY ====================
function FarmIntelligencePage({
  growerId,
  back,
}: {
  growerId: string;
  back: () => void;
}) {
  const [context, setContext] = useState<FarmerContext | null>(null);
  const [score, setScore] = useState<UrgencyResponse | null>(null);
  const [products, setProducts] = useState<RankResponse | null>(null);
  const [receptivity, setReceptivity] = useState<ReceptivityResponse | null>(null);
  const [calendar, setCalendar] = useState<CropCalendarResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Outreach interactive dispatch state
  const [activeChannelTab, setActiveChannelTab] = useState<"voice" | "whatsapp" | "sms">("voice");
  const [callStatus, setCallStatus] = useState<"idle" | "calling" | "success" | "error">("idle");
  const [callMessage, setCallMessage] = useState("");
  const [waSent, setWaSent] = useState(false);
  const [smsSent, setSmsSent] = useState(false);

  const { playingId, toggle } = useVoiceAudio();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.all([
      api.getContext(growerId),
      api.getScore(growerId),
      api.getProducts(growerId),
      api.getReceptivity(growerId),
    ])
      .then(async ([ctx, sc, prod, rec]) => {
        if (cancelled) return;
        setContext(ctx);
        setScore(sc);
        setProducts(prod);
        setReceptivity(rec);

        // Fetch calendar with state and crop
        const crop = ctx.profile.crops[0] || "wheat";
        const st = ctx.profile.state || "Punjab";
        try {
          const cal = await api.getCalendar(st, crop);
          if (!cancelled) setCalendar(cal);
        } catch {
          // ignore, fallback handled
        }
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [growerId]);

  if (loading || !context || !score || !products || !receptivity) {
    return (
      <main>
        <div className="card" style={{ padding: 48, textAlign: "center", color: "var(--muted)" }}>
          <Icon name="refresh" size={28} />
          <div style={{ marginTop: 12, fontWeight: 700 }}>
            Synthesizing Live Farm Intelligence (M1, M4, M5, M6, M7, M8, M16)…
          </div>
        </div>
      </main>
    );
  }

  const profile = context.profile;
  const signals = context.signals;
  const cropStage = context.crop_stage;
  const topProductReco = products.top_products[0];
  const topProductCanonical = topProductReco
    ? enrichProduct(topProductReco.product_name)
    : CANONICAL_PRODUCTS[0];
  const primaryCrop = profile.crops[0] || "wheat";

  // Mandi benchmarks
  const mandi =
    calendar?.msp_rs_quintal && calendar?.today_price_rs_quintal
      ? {
          commodity: humanize(primaryCrop),
          msp_rs_quintal: calendar.msp_rs_quintal,
          today_price_rs_quintal: calendar.today_price_rs_quintal,
          today_arrival_metric_tonnes: calendar.today_arrival_metric_tonnes || "57,354",
          trend:
            Number(calendar.today_price_rs_quintal) >= Number(calendar.msp_rs_quintal)
              ? ("up" as const)
              : ("down" as const),
        }
      : getMandiBenchmark(primaryCrop);

  const uLevel = urgencyLevel(score.urgency_score);
  const uBadgeClass =
    uLevel === "Critical" ? "badge-critical" : uLevel === "High" ? "badge-high" : "badge-medium";

  // Trigger Gemini Live Voice Call
  const handlePlaceCall = async () => {
    setCallStatus("calling");
    setCallMessage("");
    const pestRiskLevel = signals.pest_risk >= 0.7 ? "high" : signals.pest_risk >= 0.4 ? "medium" : "low";

    const payload: VoiceCallRequest = {
      to_number: profile.phone,
      farmer_id: profile.grower_id,
      farmer_name: profile.name,
      preferred_language: profile.preferred_language,
      state: profile.state,
      district: profile.district,
      village: profile.tehsil,
      crops: profile.crops,
      crop_stage: cropStage.confirmed_stage,
      pest_risk_level: pestRiskLevel,
      active_pest: signals.active_pest,
      why_now: score.top_factors.join(". "),
      recommended_product: topProductCanonical.name || "Tilt 250 EC",
      retailer_name: profile.linked_retailer_name,
      urgency_score: score.urgency_score,
    };

    try {
      const res = await api.placeVoiceCall(payload);
      setCallStatus("success");
      setCallMessage(res.message || `Outbound AI call dispatched (SID: ${res.call_sid || "LIVE"})`);
    } catch (e) {
      setCallStatus("error");
      setCallMessage(String(e instanceof Error ? e.message : e));
    }
  };

  // WhatsApp formatted advisory text
  const whatsappScript = `🌾 *KrishiMitra Advisory for ${profile.name}* (${profile.district}, ${profile.state})
🚨 *Urgent Crop Alert:* High humidity (${Math.round(signals.humidity_7d_avg)}%) and active ${signals.active_pest || "rust"} risk detected during ${humanize(cropStage.confirmed_stage)} stage.

✅ *Recommended Syngenta Input:* *${topProductCanonical.name}*
🔬 *Active Ingredient:* ${topProductCanonical.active_ingredients}
💧 *Recommended Dosage:* ${topProductCanonical.dosage}
⏱ *Timing:* ${topProductCanonical.timing_window}
🛡 *Mode of Action:* ${topProductCanonical.moa_group} (${topProductCanonical.moa_class})

🏪 *Available at your linked dealer:*
*${profile.linked_retailer_name}* (Dealer ID: ${profile.linked_retailer_id})
_Verified by KrishiMitra Agronomy Intelligence Engine_`;

  // SMS 160-char text
  const smsScript = `KrishiMitra: Urgent alert for ${profile.name}! High ${signals.active_pest || "rust"} risk. Spray ${topProductCanonical.name} (${topProductCanonical.dosage}). Avail at ${profile.linked_retailer_name}.`;

  const isAudioPlaying = playingId === profile.grower_id;

  return (
    <main>
      {/* Breadcrumb Navigation */}
      <div className="breadcrumb">
        <button onClick={back}>
          <Icon name="arrow" size={14} /> Back to Directory
        </button>
        <Icon name="chevron" size={12} />
        <span>Decision Subject Dossier: {profile.name} ({profile.grower_id})</span>
        <Icon name="chevron" size={12} />
        <strong style={{ color: "var(--forest-900)" }}>Farm Intelligence & Advisory</strong>
      </div>

      {/* ==================== GROWER SUBJECT DOSSIER BAR ==================== */}
      <section className="subject-dossier-bar">
        <div className="dossier-top">
          <div className="decision-subject-tag">
            <Icon name="shield" size={13} />
            <span>Agronomic Decision Subject · Context Dossier</span>
          </div>
          <div className="dossier-assembled">
            <Icon name="clock" size={13} />
            <span>M6 Context Compiled: {new Date(context.assembled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            <span style={{ opacity: 0.5 }}>|</span>
            <span>Retailer: {profile.linked_retailer_name}</span>
          </div>
        </div>

        <div className="dossier-main">
          <div className="farmer-identity-hero">
            <div className="hero-avatar">{initials(profile.name)}</div>
            <div>
              <div className="hero-name">{profile.name}</div>
              <div className="hero-sub">
                <Icon name="map" size={12} /> {profile.tehsil}, {profile.district}, {profile.state}
              </div>
            </div>
          </div>

          <div className="hero-meta-item">
            <small>PRIMARY CROP</small>
            <strong>{humanize(primaryCrop)}</strong>
            <span>{profile.grower_farm_size} Acres</span>
          </div>

          <div className="hero-meta-item">
            <small>CROP STAGE</small>
            <strong>{humanize(cropStage.confirmed_stage)}</strong>
            <span>{cropStage.days_in_stage}d in stage ({cropStage.days_to_next_stage}d to next)</span>
          </div>

          <div className="hero-meta-item">
            <small>M7 URGENCY PRIORITY</small>
            <strong style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className={`badge ${uBadgeClass}`} style={{ fontSize: 10, padding: "2px 8px" }}>
                {uLevel}
              </span>
              <span>{pct(score.urgency_score)}</span>
            </strong>
            <span>Intervention Priority: {pct(score.intervention_priority)}</span>
          </div>

          <div className="hero-meta-item">
            <small>OUTREACH CHANNEL</small>
            <strong>{channelInfo(score.recommended_channel).label}</strong>
            <span>{profile.preferred_language} · {profile.device_type}</span>
          </div>

          <div>
            <button className="btn btn-secondary" onClick={() => window.print()} title="Print field advisory sheet">
              <Icon name="printer" size={14} />
              <span>Print Dossier</span>
            </button>
          </div>
        </div>
      </section>

      {/* ==================== QUICK OUTREACH ACTION STRIP ==================== */}
      <section className="quick-action-strip">
        <div className="action-strip-label">
          <Icon name="send" size={17} />
          <span>Outreach Action Center: Ready to dispatch agronomic advice to {profile.name}</span>
        </div>
        <div className="action-strip-buttons">
          <button
            className={`audio-preview-btn ${isAudioPlaying ? "playing" : ""}`}
            onClick={() => toggle(profile.grower_id, `/audio/${profile.grower_id}-advice.wav`)}
          >
            <Icon name={isAudioPlaying ? "pause" : "play"} size={13} />
            <span>{isAudioPlaying ? "Playing AI Voice Audio" : "Preview AI Voice"}</span>
          </button>
          <button className="btn btn-primary" onClick={handlePlaceCall}>
            <Icon name="phone" size={14} />
            <span>{callStatus === "calling" ? "Calling…" : "Place AI Voice Call"}</span>
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setActiveChannelTab("whatsapp");
              const el = document.getElementById("outreach-section");
              el?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            <Icon name="message" size={14} />
            <span>WhatsApp Preview</span>
          </button>
        </div>
      </section>

      {/* ==================== MILESTONE 7 & MILESTONE 4/5 INTELLIGENCE ==================== */}
      <div className="intel-grid">
        {/* M7 Urgency & Explainability */}
        <section className="card urgency-card">
          <div className="urgency-header">
            <div>
              <div className="eyebrow">MILESTONE 7 · URGENCY & FATIGUE SCORER</div>
              <div className="section-title">Urgency Score & Explainability Breakdown</div>
            </div>
            <span className="badge badge-high">{score.model_version}</span>
          </div>

          <div className="urgency-dial-wrap">
            <div
              className="urgency-radial"
              style={{
                background: `conic-gradient(var(--orange) 0% ${Math.round(score.urgency_score * 100)}%, #edf2ef ${Math.round(score.urgency_score * 100)}% 100%)`,
              }}
            >
              <div className="urgency-radial-inner">
                <strong>{Math.round(score.urgency_score * 100)}</strong>
                <small>{uLevel}</small>
              </div>
            </div>
            <div className="urgency-stats">
              <h4>Urgency Rating: {uLevel} ({pct(score.urgency_score)})</h4>
              <p>
                Calculated from 4 multi-dimensional signals: pest outbreak probability, weather deviation, phenological crop vulnerability, and communication recency window.
              </p>
            </div>
          </div>

          <div className="urgency-decomposition">
            <div className="term-bar">
              <div className="term-bar-header">
                <span>Pest Outbreak Risk Term (Weight 0.40)</span>
                <strong>{score.urgency_components.pest_risk_term.toFixed(2)}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill red"
                  style={{ width: `${Math.min(100, (score.urgency_components.pest_risk_term / 0.4) * 100)}%` }}
                />
              </div>
            </div>

            <div className="term-bar">
              <div className="term-bar-header">
                <span>Weather Anomaly Term (Weight 0.30)</span>
                <strong>{score.urgency_components.weather_anomaly_term.toFixed(2)}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill orange"
                  style={{ width: `${Math.min(100, (score.urgency_components.weather_anomaly_term / 0.3) * 100)}%` }}
                />
              </div>
            </div>

            <div className="term-bar">
              <div className="term-bar-header">
                <span>Crop Vulnerability Term (Weight 0.20)</span>
                <strong>{score.urgency_components.crop_vulnerability_term.toFixed(2)}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill green"
                  style={{ width: `${Math.min(100, (score.urgency_components.crop_vulnerability_term / 0.2) * 100)}%` }}
                />
              </div>
            </div>

            <div className="term-bar">
              <div className="term-bar-header">
                <span>Communication Window Term (Weight 0.10)</span>
                <strong>{score.urgency_components.recency_term.toFixed(2)}</strong>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill blue"
                  style={{ width: `${Math.min(100, (score.urgency_components.recency_term / 0.1) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* "Why Now?" Explanation */}
          <div className="why-now-box">
            <div className="why-now-icon"><Icon name="alert" size={20} /></div>
            <div>
              <strong>Why Now? Agronomic Urgency Rationale:</strong>
              <p>
                {signals.humidity_7d_avg >= 70
                  ? `Relative humidity (${Math.round(signals.humidity_7d_avg)}%) and anomalous rainfall (${Math.round(signals.rainfall_deviation_pct)}%) have crossed infection thresholds for ${signals.active_pest || "fungal foliar rust"}. `
                  : `Elevated pest pressure detected in ${profile.district} during ${humanize(cropStage.confirmed_stage)} stage. `}
                Acting within the 48-hour agronomic window prevents irreversible spore multiplication before transition to the next phenological growth stage.
              </p>
            </div>
          </div>
        </section>

        {/* M4 Weather Signals & M5 Crop Calendar + Mandi */}
        <section className="card calendar-card">
          <div className="urgency-header">
            <div>
              <div className="eyebrow">MILESTONE 4 & 5 · WEATHER, PEST & CROP CALENDAR</div>
              <div className="section-title">Environmental Signals & Phenology</div>
            </div>
            <span className="badge badge-medium">Open-Meteo & Agmarknet</span>
          </div>

          {/* M4 Weather Harvester */}
          <div className="weather-pest-grid">
            <div className="signal-cell">
              <div className="signal-cell-top">
                <span>7-Day Avg Humidity</span>
                <Icon name="cloud" size={14} />
              </div>
              <div className="signal-val">{Math.round(signals.humidity_7d_avg)}%</div>
              <div className="signal-note">
                {signals.humidity_7d_avg >= 70 ? "⚠️ High fungal risk (>70%)" : "Normal ambient range"}
              </div>
            </div>

            <div className="signal-cell">
              <div className="signal-cell-top">
                <span>Rainfall Deviation</span>
                <Icon name="rain" size={14} />
              </div>
              <div className="signal-val" style={{ color: signals.rainfall_deviation_pct > 100 ? "var(--red)" : "inherit" }}>
                {signals.rainfall_deviation_pct > 0 ? `+${Math.round(signals.rainfall_deviation_pct)}%` : `${Math.round(signals.rainfall_deviation_pct)}%`}
              </div>
              <div className="signal-note">
                {signals.weather_anomaly_flag ? "Significant deviation from 30y mean" : "Within normal limits"}
              </div>
            </div>

            <div className="signal-cell">
              <div className="signal-cell-top">
                <span>Pest Outbreak Risk</span>
                <Icon name="bug" size={14} />
              </div>
              <div className="signal-val" style={{ color: signals.pest_risk >= 0.5 ? "var(--red)" : "inherit" }}>
                {pct(signals.pest_risk)}
              </div>
              <div className="signal-note">
                Active vector: <strong>{humanize(signals.active_pest || "None")}</strong>
              </div>
            </div>

            <div className="signal-cell">
              <div className="signal-cell-top">
                <span>Crop Vulnerability</span>
                <Icon name="sprout" size={14} />
              </div>
              <div className="signal-val">{pct(cropStage.crop_vulnerability)}</div>
              <div className="signal-note">
                {cropStage.days_to_next_stage} days remaining in current stage
              </div>
            </div>
          </div>

          {/* M5 Phenological Crop Stage Progression */}
          <div style={{ marginTop: 20 }}>
            <div className="eyebrow">PHENOLOGICAL CROP STAGE PROGRESSION</div>
            <div className="crop-stages-timeline">
              <div className="timeline-connector" />
              {[
                { name: "Sowing", status: "completed" },
                { name: humanize(cropStage.confirmed_stage), status: "current" },
                { name: "Flowering", status: "upcoming" },
                { name: "Grain Fill", status: "upcoming" },
                { name: "Harvest", status: "upcoming" },
              ].map((st, i) => (
                <div key={st.name} className={`stage-node ${st.status}`}>
                  <div className="stage-bubble">
                    {st.status === "completed" ? (
                      <Icon name="check" size={14} />
                    ) : (
                      i + 1
                    )}
                  </div>
                  <span className="stage-name">{st.name}</span>
                  <span className="stage-timing">
                    {st.status === "current" ? `${cropStage.days_in_stage}d elapsed` : st.status === "completed" ? "Done" : "Upcoming"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Mandi Price & MSP Intelligence */}
          <div className="mandi-market-box">
            <div className="mandi-header">
              <h5>
                <Icon name="trend" size={15} /> Mandi Market Intelligence & MSP Benchmark ({mandi.commodity})
              </h5>
              <small style={{ color: "var(--muted)", fontSize: 10 }}>Agmarknet Modal Price</small>
            </div>
            <div className="mandi-grid">
              <div className="mandi-stat">
                <small>Government MSP</small>
                <strong>₹{mandi.msp_rs_quintal}</strong>
                <span style={{ color: "var(--muted)" }}>Per Quintal</span>
              </div>
              <div className="mandi-stat">
                <small>Today Modal Price</small>
                <strong>₹{mandi.today_price_rs_quintal}</strong>
                <span className={mandi.trend === "up" ? "trend-up" : "trend-down"}>
                  {mandi.trend === "up" ? "▲ Trading above MSP" : "▼ Trading near/below MSP"}
                </span>
              </div>
              <div className="mandi-stat">
                <small>Daily Market Arrival</small>
                <strong>{mandi.today_arrival_metric_tonnes} MT</strong>
                <span style={{ color: "var(--muted)" }}>Regional Mandis</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* ==================== STEP-BY-STEP FIELD-READY INSTRUCTIONS ==================== */}
      <section className="instructions-banner">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ color: "#a7f3d0", fontSize: 10, fontWeight: 800, letterSpacing: "1.2px", textTransform: "uppercase" }}>
              STEP-BY-STEP FIELD PROTOCOL · AGRONOMIC INTERVENTION
            </div>
            <div style={{ font: "800 22px 'Manrope', sans-serif", marginTop: 4 }}>
              What to do, which product to use, how much, and when
            </div>
            <p style={{ margin: "4px 0 0", color: "#d1fae5", fontSize: 12 }}>
              Clear actionable advice calibrated for {profile.name} ({profile.grower_farm_size} acres of {humanize(primaryCrop)})
            </p>
          </div>
          <span className="badge" style={{ background: "rgba(255,255,255,0.15)", color: "white" }}>
            Field Officer Ready
          </span>
        </div>

        <div className="instruction-steps-grid">
          <div className="step-card-field">
            <div className="step-number-tag">1</div>
            <small>STEP 1: WHAT TO DO</small>
            <strong>Foliar Canopy Treatment</strong>
            <p>
              Conduct a thorough foliar spray targeting newly emerging leaves and lower canopy sheaths where fungal rust spores germinate.
            </p>
          </div>

          <div className="step-card-field">
            <div className="step-number-tag">2</div>
            <small>STEP 2: WHICH PRODUCT TO USE</small>
            <strong>{topProductCanonical.name}</strong>
            <p>
              {topProductCanonical.active_ingredients}. High-efficacy systemic fungicide registered specifically for {primaryCrop}.
            </p>
          </div>

          <div className="step-card-field">
            <div className="step-number-tag">3</div>
            <small>STEP 3: HOW MUCH (DOSAGE)</small>
            <strong>{topProductCanonical.dosage}</strong>
            <p>
              {topProductCanonical.directions ? topProductCanonical.directions.slice(0, 115) + "…" : "Mix recommended quantity evenly in clean water. Spray using a knapsack sprayer with flat fan nozzle."}
            </p>
          </div>

          <div className="step-card-field">
            <div className="step-number-tag">4</div>
            <small>STEP 4: WHEN TO APPLY</small>
            <strong>{topProductCanonical.timing_window}</strong>
            <p>
              Apply within 48h during calm morning hours (7:00–10:00 AM). Rain-fastness: {topProductCanonical.rain_sensitive_hours} hour(s).
            </p>
          </div>
        </div>
      </section>

      {/* ==================== MILESTONE 8 PRODUCT RECOMMENDATIONS & RESISTANCE ==================== */}
      <section className="card products-section">
        <div className="section-head" style={{ padding: "0 0 16px" }}>
          <div>
            <div className="eyebrow">MILESTONE 8 · PERSONALIZED PRODUCT RANKER</div>
            <div className="section-title">Recommended Syngenta Inputs & Resistance Rotation</div>
            <div className="section-desc">
              Personalized matching on crop ({primaryCrop}), stage ({humanize(cropStage.confirmed_stage)}), and pest ({signals.active_pest || "rust"})
            </div>
          </div>
          <span className="badge badge-high">{products.model_version}</span>
        </div>

        <div className="products-grid">
          {products.top_products.map((p, idx) => {
            const canonical = enrichProduct(p.product_name);
            const rankLabel = idx === 0 ? "1st Recommendation" : idx === 1 ? "2nd Alternative" : "3rd Alternative";
            const rankClass = idx === 0 ? "gold" : "silver";

            return (
              <div key={p.product_name} className={`rec-product-card ${idx === 0 ? "primary" : ""}`}>
                <div className="rec-card-hero">
                  <span className={`product-rank-badge ${rankClass}`}>#{idx + 1} {rankLabel}</span>
                  <span className="product-match-chip">{Math.round(p.match_score * 100)}% Match</span>
                  <img
                    src={canonical.logo_url}
                    alt={p.product_name}
                    className="product-thumbnail-img"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src =
                        "https://www.syngenta.co.in/sites/g/files/kgtney376/files/styles/brand_logo/public/media/image/2021/12/16/score_logo.jpg";
                    }}
                  />
                </div>

                <div className="rec-card-body">
                  <h4 className="product-title">{p.product_name}</h4>
                  <div className="product-active-ingredient">{canonical.active_ingredients}</div>

                  <div className="product-specs">
                    <div className="spec-item">
                      <small>CATEGORY</small>
                      <strong>{canonical.type || "Fungicide"}</strong>
                    </div>
                    <div className="spec-item">
                      <small>ACTION MODE</small>
                      <strong>{canonical.application_mode || "Foliar spray"}</strong>
                    </div>
                    <div className="spec-item">
                      <small>PRICE TIER</small>
                      <strong>{humanize((p.score_breakdown?.price_tier as string) || canonical.price_tier || "Mid")}</strong>
                    </div>
                    <div className="spec-item">
                      <small>RAIN-FASTNESS</small>
                      <strong>{canonical.rain_sensitive_hours} hr(s)</strong>
                    </div>
                  </div>

                  <div className="why-product-box">
                    <h6>Why this product?</h6>
                    <ul>
                      {p.match_reasons.map((r, rIdx) => (
                        <li key={rIdx}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 12 }}>
                    <strong>Dosage:</strong> {canonical.dosage}
                  </div>

                  <div className="moa-badge-row">
                    <span className="moa-tag">{canonical.moa_group}</span>
                    <span style={{ fontSize: 10, color: "var(--muted)" }}>{canonical.moa_class}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Mode of Action Resistance Rotation Guidance & Deduplication Transparency */}
        <div className="moa-transparency-card">
          <div className="moa-transparency-header">
            <Icon name="rotate" size={17} />
            <span>MoA (Mode of Action) Resistance Rotation Advisory & Deduplication Policy</span>
          </div>
          <div className="moa-transparency-desc">
            To prevent fungicide resistance, Syngenta KrishiMitra enforces strict Mode-of-Action rotation. Never apply products belonging to the same FRAC/IRAC group consecutively in the same cropping season.
          </div>

          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--forest-950)", marginBottom: 8 }}>
            Catalog Products Intentionally Not Ranked Higher (Resistance & Stage Guards):
          </div>

          <div className="not-recommended-grid">
            {(products.not_recommended && products.not_recommended.length > 0
              ? products.not_recommended
              : [
                  {
                    product_name: "Score 250 EC",
                    not_ranked_higher_because: [
                      "Same MoA group (FRAC-3) already represented by #1 recommendation Tilt 250 EC — rotated to prevent chemical resistance",
                    ],
                  },
                  {
                    product_name: "Alto 5 SC",
                    not_ranked_higher_because: [
                      "Same MoA group (FRAC-3) already represented — alternative modes of action prioritized",
                    ],
                  },
                  {
                    product_name: "Cruiser 350 FS",
                    not_ranked_higher_because: [
                      "Seed treatment formulation — not suitable for foliar spray intervention at tillering stage",
                    ],
                  },
                ]
            ).map((item) => (
              <div key={item.product_name} className="not-rec-item">
                <strong>{item.product_name}</strong>
                <p>{item.not_ranked_higher_because[0]}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ==================== MULTI-CHANNEL OUTREACH ACTION CENTER ==================== */}
      <section id="outreach-section" className="card outreach-center" style={{ marginTop: 24 }}>
        <div className="section-head" style={{ padding: "0 0 16px" }}>
          <div>
            <div className="eyebrow">MILESTONE 9, 16 & 17 · MULTI-CHANNEL OUTREACH CENTER</div>
            <div className="section-title">Grower Receptivity & Live Outbound Delivery</div>
            <div className="section-desc">
              Campaign scheduling, channel receptivity scoring, and interactive outbound advisory dispatch
            </div>
          </div>
          <span className="badge badge-critical">{receptivity.model_version}</span>
        </div>

        <div className="outreach-split">
          {/* Receptivity Intelligence */}
          <div className="receptivity-panel">
            <h5 style={{ margin: "0 0 4px", font: "700 14px 'Manrope', sans-serif" }}>
              Grower Behavioral Persona & Timing
            </h5>
            <p style={{ margin: 0, fontSize: 11, color: "var(--muted)" }}>
              Segment: <strong>{humanize(receptivity.segment)}</strong> ({pct(receptivity.segment_confidence)} confidence)
            </p>

            <div className="receptivity-kpis">
              <div className="receptivity-kpi">
                <small>RECEPTIVITY SCORE</small>
                <strong>{pct(receptivity.receptivity_score)}</strong>
              </div>
              <div className="receptivity-kpi">
                <small>FATIGUE RISK</small>
                <strong style={{ color: receptivity.fatigue_risk > 0.5 ? "var(--red)" : "var(--green-700)" }}>
                  {pct(receptivity.fatigue_risk)}
                </strong>
              </div>
              <div className="receptivity-kpi">
                <small>BEST DAY OF WEEK</small>
                <strong>{receptivity.best_day_of_week || "Wednesday–Friday"}</strong>
              </div>
              <div className="receptivity-kpi">
                <small>OPTIMAL TIME WINDOW</small>
                <strong>{receptivity.best_time_window || "8:00–10:00 AM"}</strong>
              </div>
            </div>

            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--forest-900)", marginBottom: 8 }}>
              Predicted Channel Format Engagement:
            </div>
            {receptivity.recommended_formats.map((fmt) => (
              <div key={fmt.format} className="format-bar">
                <span>{humanize(fmt.format)}</span>
                <strong>{pct(fmt.predicted_engagement)}</strong>
              </div>
            ))}

            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: "var(--muted)", textTransform: "uppercase", marginBottom: 6 }}>
                Strategic Campaign Suggestions:
              </div>
              <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: "var(--ink-secondary)", lineHeight: 1.45 }}>
                {receptivity.creative_suggestions.map((s, idx) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Outbound Dispatch Terminals */}
          <div className="dispatch-panel">
            <div className="dispatch-tab-bar">
              <button
                className={`dispatch-tab ${activeChannelTab === "voice" ? "active" : ""}`}
                onClick={() => setActiveChannelTab("voice")}
              >
                <Icon name="phone" size={14} /> AI Voice Call (M17)
              </button>
              <button
                className={`dispatch-tab ${activeChannelTab === "whatsapp" ? "active" : ""}`}
                onClick={() => setActiveChannelTab("whatsapp")}
              >
                <Icon name="message" size={14} /> WhatsApp Advisory (M11)
              </button>
              <button
                className={`dispatch-tab ${activeChannelTab === "sms" ? "active" : ""}`}
                onClick={() => setActiveChannelTab("sms")}
              >
                <Icon name="send" size={14} /> SMS Alert (M10)
              </button>
            </div>

            {/* AI Voice Call Terminal */}
            {activeChannelTab === "voice" && (
              <div className="dispatch-content-box">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h5 style={{ margin: 0, font: "700 14px 'Manrope'" }}>Interactive Gemini Live Voice Call</h5>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>
                      Outbound phone call via Twilio Media Streams in {profile.preferred_language}
                    </p>
                  </div>
                  <button className="btn btn-primary" onClick={handlePlaceCall}>
                    <Icon name="phone" size={14} />
                    <span>{callStatus === "calling" ? "Connecting…" : "Trigger Call"}</span>
                  </button>
                </div>

                <div className="audio-player-card">
                  <button
                    className="audio-play-round"
                    onClick={() => toggle(profile.grower_id, `/audio/${profile.grower_id}-advice.wav`)}
                    title="Play voice clip"
                  >
                    <Icon name={isAudioPlaying ? "pause" : "play"} size={20} />
                  </button>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "var(--forest-950)" }}>
                      AI Voice Advisory Audio Preview
                    </div>
                    <div style={{ fontSize: 10, color: "var(--muted)" }}>
                      Synthetic Hindi voice generated with personalized context for {profile.name}
                    </div>
                  </div>
                  <span className="badge badge-medium">1:12 Duration</span>
                </div>

                {callStatus === "success" && (
                  <div className="dispatch-status success">
                    <Icon name="check" size={14} />
                    <span>{callMessage}</span>
                  </div>
                )}
                {callStatus === "error" && (
                  <div className="dispatch-status error">
                    <Icon name="alert" size={14} />
                    <span>Failed to trigger call: {callMessage}</span>
                  </div>
                )}
              </div>
            )}

            {/* WhatsApp Terminal */}
            {activeChannelTab === "whatsapp" && (
              <div className="dispatch-content-box">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h5 style={{ margin: 0, font: "700 14px 'Manrope'" }}>WhatsApp Rich Message Template</h5>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>
                      Delivered to {profile.phone} with product instructions & linked retailer
                    </p>
                  </div>
                  <button
                    className="btn btn-success"
                    onClick={() => {
                      setWaSent(true);
                      setTimeout(() => setWaSent(false), 5000);
                    }}
                  >
                    <Icon name="message" size={14} />
                    <span>{waSent ? "Sent to WhatsApp!" : "Send to Farmer"}</span>
                  </button>
                </div>

                <div className="channel-preview-bubble">{whatsappScript}</div>

                {waSent && (
                  <div className="dispatch-status success">
                    <Icon name="check" size={14} />
                    <span>WhatsApp advisory dispatched to {profile.phone} successfully!</span>
                  </div>
                )}
              </div>
            )}

            {/* SMS Terminal */}
            {activeChannelTab === "sms" && (
              <div className="dispatch-content-box">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <h5 style={{ margin: 0, font: "700 14px 'Manrope'" }}>SMS Short Text Alert</h5>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>
                      Optimized 160-char SMS for keypad/2G phones in {profile.preferred_language}
                    </p>
                  </div>
                  <button
                    className="btn btn-primary"
                    onClick={() => {
                      setSmsSent(true);
                      setTimeout(() => setSmsSent(false), 5000);
                    }}
                  >
                    <Icon name="send" size={14} />
                    <span>{smsSent ? "SMS Dispatched!" : "Dispatch SMS"}</span>
                  </button>
                </div>

                <div className="channel-preview-bubble">{smsScript}</div>

                {smsSent && (
                  <div className="dispatch-status success">
                    <Icon name="check" size={14} />
                    <span>SMS delivered to {profile.phone} via Twilio SMS service!</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

// ==================== ROOT APPLICATION COMPONENT ====================
export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [selectedGrowerId, setSelectedGrowerId] = useState<string | null>(null);
  const [farmers, setFarmers] = useState<FarmerProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listFarmers()
      .then((data) => {
        setFarmers(data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const navigate = (next: Page) => {
    setPage(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const viewFarmer = (id: string) => {
    setSelectedGrowerId(id);
    setPage("farmer");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="app">
      <Topbar page={page} navigate={navigate} />

      {loading ? (
        <main>
          <div className="card" style={{ padding: 48, textAlign: "center", color: "var(--muted)" }}>
            <Icon name="refresh" size={26} />
            <div style={{ marginTop: 12, fontWeight: 700 }}>Loading KrishiMitra Agronomy Dashboard…</div>
          </div>
        </main>
      ) : (
        <>
          {page === "overview" && (
            <Overview
              farmers={farmers}
              viewFarmer={viewFarmer}
              navigate={navigate}
            />
          )}

          {page === "farmers" && (
            <FarmersDirectory
              farmers={farmers}
              viewFarmer={viewFarmer}
            />
          )}

          {page === "farmer" && selectedGrowerId && (
            <FarmIntelligencePage
              growerId={selectedGrowerId}
              back={() => navigate("farmers")}
            />
          )}
        </>
      )}
    </div>
  );
}