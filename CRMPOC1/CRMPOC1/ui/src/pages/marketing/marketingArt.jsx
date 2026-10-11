import { ICON_PATHS } from "../sales/salesUi.jsx";

// The broadcast picture on the Marketing banner: rings that spread out from a megaphone.
export function HeroArt() {
  return (
    <svg viewBox="0 0 220 150" className="hidden h-32 w-48 shrink-0 sm:block" aria-hidden="true">
      {[0, 1, 2].map((i) => <circle key={i} className="mk-ring" style={{ "--i": i }} cx="70" cy="75" r="62" fill="none" stroke="#c4b5fd" strokeWidth="2" />)}
      <g className="mk-bob">
        <path d="M44 62h22l38-22v70L66 88H44z" fill="#ede9fe" />
        <rect x="40" y="62" width="10" height="26" rx="3" fill="#c4b5fd" />
        <path d="M66 88l6 26h12l-8-26" fill="#c4b5fd" />
        <path d="M112 56c10 6 10 32 0 38" fill="none" stroke="#ede9fe" strokeWidth="5" strokeLinecap="round" />
        <path d="M124 46c18 12 18 46 0 58" fill="none" stroke="#c4b5fd" strokeWidth="5" strokeLinecap="round" />
      </g>
      {[[170, 40, 0], [185, 105, 1], [150, 118, 2]].map(([x, y, i]) => (
        <g key={i} className="mk-bob" style={{ "--i": i }}><circle cx={x} cy={y} r="11" fill="#fff" opacity=".9" /><circle cx={x} cy={y} r="4" fill="#7c3aed" /></g>
      ))}
    </svg>
  );
}

const NODES = [
  ["Audience", "users", "#7c3aed", "Marketing"],
  ["Message", "chat", "#7c3aed", "Marketing"],
  ["Reply", "mail", "#a855f7", "Marketing"],
  ["Lead", "phone", "#2f5bb5", "Sales"],
  ["Sale", "trophy", "#059669", "Sales"],
];

// How a campaign travels: Marketing builds the audience and sends, a reply becomes a Sales lead, Sales closes the sale.
export function FlowGraphic() {
  const xs = NODES.map((_, i) => 70 + i * 155);
  return (
    <svg viewBox="0 0 760 170" className="h-auto w-full" role="img" aria-label="Audience, message and reply belong to Marketing; the lead and the sale belong to Sales">
      <rect x="20" y="8" width="460" height="24" rx="12" fill="#ede9fe" /><text x="250" y="25" textAnchor="middle" fontSize="12" fontWeight="700" fill="#5b21b6">MARKETING</text>
      <rect x="500" y="8" width="240" height="24" rx="12" fill="#dbeafe" /><text x="620" y="25" textAnchor="middle" fontSize="12" fontWeight="700" fill="#1e3a78">SALES</text>
      {xs.slice(0, -1).map((x, i) => <line key={i} className="mk-line" x1={x + 30} y1="84" x2={xs[i + 1] - 30} y2="84" stroke={i < 2 ? "#a78bfa" : "#60a5fa"} strokeWidth="3" strokeLinecap="round" />)}
      <circle className="mk-dot" style={{ "--w": `${xs[4] - xs[0]}px` }} cx={xs[0]} cy="84" r="7" fill="#f59e0b" />
      {NODES.map(([label, icon, color], i) => (
        <g key={label} className="mk-node" style={{ "--i": i }}>
          <circle cx={xs[i]} cy="84" r="28" fill={color} />
          <g transform={`translate(${xs[i]} 84)`}><path d={ICON_PATHS[icon]} transform="translate(-12 -12)" fill="none" stroke="#fff" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" /></g>
          <text x={xs[i]} y="136" textAnchor="middle" fontSize="14" fontWeight="700" fill="currentColor">{label}</text>
        </g>
      ))}
      <text x="305" y="160" textAnchor="middle" fontSize="11" fill="#64748b">people who agreed to promotions</text>
      <text x="620" y="160" textAnchor="middle" fontSize="11" fill="#64748b">an interested reply becomes a Sales lead</text>
    </svg>
  );
}
