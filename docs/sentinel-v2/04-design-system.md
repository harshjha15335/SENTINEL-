> Historical rejected visual direction. Superseded by [09-money-trail-reset.md](09-money-trail-reset.md).

# Forensic Editorial — prototype design system

Approval status: PENDING. Source: `apps/web/src/preview/preview.css`; all selectors are below `.v2-preview`. Existing global styling and components are unchanged. Fontface imports are lazy preview assets; font-family assignments apply only inside that root. Existing Tailwind base styles are overridden within the preview, never globally rewritten.

| Role | Token |
|---|---|
| Canvas | #101418 |
| Deep / raised | #171D21 / #20282D |
| Border | #333D42 |
| Foreground / muted | #F5F2EA / #9BA6AC |
| Brand / hover | #C6FF4D / #D9FF82 |
| Critical | #FF625C |
| Warning / information | #F4B860 / #82A5FF |

Space Grotesk 400/500 for display, Inter 400/500 for reading/UI, JetBrains Mono 400 for identifiers and technical annotations. Self-hosted latin Fontsource assets, no remote font requests. Fallbacks sans-serif/monospace. Record currency formatting reuses existing `formatMoney`; times are explicitly labeled UTC. No scoring logic is duplicated.

The marketing composition is asymmetrical: editorial headline left, original mechanical device right. Fine labels support the device rather than decorate it with arbitrary status claims. The app uses a compact navigation rail, large payment identity, facts column and contrasting risk panel. Mobile converts to a top navigation and stacked dossier; controls stay available.

Spacing uses 4/8/12/16/20/24/32/48px families with fluid page padding. Borders define structure; corner radii are 0–2px for controls. Depth is reserved for machine/readout layers. Focus uses a lime outline with offset. Buttons have hover and press states; selected examples and dossier views use `aria-pressed`; story chapters expose `aria-current=step`. Native buttons/links remain keyboard accessible. Form controls use labels; errors use `role=alert` and loading uses `role=status`.

Shared prototype components: Workspace (shell and navigation), Dossier (typed transaction presentation), QueryError (retry), Machine (original SVG), EvidenceStory (scene/chapter/skip controller). These are a foundation for review, not an attempt to manufacture a complete primitive library before real screens need one. Existing reliable hooks and accessible primitives may be retained during Phase 2.

Do not interpret the simulated 87/100 example as a production band threshold. Its factors/score are authored illustrative data; actual dossier reads display the assessment exactly as supplied by the existing API and include model limitations and policy mode. The demonstration fixture version is `sentinel-public-v1`.
