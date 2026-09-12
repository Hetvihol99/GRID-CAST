import Link from "next/link";

export default function NotFound() {
  return (
    <main className="max-w-4xl mx-auto min-h-screen px-6 py-20 flex flex-col items-center justify-center text-center bg-white text-dark">
      <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark mb-6 shadow-positivus text-4xl">
        ⚡
      </div>
      <h1 className="font-display font-bold text-3xl text-dark mb-2">
        Page Not Found
      </h1>
      <p className="text-sm text-ink-muted max-w-md mb-8">
        The requested renewable grid URL could not be found. Return to the main AI Solution &amp; Dispatch Dashboard below.
      </p>
      <Link
        href="/"
        className="px-6 py-3 rounded-xl bg-lime text-dark font-bold text-sm hover:bg-dark hover:text-white transition-all border-2 border-dark shadow-positivus flex items-center gap-2"
      >
        ← Return to Grid Cast Dashboard
      </Link>
    </main>
  );
}
