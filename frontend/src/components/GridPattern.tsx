import { useId } from "react";

/**
 * Fon uchun to'r (grid) naqshi — SVG `pattern` bilan chiziladi, ya'ni ekran
 * qanchalik katta bo'lsa ham bitta element yetadi.
 *
 * Asl namunadan farqi: Tailwind va `cn()` yordamchisi olib tashlandi (loyihada
 * ular yo'q) — rang va shaffoflik CSS modulidan `className` orqali beriladi.
 */
interface GridPatternProps {
  /** Bitta katak o'lchami (piksel). */
  width?: number;
  height?: number;
  x?: number;
  y?: number;
  /** Chiziqni uzuq qilish uchun, masalan "4 2". */
  strokeDasharray?: string;
  className?: string;
}

export default function GridPattern({
  width = 44,
  height = 44,
  x = -1,
  y = -1,
  strokeDasharray = "0",
  className,
}: GridPatternProps) {
  const id = useId();
  return (
    <svg aria-hidden="true" className={className}>
      <defs>
        <pattern
          id={id}
          width={width}
          height={height}
          x={x}
          y={y}
          patternUnits="userSpaceOnUse"
        >
          <path
            d={`M.5 ${height}V.5H${width}`}
            fill="none"
            strokeDasharray={strokeDasharray}
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" strokeWidth={0} fill={`url(#${id})`} />
    </svg>
  );
}
