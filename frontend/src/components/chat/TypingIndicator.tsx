// Bot javobini kutish paytidagi jonli "yozyapti" animatsiyasi (uch nuqta sakraydi).
// Stillar global index.css'da (.tu-typing) — CSS-module keyframe muammosidan xoli.
interface TypingIndicatorProps {
  color?: string;
}

export default function TypingIndicator({ color = "#2563EB" }: TypingIndicatorProps) {
  return (
    <span className="tu-typing" style={{ color }} aria-label="..." role="status">
      <span />
      <span />
      <span />
    </span>
  );
}
