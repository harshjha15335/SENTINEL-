/** Original vector construction. All moving parts share a tape-distance driver. */
export function Machine() {
  return (
    <svg
      className="v2-machine"
      viewBox="0 0 820 560"
      role="img"
      aria-labelledby="machine-title machine-desc"
    >
      <title id="machine-title">SENTINEL Evidence Reel</title>
      <desc id="machine-desc">
        Two mechanical reels guide evidence tape through a scanning head. Scroll
        advances the tape and turns both reels. A readable story follows the
        illustration.
      </desc>
      <defs>
        <linearGradient id="housing" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#41494c" />
          <stop offset=".3" stopColor="#252d31" />
          <stop offset="1" stopColor="#161c20" />
        </linearGradient>
        <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#d4d4c9" />
          <stop offset=".35" stopColor="#727a7a" />
          <stop offset=".55" stopColor="#c1c4bb" />
          <stop offset="1" stopColor="#4d5558" />
        </linearGradient>
        <radialGradient id="spool">
          <stop stopColor="#383f41" />
          <stop offset=".8" stopColor="#1c2326" />
          <stop offset="1" stopColor="#464e50" />
        </radialGradient>
        <linearGradient id="edge">
          <stop stopColor="#7f8988" />
          <stop offset="1" stopColor="#272e31" />
        </linearGradient>
        <pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse">
          <path d="M0 0V5" stroke="#020607" strokeWidth="2" />
        </pattern>
        <pattern
          id="tape-marks"
          width="36"
          height="14"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M0 2V12M5 3V11M10 3V11M16 2V12M23 3V11"
            stroke="#c6ff4d"
            strokeWidth="2"
          />
        </pattern>
      </defs>
      <ellipse cx="421" cy="518" rx="309" ry="19" fill="#000" opacity=".45" />
      <g transform="translate(27 20)">
        <path
          d="M70 58L677 36 736 82 736 445 120 483 62 445Z"
          fill="#0d1215"
          stroke="#384247"
        />
        <path d="M70 58L677 36 728 70 116 97Z" fill="url(#edge)" />
        <path
          d="M116 97L728 70 728 438 116 477Z"
          fill="url(#housing)"
          stroke="#687273"
          strokeWidth="1.5"
        />
        <path d="M62 90L110 114V470L62 445Z" fill="#12191d" />
        <path
          d="M132 119L708 95V413L132 447Z"
          fill="#11191d"
          stroke="#444e51"
        />
        <path d="M147 135L694 112V293L147 321Z" fill="#141b1f" />
        <text
          x="145"
          y="86"
          fill="#101418"
          fontSize="11"
          letterSpacing="4"
          fontFamily="monospace"
        >
          S E N T I N E L
        </text>
        <text
          x="550"
          y="69"
          fill="#101418"
          fontSize="8"
          letterSpacing="2"
          fontFamily="monospace"
        >
          EVIDENCE TRANSPORT / 01
        </text>
        <g transform="translate(266 222)">
          <Reel side="left" />
        </g>
        <g transform="translate(564 207)">
          <Reel side="right" />
        </g>
        <path
          d="M266 312L266 347 340 369 459 363 564 331 564 297"
          fill="none"
          stroke="#070b0d"
          strokeWidth="19"
        />
        <path
          d="M266 312L266 347 340 369 459 363 564 331 564 297"
          fill="none"
          stroke="#677066"
          strokeWidth="9"
        />
        <path
          data-tape
          d="M266 312L266 347 340 369 459 363 564 331 564 297"
          fill="none"
          stroke="#c6ff4d"
          strokeWidth="3"
          strokeDasharray="2 14"
          opacity=".7"
        />
        {[
          [266, 347],
          [340, 369],
          [459, 363],
          [564, 331],
        ].map(([x, y], i) => (
          <g key={i}>
            <circle
              cx={x}
              cy={y}
              r="11"
              fill="url(#metal)"
              stroke="#0a1115"
              strokeWidth="3"
            />
            <circle cx={x} cy={y} r="3" fill="#0a1115" />
          </g>
        ))}
        <g className="v2-scanner">
          <rect
            x="375"
            y="332"
            width="50"
            height="55"
            rx="3"
            fill="url(#metal)"
          />
          <rect x="382" y="339" width="36" height="40" fill="#0e1718" />
          <path d="M383 361H417" stroke="#c6ff4d" strokeWidth="3" />
          <path
            data-scan
            d="M400 328V391"
            stroke="#c6ff4d"
            strokeWidth="2"
            opacity="0"
          />
        </g>
        <g transform="translate(146 359)">
          <rect width="85" height="57" rx="2" fill="#090f12" stroke="#465052" />
          <text
            x="10"
            y="18"
            fill="#a5b1b4"
            fontSize="7"
            fontFamily="monospace"
          >
            INPUT / SIMULATED
          </text>
          <text
            x="10"
            y="35"
            fill="#f5f2ea"
            fontSize="13"
            fontFamily="monospace"
          >
            $1,849.00
          </text>
          <text
            x="10"
            y="47"
            fill="#9ba6ac"
            fontSize="6"
            fontFamily="monospace"
          >
            USD · DEMO-0148
          </text>
        </g>
        <g transform="translate(480 374)">
          <path d="M0 0L209 -12V40L0 52Z" fill="#081211" stroke="#465052" />
          <text
            x="12"
            y="16"
            fill="#9ba6ac"
            fontSize="7"
            letterSpacing="1"
            fontFamily="monospace"
          >
            SIGNAL PROCESSOR
          </text>
          <text
            data-machine-status
            x="12"
            y="36"
            fill="#c6ff4d"
            fontSize="10"
            fontFamily="monospace"
          >
            AWAITING INPUT
          </text>
          <g data-diagnostic opacity=".15">
            {Array.from({ length: 12 }, (_, i) => (
              <rect
                key={i}
                x={125 + i * 5}
                y={12 + (i % 3) * 4}
                width="2"
                height={22 - (i % 3) * 4}
                fill="#c6ff4d"
              />
            ))}
          </g>
        </g>
        <g fill="#b1b8b4" stroke="#131a1d" strokeWidth="2">
          {[
            [125, 109],
            [718, 82],
            [125, 463],
            [718, 425],
          ].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x} cy={y} r="4" />
              <path d={`M${(x ?? 0) - 2} ${y}h4`} strokeWidth="1" />
            </g>
          ))}
        </g>
        <path d="M144 431L450 412" stroke="#4e585b" />
        <text
          x="155"
          y="444"
          fill="#a3acae"
          fontSize="6"
          letterSpacing="2"
          fontFamily="monospace"
        >
          PAST-ONLY SIGNALS / HUMAN REVIEW / TRACEABLE EVIDENCE
        </text>
        <rect x="139" y="466" width="32" height="19" rx="3" fill="#090e11" />
        <rect x="665" y="433" width="32" height="19" rx="3" fill="#090e11" />
        <path d="M76 120V420" stroke="#3b4448" strokeWidth="12" />
        <path d="M76 120V420" stroke="url(#hatch)" strokeWidth="12" />
      </g>
      <g fill="#9ba6ac" fontSize="8" fontFamily="monospace" letterSpacing="1.5">
        <path d="M230 53V28H132" stroke="#4b575b" fill="none" />
        <text x="60" y="22">
          01 / SUPPLY REEL
        </text>
        <path d="M609 51V24H720" stroke="#4b575b" fill="none" />
        <text x="626" y="17">
          02 / TAKE-UP
        </text>
        <path d="M430 410V500H560" stroke="#4b575b" fill="none" />
        <text x="574" y="504">
          03 / SCANNING HEAD
        </text>
      </g>
    </svg>
  );
}
function Reel({ side }: { side: string }) {
  return (
    <g data-reel={side}>
      <circle r="104" fill="#080d10" stroke="#4c565a" strokeWidth="2" />
      <circle r="98" fill="url(#spool)" stroke="#8a9390" />
      {Array.from({ length: 32 }, (_, i) => (
        <circle
          key={i}
          r={49 + i * 1.3}
          fill="none"
          stroke="#7a7665"
          strokeWidth=".4"
          opacity=".3"
        />
      ))}
      <circle r="84" fill="url(#metal)" opacity=".85" />
      {[0, 120, 240].map((a) => (
        <path
          key={a}
          transform={`rotate(${a})`}
          d="M-16 -27C-39 -48 -52 -57 -46 -66C-21 -84 12 -81 24 -68L18 -29Z"
          fill="#121b1e"
          stroke="#596366"
          strokeWidth="2"
        />
      ))}
      <circle r="31" fill="#151e22" stroke="#cad0c4" strokeWidth="2" />
      <circle r="22" fill="url(#metal)" />
      <circle r="8" fill="#131b1e" stroke="#9aa6a3" />
      <path d="M0 -98V-89" stroke="#c6ff4d" strokeWidth="3" />
      {[0, 120, 240].map((a) => (
        <circle
          key={a}
          transform={`rotate(${a})`}
          cx="0"
          cy="-16"
          r="2"
          fill="#141c20"
        />
      ))}
    </g>
  );
}
