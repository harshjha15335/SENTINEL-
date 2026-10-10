import { AllCommunityModule, ModuleRegistry, colorSchemeDark, themeQuartz } from "ag-grid-community";

// Community modules only: SENTINEL must not depend on AG Grid Enterprise features.
ModuleRegistry.registerModules([AllCommunityModule]);

export const sentinelGridTheme = themeQuartz.withPart(colorSchemeDark).withParams({
  backgroundColor: "#0f161e",
  foregroundColor: "#e6ebf1",
  chromeBackgroundColor: "#0f161e",
  headerTextColor: "#a7b2bf",
  headerFontWeight: 500,
  headerFontSize: 12,
  borderColor: "#1f2a37",
  rowHoverColor: "#141d27",
  accentColor: "#5b9bf0",
  fontFamily: "'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif",
  fontSize: 13,
  browserColorScheme: "dark",
  columnBorder: false,
  wrapperBorderRadius: 10,
  spacing: 6,
});
