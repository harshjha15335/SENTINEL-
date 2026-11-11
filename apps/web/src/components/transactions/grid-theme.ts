import {
  CellStyleModule,
  ClientSideRowModelModule,
  ModuleRegistry,
  TooltipModule,
  ValidationModule,
  themeQuartz,
} from "ag-grid-community";

// Community modules only, and only the ones the transactions grid uses (client-side rows with
// sorting and resizing, cellClass, header tooltips). Registering AllCommunityModule pulled every
// filter, editor and export into the bundle. ValidationModule names a missing module in the
// console during development and is dropped from production builds.
ModuleRegistry.registerModules([
  ClientSideRowModelModule,
  CellStyleModule,
  TooltipModule,
  ...(import.meta.env.DEV ? [ValidationModule] : []),
]);

export const sentinelGridTheme = themeQuartz.withParams({
  backgroundColor: "#F7F4EE",
  foregroundColor: "#201A2B",
  chromeBackgroundColor: "#F7F4EE",
  headerTextColor: "#686273",
  headerFontWeight: 500,
  headerFontSize: 12,
  borderColor: "#DED7E5",
  rowHoverColor: "#EFEBF5",
  accentColor: "#7547EB",
  fontFamily: "'DM Sans', ui-sans-serif, system-ui, sans-serif",
  fontSize: 13,
  browserColorScheme: "light",
  columnBorder: false,
  wrapperBorderRadius: 0,
  spacing: 9,
});
