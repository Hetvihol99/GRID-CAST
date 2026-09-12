"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import HeroForecast from "@/components/HeroForecast";
import KpiRow from "@/components/KpiRow";
import BatteryStoragePanel from "@/components/BatteryStoragePanel";
import AlertsPanel from "@/components/AlertsPanel";
import RecommendationsPanel from "@/components/RecommendationsPanel";
import SitesTable from "@/components/SitesTable";
import Footer from "@/components/Footer";
import AiCopilotModal from "@/components/AiCopilotModal";
import AuthModal from "@/components/AuthModal";
import PlantRegistrationModal from "@/components/PlantRegistrationModal";
import PlantDetailInspector from "@/components/PlantDetailInspector";
import ExportReportModal from "@/components/ExportReportModal";
import LiveGridTicker from "@/components/LiveGridTicker";
import FinancialTraderPanel from "@/components/FinancialTraderPanel";
import { DashboardSummary, PlantStatusSummary, PlantForecastResult } from "@/lib/types";
import {
  getDashboardSummary,
  getStoredCustomPlants,
  deleteCustomPlant,
  mergeCustomPlantsIntoSummary,
} from "@/lib/api";
import { generateDefaultDashboard } from "@/lib/defaultData";
import { OperatorUser, getStoredOperator, saveOperatorSession, clearOperatorSession } from "@/lib/auth";

interface DashboardClientProps {
  initialSummary: DashboardSummary;
  initialIsLive: boolean;
}

export default function DashboardClient({ initialSummary, initialIsLive }: DashboardClientProps) {
  const [summary, setSummary] = useState<DashboardSummary>(initialSummary);
  const [isLive, setIsLive] = useState<boolean>(initialIsLive);

  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [inspectedPlant, setInspectedPlant] = useState<PlantStatusSummary | null>(null);

  const [currentUser, setCurrentUser] = useState<OperatorUser | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    setCurrentUser(getStoredOperator());
    const storedCustomPlants = getStoredCustomPlants();
    if (storedCustomPlants.length > 0) {
      setSummary((prev) => mergeCustomPlantsIntoSummary(prev, storedCustomPlants));
    }
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleRefresh = async () => {
    const result = await getDashboardSummary();
    const storedCustomPlants = getStoredCustomPlants();
    const merged = mergeCustomPlantsIntoSummary(result.data, storedCustomPlants);
    setSummary(merged);
    setIsLive(result.isLive);
    showToast("Dashboard synchronized with latest telemetry & predictions.");
  };

  const handleLogin = (user: OperatorUser) => {
    setCurrentUser(user);
    saveOperatorSession(user);
    showToast(`Welcome, ${user.name} (${user.roleTitle})`);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    clearOperatorSession();
    showToast("Operator signed out.");
  };

  const handleDeletePlant = (plantId: number) => {
    deleteCustomPlant(plantId);
    const remainingCustom = getStoredCustomPlants();
    const defaultData = generateDefaultDashboard();
    setSummary(mergeCustomPlantsIntoSummary(defaultData, remainingCustom));
    showToast("Plant removed from active dispatch fleet.");
  };

  const handlePlantRegistered = (newPlant: PlantStatusSummary, forecastResult: PlantForecastResult) => {
    setSummary((prev) => {
      const customPlants = getStoredCustomPlants();
      const allCustom = [newPlant, ...customPlants.filter((p) => p.plant_id !== newPlant.plant_id)];
      return mergeCustomPlantsIntoSummary(prev, allCustom);
    });

    showToast(`Site "${newPlant.plant_name}" (${newPlant.capacity_mw} MW) saved in database & connected!`);
    setInspectedPlant(newPlant);
  };

  return (
    <main className="max-w-7xl mx-auto min-h-screen flex flex-col relative bg-white text-dark">
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-white border-2 border-dark text-dark px-5 py-4 rounded-2xl shadow-positivus flex items-center gap-3 backdrop-blur-md animate-in fade-in slide-in-from-bottom-3 duration-200">
          <span className="w-3 h-3 rounded-full bg-lime border border-dark" />
          <span className="text-xs font-bold">{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="text-dark hover:opacity-70 text-xs ml-2 font-bold">✕</button>
        </div>
      )}

      <Header
        isLive={isLive}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onOpenRegisterPlant={() => setIsRegisterModalOpen(true)}
        onOpenAiBriefing={() => setIsAiModalOpen(true)}
        onOpenExportReport={() => setIsExportModalOpen(true)}
        onRefresh={handleRefresh}
      />

      <LiveGridTicker />
      <HeroForecast summary={summary} />
      <KpiRow summary={summary} />
      <BatteryStoragePanel battery={summary.battery} />
      <AlertsPanel alerts={summary.active_alerts} />
      <RecommendationsPanel recommendations={summary.recommendations} />
      <FinancialTraderPanel summary={summary} />
      <SitesTable
        plants={summary.plants}
        onSelectPlant={(plant) => setInspectedPlant(plant)}
        onOpenRegisterPlant={() => setIsRegisterModalOpen(true)}
        onDeletePlant={handleDeletePlant}
      />
      <Footer />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        currentUser={currentUser}
        onLogin={handleLogin}
        onLogout={handleLogout}
      />

      <PlantRegistrationModal
        isOpen={isRegisterModalOpen}
        onClose={() => setIsRegisterModalOpen(false)}
        onPlantRegistered={handlePlantRegistered}
      />

      <PlantDetailInspector
        plant={inspectedPlant}
        onClose={() => setInspectedPlant(null)}
      />

      <AiCopilotModal
        isOpen={isAiModalOpen}
        onClose={() => setIsAiModalOpen(false)}
        summary={summary}
      />

      <ExportReportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        summary={summary}
      />
    </main>
  );
}
