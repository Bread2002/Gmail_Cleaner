// Copyright (c) 2026, Rye Stahle-Smith; All rights reserved.
// Gmail Cleaner
// Last Updated: May 26th, 2026
// Description: Main entry point for the Gmail Cleaner frontend application.
//              Initializes the React application and renders the main App component into the DOM.
//              It also imports global styles for the application.

// Import necessary modules and components
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

// Create the root element and render the App component wrapped in StrictMode for highlighting potential issues in the application.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
