export function EvidenceTape() {
  return (
    <g data-evidence-strip>
      <defs>
        <linearGradient id="evidence-edge" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#c7cabc" />
          <stop offset=".45" stopColor="#627369" />
          <stop offset="1" stopColor="#252e2c" />
        </linearGradient>
        <mask
          id="evidence-reveal"
          maskUnits="userSpaceOnUse"
          x="0"
          y="0"
          width="1440"
          height="900"
        >
          <path
            data-strip-path
            data-strip-mask
            fill="none"
            stroke="white"
            strokeWidth="40"
          />
        </mask>
      </defs>
      <path
        data-strip-path
        className="v2-strip-shadow"
        fill="none"
        stroke="#000"
        strokeWidth="44"
        opacity=".35"
      />
      <path
        data-strip-path
        data-strip-length
        fill="none"
        stroke="url(#evidence-edge)"
        strokeWidth="32"
      />
      <path data-strip-path fill="none" stroke="#172220" strokeWidth="25" />
      <path
        data-strip-path
        data-strip-marks
        mask="url(#evidence-reveal)"
        fill="none"
        stroke="#c6ff4d"
        strokeWidth="3"
        strokeDasharray="2 17"
      />
      <path
        data-strip-path
        data-strip-spine
        fill="none"
        stroke="#afc59b"
        strokeWidth="1"
        opacity=".35"
      />
      <g data-path-node data-at=".24">
        <FilmFrame
          index="01"
          label="TRANSACTION RECEIVED"
          title="$1,849.00"
          detail="USD / SIMULATED PAYMENT"
        />
      </g>
      <g data-path-node data-at=".52">
        <FilmFrame
          index="02"
          label="PAST-ONLY SIGNAL"
          title="7 payments"
          detail="FROM PAYER / PREVIOUS 24H"
        />
      </g>
      <g data-path-node data-at=".76">
        <FilmFrame
          index="03"
          label="AMOUNT DEVIATION"
          title="8.4× median"
          detail="ILLUSTRATIVE SIGNAL VALUE"
        />
      </g>
      <g data-risk-visual transform="translate(1120 610)">
        <circle r="116" fill="#101918" stroke="#4a5b4b" />
        <circle r="100" fill="none" stroke="#333d42" strokeWidth="7" />
        <circle
          data-risk-ring
          r="100"
          fill="none"
          stroke="#ff625c"
          strokeWidth="7"
          strokeDasharray="628.319"
          strokeDashoffset="628.319"
          transform="rotate(-90)"
        />
        <text
          y="-34"
          textAnchor="middle"
          fill="#9ba6ac"
          fontSize="11"
          letterSpacing="2"
        >
          SIGNALS → INTELLIGENCE
        </text>
        <text
          y="26"
          textAnchor="middle"
          fill="#f5f2ea"
          fontSize="67"
          fontFamily="Space Grotesk, sans-serif"
        >
          87
          <tspan fontSize="17" fill="#9ba6ac">
            {" "}
            /100
          </tspan>
        </text>
        <text
          y="55"
          textAnchor="middle"
          fill="#ff625c"
          fontSize="13"
          letterSpacing="2"
        >
          HIGH RISK
        </text>
        <text y="78" textAnchor="middle" fill="#9ba6ac" fontSize="10">
          SIMULATED / NOT LIVE INFERENCE
        </text>
      </g>
    </g>
  );
}
function FilmFrame({
  index,
  label,
  title,
  detail,
}: {
  index: string;
  label: string;
  title: string;
  detail: string;
}) {
  return (
    <g className="v2-film-frame">
      <rect
        x="-120"
        y="-62"
        width="240"
        height="124"
        rx="3"
        fill="#182321"
        stroke="#a5b19d"
        strokeWidth="1.5"
      />
      <path
        d="M-115 -53H115M-115 53H115"
        stroke="#b8c4ae"
        strokeWidth="5"
        strokeDasharray="5 12"
      />
      <text x="-101" y="-28" fill="#c6ff4d" fontSize="10" letterSpacing="1">
        {index} / {label}
      </text>
      <text
        x="-101"
        y="8"
        fill="#f5f2ea"
        fontSize="27"
        fontFamily="Space Grotesk, sans-serif"
      >
        {title}
      </text>
      <text x="-101" y="32" fill="#b5c1bb" fontSize="10" letterSpacing=".5">
        {detail}
      </text>
    </g>
  );
}
