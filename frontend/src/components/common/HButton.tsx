import { useState, ButtonHTMLAttributes, CSSProperties } from "react";

// Hover stilini qo'llab-quvvatlovchi tugma (inline-style uchun)
type HButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  baseStyle: CSSProperties;
  hoverStyle?: CSSProperties;
};

export default function HButton({ baseStyle, hoverStyle, ...props }: HButtonProps) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      {...props}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ ...baseStyle, ...(hovered && hoverStyle ? hoverStyle : {}) }}
    />
  );
}
