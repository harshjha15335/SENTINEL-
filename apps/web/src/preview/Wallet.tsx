/** Original layered vector artwork. No external imagery or realtime 3D. */
export function Wallet() {
  return (
    <svg
      className="v2-wallet"
      width="600"
      height="430"
      viewBox="0 0 600 430"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="wallet-body" x1="0" y1="0" x2=".8" y2="1">
          <stop stopColor="#9667FA" />
          <stop offset=".45" stopColor="#7547EB" />
          <stop offset="1" stopColor="#472395" />
        </linearGradient>
        <linearGradient id="wallet-edge">
          <stop stopColor="#3A1F69" />
          <stop offset=".5" stopColor="#6240A4" />
          <stop offset="1" stopColor="#301E4C" />
        </linearGradient>
        <linearGradient id="wallet-flap" x2=".2" y2="1">
          <stop stopColor="#B393F9" />
          <stop offset=".35" stopColor="#8554E9" />
          <stop offset="1" stopColor="#6439C4" />
        </linearGradient>
        <linearGradient id="wallet-lining" x2="0" y2="1">
          <stop stopColor="#37234E" />
          <stop offset="1" stopColor="#5E3A93" />
        </linearGradient>
        <radialGradient id="wallet-shadow">
          <stop stopColor="#39234E" stopOpacity=".22" />
          <stop offset="1" stopColor="#39234E" stopOpacity="0" />
        </radialGradient>
        <pattern
          id="wallet-grain"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="m1 1 1 .5m3 3 1 .5"
            stroke="#F7F4EE"
            strokeOpacity=".1"
            strokeWidth=".7"
          />
        </pattern>
      </defs>
      <ellipse cx="310" cy="370" rx="278" ry="45" fill="url(#wallet-shadow)" />
      <path
        d="M65 105 Q65 76 98 76H490Q522 76 526 108L548 300Q548 337 511 344L115 365Q78 368 74 329Z"
        fill="url(#wallet-edge)"
      />
      <path
        d="M63 99Q64 71 97 71H484Q514 71 518 102L533 293Q535 326 501 332L105 350Q73 352 70 320Z"
        fill="url(#wallet-lining)"
      />
      <path d="M80 106H498L512 285 94 304Z" fill="#2D1D44" />
      <g data-wallet-fold style={{ transformOrigin: "290px 148px" }}>
        <path
          d="M70 105Q65 72 99 68L477 53Q510 53 516 86L526 189Q527 208 507 212L102 230Q78 232 77 209Z"
          fill="url(#wallet-flap)"
        />
        <path
          d="M90 104Q89 88 105 86L475 72Q492 72 495 90L506 187Q509 195 494 196L108 213Q96 214 95 201Z"
          fill="none"
          stroke="#D7BCFF"
          strokeOpacity=".65"
          strokeDasharray="3 5"
        />
        <path
          d="M74 113 514 96"
          stroke="#D6B4FF"
          strokeOpacity=".35"
          strokeWidth="2"
        />
      </g>
      <path
        d="M72 179Q71 157 95 157L509 141 532 292Q536 325 501 332L105 350Q76 351 73 320Z"
        fill="url(#wallet-body)"
      />
      <path
        d="M72 179Q71 157 95 157L509 141 532 292Q536 325 501 332L105 350Q76 351 73 320Z"
        fill="url(#wallet-grain)"
      />
      <path
        d="M92 186Q90 177 105 176L492 161 512 289Q515 307 495 312L111 330Q93 331 93 313Z"
        fill="none"
        stroke="#D1AEFF"
        strokeOpacity=".6"
        strokeDasharray="3 5"
      />
      <path
        d="m75 178 434-18"
        stroke="#C3A0FF"
        strokeWidth="2"
        strokeOpacity=".7"
      />
      <path
        d="M448 217 543 213Q558 213 560 229L562 260Q563 275 548 277L454 281Q438 282 437 266L434 236Q433 219 448 217Z"
        fill="#47268B"
      />
      <path
        d="M447 218 540 216Q554 216 555 231L557 257Q558 271 543 272L452 277Q440 278 439 264L437 237Q436 221 447 218Z"
        fill="url(#wallet-flap)"
      />
      <circle cx="466" cy="247" r="10" fill="#DDD2EA" />
      <circle cx="466" cy="247" r="6" fill="#A395B4" />
      <path d="m462 244 7-1" stroke="white" strokeOpacity=".8" />
      <text
        x="123"
        y="287"
        fill="#E4D3FF"
        fontSize="18"
        letterSpacing="5"
        fontFamily="Manrope,sans-serif"
      >
        SENTINEL
      </text>
      <path d="m122 299 98-4" stroke="#C5A6F4" strokeOpacity=".4" />
    </svg>
  );
}
export function Banknote({ variant = 0 }: { variant?: number }) {
  return (
    <g>
      <rect
        x="-150"
        y="-73"
        width="300"
        height="146"
        rx="9"
        fill={variant === 0 ? "#D9D2E6" : "#E9E0FF"}
        stroke="#A89ABA"
        strokeWidth="2"
      />
      <rect
        x="-138"
        y="-61"
        width="276"
        height="122"
        rx="5"
        fill="none"
        stroke="#A89ABA"
      />
      <path
        d="M-125-48Q-80 0-125 48M125-48Q80 0 125 48"
        fill="none"
        stroke="#B5A5CA"
        strokeWidth="12"
      />
      <ellipse rx="50" ry="53" fill="none" stroke="#B5A5CA" strokeWidth="1.5" />
      <ellipse rx="38" ry="43" fill="none" stroke="#B5A5CA" />
      <text
        textAnchor="middle"
        y="14"
        fontFamily="Manrope,sans-serif"
        fontSize="42"
        fill="#66517F"
      >
        S
      </text>
      <text x="-119" y="-27" fontSize="11" fill="#66517F">
        MONEY
      </text>
      <text x="80" y="45" fontSize="11" fill="#66517F">
        MOVES
      </text>
    </g>
  );
}
export function Receipt() {
  return (
    <g>
      <path
        d="M-131-166H131V146L120 155 109 146 98 155 87 146 76 155 65 146 54 155 43 146 32 155 21 146 10 155-1 146-12 155-23 146-34 155-45 146-56 155-67 146-78 155-89 146-100 155-111 146-122 155-131 146Z"
        fill="#FFFFFF"
        stroke="#DED7E5"
        strokeWidth="2"
      />
      <rect
        x="-131"
        y="-166"
        width="262"
        height="9"
        fill="#7547EB"
        data-receipt-accent
      />
      <text
        x="-106"
        y="-121"
        fontFamily="Manrope,sans-serif"
        fontWeight="700"
        fontSize="17"
        fill="#201A2B"
      >
        SENTINEL
      </text>
      <text x="-106" y="-97" fontSize="10" fill="#686273">
        PAYMENT / DEMO-0148
      </text>
      <text
        x="-106"
        y="-44"
        fontFamily="Manrope,sans-serif"
        fontWeight="600"
        fontSize="35"
        fill="#201A2B"
      >
        $1,849.00
      </text>
      <text x="-106" y="-20" fontSize="11" fill="#686273">
        USD · SIMULATED
      </text>
      <path
        d="M-106 0H106M-106 73H106"
        stroke="#DED7E5"
        strokeDasharray="3 4"
      />
      <text x="-106" y="27" fontSize="12" fill="#686273">
        1 NOV 2026
      </text>
      <text x="106" y="27" fontSize="12" textAnchor="end" fill="#201A2B">
        10:43 UTC
      </text>
      <text x="-106" y="53" fontSize="12" fill="#686273">
        Payment status
      </text>
      <text x="106" y="53" fontSize="12" textAnchor="end" fill="#201A2B">
        Captured
      </text>
      <text x="-106" y="105" fontSize="11" fill="#7547EB">
        FOLLOW THE MONEY ↗
      </text>
      <path
        d="M-106 122H-61M-54 122H-33M-26 122H18M25 122H47M54 122H106"
        stroke="#D9D2E6"
        strokeWidth="9"
      />
    </g>
  );
}
