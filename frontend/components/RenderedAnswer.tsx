"use client";

export default function RenderedAnswer({
  text,
  onCiteClick,
}: {
  text: string;
  onCiteClick: (n: number) => void;
}) {
  const parts = text.split(/(\[\d+\])/g);

  return (
    <div className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const num = parseInt(match[1]);
          return (
            <button
              key={i}
              onClick={() => onCiteClick(num)}
              className="inline-flex items-center justify-center text-[10px] font-bold rounded-full mx-0.5 transition-all"
              style={{
                width: "18px",
                height: "18px",
                background: "var(--accent-dim)",
                color: "var(--accent)",
                border: "1px solid rgba(99,162,255,0.3)",
                verticalAlign: "super",
                cursor: "pointer",
              }}
              title={`View source ${num}`}
            >
              {num}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
}
