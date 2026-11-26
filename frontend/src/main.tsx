import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@/contexts/auth-context";
import { OrganisationProvider } from "@/contexts/organisation-context";

import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <OrganisationProvider>
          <App />
        </OrganisationProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
