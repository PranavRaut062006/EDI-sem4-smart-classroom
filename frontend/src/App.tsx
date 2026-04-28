import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Dashboard from "./pages/Dashboard";
import StudentRegistration from "./pages/StudentRegistration";
import StartClass from "./pages/StartClass";
import Attendance from "./pages/Attendance";
import Analytics from "./pages/Analytics";
import IoT from "./pages/IoT";
import HistoryPage from "./pages/History";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/students" element={<StudentRegistration />} />
          <Route path="/start-class" element={<StartClass />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/iot" element={<IoT />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
