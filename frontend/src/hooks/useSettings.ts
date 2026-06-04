// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: June 4th, 2026
// Description: Re-exports the shared settings hook from SettingsContext so all call sites share one state instance.

export { useSettingsContext as useSettings } from "../context/SettingsContext";
