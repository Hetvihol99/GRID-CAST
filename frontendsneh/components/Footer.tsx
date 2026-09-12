import { defaultWeatherProviders } from "@/lib/defaultData";

export default function Footer() {
  return (
    <footer className="mt-12 px-6 md:px-12 py-12 bg-dark text-white rounded-t-[36px] md:rounded-t-[48px] border-t-2 border-dark text-xs">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-10 border-b border-dark-secondary">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-lime text-dark font-bold border border-dark">
            <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="11" stroke="#191A23" strokeWidth="2.5" />
              <path d="M14 6 L14 14 L19.5 17" stroke="#191A23" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <span className="font-display font-bold text-xl text-white tracking-tight">Grid Cast</span>
        </div>

        <div className="flex flex-wrap gap-6 text-sm font-medium text-gray-300">
          <a href="#forecast" className="hover:text-lime transition-colors">Forecast</a>
          <a href="#battery" className="hover:text-lime transition-colors">Battery Storage</a>
          <a href="#alerts" className="hover:text-lime transition-colors">Alerts</a>
          <a href="#actions" className="hover:text-lime transition-colors">Recommendations</a>
          <a href="#trading" className="hover:text-lime transition-colors">Trading Desk</a>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 py-8 border-b border-dark-secondary">
        <div>
          <span className="bg-lime text-dark font-bold text-xs uppercase px-2.5 py-0.5 rounded-md inline-block mb-3">
            Contact &amp; Operations
          </span>
          <p className="text-gray-300 leading-relaxed text-xs">
            24/7 National Grid Integration &amp; Dispatch Desk<br />
            Email: dispatch@gridcast.ai<br />
            Phone: +91 (011) 2436-1200
          </p>
        </div>

        <div>
          <span className="bg-lime text-dark font-bold text-xs uppercase px-2.5 py-0.5 rounded-md inline-block mb-3">
            Atmospheric Telemetry
          </span>
          <div className="space-y-2">
            {defaultWeatherProviders.map((p) => (
              <div key={p.name} className="flex items-center justify-between text-xs">
                <span className="text-gray-300 font-medium">{p.name}</span>
                <span className="text-[10px] font-bold text-lime bg-dark-secondary px-2 py-0.5 rounded border border-gray-700">
                  {p.role.split("(")[0]}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="p-4 rounded-2xl bg-dark-secondary border border-gray-700 text-xs text-gray-300 leading-relaxed">
            💡 <strong>Grid Cast ML Core:</strong> Multi-step XGBoost ensemble models trained on solar irradiance (GHI), ambient temperature, and hub-height wind speed datasets.
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8 text-xs text-gray-400 font-medium">
        <p>© 2026 Grid Cast. All rights reserved.</p>
        <div className="flex items-center gap-4">
          <span className="text-lime font-bold">XGBoost ML v1.2</span>
          <span>•</span>
          <span>FastAPI REST</span>
          <span>•</span>
          <span>Next.js 14</span>
        </div>
      </div>
    </footer>
  );
}
