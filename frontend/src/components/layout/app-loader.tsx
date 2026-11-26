import { Activity, Sparkles } from "lucide-react";
import { motion } from "motion/react";

export function AppLoader() {
  return (
    <motion.div
      className="fixed inset-0 z-[100] flex min-h-screen items-center justify-center bg-[#f5f7fb]"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      role="status"
      aria-label="Loading ResolveIQ"
    >
      <div className="flex w-full max-w-sm flex-col items-center px-6 text-center">
        <motion.div
          className="relative mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-blue-600 text-white shadow-xl shadow-blue-200"
          animate={{ y: [0, -7, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <Activity size={38} strokeWidth={2.2} />
          <motion.span
            className="absolute -right-2 -top-2 rounded-full bg-white p-1.5 text-blue-600 shadow-md"
            animate={{ rotate: [0, 15, -15, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Sparkles size={17} />
          </motion.span>
        </motion.div>

        <motion.h1
          className="text-3xl font-bold tracking-tight text-slate-900"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          ResolveIQ
        </motion.h1>

        <p className="mt-2 text-sm text-slate-500">
          Support intelligence. Simplified.
        </p>

        <div className="mt-9 h-1.5 w-56 overflow-hidden rounded-full bg-blue-100">
          <motion.div
            className="h-full w-full origin-left rounded-full bg-blue-600"
            animate={{ scaleX: [0, 1, 0] }}
            transition={{
              duration: 1.6,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </div>

        <p className="mt-4 text-xs font-medium tracking-wide text-slate-400">
          PREPARING YOUR WORKSPACE...
        </p>
      </div>
    </motion.div>
  );
}
