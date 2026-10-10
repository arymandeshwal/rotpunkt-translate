import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { Toaster } from "./components/ui/sonner";
import { GlossaryPage } from "./pages/GlossaryPage";
import { ProjectSetupPage } from "./pages/ProjectSetupPage";
import { ProjectEditorPage } from "./pages/ProjectEditorPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { LoginPage } from "./pages/LoginPage";
import { AuthProvider } from "./contexts/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute allowedRoles={["admin", "reviewer", "translator"]} />}>
        <Route element={<Layout />}>
          <Route index element={<ProjectsPage />} />
          <Route path="projects/:id/setup" element={<ProjectSetupPage />} />
          <Route path="projects/:id" element={<ProjectEditorPage />} />
          <Route path="glossary" element={<GlossaryPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

export function App() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </AuthProvider>
    </QueryClientProvider>
  );
}
