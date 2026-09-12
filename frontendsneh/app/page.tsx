import DashboardClient from "@/components/DashboardClient";
import { getDashboardSummary } from "@/lib/api";

export const revalidate = 0; // Disable static cache for live data

export default async function Home() {
  const { data: initialSummary, isLive: initialIsLive } = await getDashboardSummary();

  return <DashboardClient initialSummary={initialSummary} initialIsLive={initialIsLive} />;
}
