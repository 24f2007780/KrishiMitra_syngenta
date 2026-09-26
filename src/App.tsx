import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  api,
  type FarmerContext,
  type FarmerProfile,
  type RankResponse,
  type ReceptivityResponse,
  type UrgencyResponse,
  type VoiceCallRequest,
} from "./api";

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
  | "pause";

const iconPaths: Record<IconName, ReactNode> = {
  leaf: <><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 4.8 18 2 18 2c1 6.5-1.1 12.7-7 14.2" /><path d="M2 21c0-3 1.85-5.36 5.08-6.94C9.47 12.9 12.16 12 16 12" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
  alert: <><path d="M10.3 2.9 1.8 17a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 2.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m7 16 4-5 4 3 5-7" /></>,
  arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
  cloud: <><path d="M17.5 19H9a7 7 0 1 1 6.7-9h1.8a4.5 4.5 0 1 1 0 9Z" /><path d="m9 22 1-2m4 2 1-2" /></>,
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
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{iconPaths[name]}</svg>;
}

function Button({ children, variant = "primary", icon, onClick, className = "" }: { children: ReactNode; variant?: "primary" | "secondary" | "ghost"; icon?: IconName; onClick?: () => void; className?: string }) {
  return <button className={`btn btn-${variant} ${className}`} onClick={onClick}>{icon && <Icon name={icon} size={16} />}<span>{children}</span></button>;
}

function urgencyLevel(score: number | undefined): "Critical" | "High" | "Medium" {
  const value = score ?? 0;
  if (value >= 0.75) return "Critical";
  if (value >= 0.5) return "High";
  return "Medium";
}

function Badge({ score }: { score: number | undefined }) {
  const level = urgencyLevel(score);
  return <span className={`badge badge-${level.toLowerCase()}`}><span className="status-dot" />{level}</span>;
}

const channelMeta: Record<string, { icon: IconName; label: string }> = {
  whatsapp: { icon: "message", label: "WhatsApp" },
  sms: { icon: "send", label: "SMS" },
  voice_call: { icon: "phone", label: "Voice call" },
  field_visit: { icon: "map", label: "Field visit" },
  suppress: { icon: "alert", label: "Suppressed" },
};

function channelInfo(channel?: string | null) {
  if (!channel) return { icon: "message" as IconName, label: "Unassigned" };
  return channelMeta[channel] ?? { icon: "message" as IconName, label: channel };
}

function humanize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function pct(value: number | undefined) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

function Header({ page, navigate }: { page: Page; navigate: (p: Page) => void }) {
  const items: { label: string; page: Page }[] = [
    { label: "Overview", page: "overview" },
    { label: "Farmers", page: "farmers" },
  ];
  return <header className="topbar">
    <button className="brand" onClick={() => navigate("overview")}><span className="brand-mark"><Icon name="leaf" size={21} /></span><span className="brand-name">KrishiMitra</span><span className="brand-divider" /><span className="brand-sub">Farmer Intelligence</span></button>
    <nav>{items.map((item) => <button key={item.label} onClick={() => navigate(item.page)} className={page === item.page ? "nav-item active" : "nav-item"}>{item.label}</button>)}</nav>
    <div className="top-actions">
      <button className="icon-button" aria-label="Search"><Icon name="search" /></button>
      <button className="icon-button notification" aria-label="Notifications"><Icon name="bell" /><span /></button>
      <button className="profile"><span className="avatar small">FO</span><span><strong>Field Operations</strong><small>KrishiMitra</small></span><Icon name="chevron" size={14} /></button>
    </div>
  </header>;
}

function PageTitle({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: ReactNode }) {
  return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><div className="title">{title}</div><div className="subtitle">{description}</div></div>{actions && <div className="page-actions">{actions}</div>}</div>;
}

function KpiCard({ icon, label, value, note, tone }: { icon: IconName; label: string; value: string; note: string; tone: string }) {
  return <div className="card kpi"><div className={`kpi-icon ${tone}`}><Icon name={icon} /></div><div><div className="muted-label">{label}</div><div className="kpi-value">{value}</div><div className="kpi-note">{note}</div></div></div>;
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "??";
}

function LoadingState({ label = "Loading live data…" }: { label?: string }) {
  return <div className="card" style={{ padding: 32, textAlign: "center", color: "var(--muted)", fontSize: 12 }}>{label}</div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="card" style={{ padding: 32, textAlign: "center", color: "var(--red)", fontSize: 12 }}>
    Couldn't reach the backend services. Make sure they're running (<code>./run_all.sh</code>).<br />{message}
  </div>;
}

// One real, actually-generated advisory voice clip (not a mock) used to preview
// what an AI voice call sounds like. Shared across rows via a single Audio
// element so opening the table never triggers more than one active player.
const VOICE_PREVIEW_SRC = "/audio/mayur-advice.wav";

function useVoicePreview() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => {
    const audio = new Audio(VOICE_PREVIEW_SRC);
    audio.preload = "none";
    audio.addEventListener("ended", () => setPlayingId(null));
    audioRef.current = audio;
    return () => { audio.pause(); audioRef.current = null; };
  }, []);

  const toggle = (id: string) => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playingId === id) {
      audio.pause();
      setPlayingId(null);
      return;
    }
    audio.currentTime = 0;
    audio.play().catch(() => {});
    setPlayingId(id);
  };

  return { playingId, toggle };
}

function FarmerTable({ farmers, navigate }: { farmers: FarmerProfile[]; navigate: (id: string) => void }) {
  const { playingId, toggle } = useVoicePreview();
  return <div className="table-wrap">
    <div className="farmer-table">
      <div className="table-row table-head">
        <div>Farmer</div><div>Crops</div><div>Urgency</div><div>Recommended channel</div><div>Preferred time</div><div /><div>Voice preview</div>
      </div>
      {farmers.map((farmer) => <div className="table-row" key={farmer.grower_id}>
        <div className="farmer-cell"><span className="avatar">{initials(farmer.name)}</span><span><strong>{farmer.name}</strong><small><Icon name="map" size={12} />{farmer.district}, {farmer.state}</small></span></div>
        <div><strong>{farmer.crops.map(humanize).join(", ") || "—"}</strong><small>{farmer.grower_farm_size} acres</small></div>
        <div><Badge score={farmer.urgency_score} /><small className="score">{pct(farmer.urgency_score)}</small></div>
        <div><span className="channel"><Icon name={channelInfo(farmer.recommended_channel).icon} size={15} />{channelInfo(farmer.recommended_channel).label}</span></div>
        <div><strong>{humanize(farmer.preferred_contact_time)}</strong></div>
        <div><Button variant="secondary" onClick={() => navigate(farmer.grower_id)}>View Farmer<Icon name="arrow" size={14} /></Button></div>
        <div>
          <button
            className={`audio-preview-btn ${playingId === farmer.grower_id ? "playing" : ""}`}
            onClick={(e) => { e.stopPropagation(); toggle(farmer.grower_id); }}
            aria-label="Preview AI voice advisory"
            title="Preview AI voice advisory"
          >
            <Icon name={playingId === farmer.grower_id ? "pause" : "play"} size={12} />
            {playingId === farmer.grower_id ? "Playing" : "Preview"}
          </button>
        </div>
      </div>)}
      {farmers.length === 0 && <div className="table-row"><div style={{ color: "var(--muted)", fontSize: 11 }}>No farmers match these filters.</div></div>}
    </div>
  </div>;
}

function useFarmers() {
  const [farmers, setFarmers] = useState<FarmerProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    api.listFarmers()
      .then((data) => { if (!cancelled) setFarmers(data); })
      .catch((err) => { if (!cancelled) setError(String(err)); });
    return () => { cancelled = true; };
  }, []);
  return { farmers, error };
}

function Overview({ farmers, error, viewFarmer, navigate }: { farmers: FarmerProfile[] | null; error: string | null; viewFarmer: (id: string) => void; navigate: (p: Page) => void }) {
  const today = useMemo(() => new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }), []);
  const sorted = useMemo(() => [...(farmers ?? [])].sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0)), [farmers]);
  const highUrgency = sorted.filter((f) => urgencyLevel(f.urgency_score) !== "Medium").length;
  const avgUrgency = farmers && farmers.length ? farmers.reduce((sum, f) => sum + (f.urgency_score ?? 0), 0) / farmers.length : 0;
  const whatsappReady = farmers?.filter((f) => f.whatsapp_enabled).length ?? 0;

  return <main>
    <PageTitle eyebrow={today.toUpperCase() + " · LIVE OPERATIONS"} title="Good morning" description="Live farmer intelligence pulled straight from the KrishiMitra services." actions={<Button icon="calendar" onClick={() => navigate("farmers")}>View all farmers</Button>} />
    {error && <ErrorState message={error} />}
    {!error && !farmers && <LoadingState />}
    {!error && farmers && <>
      <section className="kpi-grid">
        <KpiCard icon="users" label="FARMERS MONITORED" value={String(farmers.length)} note="Live from Farmer DB (M1)" tone="green" />
        <KpiCard icon="alert" label="HIGH URGENCY" value={String(highUrgency)} note="Urgency score ≥ 50%" tone="orange" />
        <KpiCard icon="chart" label="AVG URGENCY SCORE" value={pct(avgUrgency)} note="Across monitored farmers" tone="purple" />
        <KpiCard icon="message" label="WHATSAPP READY" value={String(whatsappReady)} note={`of ${farmers.length} farmers`} tone="blue" />
      </section>
      <section className="section-block">
        <div className="section-heading"><div><div className="section-title">Who to reach today</div><div className="section-subtitle">Ranked by live urgency score (M7 Intelligence Engine)</div></div></div>
        <FarmerTable farmers={sorted} navigate={viewFarmer} />
      </section>
    </>}
  </main>;
}

function Farmers({ farmers, error, viewFarmer }: { farmers: FarmerProfile[] | null; error: string | null; viewFarmer: (id: string) => void }) {
  const [state, setState] = useState("all");
  const [crop, setCrop] = useState("all");
  const [q, setQ] = useState("");

  const states = useMemo(() => Array.from(new Set((farmers ?? []).map((f) => f.state))).sort(), [farmers]);
  const crops = useMemo(() => Array.from(new Set((farmers ?? []).flatMap((f) => f.crops))).sort(), [farmers]);

  const filtered = useMemo(() => {
    return (farmers ?? [])
      .filter((f) => state === "all" || f.state === state)
      .filter((f) => crop === "all" || f.crops.includes(crop))
      .filter((f) => f.name.toLowerCase().includes(q.toLowerCase()))
      .sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));
  }, [farmers, state, crop, q]);

  return <main>
    <PageTitle eyebrow="FARMER DIRECTORY" title="All Farmers" description="Filter the live farmer roster by state, crop or name." />
    {error && <ErrorState message={error} />}
    {!error && !farmers && <LoadingState />}
    {!error && farmers && <>
      <div className="filter-bar">
        <span className="filter-label"><Icon name="filter" size={16} />Filters</span>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name…" style={{ border: "1px solid var(--line)", borderRadius: 7, padding: "7px 9px", fontSize: 11, minWidth: 160 }} />
        <select value={state} onChange={(e) => setState(e.target.value)} style={{ border: "1px solid var(--line)", borderRadius: 7, padding: "7px 9px", fontSize: 11, background: "white" }}>
          <option value="all">State: All</option>
          {states.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={crop} onChange={(e) => setCrop(e.target.value)} style={{ border: "1px solid var(--line)", borderRadius: 7, padding: "7px 9px", fontSize: 11, background: "white" }}>
          <option value="all">Crop: All</option>
          {crops.map((c) => <option key={c} value={c}>{humanize(c)}</option>)}
        </select>
        {(state !== "all" || crop !== "all" || q) && <button className="clear" onClick={() => { setState("all"); setCrop("all"); setQ(""); }}>Clear all</button>}
      </div>
      <section className="section-block">
        <div className="section-heading"><div><div className="section-title">{filtered.length} farmer{filtered.length === 1 ? "" : "s"}</div><div className="section-subtitle">Ranked by urgency score</div></div></div>
        <FarmerTable farmers={filtered} navigate={viewFarmer} />
      </section>
    </>}
  </main>;
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>;
}

function Progress({ value, tone = "green" }: { value: number; tone?: string }) {
  return <div className="progress"><span className={tone} style={{ width: `${Math.round(value * 100)}%` }} /></div>;
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return <div className="score-bar"><div><span>{label}</span><strong>{pct(value)}</strong></div><Progress value={value} tone={value > 0.6 ? "danger" : "warning"} /></div>;
}

function ContextCard({ title, icon, children }: { title: string; icon: IconName; children: ReactNode }) {
  return <div className="card context-card"><div className="card-title"><span><Icon name={icon} size={18} /></span>{title}</div>{children}</div>;
}

function ProductCard({ rank, product }: { rank: number; product: RankResponse["top_products"][number] }) {
  const priceTier = (product.score_breakdown?.price_tier as string) || "";
  return <div className="product-card">
    <div className="product-top"><span className="rank">#{rank}</span><span className="match"><strong>{Math.round(product.match_score * 100)}%</strong> match</span></div>
    <div className="product-name">{product.product_name}</div>
    {priceTier && <div className="product-type">{humanize(priceTier)} price tier · {Math.round(product.confidence * 100)}% confidence</div>}
    <p>{product.match_reasons[0] ?? "Recommended for this farmer's crop and pest profile."}</p>
  </div>;
}

function CallFarmerAction({ profile, context, score, topProduct }: { profile: FarmerProfile; context: FarmerContext; score: UrgencyResponse; topProduct: string }) {
  const [callState, setCallState] = useState<"idle" | "calling" | "success" | "error">("idle");
  const [callMessage, setCallMessage] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const audio = new Audio(VOICE_PREVIEW_SRC);
    audio.preload = "none";
    audio.addEventListener("ended", () => setPreviewing(false));
    audioRef.current = audio;
    return () => { audio.pause(); audioRef.current = null; };
  }, []);

  const togglePreview = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (previewing) { audio.pause(); setPreviewing(false); return; }
    audio.currentTime = 0;
    audio.play().catch(() => {});
    setPreviewing(true);
  };

  const placeCall = async () => {
    setCallState("calling");
    setCallMessage("");
    const pestRisk = context.signals.pest_risk >= 0.7 ? "high" : context.signals.pest_risk >= 0.4 ? "medium" : "low";
    const body: VoiceCallRequest = {
      to_number: profile.phone,
      farmer_id: profile.grower_id,
      farmer_name: profile.name,
      preferred_language: profile.preferred_language,
      state: profile.state,
      district: profile.district,
      village: profile.tehsil,
      crops: profile.crops,
      crop_stage: context.crop_stage.confirmed_stage,
      pest_risk_level: pestRisk,
      active_pest: context.signals.active_pest,
      why_now: `Top signals: ${score.top_factors.join(", ")}.`,
      recommended_product: topProduct,
      retailer_name: profile.linked_retailer_name,
      urgency_score: score.urgency_score,
    };
    try {
      const res = await api.placeVoiceCall(body);
      setCallState("success");
      setCallMessage(res.message || `Call placed — SID ${res.call_sid ?? "unknown"}`);
    } catch (err) {
      setCallState("error");
      setCallMessage(String(err instanceof Error ? err.message : err));
    }
  };

  return (
    <section className="call-action">
      <div className="call-action-flow">
        <span>Farmer</span><Icon name="arrow" size={11} />
        <span>AI Urgency</span><Icon name="arrow" size={11} />
        <span>Recommendation</span><Icon name="arrow" size={11} />
        <span className="current">AI Voice Advisory</span><Icon name="arrow" size={11} />
        <span>Call / Outreach</span>
      </div>
      <div className="call-action-body">
        <div>
          <div className="section-title">Ready to reach {profile.name}</div>
          <p className="call-action-note">Places a real outbound advisory call using this farmer's live crop, pest and urgency context.</p>
        </div>
        <div className="call-action-buttons">
          <button className="btn btn-secondary" onClick={togglePreview}>
            <Icon name={previewing ? "pause" : "play"} size={14} />
            <span>{previewing ? "Playing sample" : "Preview voice sample"}</span>
          </button>
          <Button icon="phone" onClick={placeCall}>{callState === "calling" ? "Calling…" : "Call Farmer"}</Button>
        </div>
      </div>
      {callState === "success" && <div className="voice-call-status success"><Icon name="check" size={12} />{callMessage}</div>}
      {callState === "error" && <div className="voice-call-status error"><Icon name="alert" size={12} />Voice backend unreachable ({callMessage})</div>}
    </section>
  );
}

function FarmerDetail({ growerId, back }: { growerId: string; back: () => void }) {
  const [context, setContext] = useState<FarmerContext | null>(null);
  const [score, setScore] = useState<UrgencyResponse | null>(null);
  const [products, setProducts] = useState<RankResponse | null>(null);
  const [receptivity, setReceptivity] = useState<ReceptivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setContext(null); setScore(null); setProducts(null); setReceptivity(null); setError(null);
    Promise.all([
      api.getContext(growerId),
      api.getScore(growerId),
      api.getProducts(growerId),
      api.getReceptivity(growerId),
    ]).then(([ctx, sc, prod, rec]) => {
      if (cancelled) return;
      setContext(ctx); setScore(sc); setProducts(prod); setReceptivity(rec);
    }).catch((err) => { if (!cancelled) setError(String(err)); });
    return () => { cancelled = true; };
  }, [growerId]);

  if (error) return <main><ErrorState message={error} /></main>;
  if (!context || !score || !products || !receptivity) return <main><LoadingState /></main>;

  const profile = context.profile;
  const components = score.urgency_components as Record<string, number>;
  const topProduct = products.top_products[0]?.product_name || "the recommended product";

  return <main className="farmer-page">
    <div className="breadcrumb"><button onClick={back}>All farmers</button><Icon name="chevron" size={13} /><span>Farmer 360</span></div>
    <PageTitle title={`${profile.name} — Farmer 360`} description={`${profile.tehsil}, ${profile.district}, ${profile.state} · ${profile.preferred_language} speaker`} />
    <div className="farmer-profile-strip">
      <div className="profile-main"><span className="avatar large">{initials(profile.name)}</span><div><strong>{profile.name}</strong><small><Icon name="map" size={13} />{profile.district} · {profile.state}</small></div></div>
      <div><div className="muted-label">PRIMARY CROP</div><strong style={{ fontSize: 12 }}>{humanize(profile.crops[0] ?? "—")}</strong></div>
      <div><div className="muted-label">FARM SIZE</div><strong style={{ fontSize: 12 }}>{profile.grower_farm_size} acres</strong></div>
      <div><div className="muted-label">LAST CONTACT</div><strong style={{ fontSize: 12 }}>{profile.last_message_sent_at ? new Date(profile.last_message_sent_at).toLocaleDateString() : "No contact yet"}</strong></div>
      <div><div className="muted-label">CURRENT PRIORITY</div><Badge score={score.urgency_score} /></div>
    </div>
    <section className="attention-card">
      <span className="ai-spark">AI</span>
      <div className="attention-content">
        <div className="attention-top"><div><div className="eyebrow">M7 URGENCY ENGINE</div><div className="section-title">Why this farmer needs attention now</div></div><span className="confidence"><Icon name="check" size={13} />{pct(score.confidence)} confidence</span></div>
        <p>Top factors: <strong>{score.top_factors.join(", ")}</strong>. Urgency score is {pct(score.urgency_score)}, engagement likelihood {pct(score.engagement_score)}, combined intervention priority {pct(score.intervention_priority)}.</p>
        <div className="signal-row"><span><Icon name="cloud" size={14} />Weather signals</span><span><Icon name="bug" size={14} />Pest forecast</span><span><Icon name="sprout" size={14} />Crop stage model</span><small>Assembled {new Date(context.assembled_at).toLocaleTimeString()}</small></div>
      </div>
    </section>
    <section className="context-grid">
      <ContextCard title="Weather & Pest Risk" icon="cloud">
        <div className="weather-main"><div><span className="weather-value">{Math.round(context.signals.humidity_7d_avg)}%</span><small>Avg humidity, 7d</small></div><div className="mini-weather"><Metric label="Rainfall deviation" value={`${Math.round(context.signals.rainfall_deviation_pct)}%`} /><Metric label="Active pest" value={context.signals.active_pest || "None"} /></div></div>
        <div className="risk-line"><span>Weather anomaly</span><strong className="warning-text">{pct(context.signals.weather_anomaly)}</strong></div><Progress value={context.signals.weather_anomaly} tone="warning" />
        <div className="risk-line"><span>Pest risk</span><strong className="danger-text">{pct(context.signals.pest_risk)}</strong></div><Progress value={context.signals.pest_risk} tone="danger" />
      </ContextCard>
      <ContextCard title="Crop Status" icon="sprout">
        <div className="crop-head"><span className="crop-symbol"><Icon name="sprout" size={25} /></span><div><strong>{humanize(profile.crops[0] ?? "—")}</strong><small>{humanize(context.crop_stage.confirmed_stage)} stage</small></div></div>
        <div className="two-col"><Metric label="NEXT STAGE" value={`${context.crop_stage.days_to_next_stage} days`} /><Metric label="CROP VULNERABILITY" value={pct(context.crop_stage.crop_vulnerability)} /></div>
      </ContextCard>
      <ContextCard title="AI Urgency Score" icon="alert">
        <div className="score-layout">
          <div className="score-ring" style={{ background: `conic-gradient(var(--orange) 0 ${Math.round(score.urgency_score * 100)}%, #edf0ee ${Math.round(score.urgency_score * 100)}%)` }}>
            <div><strong>{Math.round(score.urgency_score * 100)}</strong><span>/ 100</span><small>{urgencyLevel(score.urgency_score).toUpperCase()}</small></div>
          </div>
          <div className="score-bars">
            {"pest_risk_term" in components && <ScoreBar label="Pest risk" value={components.pest_risk_term} />}
            {"weather_anomaly_term" in components && <ScoreBar label="Weather anomaly" value={components.weather_anomaly_term} />}
            {"crop_vulnerability_term" in components && <ScoreBar label="Crop vulnerability" value={components.crop_vulnerability_term} />}
            {"recency_term" in components && <ScoreBar label="Communication window" value={components.recency_term} />}
          </div>
        </div>
      </ContextCard>
    </section>
    <section className="section-block products">
      <div className="section-heading"><div><div className="section-title">Recommended Products</div><div className="section-subtitle">From M8 Product Ranker, matched on crop, pest and growth stage</div></div><span className="model-chip"><span className="live-dot" />{products.model_version}</span></div>
      <div className="product-grid">
        {products.top_products.map((p, i) => <ProductCard key={p.product_name} rank={i + 1} product={p} />)}
      </div>
    </section>
    <section className="outreach-reco">
      <div className="recommendation-main">
        <span className="reco-icon"><Icon name={channelInfo(score.recommended_channel).icon} size={22} /></span>
        <div>
          <div className="eyebrow">RECOMMENDED OUTREACH</div>
          <div className="section-title">Best action: {channelInfo(score.recommended_channel).label}{receptivity.best_time_window ? ` on ${receptivity.best_day_of_week}, ${receptivity.best_time_window}` : ""}</div>
          <p>Segment: {humanize(receptivity.segment)} ({pct(receptivity.segment_confidence)} confidence). {receptivity.creative_suggestions[0]}</p>
        </div>
      </div>
      <div className="reco-stats">
        <Metric label="CHANNEL" value={channelInfo(score.recommended_channel).label} />
        <Metric label="BEST WINDOW" value={receptivity.best_time_window || "Any time"} note={receptivity.best_day_of_week ?? undefined} />
        <Metric label="RECEPTIVITY" value={pct(receptivity.receptivity_score)} />
        <Metric label="FATIGUE RISK" value={pct(receptivity.fatigue_risk)} />
      </div>
    </section>
    <CallFarmerAction profile={profile} context={context} score={score} topProduct={topProduct} />
    {receptivity.creative_suggestions.length > 1 && <section className="section-block" style={{ padding: 18 }}>
      <div className="section-title" style={{ marginBottom: 10 }}>Campaign strategy notes</div>
      <div className="reason-list">
        {receptivity.creative_suggestions.map((s) => <span key={s}><Icon name="check" size={14} />{s}</span>)}
      </div>
    </section>}
  </main>;
}

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { farmers, error } = useFarmers();

  const navigate = (next: Page) => { setPage(next); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const viewFarmer = (id: string) => { setSelectedId(id); setPage("farmer"); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return <div className="app">
    <Header page={page} navigate={navigate} />
    {page === "overview" && <Overview farmers={farmers} error={error} viewFarmer={viewFarmer} navigate={navigate} />}
    {page === "farmers" && <Farmers farmers={farmers} error={error} viewFarmer={viewFarmer} />}
    {page === "farmer" && selectedId && <FarmerDetail growerId={selectedId} back={() => navigate("farmers")} />}
    <div className="demo-label">LIVE DATA · KrishiMitra services</div>
  </div>;
}
