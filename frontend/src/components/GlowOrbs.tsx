import "./GlowOrbs.css";

// Yumshoq, sekin suzuvchi yorug'lik dog'lari — chat sahifasi foni uchun.
// Sof CSS animatsiya (canvas/WebGL yo'q): protsessorga yuk tushmaydi va
// prefers-reduced-motion hurmat qilinadi.

interface GlowOrbsProps {
  /** Uchta dog' rangi (rgba/hex). Tartib: chap-yuqori, o'ng, past-o'rta. */
  colors: [string, string, string];
}

export default function GlowOrbs({ colors }: GlowOrbsProps) {
  return (
    <div
      className="glow-orbs"
      style={
        {
          "--orb-a": colors[0],
          "--orb-b": colors[1],
          "--orb-c": colors[2],
        } as React.CSSProperties
      }
    >
      <div className="glow-orb glow-orb-1" />
      <div className="glow-orb glow-orb-2" />
      <div className="glow-orb glow-orb-3" />
    </div>
  );
}
